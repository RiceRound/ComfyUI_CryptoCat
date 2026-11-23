import{api}from"../../scripts/api.js";import{app}from"../../scripts/app.js";const PREFIX="input_anything"
;const configCommand="CryptoCat.Open";const publisherLoginLabel="发布者登录";const replaceWorkflowLabel="替换已有工作流"
;async function request(path,body){const response=await api.fetchApi(`/cryptocat/${path}`,body===undefined?{}:{
method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)})
;const data=await response.json().catch((error=>{if(response.ok)throw error;return{}}));if(!response.ok){
const error=new Error(data?.error_msg||"CryptoCat 请求失败");error.status=response.status
;error.challengeRequired=data?.challenge_required===true;throw error}return data}
function element(tag,{ariaLabel:ariaLabel,...attributes}={},text=""){const node=document.createElement(tag)
;Object.assign(node,attributes);if(ariaLabel)node.setAttribute("aria-label",ariaLabel);node.textContent=text;return node
}function button(text,onclick,type="button"){return element("button",{type:type,onclick:onclick},text)}
function icon(path){const namespace="http://www.w3.org/2000/svg";const svg=document.createElementNS(namespace,"svg")
;svg.setAttribute("viewBox","0 0 24 24");svg.setAttribute("aria-hidden","true")
;const shape=document.createElementNS(namespace,"path");shape.setAttribute("d",path);svg.append(shape);return svg}
function copyButton(label,input,notice,success){const copy=button(label,(async()=>{try{
await navigator.clipboard.writeText(input.value)}catch{input.focus();input.select();let copied=false;try{
copied=document.execCommand?.("copy")}catch{}if(!copied){notice.textContent="内容已选中，可手动复制。";return}}
notice.textContent=success}));copy.prepend(icon("M9 7V4h11v12h-3M4 8h12v12H4z"));return copy}
function field(form,label,attributes){const input=element("input",attributes);const wrapper=element("label",{},label)
;wrapper.append(input);form.append(wrapper);return input}function dialog(title){const modal=element("dialog",{
className:"cryptocat-dialog",ariaLabel:title});const heading=element("header");const close=element("button",{
type:"button",ariaLabel:"关闭",onclick:()=>modal.close()},"×");heading.append(element("h2",{},title),close)
;const content=element("section");modal.append(heading,content);document.body.append(modal)
;modal.addEventListener("close",(()=>modal.remove()),{once:true});modal.showModal();return{modal:modal,content:content,
close:close}}function showToast(message,level="info"){app.extensionManager.toast.add({severity:level,
summary:"CryptoCat",detail:message,life:6e3})}let settingsModal;let loginModal;let openingLogin=false
;let publisherSignedIn;function setPublisherSignedIn(signedIn){if(publisherSignedIn===signedIn)return
;publisherSignedIn=signedIn;const root=app.rootGraph;for(const graph of[root,...root.subgraphs?.values()??[]]){
for(const node of graph.nodes){if(node.comfyClass!=="SaveCryptoNode")continue
;const login=node.widgets?.find((widget=>widget.name===publisherLoginLabel));if(!login||login.hidden===signedIn)continue
;const previousHeight=node.computeSize()[1];login.hidden=signedIn;const[minWidth,minHeight]=node.computeSize()
;node.setSize([Math.max(node.size[0],minWidth),Math.max(minHeight,node.size[1]+minHeight-previousHeight)])
;node.setDirtyCanvas(true,true)}}}function openLogin(connection,onLogin,useToken){
const{modal:modal,content:content}=dialog("登录 CryptoCat");loginModal=modal;const form=element("form")
;const phone=field(form,"手机号",{type:"tel",autocomplete:"tel",pattern:"1[3-9][0-9]{9}",required:true})
;const captcha=element("div",{hidden:true});const image=element("img",{alt:"图形验证码",width:148,height:50})
;const answer=field(captcha,"图形验证码",{inputMode:"numeric",maxLength:4});const code=field(form,"短信验证码",{
inputMode:"numeric",autocomplete:"one-time-code",pattern:"[0-9]{6}",required:true});const status=element("p",{
role:"status"});const actions=element("div",{className:"cryptocat-actions"});let challengeId;let busy=false
;let cooldownUntil=0;let cooldownPhone;function refresh(){
const seconds=phone.value===cooldownPhone?Math.max(0,Math.ceil((cooldownUntil-Date.now())/1e3)):0
;send.disabled=busy||!phone.validity.valid||seconds>0;send.textContent=seconds?`${seconds} 秒后重发`:"发送验证码"
;submit.disabled=busy;tokenLogin.disabled=busy;reload.disabled=busy;phone.readOnly=busy}async function loadChallenge(){
captcha.hidden=false;image.hidden=true;answer.value="";challengeId=undefined
;const data=await request("login/challenge",{...connection,phone:phone.value});challengeId=data.id
;image.src=`data:image/png;base64,${data.image}`;image.hidden=false}function showLoginError(error){
status.textContent=error.message;tokenLogin.hidden=!(error.status>=500&&error.status<600)}async function run(action){
if(busy||!phone.reportValidity())return;busy=true;refresh();status.textContent="";tokenLogin.hidden=true;try{
if(action==="challenge"){await loadChallenge();return}
if(!captcha.hidden&&(!challengeId||!/^[0-9]{4}$/.test(answer.value.trim()))){status.textContent="请输入图形验证码"
;answer.focus();return}const result=await request(`login/${action}`,{...connection,phone:phone.value,
code:action==="verify"?code.value.trim():undefined,challenge_id:challengeId,challenge_answer:answer.value.trim()})
;if(action==="verify"){onLogin(result);if(modal.open)modal.close();return}cooldownPhone=phone.value
;cooldownUntil=Date.now()+Number(result.retry_after)*1e3
;status.textContent=result.delivery==="internal"?"请联系管理员获取验证码":"短信验证码已发送"
;if(result.challenge_required)await loadChallenge();else captcha.hidden=true}catch(error){showLoginError(error)
;if(action!=="challenge"&&error.challengeRequired){try{await loadChallenge();answer.focus()}catch(failure){
showLoginError(failure)}}}finally{busy=false;refresh()}}const send=button("发送验证码",(()=>run("sms")))
;const submit=button("登录",null,"submit");const reload=button("换一张",(()=>run("challenge")))
;const tokenLogin=button("改用登录 Token",(()=>{modal.close();useToken()}));tokenLogin.hidden=true
;captcha.prepend(image,reload);form.insertBefore(captcha,code.parentElement);actions.append(send,submit)
;form.append(actions,status,tokenLogin);form.addEventListener("submit",(event=>{event.preventDefault();run("verify")}))
;phone.addEventListener("input",(()=>{captcha.hidden=true;challengeId=undefined
;answer.value=code.value=status.textContent="";tokenLogin.hidden=true;refresh()}));const timer=setInterval(refresh,1e3)
;modal.addEventListener("close",(()=>clearInterval(timer)),{once:true});content.append(form);refresh();phone.focus()}
async function openPublisherLogin(connection,{tokenOnly:tokenOnly=false,afterLogin:afterLogin}={}){
if(loginModal?.open||openingLogin)return;openingLogin=true;try{const config=connection??await request("config")
;const settings={url:config.url};const signedIn=result=>{setPublisherSignedIn(result.has_token)
;settingsModal?.dispatchEvent(new CustomEvent("cryptocat:publisher-login",{detail:result}))
;if(afterLogin)queueMicrotask(afterLogin);else showToast("已登录 CryptoCat，可以重新排队发布")};if(!tokenOnly){
openLogin(settings,signedIn,(()=>openPublisherLogin(settings,{tokenOnly:true,afterLogin:afterLogin})));return}
const site=new URL("/plugin/connect",settings.url)
;if(!["https:","http:"].includes(site.protocol))throw new Error("服务地址格式无效")
;const{modal:modal,content:content}=dialog("登录 CryptoCat 发布者");loginModal=modal;const form=element("form")
;const website=element("a",{href:site.href,target:"_blank",rel:"noopener noreferrer",className:"cryptocat-primary"
},"前往网站获取登录 Token");const actions=element("div",{className:"cryptocat-actions"});actions.append(website)
;form.append(element("p",{},"在网站的插件接入页登录后复制 Token，再粘贴到这里。"),actions);const token=field(form,"登录 Token",{type:"password",
required:true,autocomplete:"off"});const submit=button("验证并登录",null,"submit");const status=element("p",{role:"status"})
;form.append(submit,status);form.addEventListener("submit",(async event=>{event.preventDefault();submit.disabled=true
;status.textContent="正在验证…";try{const result=await request("config",{...settings,token:token.value});token.value=""
;signedIn(result);modal.close()}catch(error){status.textContent=error.message}finally{submit.disabled=false}}))
;content.append(form)}catch(error){showToast(error.message,"error")}finally{openingLogin=false}}
async function openSettings(publisher,decodeTemplate){if(settingsModal?.open)return
;const{modal:modal,content:content}=dialog("CryptoCat 设置");modal.classList.add("cryptocat-settings");settingsModal=modal
;content.append(element("p",{role:"status"},"正在读取设置…"));let config;try{config=await request("config")}catch(error){
content.replaceChildren(element("p",{role:"alert"},error.message));return}if(!modal.open)return
;setPublisherSignedIn(config.has_token);content.replaceChildren();const connection=element("div",{
className:"cryptocat-connection"});const address=element("span",{className:"cryptocat-address"})
;const edit=button("✎",editAddress);edit.className="cryptocat-edit-address"
;edit.setAttribute("aria-label",edit.title="编辑服务地址");const addressRow=element("div",{className:"cryptocat-address-row"})
;addressRow.append(address,edit);const status=element("p",{role:"status"})
;connection.prepend(element("span",{},"服务地址"),addressRow);connection.append(status);const account=element("div",{
className:"cryptocat-actions cryptocat-account"});const accountStatus=element("p",{role:"status"})
;const login=button(publisherLoginLabel,(()=>openPublisherLogin(config)));const clear=button("退出发布账号",(async()=>{
await runAction((async()=>{applyConfig(await request("clear",{}));status.textContent="已退出发布账号"}))}))
;const overwrite=publisher?element("input",{type:"checkbox",checked:config.auto_overwrite}):null;let busy=false
;function applyConfig(next){config=next;if(overwrite)overwrite.checked=config.auto_overwrite
;setPublisherSignedIn(config.has_token)}function refresh(){const connected=config.has_token
;address.textContent=config.url;edit.hidden=config.url_locked;accountStatus.textContent=connected?"发布者已登录":"请先登录发布者账号"
;account.classList.toggle("cryptocat-login-required",!connected);login.hidden=connected;clear.hidden=!connected
;login.disabled=clear.disabled=edit.disabled=busy;if(overwrite)overwrite.disabled=busy}
async function runAction(action,notice=status){busy=true;refresh();try{await action();return true}catch(error){
notice.textContent=error.message;return false}finally{busy=false;refresh()}}function editAddress(){
const{modal:editor,content:body,close:close}=dialog("编辑服务地址");const form=element("form");const input=field(form,"服务地址",{
type:"url",value:config.url,placeholder:"https://cryptocat.example.com",required:true,spellcheck:false})
;if(config.has_token)form.append(element("small",{},"更换服务地址后需要重新登录。"));const cancel=button("取消",(()=>editor.close()))
;const confirm=button("确认",null,"submit");confirm.className="cryptocat-primary";const actions=element("div",{
className:"cryptocat-actions"});actions.append(cancel,confirm);const notice=element("p",{role:"status"})
;form.append(actions,notice);body.append(form);input.focus();input.select();editor.addEventListener("cancel",(event=>{
if(busy)event.preventDefault()}));form.addEventListener("submit",(async event=>{event.preventDefault();if(busy)return
;const url=input.value.trim().replace(/\/+$/,"");if(url===config.url){editor.close();return}
input.readOnly=confirm.disabled=cancel.disabled=close.disabled=true;notice.textContent="正在更新…"
;const updated=await runAction((async()=>{applyConfig(await request("config",{url:url}));status.textContent="服务地址已更新"
}),notice);if(updated)editor.close();input.readOnly=confirm.disabled=cancel.disabled=close.disabled=false}))}
modal.addEventListener("cryptocat:publisher-login",(({detail:detail})=>{applyConfig(detail);status.textContent=""
;refresh()}));account.append(accountStatus,login,clear);content.append(element("h3",{},"全局设置"))
;if(publisher||!decodeTemplate)content.append(account);content.append(connection);if(publisher){
const preference=element("label",{className:"cryptocat-overwrite-toggle"})
;preference.append(overwrite,element("span",{},"自动覆盖同 ID 模板"));const preferenceStatus=element("p",{role:"status"})
;overwrite.onchange=async()=>{const auto_overwrite=overwrite.checked;preferenceStatus.textContent=""
;await runAction((async()=>applyConfig(await request("config",{auto_overwrite:auto_overwrite}))),preferenceStatus)
;overwrite.checked=config.auto_overwrite};const workflow=publisherSettings(publisher,modal)
;workflow.append(preference,element("small",{},"此开关适用于当前 ComfyUI 中的所有工作流。"),preferenceStatus);content.append(workflow)}
if(decodeTemplate)content.append(decodeSettings(decodeTemplate.value));refresh()}function decodeSettings(templateId){
const section=element("section",{className:"cryptocat-workflow-settings"});const input=element("input",{type:"text",
id:"cryptocat-template-id",readOnly:true,value:templateId??"",spellcheck:false,placeholder:"未设置模板 ID"})
;const notice=element("p",{role:"status"});const copy=copyButton("",input,notice,"已复制模板 ID。")
;copy.setAttribute("aria-label",copy.title="复制模板 ID");copy.disabled=!input.value;const row=element("div",{
className:"cryptocat-template-row cryptocat-decode-template-row"});row.append(input,copy)
;section.append(element("h3",{},"当前工作流"),element("label",{htmlFor:input.id
},"模板 ID"),row,element("small",{},"可将模板 ID 复制给开发者排查问题。"),notice);return section}
function publisherSettings({node:node,name:name,template:template,sync:sync},modal){const section=element("section",{
className:"cryptocat-workflow-settings"});section.append(element("h3",{},"当前工作流"))
;const nameInput=field(section,"工作流名称",{type:"text",value:publisherName(node,name,template),maxLength:120})
;section.append(element("small",{},"使用默认名称时，替换会保留目标在网站上的名称。"));const templateId=element("input",{
id:"cryptocat-template-id",type:"text",readOnly:true,spellcheck:false});const templateLabel=element("label",{
htmlFor:templateId.id},"模板 ID");const selection=element("p",{role:"status"});function updateTemplate(){sync()
;nameInput.value=publisherName(node,name,template);templateId.value=templateId.title=template.value
;selection.textContent=node.properties?.cryptocat_overwrite?.template_id===template.value?"下次发布将替换所选工作流。":""}
function changeTemplate(id,target){if(!node.graph||!modal.open)return;node.graph.beforeChange?.(node);template.value=id
;if(target)node.properties={...node.properties,cryptocat_overwrite:target
};else delete node.properties?.cryptocat_overwrite;updateTemplate();node.graph.afterChange?.(node)}
const randomize=button("↻",(()=>changeTemplate(randomTemplateId())))
;randomize.setAttribute("aria-label",randomize.title="随机生成模板 ID");const pickTemplate=()=>{if(!modal.open)return
;return chooseOverwrite(template.value,(()=>{setPublisherSignedIn(false);return openPublisherLogin(undefined,{
afterLogin:pickTemplate})}),(target=>changeTemplate(target.template_id,target)))};const replace=button("⇄",pickTemplate)
;replace.setAttribute("aria-label",replace.title=replaceWorkflowLabel);const templateRow=element("div",{
className:"cryptocat-template-row"});templateRow.append(templateId,randomize,replace)
;section.append(templateLabel,templateRow,selection);nameInput.addEventListener("input",(()=>{name.value=nameInput.value
;sync()}));nameInput.addEventListener("change",(()=>node.graph?.afterChange?.(node)))
;nameInput.addEventListener("blur",(()=>{nameInput.value=publisherName(node,name,template)}));updateTemplate()
;return section}async function chooseOverwrite(currentId,onUnauthorized,onSelect){
const{modal:modal,content:content}=dialog(replaceWorkflowLabel);modal.classList.add("cryptocat-overwrite-dialog")
;const notice=element("p",{role:"status"},"正在加载最近发布的工作流…");content.append(notice);try{
const{items:items,url:url}=await request("workflows");if(!modal.open)return;if(!items.length){
notice.textContent="当前账号还没有发布工作流。";return}const form=element("form");const choices=element("fieldset",{
className:"cryptocat-overwrite-choices"});choices.append(element("legend",{},"最近更新的工作流"));const list=element("div",{
className:"cryptocat-overwrite-list"});for(const item of items){const option=element("label")
;const description=element("span",{className:"cryptocat-overwrite-description"});description.append(element("span",{
className:"cryptocat-overwrite-id"},item.template_id));if(item.name)description.append(element("span",{
className:"cryptocat-overwrite-name"},`（${item.name}）`));option.append(element("input",{type:"radio",name:"template_id",
value:item.template_id,required:true,checked:item.template_id===currentId}),description);list.append(option)}
choices.append(list);const actions=element("div",{className:"cryptocat-actions cryptocat-overwrite-actions"})
;const confirm=button("选为替换目标",null,"submit");confirm.className="cryptocat-overwrite-confirm"
;confirm.disabled=!items.some((item=>item.template_id===currentId));choices.addEventListener("change",(()=>{
confirm.disabled=false}));actions.append(button("取消",(()=>modal.close())),confirm);form.append(choices,actions)
;notice.textContent="";content.append(form);form.addEventListener("submit",(event=>{event.preventDefault()
;const value=new FormData(form).get("template_id")
;const item=items.find((({template_id:template_id})=>template_id===value));if(!item)return;onSelect({
template_id:item.template_id,user_id:item.user_id,url:url,name:item.name});modal.close()}))}catch(error){
if(!modal.open)return;if(error.status===401){modal.close();await onUnauthorized()}else{notice.textContent=error.message}
}}api.addEventListener("cryptocat_toast",(({detail:detail})=>showToast(detail.message,detail.level)))
;api.addEventListener("cryptocat_published",(({detail:detail})=>{const{modal:modal,content:content}=dialog("工作流已发布")
;modal.classList.add("cryptocat-published");const check=element("span",{className:"cryptocat-published-check"})
;check.append(icon("M5 12l4 4L19 6"));modal.querySelector("h2").prepend(check);const file=element("div",{
className:"cryptocat-published-file"});file.append(element("span",{},"已保存文件"),element("strong",{},detail.filename))
;if(detail.output_dir){const path=element("input",{type:"text",readOnly:true,value:detail.output_dir,ariaLabel:"输出目录"})
;const notice=element("p",{role:"status"});const copy=copyButton("复制路径",path,notice,"已复制输出目录。")
;const pathRow=element("div",{className:"cryptocat-published-path"});pathRow.append(path,copy)
;file.append(element("span",{},"输出目录"),pathRow,notice)}const website=element("a",{href:detail.serials_url,
target:"_blank",rel:"noopener noreferrer",className:"cryptocat-published-link"},"前往网站生成序列号")
;website.append(icon("M14 5h5v5m0-5-8 8m7 0v6H5V6h6"));const actions=element("div",{className:"cryptocat-actions"})
;actions.append(website);content.append(file,element("p",{className:"cryptocat-published-guide"
},"在 CryptoCat 网站使用发布该工作流的账号登录后，可以生成序列号。"),actions)}));api.addEventListener("cryptocat_login_required",(()=>{
setPublisherSignedIn(false);openPublisherLogin()}));api.addEventListener("execution_error",(({detail:detail})=>{
if(detail?.node_type!=="DecodeCryptoNode"||!detail.exception_type?.endsWith(".MissingSerialNumber"))return
;const{modal:modal,content:content}=dialog("缺少序列号");const actions=element("div",{className:"cryptocat-actions"})
;actions.append(button("知道了",(()=>modal.close())))
;content.append(element("p",{},`解密组件（节点 ${detail.node_id}）这次没有收到序列号，工作流未解密。`),element("p",{},"请把该工作流的序列号粘贴到画布上解密组件的「请输入序列号」框，再重新排队。"),actions)
}));api.addEventListener("cryptocat_dialog",(({detail:detail})=>{const{modal:modal,content:content}=dialog("覆盖工作流")
;content.append(element("p",{},`模板 ${detail.template_id} 已存在。是否发布新版本？`));const actions=element("div",{
className:"cryptocat-actions"})
;actions.append(button("取消",(()=>modal.close("cancel"))),button("覆盖",(()=>modal.close("confirm"))))
;content.append(actions);const timer=window.setTimeout((()=>modal.close("cancel")),48e3)
;modal.addEventListener("close",(async()=>{window.clearTimeout(timer);try{await request("message",{id:detail.id,
client_id:api.clientId,confirmed:modal.returnValue==="confirm"})}catch(error){showToast(error.message,"error")}}),{
once:true})}));function ensureInput(node){const slots=(node.inputs??[]).filter((input=>input.name.startsWith(PREFIX)))
;if(slots.some((slot=>slot.link==null)))return;let index=0
;while(slots.some((slot=>slot.name===(index?`${PREFIX}${index}`:PREFIX))))index++
;node.addInput(index?`${PREFIX}${index}`:PREFIX,"*")}function randomTemplateId(){
return Array.from(crypto.getRandomValues(new Uint8Array(16)),(byte=>byte.toString(16).padStart(2,"0"))).join("")}
function workflowTitle(){const workflow=app.extensionManager?.workflow?.activeWorkflow
;const title=[workflow?.title,workflow?.filename].find((value=>typeof value==="string"&&value.trim()))
;return title?.trim().replace(/\.json$/i,"").trim()}function publisherName(node,name,template){
const custom=typeof name.value==="string"?name.value.trim():"";const target=node.properties?.cryptocat_overwrite
;const targetName=template&&target?.template_id===template.value&&typeof target.name==="string"?target.name:""
;return custom||targetName||workflowTitle()||node.properties?.cryptocat_workflow_title||"未命名工作流"}
function bindPublisherNode(node){const template=node.widgets?.find((widget=>widget.name==="template_id"))
;const name=node.widgets?.find((widget=>widget.name==="workflow_name"));if(!template||!name)return
;template.hidden=name.hidden=true;template.options.hidden=name.options.hidden=true;function readOnlyText(label){
const widget=node.addWidget("text",label,"",null,{read_only:true,serialize:false});widget.serialize=false
;widget.onClick=()=>{};widget.mouse=()=>false;return widget}const displayedName=readOnlyText("工作流名称")
;const displayedTemplate=readOnlyText("模板 ID");function sync(){const title=publisherName(node,name,template)
;if(displayedName.value===title&&displayedTemplate.value===template.value)return;displayedName.value=title
;displayedTemplate.value=template.value;node.setDirtyCanvas(true,true)}function configure(){
if(typeof name.value!=="string")name.value=""
;if(typeof template.value!=="string"||!/^[0-9a-f]{32}$/i.test(template.value)){template.value=randomTemplateId()
;delete node.properties?.cryptocat_overwrite}sync();requestAnimationFrame(sync)}const onConfigure=node.onConfigure
;node.onConfigure=function(...args){onConfigure?.apply(this,args);configure()};const onSerialize=node.onSerialize
;node.onSerialize=function(data){onSerialize?.call(this,data);sync()};configure();return{node:node,name:name,
template:template,sync:sync}}app.registerExtension({name:"CryptoCat",commands:[{id:configCommand,label:"CryptoCat",
function:()=>openSettings()}],menuCommands:[{path:["Extensions"],commands:[configCommand]}],setup(){
document.head.append(element("link",{rel:"stylesheet",href:new URL("./cryptocat.css",import.meta.url).href}))
;request("config").catch((()=>null)).then((config=>{
if(publisherSignedIn===undefined)setPublisherSignedIn(config?.has_token??false)}))},
beforeRegisterNodeDef(nodeType,nodeData){if(nodeData.name!=="SaveCryptoNode")return
;const onSerialize=nodeType.prototype.onSerialize;nodeType.prototype.onSerialize=function(data){
onSerialize?.call(this,data);const title=workflowTitle();if(title)data.properties={...data.properties,
cryptocat_workflow_title:title}};const onConnectionsChange=nodeType.prototype.onConnectionsChange
;nodeType.prototype.onConnectionsChange=function(type,slot,connected,link,io){
const result=onConnectionsChange?.call(this,type,slot,connected,link,io)
;if(type===1&&connected&&!app.configuringGraph)ensureInput(this);return result}},nodeCreated(node){
if(node.comfyClass!=="SaveCryptoNode"&&node.comfyClass!=="DecodeCryptoNode")return;let publisher;let decodeTemplate
;if(node.comfyClass==="SaveCryptoNode"){publisher=bindPublisherNode(node)
;const login=node.addWidget("button",publisherLoginLabel,null,(()=>openPublisherLogin()),{serialize:false,
hidden:publisherSignedIn!==false});login.serialize=false}else{
decodeTemplate=node.widgets?.find((widget=>widget.name==="template_id"))
;if(decodeTemplate)decodeTemplate.hidden=decodeTemplate.options.hidden=true
;const serialInput=node.widgets?.find((widget=>widget.name==="serial_number"))?.element
;if(serialInput&&node.innerFontStyle){serialInput.style.font=node.innerFontStyle}}
const settings=node.addWidget("button","CryptoCat 设置",null,(()=>openSettings(publisher,decodeTemplate)),{serialize:false
});settings.serialize=false}});

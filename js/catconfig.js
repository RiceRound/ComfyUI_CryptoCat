import{api}from"../../../scripts/api.js";import{ComfyApp,app}from"../../../scripts/app.js";export const UserTokenKey="cryptocat_user_token";async function showKeygenMessageBox(e){const t=document.createElement("div");t.style.position="fixed",t.style.top="0",t.style.left="0",t.style.width="100%",t.style.height="100%",t.style.backgroundColor="rgba(0, 0, 0, 0.5)",t.style.zIndex="9999",t.style.display="flex",t.style.justifyContent="center",t.style.alignItems="center";const o=document.createElement("div");o.style.backgroundColor="#fff",o.style.padding="20px",o.style.borderRadius="10px",o.style.width="400px",o.style.boxShadow="0 4px 8px rgba(0, 0, 0, 0.2)",o.style.display="flex",o.style.flexDirection="column",o.style.alignItems="center";const n=document.createElement("h2");n.innerText=e,n.style.color="#333",n.style.marginBottom="20px",o.appendChild(n);const r=document.createElement("input");r.type="text",r.placeholder="请输入template_id",r.style.width="100%",r.style.padding="10px",r.style.marginBottom="20px",r.style.border="1px solid #ccc",r.style.borderRadius="4px",r.style.fontSize="16px",o.appendChild(r);const s=document.createElement("div");s.style.marginBottom="20px",s.style.width="100%",s.style.backgroundColor="#f9f9f9",s.style.border="1px solid #ddd",s.style.borderRadius="4px",s.style.padding="10px",s.style.fontSize="14px",s.style.color="#333",s.style.wordWrap="break-word",s.style.wordBreak="break-all",s.style.minHeight="50px",s.innerText="生成的序列号: ",o.appendChild(s);const i=document.createElement("button");function a(e){i.disabled=e,i.innerText=e?"生成中...":"生成序列号",e&&(s.innerText="正在获取序列号...")}i.innerText="生成序列号",i.style.padding="10px 20px",i.style.border="none",i.style.backgroundColor="#4CAF50",i.style.color="white",i.style.borderRadius="4px",i.style.cursor="pointer",i.style.fontSize="16px",i.style.alignSelf="center",i.addEventListener("click",(async()=>{a(!0);try{const e=r.value.trim(),t=await async function(e){try{const t=await api.fetchApi("/cryptocat/keygen",{method:"POST",body:JSON.stringify({template_id:e})}),o=await t.json();if(!t.ok)throw new Error(o.error_msg||`HTTP error! status: ${t.status}`);return o.serial_number||o.error_msg||"获取失败：服务器返回数据格式错误"}catch(e){throw new Error(`获取序列号失败: ${e.message}`)}}(e);s.innerText=`${t}`}catch(e){s.innerText=`发生错误: ${e.message||"未知错误"}`}finally{a(!1)}})),o.appendChild(i),t.appendChild(o),document.body.appendChild(t),t.addEventListener("click",(function(e){e.target===t&&t.remove()}))}function isValidJWTFormat(e){if("string"!=typeof e)return!1;if(e.length<50)return!1;const t=e.split(".");if(3!==t.length)return!1;const o=/^[A-Za-z0-9_-]+$/;return t.every((e=>e.length>0&&o.test(e)))}app.registerExtension({name:"CryptoCat.config",async setup(){app.ui.settings.addSetting({id:"CryptoCat.Keygen.name",name:"输入template_id，计算序列号，序列号有效期7天",type:()=>{const e=document.createElement("tr"),t=document.createElement("td"),o=document.createElement("input");return o.type="button",o.value="算号器",o.style.borderRadius="8px",o.style.padding="8px 16px",o.style.fontSize="14px",o.style.cursor="pointer",o.style.border="1px solid #666",o.style.backgroundColor="#444",o.style.color="#fff",o.onmouseover=()=>{o.style.backgroundColor="#555"},o.onmouseout=()=>{o.style.backgroundColor="#444"},o.onclick=()=>{showKeygenMessageBox("算号器","算号器","question")},t.appendChild(o),e.appendChild(t),e}}),app.ui.settings.addSetting({id:"CryptoCat.User.logout",name:"登出当前用户",type:()=>{const e=document.createElement("tr"),t=document.createElement("td"),o=document.createElement("input");return o.type="button",o.value="登出",o.style.borderRadius="8px",o.style.padding="8px 16px",o.style.fontSize="14px",o.style.cursor="pointer",o.style.border="1px solid #666",o.style.backgroundColor="#444",o.style.color="#fff",o.onclick=async()=>{localStorage.setItem(UserTokenKey,""),window.clearUserInfo(),await api.fetchApi("/cryptocat/logout")},t.appendChild(o),e.appendChild(t),e}}),app.ui.settings.addSetting({id:"CryptoCat.User.long_token",name:"设置长效token",type:"text",textType:"password",defaultValue:"",tooltip:"用于非本机授权登录情况，请勿泄露！提倡使用本机登录授权更安全！",onChange:async function(e){isValidJWTFormat(e)&&await api.fetchApi("/cryptocat/set_long_token",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({long_token:e})})}}),app.ui.settings.addSetting({id:"CryptoCat.Setting.auto_overwrite",name:"自动覆盖更新同id工作流",type:"boolean",defaultValue:!1,tooltip:"设置为true时，会自动覆盖已有的template_id的数据",onChange:function(e){api.fetchApi("/cryptocat/set_auto_overwrite",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({auto_overwrite:e})})}})}});
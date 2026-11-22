import { api } from "../../scripts/api.js";
import { app } from "../../scripts/app.js";

const PREFIX = "input_anything";
const configCommand = "CryptoCat.Open";

async function request(path, body) {
    const response = await api.fetchApi(`/cryptocat/${path}`, body === undefined ? {} : {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error_msg || "CryptoCat 请求失败");
    return data;
}

function element(tag, attributes = {}, text = "") {
    const node = document.createElement(tag);
    Object.assign(node, attributes);
    node.textContent = text;
    return node;
}

function button(text, onclick, type = "button") {
    return element("button", { type, onclick }, text);
}

function field(form, label, attributes) {
    const input = element("input", attributes);
    const wrapper = element("label", {}, label);
    wrapper.append(input);
    form.append(wrapper);
    return input;
}

function dialog(title) {
    const modal = element("dialog", { className: "cryptocat-dialog", ariaLabel: title });
    const heading = element("header");
    heading.append(element("h2", {}, title), element("button", {
        type: "button", ariaLabel: "关闭", onclick: () => modal.close(),
    }, "×"));
    const content = element("section");
    modal.append(heading, content);
    document.body.append(modal);
    modal.addEventListener("close", () => modal.remove(), { once: true });
    modal.showModal();
    return { modal, content };
}

function showToast(message, level = "info") {
    app.extensionManager.toast.add({ severity: level, summary: "CryptoCat", detail: message, life: 6000 });
}

async function copyText(text, input, notice) {
    try {
        await navigator.clipboard.writeText(text);
        notice.textContent = "已复制";
    } catch {
        input.focus();
        input.select();
        notice.textContent = "已选中，请按 Ctrl+C 或 ⌘C 复制";
    }
}

let settingsModal;

async function openSettings(templateId = "") {
    if (settingsModal?.open) return;
    const { modal, content } = dialog("CryptoCat");
    settingsModal = modal;
    content.append(element("p", { role: "status" }, "正在读取设置…"));
    let config;
    try {
        config = await request("config");
    } catch (error) {
        content.replaceChildren(element("p", { role: "alert" }, error.message));
        return;
    }
    if (!modal.open) return;
    content.replaceChildren();
    const form = element("form");
    const url = field(form, "服务地址", {
        type: "url", value: config.url, placeholder: "https://cryptocat.example.com",
        required: true, readOnly: config.url_locked,
    });
    const portal = element("a", { target: "_blank", rel: "noopener noreferrer" }, "打开服务端插件接入页");
    const token = field(form, "发布 Token", { type: "password", autocomplete: "off", spellcheck: false });
    const overwrite = field(form, "自动覆盖我的同 ID 模板", { type: "checkbox", checked: config.auto_overwrite });
    const status = element("p", { role: "status" });
    const actions = element("div", { className: "cryptocat-actions" });
    const save = button("保存连接", null, "submit");
    const clear = button("移除 Token", async () => {
        await runConnectionAction(async () => {
            config = await request("clear", {});
            status.textContent = "发布 Token 已移除";
        });
    });

    function refresh() {
        let href = "";
        try {
            const entered = new URL(url.value);
            if (["https:", "http:"].includes(entered.protocol) && !entered.username && !entered.password) {
                href = `${entered.origin}/plugin`;
            }
        } catch { /* The address is still being entered. */ }
        portal.hidden = !href;
        if (href) portal.href = href;
        token.placeholder = config.has_token && url.value.trim().replace(/\/+$/, "") === config.url
            ? "已保存。输入新 Token 可替换" : "激活工作流可留空";
        clear.disabled = !config.has_token;
        keygen.disabled = !config.has_token;
    }

    async function runConnectionAction(action) {
        save.disabled = clear.disabled = true;
        try {
            await action();
        } catch (error) {
            status.textContent = error.message;
        } finally {
            save.disabled = false;
            refresh();
        }
    }

    url.addEventListener("input", refresh);
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        status.textContent = "正在保存…";
        await runConnectionAction(async () => {
            config = await request("config", { url: url.value, token: token.value, auto_overwrite: overwrite.checked });
            url.value = config.url;
            token.value = "";
            status.textContent = config.publisher ? `已连接，发布者 ID ${config.publisher}` : "服务地址已保存";
        });
    });
    actions.append(save, clear);
    form.append(actions, portal, status);
    content.append(form, element("hr"), element("h3", {}, "生成序列号"));

    const serialForm = element("form");
    const template = field(serialForm, "模板 ID", {
        value: templateId, required: true, pattern: "[0-9a-fA-F]{32}", maxLength: 32, spellcheck: false,
    });
    const details = element("div", { className: "cryptocat-fields" });
    const expiry = field(details, "失效日期（UTC）", { type: "date" });
    const days = field(details, "激活后天数（0 为不限）", { type: "number", value: "0", min: "0", max: "365", required: true });
    const count = field(details, "数量", { type: "number", value: "1", min: "1", max: "10", required: true });
    serialForm.append(details);
    const keygen = button("生成序列号", null, "submit");
    const copy = button("复制全部", () => copyText(result.value, result, serialNotice));
    copy.hidden = true;
    const serialActions = element("div", { className: "cryptocat-actions" });
    serialActions.append(keygen, copy);
    const serialNotice = element("p", { role: "status" });
    const result = element("textarea", { rows: 4, readOnly: true, hidden: true, ariaLabel: "生成的序列号" });
    serialForm.append(serialActions, serialNotice, result);
    serialForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        keygen.disabled = true;
        result.value = "";
        result.hidden = copy.hidden = true;
        serialNotice.textContent = "正在生成…";
        try {
            const data = await request("keygen", {
                template_id: template.value.trim(), count: count.valueAsNumber,
                use_days: days.valueAsNumber, expire_date: expiry.value,
            });
            result.value = data.serial_numbers.join("\n");
            result.hidden = copy.hidden = false;
            serialNotice.textContent = `已生成 ${data.serial_numbers.length} 个序列号`;
        } catch (error) {
            serialNotice.textContent = error.message;
        } finally {
            keygen.disabled = !config.has_token;
        }
    });
    content.append(serialForm);
    refresh();
}

api.addEventListener("cryptocat_toast", ({ detail }) => showToast(detail.message, detail.level));
api.addEventListener("cryptocat_dialog", ({ detail }) => {
    const { modal, content } = dialog("覆盖工作流");
    content.append(element("p", {}, `模板 ${detail.template_id} 已存在。是否发布新版本？`));
    const actions = element("div", { className: "cryptocat-actions" });
    actions.append(button("取消", () => modal.close("cancel")), button("覆盖", () => modal.close("confirm")));
    content.append(actions);
    const timer = window.setTimeout(() => modal.close("cancel"), 48000);
    modal.addEventListener("close", async () => {
        window.clearTimeout(timer);
        try {
            await request("message", { id: detail.id, client_id: api.clientId, confirmed: modal.returnValue === "confirm" });
        } catch (error) {
            showToast(error.message, "error");
        }
    }, { once: true });
});

function ensureInput(node) {
    const slots = (node.inputs ?? []).filter((input) => input.name.startsWith(PREFIX));
    if (slots.some((slot) => slot.link == null)) return;
    let index = 0;
    while (slots.some((slot) => slot.name === (index ? `${PREFIX}${index}` : PREFIX))) index++;
    node.addInput(index ? `${PREFIX}${index}` : PREFIX, "*");
}

app.registerExtension({
    name: "CryptoCat",
    commands: [{ id: configCommand, label: "CryptoCat", function: () => openSettings() }],
    menuCommands: [{ path: ["Extensions"], commands: [configCommand] }],
    setup() {
        document.head.append(element("link", { rel: "stylesheet", href: new URL("./cryptocat.css", import.meta.url).href }));
    },
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "SaveCryptoNode") return;
        const onConnectionsChange = nodeType.prototype.onConnectionsChange;
        nodeType.prototype.onConnectionsChange = function (type, slot, connected, link, io) {
            const result = onConnectionsChange?.call(this, type, slot, connected, link, io);
            if (type === 1 && connected && !app.configuringGraph) ensureInput(this);
            return result;
        };
    },
    nodeCreated(node) {
        if (node.comfyClass !== "SaveCryptoNode" && node.comfyClass !== "DecodeCryptoNode") return;
        const template = node.widgets?.find((widget) => widget.name === "template_id");
        node.addWidget("button", "CryptoCat 设置", null, () => openSettings(template?.value), { serialize: false });
        if (node.comfyClass !== "SaveCryptoNode" || !template) return;
        const generate = () => {
            template.value = Array.from(crypto.getRandomValues(new Uint8Array(16)), (byte) =>
                byte.toString(16).padStart(2, "0")).join("");
            node.setDirtyCanvas(true, true);
        };
        node.addWidget("button", "新建模板 ID", null, generate, { serialize: false });
        if (!template.value) generate();
    },
});

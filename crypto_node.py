import json
from pathlib import Path
import random
from threading import Event, Lock
import uuid

from comfy_execution.graph_utils import GraphBuilder, is_link
import folder_paths
from server import PromptServer

from .client import CryptoCatClient, ServiceError, validate_template_id
from .settings import auto_overwrite, connection, read_settings
from .workflow import external_input, package_workflow


class DynamicInputs(dict):
    def __init__(self, *, lazy=False):
        self.options = ("*", {"rawLink": True, "lazy": lazy})
        super().__init__(input_anything=self.options)

    def __contains__(self, name):
        return external_input(name)

    def __getitem__(self, name):
        if name in self:
            return self.options
        raise KeyError(name)


class OverwriteDialogs:
    pending = {}
    lock = Lock()

    @classmethod
    def respond(cls, dialog_id, client_id, confirmed):
        with cls.lock:
            dialog = cls.pending.get(dialog_id)
            if not dialog or dialog["client_id"] != client_id or dialog["ready"].is_set():
                return False
            dialog["confirmed"] = confirmed
            dialog["ready"].set()
            return True

    @classmethod
    def confirm(cls, template_id):
        server = PromptServer.instance
        if not server.client_id:
            raise ValueError("模板已存在。请从画布确认覆盖，或在 CryptoCat 面板启用自动覆盖")
        dialog_id = uuid.uuid4().hex
        dialog = {"client_id": server.client_id, "ready": Event(), "confirmed": False}
        with cls.lock:
            cls.pending[dialog_id] = dialog
        try:
            server.send_sync("cryptocat_dialog", {"id": dialog_id, "template_id": template_id},
                             dialog["client_id"])
            dialog["ready"].wait(50)
            return dialog["confirmed"]
        finally:
            with cls.lock:
                cls.pending.pop(dialog_id, None)


def notify(message, level="info"):
    server = PromptServer.instance
    if server.client_id:
        server.send_sync("cryptocat_toast", {"message": message, "level": level}, server.client_id)


class SaveCryptoNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {"template_id": ("STRING", {"default": ""})},
            "optional": DynamicInputs(lazy=True),
            "hidden": {"unique_id": "UNIQUE_ID", "prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ()
    OUTPUT_NODE = True
    FUNCTION = "publish"
    CATEGORY = "advanced/CryptoCat"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    @classmethod
    def VALIDATE_INPUTS(cls, input_types):
        return True

    def publish(self, template_id, unique_id, prompt, extra_pnginfo, **kwargs):
        validate_template_id(template_id)
        payload, shell = package_workflow((extra_pnginfo or {}).get("workflow"), prompt, unique_id, template_id)
        config = read_settings()
        client = CryptoCatClient(*connection(config))
        exists = client.check(template_id)
        if exists and not auto_overwrite(config) and not OverwriteDialogs.confirm(template_id):
            notify("已取消覆盖工作流")
            return ()
        client.publish(template_id, json.dumps(payload, ensure_ascii=False).encode("utf-8"), replace=exists)
        output = Path(folder_paths.get_output_directory())
        output.mkdir(parents=True, exist_ok=True)
        shell_filename = f"cryptocat_{template_id}.json"
        (output / shell_filename).write_text(json.dumps(shell, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            serials = client.issue_serials(template_id, count=10)
        except ServiceError:
            notify(f"已发布并保存 {shell_filename}。自动发码失败，可在 CryptoCat 面板重新发码", "warn")
            return ()
        serial_file = output / f"serial_numbers_{template_id}.txt"
        serial_file.write_text("\n".join(serials) + "\n", encoding="utf-8")
        notify(f"已发布工作流。请在输出目录查看 {shell_filename} 和 {serial_file.name}")
        return ()


class SaveCryptoBridgeNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"value": ("*",)}}

    RETURN_TYPES = ("*",)
    RETURN_NAMES = ("value",)
    FUNCTION = "forward"
    CATEGORY = "advanced/CryptoCat"

    @classmethod
    def VALIDATE_INPUTS(cls, input_types):
        return True

    def forward(self, value):
        return (value,)


class DecodeCryptoNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "template_id": ("STRING",),
                "serial_number": ("STRING", {"multiline": True, "placeholder": "请输入序列号"}),
            },
            "optional": DynamicInputs(),
            "hidden": {"unique_id": "UNIQUE_ID", "prompt": "PROMPT"},
        }

    RETURN_TYPES = ("*",)
    RETURN_NAMES = ("value",)
    FUNCTION = "decode"
    CATEGORY = "advanced/CryptoCat"

    @classmethod
    def VALIDATE_INPUTS(cls, input_types):
        return True

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def decode(self, template_id, serial_number, unique_id, prompt, **kwargs):
        validate_template_id(template_id)
        serial = serial_number.strip()
        if not serial:
            raise ValueError("请输入序列号")
        client = CryptoCatClient(*connection(read_settings()))
        payload = json.loads(client.download(template_id, serial))
        if not isinstance(payload, dict) or not isinstance(payload.get("prompt"), dict) or not isinstance(payload.get("outputs"), list):
            raise ValueError("加密工作流格式无效")
        original_inputs = payload.get("inputs")
        legacy = original_inputs is None
        if original_inputs is None:
            original_inputs = prompt.get(unique_id, {}).get("inputs", {})
        if not isinstance(original_inputs, dict):
            raise ValueError("加密工作流的公开输入格式无效")
        external = {}
        for name, link in original_inputs.items():
            if external_input(name) and is_link(link):
                external.setdefault(tuple(link), name)
        graph = GraphBuilder()
        private = payload["prompt"]
        for node_id, node in private.items():
            graph.node(node["class_type"], node_id)

        def resolve(link, *, skip_missing=False):
            target, slot = link
            index = int(slot)
            source = graph.lookup_node(target)
            if source is not None:
                return source.out(index)
            name = external.get((target, index))
            if name in kwargs:
                return kwargs[name]
            if skip_missing and name is None:
                return None
            raise ValueError(f"请连接解密组件的公开输入 {name or target}")

        for node_id, node in private.items():
            expanded = graph.lookup_node(node_id)
            for name, value in node["inputs"].items():
                if is_link(value) or (legacy and isinstance(value, list) and len(value) == 2
                                      and isinstance(value[0], str) and isinstance(value[1], str)
                                      and value[1].isdigit()):
                    value = resolve(value, skip_missing=legacy)
                    if value is None:
                        continue
                expanded.inputs[name] = value
        return {"result": (resolve(payload["outputs"]),), "expand": graph.finalize()}


class RandomSeedNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {}}

    RETURN_TYPES = ("INT",)
    FUNCTION = "random"
    CATEGORY = "advanced/CryptoCat"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def random(self):
        return (random.randint(0, 999999),)

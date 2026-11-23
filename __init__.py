import asyncio
import os
import random

from aiohttp import web
from server import PromptServer

from .client import CryptoCatClient, ServiceError, web_login
from .crypto_node import DecodeCryptoNode, OverwriteDialogs, RandomSeedNode, SaveCryptoBridgeNode, SaveCryptoNode
from .crypto_node_old import CryptoCatImage, ExcuteCryptoNode
from .file_compressor import FileCompressor
from .settings import auto_overwrite, clear_token, connection, normalize_url, read_settings, save_auto_overwrite, save_connection
from .workflow import SAVE


NODE_CLASS_MAPPINGS = {
    "SaveCryptoNode": SaveCryptoNode,
    "SaveCryptoBridgeNode": SaveCryptoBridgeNode,
    "DecodeCryptoNode": DecodeCryptoNode,
    "RandomSeedNode": RandomSeedNode,
    "ExcuteCryptoNode": ExcuteCryptoNode,
    "CryptoCatImage": CryptoCatImage,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SaveCryptoNode": "加密组件",
    "SaveCryptoBridgeNode": "加密结束桥接",
    "DecodeCryptoNode": "解密组件",
    "RandomSeedNode": "随机种子",
    "ExcuteCryptoNode": "OutputCrypto",
    "CryptoCatImage": "CryptoCatImage",
}
WEB_DIRECTORY = "./js"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]


def prepare_prompt(data):
    prompt = data.get("prompt") or {}
    publishers = [node_id for node_id, node in prompt.items() if node.get("class_type") == SAVE]
    if publishers:
        if "partial_execution_targets" not in data:
            data["partial_execution_targets"] = publishers
        return data
    for node_id, node in list(prompt.items()):
        if node.get("class_type") != "ExcuteCryptoNode":
            continue
        injected = FileCompressor.decompress_from_json(node["inputs"]["crypto_file_path"], "19040822")
        if not injected:
            raise ValueError("无法读取旧版 CryptoCat 工作流文件")
        output = injected.pop("output_images_ids")
        del prompt[node_id]
        for item in prompt.values():
            if item["class_type"] == "CryptoCatImage" and item["inputs"].get("images", [None])[0] == node_id:
                item["inputs"]["images"] = output
        for item in injected.values():
            if item.get("class_type") == "RandomSeedNode":
                item["inputs"]["is_changed"] = random.randint(0, 999999)
        prompt.update(injected)
        break
    return data


server = PromptServer.instance
server.add_on_prompt_handler(prepare_prompt)
routes = server.routes


def reply(payload, status=200):
    return web.json_response(payload, status=status, headers={"Cache-Control": "no-store"})


def failure(exc):
    return reply({"error_msg": str(exc)}, exc.status if isinstance(exc, ServiceError) else 400)


def check_request_origin(request):
    fetch_site = request.headers.get("Sec-Fetch-Site")
    origin = request.headers.get("Origin")
    # Browsers set same-origin for requests made through the public reverse-proxy URL.
    if fetch_site in {"cross-site", "same-site"} or (
        origin is not None and fetch_site != "same-origin" and origin != f"{request.scheme}://{request.host}"
    ):
        raise ServiceError("请求来源无效", 403)


async def read_json(request):
    check_request_origin(request)
    if request.content_type != "application/json":
        raise ServiceError("请提交 JSON 请求", 415)
    data = await request.json()
    if not isinstance(data, dict):
        raise ValueError("请求格式无效")
    return data


def status():
    config = read_settings()
    url, token = connection(config)
    return {"url": url, "url_locked": bool(os.environ.get("CRYPTOCAT_API_URL", "").strip()),
            "has_token": bool(token), "auto_overwrite": auto_overwrite(config)}


@routes.get("/cryptocat/config")
async def get_config(request):
    try:
        return reply(status())
    except ValueError as exc:
        return failure(exc)


@routes.post("/cryptocat/config")
async def configure(request):
    try:
        data = await read_json(request)
        url, token, overwrite = data.get("url"), data.get("token", ""), data.get("auto_overwrite")
        if "auto_overwrite" in data and not isinstance(overwrite, bool):
            raise ValueError("覆盖选项必须为布尔值")
        if data.keys() == {"auto_overwrite"}:
            save_auto_overwrite(overwrite)
            return reply(status())
        if not isinstance(url, str) or not isinstance(token, str):
            raise ValueError("请检查服务地址、登录 Token 和覆盖选项")
        token = token.strip()
        if len(token) > 4096 or any(char.isspace() for char in token):
            raise ValueError("登录 Token 格式无效")
        url = normalize_url(url)
        current = read_settings()
        current_url, current_token = connection(current)
        if status()["url_locked"] and url != current_url:
            raise ValueError("当前服务地址由 CRYPTOCAT_API_URL 指定")
        if not token and url == current_url:
            token = current_token
        publisher = await asyncio.to_thread(CryptoCatClient(url, token).publisher) if token else None
        save_connection(url, token, overwrite)
        return reply({**status(), "publisher": publisher})
    except ValueError as exc:
        return failure(exc)


@routes.post("/cryptocat/clear")
async def logout(request):
    try:
        await read_json(request)
        clear_token()
        return reply(status())
    except ValueError as exc:
        return failure(exc)


@routes.post("/cryptocat/login/{action:challenge|sms|verify}")
async def login(request):
    try:
        data = await read_json(request)
        action = request.match_info["action"]
        url, overwrite = data.get("url"), data.get("auto_overwrite")
        if not isinstance(url, str) or ("auto_overwrite" in data and not isinstance(overwrite, bool)):
            raise ValueError("请检查服务地址和覆盖选项")
        url = normalize_url(url)
        current = status()
        if current["url_locked"] and current["url"] != url:
            raise ValueError("当前服务地址由 CRYPTOCAT_API_URL 指定")
        fields = ("phone", "code", "challenge_id", "challenge_answer")
        payload = {key: data[key] for key in fields if key in data}
        result, code = await asyncio.to_thread(web_login, url, action, payload)
        if code != 200 or action != "verify":
            return reply(result, code)
        token = result.get("token")
        if not isinstance(token, str) or not token or len(token) > 4096 or any(char.isspace() for char in token):
            raise ServiceError("登录服务未返回有效的登录 Token", 502)
        publisher = await asyncio.to_thread(CryptoCatClient(url, token).publisher)
        save_connection(url, token, overwrite)
        return reply({**status(), "publisher": publisher, "phone": result.get("phone")})
    except ValueError as exc:
        return failure(exc)


@routes.get("/cryptocat/workflows")
async def workflows(request):
    try:
        check_request_origin(request)
        client = CryptoCatClient(*connection(read_settings()))
        items = await asyncio.to_thread(client.recent_workflows)
        return reply({"items": items, "url": client.url})
    except ValueError as exc:
        return failure(exc)


@routes.post("/cryptocat/message")
async def overwrite_reply(request):
    try:
        data = await read_json(request)
        if (not isinstance(data.get("id"), str) or not isinstance(data.get("client_id"), str)
                or not isinstance(data.get("confirmed"), bool)):
            raise ValueError("覆盖确认数据无效")
        accepted = OverwriteDialogs.respond(data["id"], data["client_id"], data["confirmed"])
        return reply({"accepted": accepted}, 200 if accepted else 409)
    except ValueError as exc:
        return failure(exc)

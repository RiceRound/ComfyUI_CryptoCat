from functools import partial, wraps
import os
from .trim_workflow import WorkflowTrimHandler
from .crypto_node import (
    SaveCryptoNode,
    RandomSeedNode,
    SaveCryptoBridgeNode,
    DecodeCryptoNode,
)
from .crypto_node_old import ExcuteCryptoNode, CryptoCatImage

NODE_CLASS_MAPPINGS = {
    "SaveCryptoNode": SaveCryptoNode,
    "ExcuteCryptoNode": ExcuteCryptoNode,
    "RandomSeedNode": RandomSeedNode,
    "CryptoCatImage": CryptoCatImage,
    "SaveCryptoBridgeNode": SaveCryptoBridgeNode,
    "DecodeCryptoNode": DecodeCryptoNode,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SaveCryptoNode": "加密组件",
    "RandomSeedNode": "随机种子",
    "SaveCryptoBridgeNode": "加密结束桥接",
    "DecodeCryptoNode": "解密组件",
    "ExcuteCryptoNode": "OutputCrypto",
    "CryptoCatImage": "CryptoCatImage",
}
WEB_DIRECTORY = "./js"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAMES_MAPPINGS", "WEB_DIRECTORY"]
from server import PromptServer
import aiohttp

workspace_path = os.path.join(os.path.dirname(__file__))
dist_path = os.path.join(workspace_path, "static")
if os.path.exists(dist_path):
    PromptServer.instance.app.add_routes(
        [aiohttp.web.static("/cryptocat/static", dist_path)]
    )
from urllib.parse import unquote
from .auth_unit import AuthUnit
from .updown_workflow import UploadWorkflow, UserWorkflowSetting

handler_instance = WorkflowTrimHandler()
onprompt_callback = partial(handler_instance.onprompt_handler)
PromptServer.instance.add_on_prompt_handler(onprompt_callback)
routes = PromptServer.instance.routes


@routes.post("/cryptocat/auth_callback")
async def auth_callback(request):
    auth_query = await request.json()
    token = auth_query.get("token", "")
    client_key = auth_query.get("client_key", "")
    if token and client_key:
        token = unquote(token)
        client_key = unquote(client_key)
        AuthUnit().set_user_token(token, client_key)
    return aiohttp.web.json_response({"status": "success"}, status=200)


@routes.post("/cryptocat/keygen")
async def keygen(request):
    data = await request.json()
    template_id = data.get("template_id", "").strip()
    if not template_id or len(template_id) != 32:
        return aiohttp.web.json_response(
            {"error_msg": "template_id is required"}, status=500
        )
    expire_date = data.get("expire_date", "")
    use_days = data.get("use_days", "")
    user_token, error_msg, error_code = AuthUnit().get_user_token()
    if not user_token:
        return aiohttp.web.json_response({"error_msg": error_msg}, status=200)
    user_workflow = UploadWorkflow(user_token)
    serial_numbers = user_workflow.generate_serial_number(
        template_id, expire_date, use_days, 1
    )
    if not serial_numbers:
        return aiohttp.web.json_response({"error_msg": "获取失败"}, status=200)
    serial_number = serial_numbers[0]
    return aiohttp.web.json_response({"serial_number": serial_number}, status=200)


@routes.get("/cryptocat/logout")
async def logout(request):
    AuthUnit().clear_user_token()
    return aiohttp.web.json_response({"status": "success"}, status=200)


@routes.post("/cryptocat/set_long_token")
async def set_long_token(request):
    data = await request.json()
    long_token = data.get("long_token", "")
    AuthUnit().set_long_token(long_token)
    return aiohttp.web.json_response({"status": "success"}, status=200)


@routes.post("/cryptocat/set_auto_overwrite")
async def set_auto_overwrite(request):
    data = await request.json()
    auto_overwrite = data.get("auto_overwrite")
    UserWorkflowSetting().set_auto_overwrite(auto_overwrite)
    return aiohttp.web.json_response({"status": "success"}, status=200)

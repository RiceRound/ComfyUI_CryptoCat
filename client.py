from base64 import b64encode
import configparser
import hashlib
from io import BytesIO
import json
import platform
import re
import secrets
from urllib.parse import urlsplit
import uuid

import pyzipper
import requests

from .settings import LOCK, settings_dir, write_ini


TEMPLATE_ID = re.compile(r"[0-9a-fA-F]{32}")
MAX_UPLOAD = 2 * 1024 * 1024
MAX_WORKFLOW = 8 * 1024 * 1024


class ServiceError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def archive_md5(data):
    return b64encode(hashlib.md5(data).digest()).decode("ascii")


def web_login(url, action, payload):
    def call(path, data=None):
        response = session.request("GET" if data is None else "POST",
                                   f"{url}/api/web/{path}", json=data,
                                   timeout=(5, 30), allow_redirects=False)
        if 200 <= response.status_code < 300 and data is None and response.headers.get("Content-Type") == "image/png":
            return response.content, None
        try:
            result = response.json()
        except ValueError:
            result = None
        if response.status_code >= 400:
            error = result if isinstance(result, dict) else {}
            return None, ({"error_msg": error.get("message") or f"登录请求失败（HTTP {response.status_code}）",
                           "challenge_required": error.get("challenge_required") is True}, response.status_code)
        if not isinstance(result, dict) or not 200 <= response.status_code < 300:
            raise ServiceError("登录服务返回了无效响应，请检查服务地址", 502)
        return result, None

    try:
        with requests.Session() as session:
            result, error = call(f"auth/{action}", payload)
            if error:
                return error
            if action == "sms":
                return {key: result.get(key) for key in ("delivery", "retry_after", "challenge_required")}, 200
            if action == "challenge":
                challenge = result.get("id")
                if not isinstance(challenge, str) or not re.fullmatch(r"[A-Za-z0-9_-]{24}", challenge):
                    raise ServiceError("登录服务返回了无效的图形验证码", 502)
                image, error = call(f"auth/challenge/{challenge}.png")
                if error:
                    return error
                if not isinstance(image, bytes):
                    raise ServiceError("登录服务返回了无效的图形验证码", 502)
                return {"id": challenge, "image": b64encode(image).decode("ascii")}, 200
            token, error = call("publisher-token", {})
            if error:
                return error
            return {"token": token.get("token"), "phone": result.get("phone")}, 200
    except requests.RequestException:
        raise ServiceError("无法连接 CryptoCat 登录服务，请检查服务地址和网络", 502) from None


def validate_template_id(value):
    if not isinstance(value, str) or not TEMPLATE_ID.fullmatch(value):
        raise ValueError("模板 ID 必须是 32 位十六进制字符")
    return value


def machine_id():
    with LOCK:
        path = settings_dir() / "machine.ini"
        config = configparser.ConfigParser()
        config.read(path, encoding="utf-8")
        existing = config.get("Machine", "machine_id", fallback="")
        if existing:
            return existing
        cpu = platform.processor() if platform.system() == "Windows" else platform.machine()
        identity = f"{cpu}{uuid.getnode()}{platform.machine()}"
        if platform.system() == "Linux":
            identity += str(uuid.uuid4())
        result = hashlib.md5((identity.strip().lower() + "CryptoCat").encode()).hexdigest()
        config["Machine"] = {"machine_id": result}
        write_ini(path, config)
        return result


class CryptoCatClient:
    def __init__(self, url, token=""):
        if not url:
            raise ServiceError("请先在 ComfyUI 的 CryptoCat 面板设置服务地址")
        self.url = url
        self.token = token

    def request(self, method, path, *, publish=False, token=None, **kwargs):
        if publish and not self.token:
            raise ServiceError("请在 CryptoCat 网站的插件接入页生成登录 Token，并在插件中完成登录", 401)
        credential = self.token if publish else token
        headers = {"Authorization": f"Bearer {credential}"} if credential else {}
        try:
            response = requests.request(method, f"{self.url}/api/cryptocat/{path}",
                                        headers=headers, timeout=(5, 30), allow_redirects=False, **kwargs)
        except requests.RequestException:
            raise ServiceError("无法连接 CryptoCat 服务，请检查服务地址和网络", 502) from None
        try:
            data = response.json()
        except ValueError:
            data = None
        if not 200 <= response.status_code < 300:
            message = data.get("message") if isinstance(data, dict) else None
            if response.status_code == 401:
                message = "登录 Token 无效或已过期，请从网站的插件接入页重新生成"
            raise ServiceError(message or f"CryptoCat 服务请求失败（HTTP {response.status_code}）",
                               response.status_code if response.status_code >= 400 else 502)
        if not isinstance(data, dict):
            raise ServiceError("服务返回了无效的数据，请检查 CryptoCat 地址", 502)
        return data

    def publisher(self):
        data = self.request("GET", "get_info", publish=True)
        user_id = data.get("user_id")
        if user_id is None and isinstance(data.get("data"), dict):
            user_id = data["data"].get("user_id")
        if not isinstance(user_id, (int, str)) or not str(user_id):
            raise ServiceError("服务未返回发布者 ID", 502)
        return str(user_id)

    def check(self, template_id):
        data = self.request("GET", "workflow", publish=True, params={"template_id": template_id, "action": "check"})
        if data.get("code") not in (0, 1):
            raise ServiceError(data.get("message") or "无法检查模板发布状态")
        return data["code"] == 1

    def recent_workflows(self):
        data = self.request("GET", "workflow_list", publish=True, params={"limit": 20})
        rows = data.get("data")
        if data.get("code") != 0 or not isinstance(rows, list):
            raise ServiceError("无法获取发布者的工作流", 502)
        items = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            template_id, user_id = row.get("template_id"), row.get("user_id")
            if not isinstance(template_id, str) or not TEMPLATE_ID.fullmatch(template_id) or user_id is None:
                continue
            name = row.get("name")
            items.append({"template_id": template_id, "name": name.strip() if isinstance(name, str) else None,
                          "user_id": str(user_id)})
            if len(items) == 20:
                break
        return items

    def publish(self, template_id, payload, *, replace):
        if len(payload) > MAX_WORKFLOW:
            raise ServiceError("工作流超过大小限制", 413)
        try:
            document = json.loads(payload)
        except ValueError:
            raise ServiceError("工作流内容无效", 400) from None
        if not isinstance(document, dict) or not isinstance(document.get("prompt"), dict):
            raise ServiceError("工作流内容无效", 400)
        outputs = document.get("outputs")
        if not isinstance(outputs, list) or len(outputs) != 2:
            raise ServiceError("工作流需要一个桥接输出", 400)
        password = secrets.token_urlsafe(24)
        name = document.get("workflow_name") if isinstance(document.get("workflow_name"), str) else ""
        title = document.get("workflow_title") if isinstance(document.get("workflow_title"), str) else ""

        def encrypted(entry, secret):
            archive = BytesIO()
            with pyzipper.AESZipFile(archive, "w", compression=pyzipper.ZIP_DEFLATED,
                                     encryption=pyzipper.WZ_AES) as zip_file:
                zip_file.setpassword(secret.encode())
                zip_file.writestr(entry, payload)
            return archive.getvalue()

        def direct(action):
            body = encrypted("workflow.json", password)
            if len(body) > MAX_UPLOAD:
                raise ServiceError("工作流压缩包超过大小限制", 413)
            digest = archive_md5(body)
            try:
                data = self.request("GET", "workflow/upload", publish=True,
                                    params={"template_id": template_id, "action": action,
                                            "content_length": str(len(body)), "content_md5": digest})
            except ServiceError as exc:
                # Older servers reject direct uploads (or the new size/MD5 query) and only
                # accept the multipart body.
                if exc.status not in (400, 404, 405, 501):
                    raise
                return None
            details = data.get("data")
            url = details.get("url") if isinstance(details, dict) else None
            token = details.get("token") if isinstance(details, dict) else None
            if not isinstance(url, str) or urlsplit(url).scheme not in {"http", "https"} or not isinstance(token, str):
                raise ServiceError("服务未返回有效的上传地址", 502)
            try:
                response = requests.put(
                    url, data=body,
                    headers={"Content-Type": "application/zip", "Content-MD5": digest},
                    timeout=(5, 300),
                )
            except requests.RequestException:
                raise ServiceError("上传工作流到对象存储失败，请检查网络", 502) from None
            if not 200 <= response.status_code < 300:
                raise ServiceError(f"上传工作流到对象存储失败（HTTP {response.status_code}）", 502)
            return token

        def upload(action):
            token = direct(action)
            if token:
                data = self.request("PUT", "workflow", publish=True,
                                    data={"template_id": template_id, "action": action,
                                          "upload_token": token, "password": password,
                                          "name": name, "title": title})
            else:
                body = encrypted("1.bin", template_id)
                data = self.request("PUT", "workflow", publish=True,
                                    data={"template_id": template_id, "action": action},
                                    files={"file": (f"cryptocat_{template_id}.zip", body, "application/zip")})
            if data.get("code") != 0:
                raise ServiceError(data.get("message") or "发布工作流失败")
            return action

        if not replace:
            return upload("create")
        try:
            return upload("replace")
        except ServiceError as exc:
            # Older servers report this validation error with HTTP 500.
            if exc.status not in (400, 500) or str(exc) != "action must be create or upload":
                raise
        if not self.check(template_id):
            raise ServiceError("所选模板已不存在，请刷新模板 ID 后重新发布", 404)
        return upload("upload")

    def download(self, template_id, serial):
        form = {"template_id": template_id, "hardware_id": machine_id(), "serial_number": serial}
        try:
            data = self.request("POST", "client_workflow", data=form)
        except ServiceError as exc:
            # Older activations may also be bound to the publisher account.
            if not self.token or "user ID mismatch" not in str(exc):
                raise
            data = self.request("POST", "client_workflow", data=form, token=self.token)
        if data.get("code") != 0:
            raise ServiceError(data.get("message") or "序列号激活失败")
        url, password = data.get("workflow_url"), data.get("password")
        if not isinstance(url, str) or urlsplit(url).scheme not in {"http", "https"} or not isinstance(password, str):
            raise ServiceError("服务未返回有效的工作流下载信息", 502)
        try:
            response = requests.get(url, timeout=(5, 30))
            response.raise_for_status()
        except requests.RequestException:
            raise ServiceError("下载工作流失败，请检查服务端下载地址", 502) from None
        try:
            with pyzipper.AESZipFile(BytesIO(response.content)) as archive:
                names = archive.namelist()
                member = next((name for name in ("workflow.json", "1.bin") if name in names), None)
                if member is None:
                    member = next(name for name in names if not name.endswith("/"))
                if archive.getinfo(member).file_size > MAX_WORKFLOW:
                    raise ValueError("zip member exceeds workflow size limit")
                return archive.read(member, pwd=password.encode())
        except (ValueError, RuntimeError, KeyError, pyzipper.BadZipFile, StopIteration, OSError):
            raise ServiceError("无法读取加密工作流文件", 502) from None

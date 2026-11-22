import configparser
import hashlib
from io import BytesIO
import platform
import re
from urllib.parse import urlsplit
import uuid

import pyzipper
import requests

from .settings import LOCK, settings_dir, write_ini


TEMPLATE_ID = re.compile(r"[0-9a-fA-F]{32}")


class ServiceError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


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
            raise ServiceError("请在 CryptoCat 服务端生成发布 Token，并在插件面板保存", 401)
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
                message = "发布 Token 无效或已过期，请从 CryptoCat 服务端重新生成"
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

    def publish(self, template_id, payload, *, replace):
        archive = BytesIO()
        with pyzipper.AESZipFile(archive, "w", compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zip_file:
            zip_file.setpassword(template_id.encode())
            zip_file.writestr("1.bin", payload)
        archive.seek(0)
        data = self.request("PUT", "workflow", publish=True,
                            data={"template_id": template_id, "action": "upload" if replace else "create"},
                            files={"file": (f"cryptocat_{template_id}.zip", archive, "application/zip")})
        if data.get("code") != 0:
            raise ServiceError(data.get("message") or "发布工作流失败")

    def issue_serials(self, template_id, *, count=1, expire_date=None, use_days=0):
        data = self.request("GET", "serial_number", publish=True, params={
            "template_id": template_id, "count": count, "expire_date": expire_date, "use_days": use_days,
        })
        serials = data.get("data")
        if data.get("code") != 0 or not isinstance(serials, list) or not serials or not all(isinstance(s, str) for s in serials):
            raise ServiceError(data.get("message") or "服务未返回序列号")
        return serials

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
                if archive.getinfo(member).file_size > 64 * 1024 * 1024:
                    raise ValueError("zip member exceeds workflow size limit")
                return archive.read(member, pwd=password.encode())
        except (ValueError, RuntimeError, KeyError, pyzipper.BadZipFile, StopIteration, OSError):
            raise ServiceError("无法读取加密工作流文件", 502) from None

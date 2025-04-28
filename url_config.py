from enum import IntEnum
import json
import os
from PIL import Image
from io import BytesIO
import numpy as np
import requests
import pyzipper
from requests.exceptions import RequestException, Timeout, HTTPError
from urllib.parse import urljoin
from .utils import get_local_app_setting_path

DEFAULT_SUBDOMAIN = "api" if os.getenv("RICE_ROUND_DEBUG") != "true" else "test"
DEFAULT_URL_PREFIX = f"https://{DEFAULT_SUBDOMAIN}.riceround.online"
DEFAULT_WS_PREFIX = f"wss://{DEFAULT_SUBDOMAIN}.riceround.online"


class UploadType(IntEnum):
    TEMPLATE_PUBLISH_IMAGE = 1
    USER_UPLOAD_TASK_IMAGE = 2
    MACHINE_TASK_RESULT = 1000


class CatUrlConfig:
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(CatUrlConfig, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._initialized = True

    def get_server_url(self, url_path):
        return urljoin(self.url_prefix, url_path)

    def get_ws_url(self, url_path):
        return urljoin(self.ws_prefix, url_path)

    @property
    def ws_prefix(self):
        return DEFAULT_WS_PREFIX

    @property
    def url_prefix(self):
        return DEFAULT_URL_PREFIX

    @property
    def login_api_url(self):
        return self.get_server_url("/api/cryptocat/get_info")

    @property
    def workflow_url(self):
        return self.get_server_url(f"/api/cryptocat/workflow")

    @property
    def serial_number_url(self):
        return self.get_server_url(f"/api/cryptocat/serial_number")

    @property
    def user_client_workflow(self):
        return self.get_server_url(f"/api/cryptocat/client_workflow")


def user_upload_image(image, user_token):
    upload_sign_url = CatUrlConfig().user_upload_sign_url
    headers = {"Authorization": f"Bearer {user_token}"}
    params = {
        "upload_type": UploadType.USER_UPLOAD_TASK_IMAGE.value,
        "file_type": "image/png",
    }
    response = requests.get(upload_sign_url, headers=headers, params=params)
    upload_url = ""
    download_url = ""
    if response.status_code == 200:
        response_data = response.json()
        if response_data.get("code") == 0:
            upload_url = response_data.get("data", {}).get("upload_sign_url", "")
            download_url = response_data.get("data", {}).get("download_url", "")
    else:
        raise ValueError(f"failed to upload image. Status code: {response.status_code}")
    if not upload_url or not download_url:
        raise ValueError(f"failed to upload image. upload_sign_url is empty")
    i = 255.0 * image.cpu().numpy()
    img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
    bytesIO = BytesIO()
    img.save(bytesIO, format="PNG", quality=95, compress_level=1)
    send_bytes = bytesIO.getvalue()
    response = requests.put(
        upload_sign_url, data=send_bytes, headers={"Content-Type": "image/png"}
    )
    if response.status_code == 200:
        return download_url
    else:
        print(f"failed to upload image. Status code: {response.status_code}")
        raise ValueError(f"failed to upload image. Status code: {response.status_code}")


def user_upload_workflow(template_id, workflow_path, user_token, timeout=30):
    "\n    用户上传工作流文件到服务器。\n\n    :param workflow_id: 工作流的模板ID\n    :param workflow_path: 工作流文件的本地路径\n    :param user_token: 用户的认证Token\n    :param timeout: 请求超时时间（秒）\n    :return: (bool, str) 成功与否及相关消息\n"
    url = CatUrlConfig().workflow_url
    headers = {"Authorization": f"Bearer {user_token}"}
    filename = os.path.basename(workflow_path)
    if not os.path.isfile(workflow_path):
        print(f"File does not exist: {workflow_path}")
        return False, "File does not exist"
    try:
        with open(workflow_path, "rb") as file:
            file_content = file.read()
        files = {"file": (filename, file_content, "application/octet-stream")}
        data = {"template_id": template_id, "action": "upload"}
        print(f"Uploading file: {filename} to {url}")
        response = requests.put(
            url, headers=headers, files=files, data=data, timeout=timeout
        )
        response.raise_for_status()
        try:
            response_data = response.json()
        except ValueError:
            print("Response content is not valid JSON")
            return False, "Server returned invalid response"
        if response_data.get("code") == 0:
            print("Workflow uploaded successfully")
            return True, "Workflow uploaded successfully"
        else:
            error_message = response_data.get("message", "Upload failed")
            print(f"Upload failed: {error_message}")
            return False, error_message
    except FileNotFoundError:
        print(f"File not found: {workflow_path}")
        return False, "File not found"
    except Timeout:
        print("Request timed out")
        return False, "Request timed out"
    except HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        return False, f"HTTP error: {http_err}"
    except RequestException as req_err:
        print(f"Request exception occurred: {req_err}")
        return False, f"Request exception: {req_err}"
    except Exception as e:
        print("An unknown error occurred")
        return False, "An unknown error occurred"


def download_crypto_workflow(template_id, hardware_id, serial_number, user_token=None):
    "\n    下载并解密工作流的函数\n\n    :param template_id: 模板ID\n    :param hardware_id: 硬件ID\n    :param serial_number: 序列号\n    :param user_token: 用户凭证 (可选)\n    :return: (status, content)\n        - status: bool, 表示操作是否成功\n        - content: 当status为True时，返回工作流内容；否则返回错误信息\n"
    if not serial_number:
        raise ValueError("serial_number (序列号) 参数不能为空")
    url_config = CatUrlConfig()
    url = url_config.user_client_workflow
    headers = {}
    if user_token:
        headers["Authorization"] = f"Bearer {user_token}"
    form_data = {
        "template_id": template_id,
        "hardware_id": hardware_id,
        "serial_number": serial_number,
    }
    try:
        response = requests.post(url, data=form_data, headers=headers)
    except requests.RequestException as e:
        error_msg = f"网络请求出现异常: {str(e)}"
        print(error_msg)
        return False, error_msg
    if response.status_code != 200:
        if response.status_code == 500:
            try:
                response_data = response.json()
                error_msg = response_data.get(
                    "message", f"未知错误 (status_code={response.status_code})"
                )
            except Exception:
                error_msg = f"服务器内部错误 (status_code={response.status_code})"
        else:
            error_msg = f"下载工作流失败: status_code={response.status_code}"
        print(error_msg)
        return False, error_msg
    try:
        response_data = response.json()
    except ValueError:
        error_msg = "无法解析返回的 JSON 数据"
        print(error_msg)
        return False, error_msg
    response_code = response_data.get("code", -1)
    if response_code != 0:
        error_msg = response_data.get("message", f"未知错误 code={response_code}")
        print(error_msg)
        return False, error_msg
    workflow_url = response_data.get("workflow_url", "")
    password = response_data.get("password", "")
    if not workflow_url or not password:
        error_msg = "下载工作流失败: workflow_url 或 password 缺失"
        print(error_msg)
        return False, error_msg
    try:
        workflow_response = requests.get(workflow_url)
    except requests.RequestException as e:
        error_msg = f"下载工作流内容出现异常: {str(e)}"
        print(error_msg)
        return False, error_msg
    if workflow_response.status_code != 200:
        error_msg = f"下载工作流失败: status_code={workflow_response.status_code}"
        print(error_msg)
        return False, error_msg
    try:
        zip_data = BytesIO(workflow_response.content)
        with pyzipper.AESZipFile(zip_data) as zip_ref:
            zip_ref.setpassword(password.encode("utf-8"))
            file_name = zip_ref.namelist()[0]
            workflow_content = zip_ref.read(file_name)
            return True, workflow_content.decode("utf-8")
    except Exception as e:
        error_msg = f"解密工作流失败: {str(e)}"
        print(error_msg)
        return False, error_msg

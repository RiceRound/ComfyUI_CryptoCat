import json
import os
import requests
from .url_config import CatUrlConfig, download_crypto_workflow, user_upload_workflow
from .utils import combine_files, get_machine_id, get_local_app_setting_path
from .auth_unit import AuthUnit
from server import PromptServer
from aiohttp import web
import time


class Cancelled(Exception):
    pass


class MessageHolder:
    stash = {}
    messages = {}
    cancelled = False

    @classmethod
    def addMessage(cls, id, message):
        if message == "__cancel__":
            cls.messages = {}
            cls.cancelled = True
        elif message == "__start__":
            cls.messages = {}
            cls.stash = {}
            cls.cancelled = False
        else:
            cls.messages[str(id)] = message

    @classmethod
    def waitForMessage(cls, id, period=0.1, timeout=60):
        sid = str(id)
        cls.messages.clear()
        start_time = time.time()
        while not sid in cls.messages and not "-1" in cls.messages:
            if cls.cancelled:
                cls.cancelled = False
                raise Cancelled()
            if time.time() - start_time > timeout:
                raise Cancelled("Operation timed out")
            time.sleep(period)
        if cls.cancelled:
            cls.cancelled = False
            raise Cancelled()
        message = cls.messages.pop(str(id), None) or cls.messages.pop("-1")
        return message.strip()


routes = PromptServer.instance.routes


@routes.post("/cryptocat/message")
async def message_handler(request):
    post = await request.post()
    MessageHolder.addMessage(post.get("id"), post.get("message"))
    return web.json_response({})


class UploadWorkflow:
    def __init__(self, user_token):
        self.user_token = user_token

    def check_workflow(self, template_id):
        url = CatUrlConfig().workflow_url
        headers = {"Authorization": f"Bearer {self.user_token}"}
        response = requests.get(
            url, params={"template_id": template_id, "action": "check"}, headers=headers
        )
        if response.status_code == 200:
            response_data = response.json()
            error_code = response_data.get("code")
            error_msg = response_data.get("message")
            return error_code, error_msg
        else:
            return -1, ""

    def upload_workflow(self, template_id, temp_dir):
        error_code, error_msg = self.check_workflow(template_id)
        if error_code == 1:
            auto_overwrite = UserWorkflowSetting().get_auto_overwrite()
            if not auto_overwrite:
                json_content = {
                    "title": "已经存在相同template_id的数据，是否覆盖？",
                    "icon": "info",
                    "confirmButtonText": "覆盖",
                    "cancelButtonText": "取消",
                    "showCancelButton": True,
                    "timer": 50000,
                }
                PromptServer.instance.send_sync(
                    "cryptocat_dialog",
                    {"json_content": json.dumps(json_content), "id": template_id},
                )
                msg_result = MessageHolder.waitForMessage(template_id, timeout=60000)
                try:
                    result_code = int(msg_result)
                except ValueError:
                    print("crypto cat upload cancel: Invalid response format")
                    return False
                if result_code != 1:
                    print("crypto cat upload cancel: User rejected overwrite")
                    return False
        elif error_code != 0:
            print(f"crypto cat upload failed: {error_msg}")
            PromptServer.instance.send_sync(
                "cryptocat_toast", {"content": f"异常情况，{error_msg}", "type": "error"}
            )
            return False
        combine_target_path = os.path.join(temp_dir, f"cryptocat_{template_id}.zip")
        combine_file_paths = []
        for file in [
            f"crypto_{template_id}.json",
            f"original_workflow_{template_id}.json",
            f"original_prompt_{template_id}.json",
        ]:
            src_path = os.path.join(temp_dir, file)
            combine_file_paths.append(src_path)
        combine_files(combine_file_paths, template_id, combine_target_path)
        for file_path in combine_file_paths:
            os.remove(file_path)
        success, message = user_upload_workflow(
            template_id, combine_target_path, self.user_token
        )
        if success:
            PromptServer.instance.send_sync(
                "cryptocat_toast", {"content": "上传成功", "type": "info", "duration": 5000}
            )
        else:
            PromptServer.instance.send_sync(
                "cryptocat_toast",
                {"content": f"上传失败: {message}", "type": "error", "duration": 5000},
            )
        return success

    def generate_serial_number(self, template_id, count):
        url = CatUrlConfig().serial_number_url
        headers = {"Authorization": f"Bearer {self.user_token}"}
        response = requests.get(
            url, params={"template_id": template_id, "count": count}, headers=headers
        )
        if response.status_code == 200:
            response_data = response.json()
            error_code = response_data.get("code")
            error_msg = response_data.get("message", "")
            if error_code == 0:
                return response_data.get("data", [])
            else:
                raise ValueError(f"failed to generate serial number: {error_msg}")
        else:
            raise ValueError(
                f"failed to generate serial number: {response.status_code}"
            )


class DownloadWorkflow:
    _instance = None
    _cache = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DownloadWorkflow, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True

    def download_workflow(self, template_id, serial_number_token, user_token):
        if not serial_number_token:
            raise ValueError("需要输入序列号")
        cache_key = f"{template_id}_{serial_number_token}_{user_token}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        hardware_id = get_machine_id()
        success, message = download_crypto_workflow(
            template_id, hardware_id, serial_number_token, user_token
        )
        if success:
            self._cache[cache_key] = message
            return message
        elif message is not None:
            if message == "need login" or message == "需要登录":
                AuthUnit().login_dialog("运行工作流，请先完成登录")
            else:
                raise ValueError(message)
        else:
            raise ValueError("failed to download workflow")


class UserWorkflowSetting:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UserWorkflowSetting, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):
            local_app_path = get_local_app_setting_path()
            local_app_path.mkdir(parents=True, exist_ok=True)
            self.config_path = local_app_path / "config.ini"
            self.section_name = "Workflow"
            self.initialized = True

    def get_auto_overwrite(self):
        try:
            import configparser

            config = configparser.ConfigParser()
            config.read(self.config_path, encoding="utf-8")
            if not config.has_section(self.section_name):
                return False
            return config.getboolean(
                self.section_name, "auto_overwrite", fallback=False
            )
        except Exception as e:
            print(f"Error reading auto_overwrite setting: {str(e)}")
            return False

    def set_auto_overwrite(self, value):
        try:
            import configparser

            config = configparser.ConfigParser()
            config.read(self.config_path, encoding="utf-8")
            if not config.has_section(self.section_name):
                config.add_section(self.section_name)
            config.set(self.section_name, "auto_overwrite", str(value).lower())
            with open(self.config_path, "w", encoding="utf-8") as configfile:
                config.write(configfile)
            return True
        except Exception as e:
            print(f"Error saving auto_overwrite setting: {str(e)}")
            return False

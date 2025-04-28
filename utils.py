import configparser
import hashlib
from io import BytesIO
import os
from pathlib import Path
import uuid
import torch
import numpy as np
from PIL import Image
import platform
import subprocess
import random
import string
import socket


def pil2tensor(images: Image.Image | list[Image.Image]) -> torch.Tensor:
    "Converts a PIL Image or a list of PIL Images to a tensor."

    def single_pil2tensor(image: Image.Image) -> torch.Tensor:
        np_image = np.array(image).astype(np.float32) / 255.0
        if np_image.ndim == 2:
            return torch.from_numpy(np_image).unsqueeze(0)
        else:
            return torch.from_numpy(np_image).unsqueeze(0)

    if isinstance(images, Image.Image):
        return single_pil2tensor(images)
    else:
        return torch.cat([single_pil2tensor(img) for img in images], dim=0)


def _calculate_machine_id():
    "\n    获取跨平台的机器唯一标识码，优化对云平台和虚拟机的支持。\n    主要通过CPU信息、MAC地址等硬件特征来区分不同机器。\n    在Linux平台上额外添加随机数以区分相同硬件的云主机。\n"
    import platform
    import socket
    import uuid
    import hashlib

    def get_cpu_info():
        "获取CPU信息"
        try:
            if platform.system() == "Windows":
                return platform.processor()
            else:
                return platform.machine()
        except:
            return ""

    def get_mac_addresses():
        "获取所有网卡的MAC地址"
        try:
            from uuid import getnode

            mac = getnode()
            return str(mac) if mac != 0 else ""
        except:
            return ""

    system_info = [get_cpu_info(), get_mac_addresses(), platform.machine()]
    if platform.system() == "Linux":
        system_info.append(str(uuid.uuid4()))
    valid_info = list(filter(None, system_info))
    if not valid_info:
        return str(uuid.uuid4())
    return "".join(valid_info)


def normalize_machine_id(machine_id: str) -> str:
    "\n    接受一个机器标识符，并返回经过 MD5 哈希处理的规范化标识符\n"
    salt = "CryptoCat"
    trimmed_id = machine_id.strip()
    lowercase_id = trimmed_id.lower()
    salted_id = lowercase_id + salt
    hash_obj = hashlib.md5(salted_id.encode("utf-8"))
    return hash_obj.hexdigest()


def get_local_app_setting_path() -> Path:
    home = Path.home()
    config_dir = home / "CryptoCat"
    return config_dir


def get_machine_id() -> str:
    "\n    返回机器ID，为了兼容各个平台，各个语言，需要统一读写这个值\n"
    config_dir = get_local_app_setting_path()
    config_file = config_dir / "machine.ini"
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Error creating directory '{config_dir}': {e}")
        return ""
    config = configparser.ConfigParser()
    try:
        if config_file.exists():
            config.read(config_file, encoding="utf-8")
            if "Machine" in config and "machine_id" in config["Machine"]:
                return config["Machine"]["machine_id"]
        original_host_id = _calculate_machine_id()
        machine_id = normalize_machine_id(original_host_id)
        if "Machine" not in config:
            config.add_section("Machine")
        config.set("Machine", "machine_id", machine_id)
        with open(config_file, "w", encoding="utf-8") as file:
            config.write(file)
        return machine_id
    except Exception as e:
        print(f"Error handling machine ID in '{config_file}': {e}")
        return ""


def combine_files(files: list[str], password: str, zip_file_path: str) -> bool:
    import pyzipper

    for file_path in files:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"file not found: {file_path}")
    try:
        with pyzipper.AESZipFile(
            zip_file_path,
            "w",
            compression=pyzipper.ZIP_DEFLATED,
            encryption=pyzipper.WZ_AES,
        ) as zipf:
            if isinstance(password, str):
                password = password.encode("utf-8")
            else:
                raise ValueError("password must be a string")
            zipf.setpassword(password)
            for index, file_path in enumerate(files, start=1):
                arcname = f"{index}.bin"
                zipf.write(file_path, arcname)
        return True
    except Exception as e:
        print(f"Error creating zip: {str(e)}")
        return False


def generate_random_string(length: int) -> str:
    "\n    Generate a random string of specified length using uppercase and lowercase letters.\n    \n    Args:\n        length (int): The desired length of the random string\n        \n    Returns:\n        str: A random string of the specified length\n"
    letters = string.ascii_letters
    return "".join(random.choice(letters) for _ in range(length))

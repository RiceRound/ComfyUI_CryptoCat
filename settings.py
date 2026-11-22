import configparser
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import RLock
from urllib.parse import urlsplit


LOCK = RLock()


def settings_dir():
    return Path(os.environ.get("CRYPTOCAT_SETTINGS_DIR") or Path.home() / "CryptoCat")


def normalize_url(value):
    value = value.strip().rstrip("/")
    try:
        url = urlsplit(value)
        port = url.port
    except ValueError as exc:
        raise ValueError("服务地址格式无效") from exc
    if (url.scheme not in {"http", "https"} or not url.hostname or url.username is not None
            or url.path or url.query or url.fragment or any(c.isspace() for c in value)
            or port == 0 or "\\" in value):
        raise ValueError("请填写服务地址，例如 https://cryptocat.example.com")
    return value


def read_settings():
    config = configparser.ConfigParser(interpolation=None)
    config.read(settings_dir() / "config.ini", encoding="utf-8")
    return config


def write_ini(path, config):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as file:
        temp = Path(file.name)
        try:
            config.write(file)
            file.close()
            temp.replace(path)
        finally:
            temp.unlink(missing_ok=True)


def connection(config):
    configured = config.get("Server", "url", fallback="")
    env_url = os.environ.get("CRYPTOCAT_API_URL", "").strip()
    url = normalize_url(env_url or configured) if env_url or configured else ""
    token = config.get("Auth", "user_token", fallback="")
    token_url = config.get("Auth", "server_url", fallback="")
    # Older settings did not associate the token with a server.
    if token_url and token_url != url:
        token = ""
    return url, token


def auto_overwrite(config):
    return config.get("Workflow", "auto_overwrite", fallback="false").lower() == "true"


def save_connection(url, token, overwrite):
    with LOCK:
        config = read_settings()
        for section in ("Server", "Auth", "Workflow"):
            if not config.has_section(section):
                config.add_section(section)
        config["Server"]["url"] = url
        config["Auth"]["user_token"] = token
        config["Auth"]["server_url"] = url if token else ""
        config["Workflow"]["auto_overwrite"] = str(overwrite).lower()
        write_ini(settings_dir() / "config.ini", config)


def clear_token():
    with LOCK:
        config = read_settings()
        if config.has_section("Auth"):
            config.remove_section("Auth")
            write_ini(settings_dir() / "config.ini", config)

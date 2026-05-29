import os
import yaml
from dotenv import load_dotenv

_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
_CONFIG_PATH = os.path.join(_CONFIG_DIR, "config.yaml")
_PROJECT_ROOT = os.path.dirname(_CONFIG_DIR)

# 加载 .env 文件中的环境变量（如 FLIGGY_CLIENT_ID、FLIGGY_CLIENT_SECRET 等）
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))


def load_config() -> dict:
    """加载全局配置文件"""
    with open(_CONFIG_PATH, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


_config = load_config()


def get_current_env() -> str:
    return os.environ.get("API_TEST_ENV", _config.get("current_env", "test"))


def get_base_url() -> str:
    env = get_current_env()
    return _config["environments"][env]["base_url"]


def get_timeout() -> int:
    env = get_current_env()
    return _config["environments"][env].get("timeout", _config["request"]["timeout"])


def get_request_config() -> dict:
    return _config.get("request", {})


def get_project_root() -> str:
    return _PROJECT_ROOT


def get_env_var(key: str, default: str = "") -> str:
    """
    获取环境变量值（优先从 .env 文件加载）

    :param key: 环境变量名，如 FLIGGY_CLIENT_ID
    :param default: 不存在时的默认值
    :return: 环境变量值
    """
    return os.environ.get(key, default)


def get_bug_mode() -> str:
    """
    获取 Bug 模式

    优先级：环境变量 > 配置文件 > 默认值

    :return: "report" 表示记录 Bug 模式，"verify" 表示验证 Bug 模式
    """
    # 优先从环境变量读取
    env_value = os.environ.get("BUG_MODE")
    if env_value is not None:
        return env_value.lower()
    # 从配置文件读取
    return _config.get("bug", {}).get("mode", "report")

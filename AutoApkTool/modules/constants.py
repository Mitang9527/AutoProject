import os
import sys
from pathlib import Path

# ==================== 全局配置常量 ====================


def get_base_path() -> Path:
    """获取程序运行时的根路径，适配 PyInstaller"""
    if getattr(sys, "frozen", False):
        # 如果是打包后的 EXE 运行，返回临时解压目录
        return Path(sys._MEIPASS)
    # 如果是源码运行，返回当前文件所在目录的上级目录（即项目根目录）
    return Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_cwd_path() -> Path:
    """获取用户当前运行程序的目录，用于存放输出文件"""
    if getattr(sys, "frozen", False):
        # 如果是打包后的 EXE 运行，返回 EXE 所在目录
        return Path(os.path.dirname(sys.executable))
    # 如果是源码运行，返回当前工作目录
    return Path(os.getcwd())


# 资源路径（只读，打包时包含在 EXE 中）
RESOURCE_PATH = get_base_path()
# 工作路径（可读写，通常是 EXE 所在的目录）
WORKSPACE_PATH = get_cwd_path()

# 路径配置
JSON_FILE = "input.json"
TEMP_DIR = "app_out"
APKTOOL_JAR = RESOURCE_PATH / "apktool.jar"

# 内置 APK 路径
APK_LARGE = RESOURCE_PATH / "LargeApp.apk"
APK_SMALL = RESOURCE_PATH / "SmallApp.apk"
APK_SCREENLESS = RESOURCE_PATH / "Screenless.apk"

# 环境配置
ENV_CONF = {
    "overseas": {
        "ip_address": "sgdns.shanlipoc.com:10200,usdns.shanlipoc.com:10200",
        "context": "pocstar",
        "upgrade_url": "upgrade.pocstar.com",
    },
    "domestic_v2": {
        "ip_address": "cndns.shanliptt.com:10200",
        "context": "show",
        "upgrade_url": "upgrade.shanliptt.com",
    },
}

# 2. 显示名称映射
ENV_DISPLAY_NAMES = {
    "overseas": {"zh": "海外环境", "en": "Overseas Env"},
    "domestic_v2": {"zh": "国内环境2.0", "en": "Domestic 2.0"},
}

LOGIN_TYPE_MAPPING = {
    "account": {"zh": "账号登录", "en": "Account Login"},
    "serial": {"zh": "IMEI登录", "en": "IMEI Login"},
    "iccid": {"zh": "ICCID登录", "en": "ICCID Login"},
}

MAP_CONFIG_TEMPLATES = {
    "baidu_domestic": {
        "display_name": {"zh": "百度 [国内]", "en": "Baidu [Domestic]"},
        "config": {
            "enabled": True,
            "report": True,
            "map_type": "baidu",
            "provider": "baidu",
            "coor": "bd09ll",
            "update_period_sec": 40,
            "report_period_sec": 40,
        },
    },
    "baidu_oversea": {
        "display_name": {"zh": "百度 [海外]", "en": "Baidu [Oversea]"},
        "config": {
            "enabled": True,
            "report": True,
            "map_type": "baidu",
            "provider": "baidu",
            "coor": "wgs84",
            "update_period_sec": 40,
            "report_period_sec": 40,
        },
    },
    "google": {
        "display_name": {"zh": "谷歌", "en": "Google"},
        "config": {
            "enabled": True,
            "report": True,
            "map_type": "google",
            "provider": "google",
            "coor": "wgs84",
            "update_period_sec": 40,
            "report_period_sec": 40,
        },
    },
    "none": {
        "display_name": {"zh": "GPS", "en": "GPS"},
        "config": {
            "enabled": True,
            "report": True,
            "map_type": "none",
            "provider": "default",
            "coor": "wgs84",
            "update_period_sec": 40,
            "report_period_sec": 40,
        },
    },
}

# 关键文件路径
TEMP_PATH = WORKSPACE_PATH / TEMP_DIR
PATH_YML = TEMP_PATH / "apktool.yml"
PATH_ASS = TEMP_PATH / "assets"
PATH_SLCLIENT = PATH_ASS / "slclient"
PATH_SLCLIENT_JSON = PATH_ASS / "slclient.json"
PATH_INPUT_JSON_SRC = WORKSPACE_PATH / JSON_FILE
PATH_INPUT_JSON_DEFAULT = RESOURCE_PATH / JSON_FILE
PATH_INPUT_JSON_DST = PATH_SLCLIENT / JSON_FILE

# 命名空间（确保与 manifest 中一致）
ANDROID_NAMESPACE = "http://schemas.android.com/apk/res/android"
PATH_MANIFEST_XML = TEMP_PATH / "AndroidManifest.xml"

# 签名配置
KEYSTORE_BIG = RESOURCE_PATH / "cert" / "shanli.jks"
KEYSTORE_SMALL = RESOURCE_PATH / "cert" / "shanlitech.keystore"

KEYSTORE_CONFIG = {
    "large": {"path": KEYSTORE_BIG, "password": "123456"},
    "middle": {"path": KEYSTORE_BIG, "password": "123456"},
    "small": {"path": KEYSTORE_SMALL, "password": "Lgsj829517"},
    "none": {"path": KEYSTORE_SMALL, "password": "Lgsj829517"},
}

# 工具链路径
ZIPALIGN_EXE = RESOURCE_PATH / "win" / "zipalign.exe"
APKSIGNER_BAT = RESOURCE_PATH / "win" / "apksigner.bat"

# 业务常量
LAUNCHER_MODULE_PATH = ["ui", "launcherModule"]
RECORDER_ENABLE_PATH = ["recorder", "enable"]

LBS_COOR_PATH = ["lbs", "coor"]
LBS_MAP_PYPE = ["lbs", "map_type"]

DEFAULT_CUSTOM_LIST = [
    "join_next_group",
    "switch_group_name_tts",
    "switch_group_click",
    "join_prev_group",
    "new_call_in",
]

SKIP_FEEDBACK_INTERVAL = 5
DEBOUNCE_SECONDS = 1.5

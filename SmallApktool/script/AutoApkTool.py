# -*- coding: utf-8 -*-
import os
import re
import subprocess
import sys
import json
import time
import queue
import shutil
import platform
import threading
import tkinter
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Set, List, Any, Dict
import customtkinter as ctk
from tkinter import messagebox, filedialog
from ruamel.yaml import YAML
import xml.etree.ElementTree as ET
from xml.dom import minidom

# ==================== 全局配置常量 ====================

# 路径配置
PROJECT_PATH = Path(os.getcwd())
JSON_FILE = "input.json"
TEMP_DIR = "app_out"
APKTOOL_JAR = "apktool.jar"

# 环境配置
ENV_CONF = {
    "overseas": {
        "ip_address": "sgdns.shanlipoc.com:10200,usdns.shanlipoc.com:10200",
        "context": "pocstar",
        "upgrade_url": "upgrade.pocstar.com"
    },
    "domestic_v2": {
        "ip_address": "cndns.shanliptt.com:10200",
        "context": "show",
        "upgrade_url": "upgrade.shanliptt.com"
    },
}

# 2. 显示名称映射
ENV_DISPLAY_NAMES = {
    "overseas": {"zh": "海外环境", "en": "Overseas Env"},
    "domestic_v2": {"zh": "国内环境2.0", "en": "Domestic 2.0"}
}

LOGIN_TYPE_MAPPING = {
    "account": {"zh": "账号登录", "en": "Account Login"},
    "serial": {"zh": "IMEI登录", "en": "IMEI Login"},
    "iccid": {"zh": "ICCID登录", "en": "ICCID Login"}
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
            "report_period_sec": 40
        }
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
            "report_period_sec": 40
        }
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
            "report_period_sec": 40
        }
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
            "report_period_sec": 40
        }
    }
}

# 关键文件路径
PATH_YML = PROJECT_PATH / "app_out" / "apktool.yml"
PATH_ASS = PROJECT_PATH / "app_out" / "assets"
PATH_SLCLIENT = PROJECT_PATH / "app_out" / "assets" / "slclient"
PATH_SLCLIENT_JSON = PROJECT_PATH / "app_out" / "assets" / "slclient.json"
PATH_INPUT_JSON_SRC = "input.json"
PATH_INPUT_JSON_DST = PROJECT_PATH / "app_out" / "assets" / "slclient" / "input.json"

# 命名空间（确保与 manifest 中一致）
ANDROID_NAMESPACE = "http://schemas.android.com/apk/res/android"
PATH_MANIFEST_XML = PROJECT_PATH / "app_out" / "AndroidManifest.xml"

# 签名配置
KEYSTORE_BIG = PROJECT_PATH / "cert" / "shanli.jks"
KEYSTORE_SMALL = PROJECT_PATH / "cert" / "shanlitech.keystore"

KEYSTORE_CONFIG = {
    "large": {"path": KEYSTORE_BIG, "password": "123456"},
    "middle": {"path": KEYSTORE_BIG, "password": "123456"},
    "small": {"path": KEYSTORE_SMALL, "password": "Lgsj829517"},
    "none": {"path": KEYSTORE_SMALL, "password": "Lgsj829517"},
}

# 工具链路径
ZIPALIGN_EXE = PROJECT_PATH / "win" / "zipalign.exe"
APKSIGNER_BAT = PROJECT_PATH / "win" / "apksigner.bat"

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
    "new_call_in"
]

SKIP_FEEDBACK_INTERVAL = 5
DEBOUNCE_SECONDS = 1.5

# UI 初始化
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


# ==================== 环境检测工具函数 ====================

def check_command(cmd: str) -> bool:
    """检查命令是否在系统 PATH 中"""
    return shutil.which(cmd) is not None


def is_adb_installed() -> bool:
    """检测 ADB 是否安装且可运行"""
    if not check_command("adb"):
        return False
    try:
        result = subprocess.run(
            ["adb", "version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        )
        return result.returncode == 0
    except Exception:
        return False


def is_java_installed() -> bool:
    """检测 Java 是否安装且可运行"""
    if not check_command("java"):
        return False
    try:
        result = subprocess.run(
            ["java", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        )
        return result.returncode == 0
    except Exception:
        return False


def show_env_error_dialog(parent: ctk.CTk, missing_list: List[str]) -> None:
    """显示环境缺失的弹窗"""
    msg = "System environment check failed：\n\n"
    if "ADB" in missing_list:
        msg += "❌ ADB (Android Debug Bridge)\n   " \
               "Decompress and install ADB compressed package in Env\n" \
               ", and set system variables.。\n"
    if "JAVA" in missing_list:
        msg += "❌ Java (JDK/JRE)\n   " \
               "Solution: extract the JDK compressed package in Env and install it.\n"
    msg += "\nPlease install the missing components and click [Retry Detection].。"

    dialog = ctk.CTkToplevel(parent)
    dialog.title("环境缺失警告")
    dialog.geometry("500x400")
    dialog.transient(parent)
    dialog.grab_set()

    lbl = ctk.CTkLabel(dialog, text=msg, justify="left", anchor="nw")
    lbl.pack(padx=20, pady=20, fill="both", expand=True)

    btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_frame.pack(pady=20)

    def on_retry():
        dialog.destroy()
        parent.event_generate("<<EnvRetry>>")

    def on_exit():
        dialog.destroy()
        parent.quit()
        sys.exit(0)

    ctk.CTkButton(btn_frame, text="重试检测", command=on_retry, fg_color="green").pack(side="left", padx=10)
    ctk.CTkButton(btn_frame, text="退出程序", command=on_exit, fg_color="red").pack(side="left", padx=10)


class EnvChecker:
    """环境检查器类"""

    def __init__(self, parent_app: ctk.CTk):
        self.parent = parent_app

    def check_all(self, show_dialog: bool = True) -> bool:
        missing = []
        if not is_adb_installed():
            missing.append("ADB")
        if not is_java_installed():
            missing.append("JAVA")

        if missing:
            if show_dialog:
                self.parent.after(0, lambda: show_env_error_dialog(self.parent, missing))
            return False
        return True


# ==================== 后端逻辑类 (ADB 监听) ====================

class SmartKeyBackend:
    """ADB 监听与配置生成后端"""

    def __init__(self, device: str, log_callback: callable, config_callback: callable):
        self.device = device
        self.log_callback = log_callback
        self.config_callback = config_callback
        self.process: Optional[subprocess.Popen] = None
        self.stop_event = threading.Event()
        self.skip_count = 0
        self.is_running = False

        self.data: Dict = {}
        self.existing_actions: Set[str] = set()
        self.existing_codes: Set[int] = set()

    def load_config(self) -> bool:
        """加载本地 input.json 配置"""
        if not os.path.exists(JSON_FILE):
            self.data = {
                "stdkey": {}, "action": {}, "intent": {},
                "custom": DEFAULT_CUSTOM_LIST.copy()
            }
            self.existing_actions = set()
            self.existing_codes = set()
            return True

        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                self.data = json.load(f)

            self.existing_actions = {
                info.get("action") for name, info in self.data.get("intent", {}).items()
                if info.get("action")
            }
            self.existing_codes = {
                info.get("key") for name, info in self.data.get("stdkey", {}).items()
                if info.get("key") is not None
            }

            # 确保键存在
            self.data.setdefault("stdkey", {})
            self.data.setdefault("action", {})
            self.data.setdefault("intent", {})
            self.data.setdefault("custom", DEFAULT_CUSTOM_LIST.copy())
            return True

        except Exception as e:
            self.log_callback(f"[Error] Failed to read configuration：{e}\n")
            self.data = {
                "stdkey": {}, "action": {}, "intent": {},
                "custom": DEFAULT_CUSTOM_LIST.copy()
            }
            self.existing_actions = set()
            self.existing_codes = set()
            return False

    def save_config(self, silent: bool = False) -> bool:
        """保存配置到 input.json"""
        try:
            with open(JSON_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            if not silent:
                self.log_callback(f"[OK] Configuration saved to {JSON_FILE}\n")
            return True
        except Exception as e:
            self.log_callback(f"[Error] save failed：{e}\n")
            return False

    def _kill_process(self) -> None:
        """强制终止子进程"""
        if self.process is None:
            return
        try:
            if platform.system() == "Windows":
                subprocess.call(
                    ["taskkill", "/F", "/T", "/PID", str(self.process.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
                )
            else:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3)
                except Exception:
                    self.process.kill()
        except Exception:
            pass
        finally:
            self.process = None

    def _clear_logcat(self) -> bool:
        """清空 ADB Logcat 缓冲区"""
        try:
            subprocess.run(
                ["adb", "-s", self.device, "logcat", "-c"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )
            return True
        except Exception:
            return False

    def _generate_standard_config(
            self, suffix: str, key_type: str, action_str: str,
            virtual_key: int, is_many: bool
    ) -> Dict:
        """生成标准键位配置数据结构"""
        result = {"stdkey": {}, "action": {}, "intent": {}}

        if key_type.lower() == "sos":
            base_name = f"sos_{suffix}"
            result["stdkey"] = {
                base_name: {"key": virtual_key, "event": "KEY_CLICK", "time": 3000}
            }
            result["action"] = {}
            result["intent"] = {base_name: {"action": action_str}}
        else:
            prefix = "ptt" if key_type.lower() == "ptt" else "sos"
            down_name = f"many_{prefix}_down_{suffix}" if is_many else f"{prefix}_down_{suffix}"
            up_name = f"{prefix}_up_{suffix}"

            # 推导 UP Action
            if action_str.endswith(".down"):
                up_action_str = action_str[:-5] + ".up"
            elif action_str.endswith("_down"):
                up_action_str = action_str[:-5] + "_up"
            elif "DOWN" in action_str:
                up_action_str = action_str.replace("DOWN", "UP")
            else:
                up_action_str = action_str + ".up"

            stdkey = {
                down_name: {"event": "KEY_DOWN", "key": virtual_key},
                up_name: {"event": "KEY_UP", "key": virtual_key}
            }

            cmd_down_list = [] if is_many else [
                {"command": {"id": "START_SPEAK" if key_type.lower() == "ptt" else "TRIGGER_SOS"}}
            ]
            cmd_up_id = "STOP_SPEAK" if key_type.lower() == "ptt" else "NONE"
            cmd_up_list = [{"command": {"id": cmd_up_id}}] if cmd_up_id != "NONE" else []

            action_data = {
                down_name: {"default": cmd_down_list, "member": [], "new_call_in": []},
                up_name: {"default": cmd_up_list, "member": [], "new_call_in": []}
            }

            intent_data = {
                down_name: {"action": action_str},
                up_name: {"action": up_action_str}
            }

            if key_type.lower() == "sos":
                intent_data[down_name]["as_key"] = True
                intent_data[up_name]["as_key"] = True

            result = {"stdkey": stdkey, "action": action_data, "intent": intent_data}

        return result

    def _reader_thread(self, key_type: str) -> None:
        """监听线程主循环"""
        re_standard = re.compile(r"Sending.*broadcast\s+([\w\.]+)\s+from")

        re_easytalk = re.compile(r"sendEasytalkBroadCast\s+action\s*=\s*(\S+)")

        re_keycode = re.compile(r"keyCode=(\d+)")

        last_process_time = 0
        is_many_mode = (key_type.lower() == "ptt")
        mode_name = "PTT" if is_many_mode else "SOS"

        self.log_callback(f"\n--- Start monitoring (mode：{mode_name}) ---\n")
        if self._clear_logcat():
            self.log_callback("[Info] Log buffer cleared。\n"
                              "\n[tip]  If no log is output after pressing the button,\n"
                              " please enter the known key value in the terminal configuration!!!\n")

        try:
            kwargs = {
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "text": True,
                "bufsize": 1,
                "encoding": "utf-8",
                "errors": "ignore",
            }
            if platform.system() == "Windows":
                kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW

            cmd = ["adb", "-s", self.device, "logcat", "-v", "time", "*:S", "ActivityManager:I"]
            self.process = subprocess.Popen(cmd, **kwargs)
            self.is_running = True

            while not self.stop_event.is_set():
                if self.process.poll() is not None:
                    break
                line = self.process.stdout.readline()
                if not line or self.stop_event.is_set():
                    break

                action_str = None
                match_et = re_easytalk.search(line)
                if match_et:
                    action_str = match_et.group(1)
                else:
                    match_std = re_standard.search(line)
                    if match_std:
                        action_str = match_std.group(1)

                if not action_str:
                    continue

                current_time = time.time()
                if current_time - last_process_time < DEBOUNCE_SECONDS:
                    continue

                if action_str in self.existing_actions:
                    self.skip_count += 1
                    if self.skip_count % SKIP_FEEDBACK_INTERVAL == 0:
                        self.log_callback(f"[Skip] Action '{action_str}' already exists。\n")
                    continue

                last_process_time = current_time
                self.skip_count = 0

                match_k = re_keycode.search(line)
                code_info = f" (KeyCode: {match_k.group(1)})" if match_k else ""
                self.log_callback(f"\n[NEW]  Action: {action_str}{code_info}\n")

                timestamp_suffix = datetime.now().strftime("%Y%m%d%H%M%S")
                new_virtual_code = -1000
                while new_virtual_code in self.existing_codes:
                    new_virtual_code -= 1

                new_entries = self._generate_standard_config(
                    timestamp_suffix, key_type, action_str, new_virtual_code, is_many=is_many_mode
                )

                self.data["stdkey"].update(new_entries["stdkey"])
                self.data["action"].update(new_entries["action"])
                if new_entries["intent"]:
                    self.data["intent"].update(new_entries["intent"])

                self.existing_actions.add(action_str)
                self.existing_codes.add(new_virtual_code)

                created_keys = list(new_entries["stdkey"].keys())
                self.log_callback(f"[OK] {', '.join(created_keys)} (Key: {new_virtual_code})\n")

                if self.save_config(silent=True):
                    self.log_callback("[Auto-Save] ✅ Success。\n")
                    if self.config_callback:
                        self.config_callback()
                self.log_callback("\n")

        except Exception as e:
            if not self.stop_event.is_set():
                self.log_callback(f"\n[Error] {e}\n")
        finally:
            self._kill_process()
            self.is_running = False
            self.log_callback("\n[Info] Monitoring has stopped。\n")

    def start_capture(self, key_type: str) -> None:
        """启动监听线程"""
        if self.is_running:
            self.log_callback("[Warning] Monitoring is already running。\n")
            return
        self.stop_event.clear()
        self.skip_count = 0
        self.load_config()
        t = threading.Thread(target=self._reader_thread, args=(key_type,), daemon=True)
        t.start()

    def stop_capture(self) -> None:
        """停止监听"""
        self.stop_event.set()
        self._kill_process()


# ==================== slclient.json处理 ====================

def update_slclient_login_type(login_type_ui: str) -> bool:
    """
    更新slclient.json中的profile.login_mode字段
    :param login_type_ui: UI选择的登录方式（如"账号登录"）
    :return: 是否修改成功
    """
    # 1. 校验文件是否存在
    if not PATH_SLCLIENT_JSON.exists():
        messagebox.showerror("ERROR", f"Please unzip apk first")
        return False

    # 2. 映射UI值到JSON的login_mode值
    login_mode_val = "account"  # 默认值
    for storage_key, names_dict in LOGIN_TYPE_MAPPING.items():
        if names_dict.get("zh") == login_type_ui or names_dict.get("en") == login_type_ui:
            login_mode_val = storage_key
            break

    try:
        # 3. 读取JSON文件
        with open(PATH_SLCLIENT_JSON, "r", encoding="utf-8") as f:
            slclient_data = json.load(f)

        # 4. 核心修正：修改profile下的login_mode
        # 确保profile节点存在，不存在则创建
        slclient_data.setdefault("profile", {})["login_mode"] = login_mode_val

        # 5. 写回JSON文件（保留格式）
        with open(PATH_SLCLIENT_JSON, "w", encoding="utf-8") as f:
            json.dump(slclient_data, f, indent=2, ensure_ascii=False)

        return True

    except Exception as e:
        messagebox.showerror("修改失败", f"更新slclient.json出错：\n{str(e)}")
        traceback.print_exc()
        return False


def update_slclient_map_type(map_source_key: str) -> bool:
    """
    更新slclient.json中的地图源配置
    :param map_source_key: 地图源的存储键（如 "baidu_domestic"）
    :return: 是否修改成功
    """
    if not PATH_SLCLIENT_JSON.exists():
        print(f"[Error] File not found: {PATH_SLCLIENT_JSON}")
        return False

    try:
        with open(PATH_SLCLIENT_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 获取对应的完整配置
        template_config = MAP_CONFIG_TEMPLATES.get(map_source_key)
        if not template_config:
            print(f"[Error] No template found for key: {map_source_key}")
            return False

        # 将整个 config 部分写入 profile
        if "lbs" not in data:
            data["lbs"] = {}
        data["lbs"].update(template_config["config"])

        # # ⭐⭐⭐ 关键：将存储键本身也写入配置文件，作为唯一标识
        # data["profile"]["map_source"] = map_source_key

        with open(PATH_SLCLIENT_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        # print(f"[OK] slclient.json updated successfully with map_source: {map_source_key}")
        return True

    except Exception as e:
        print(f"[Error] Failed to update slclient.json: {e}")
        return False


# ==================== 前端 UI 类 ====================

class App(ctk.CTk):
    """主应用程序窗口"""

    def __init__(self):
        super().__init__()
        self.title(_("app_title"))
        self.geometry("1200x700")

        # 添加标志跟踪是否是环境预设值
        self.is_default_dns = False
        self.is_default_context = False
        self.is_default_upgrade = False

        # 添加标志跟踪是否是已有配置导入
        self.is_import = False

        # 状态变量
        self.backend: Optional[SmartKeyBackend] = None
        self.current_device: str = ""
        self.log_queue: queue.Queue = queue.Queue()
        self.is_listening: bool = False
        self.env_checker: EnvChecker = EnvChecker(self)
        self.current_apk_type: str = "大屏"

        # 事件绑定
        self.bind("<<EnvRetry>>", lambda e: self.on_env_retry())
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 打包配置状态管理
        self.build_config = {
            "env_type": "",
            "map_source": "baidu",
            "encoding": "amrnb"
        }
        self.slclient_options = {}

        # --- 新增：用于存储 Tab 的 Frame 引用 ---
        self.tab_frames = {}

        # --- 新增：SegmentedButton 的变量 ---
        self.selected_tab = ctk.StringVar(value="")

        self._init_sidebar()
        self._init_main_area()  # 重构的重点

        # 启动定时任务
        self.after(50, self.process_log_queue)
        self.after(200, self.initial_env_check)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ------------------辅助函数------------------------
    def _load_slclient_json(self) -> dict:
        """
        【通用工具】读取 slclient.json 文件内容。

        Returns:
            dict: 解析后的 JSON 数据。如果文件不存在或解析失败，返回空字典 {}。
        """
        # 写死路径
        json_path = PATH_SLCLIENT_JSON
        data = {}

        if not json_path.exists():
            return data

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    data = json.loads(content)
        except json.JSONDecodeError as e:
            self.append_log(f"[Warning] JSON error, empty configuration  be used: {e}\n")
        except Exception as e:
            self.append_log(f"[Error] Failed to read JSON file: {e}\n")

        return data

    # ------------------UI函数------------------------

    def _init_sidebar(self) -> None:
        """初始化侧边栏"""
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(100, weight=1)

        # Logo
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="App\nAdaptation",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # 设备选择
        self.device_label = ctk.CTkLabel(self.sidebar_frame, text=_("lbl_device"), anchor="w")
        self.device_label.grid(row=1, column=0, padx=20, pady=(10, 0))
        self.device_var = ctk.StringVar(value=(_("status_detecting")))
        self.device_menu = ctk.CTkOptionMenu(
            self.sidebar_frame,
            variable=self.device_var,
            values=[],
            command=self.on_device_change
        )
        self.device_menu.grid(row=2, column=0, padx=20, pady=5)
        self.refresh_btn = ctk.CTkButton(
            self.sidebar_frame,
            text=_("btn_refresh"),
            command=self.refresh_devices,
            height=30
        )
        self.refresh_btn.grid(row=3, column=0, padx=20, pady=5)

        # 监听模式
        self.mode_label = ctk.CTkLabel(self.sidebar_frame, text=_("lbl_mode"), anchor="w")
        self.mode_label.grid(row=4, column=0, padx=20, pady=(5, 0))
        self.mode_var = ctk.StringVar(value="ptt")
        self.mode_menu = ctk.CTkOptionMenu(
            self.sidebar_frame,
            variable=self.mode_var,
            values=["ptt", "sos"]
        )
        self.mode_menu.grid(row=5, column=0, padx=20, pady=5)

        # 控制按钮
        self.start_btn = ctk.CTkButton(
            self.sidebar_frame,
            text=_("btn_start_listen"),
            fg_color="green",
            command=self.toggle_listen
        )
        self.start_btn.grid(row=7, column=0, padx=20, pady=10)
        self.clear_log_btn = ctk.CTkButton(
            self.sidebar_frame,
            text=_("clear_log"),
            fg_color="gray",
            command=self.clear_log
        )
        self.clear_log_btn.grid(row=8, column=0, padx=20, pady=10)

        # APK 选择区域
        self.apk_select_label = ctk.CTkLabel(self.sidebar_frame, text=_("lbl_apk_type"), anchor="w")
        self.apk_select_label.grid(row=9, column=0, padx=20, pady=(15, 0))

        self.decompile_apk_btn = ctk.CTkButton(
            self.sidebar_frame,
            text=_("btn_decompile"),
            command=self.decompile_apk
        )
        self.decompile_apk_btn.grid(row=12, column=0, padx=20, pady=10)

        # self.build_apk_btn = ctk.CTkButton(
        #     self.sidebar_frame,
        #     text="上传自定义apk",
        #     command=self.upload_apk
        # )
        # self.build_apk_btn.grid(row=11, column=0, padx=20, pady=10)

        self.apk_type_seg = ctk.CTkSegmentedButton(
            self.sidebar_frame,
            values=[
                _("type_large_screen"),
                _("type_middle_screen"),
                _("type_small_screen"),
                _("type_none_screen"),
                _("type_custom_apk")
            ],
            command=self.on_apk_type_change,
            height=30,
            fg_color="#3498db",
            selected_color="#27ae60",
            unselected_color="gray"
        )
        self.apk_type_seg.grid(row=11, column=0, padx=20, pady=5, sticky="ew")
        self.apk_type_seg.set(_("type_large_screen"))

        self.build_apk_btn = ctk.CTkButton(
            self.sidebar_frame,
            text=_("btn_build"),
            fg_color="#d35400",
            hover_color="#e67e22",
            command=self.build_apk
        )
        self.build_apk_btn.grid(row=13, column=0, padx=20, pady=10)

        # # 底部状态栏
        # self.status_label = ctk.CTkLabel(
        #     self.sidebar_frame,
        #     text=_("status_init"),
        #     anchor="w",
        #     text_color="gray"
        # )
        # self.status_label.grid(row=100, column=0, padx=20, pady=(0, 20), sticky="s")

        # 语言选择
        self.lang_var = ctk.StringVar(value="English")
        self.lang_menu = ctk.CTkOptionMenu(
            self.sidebar_frame,
            variable=self.lang_var,
            values=["中文", "English"],
            command=self.on_language_change
        )
        self.lang_menu.grid(row=101, column=0, padx=20, pady=8)

    def on_language_change(self, selection):
        lang_code = "zh" if selection == "中文" else "en"
        if i18n.load_language(lang_code):
            self.refresh_ui_texts()
            # self.append_log(f"[Info] Language switched to {selection}\n")

    def _init_main_area(self) -> None:
        """初始化主内容区 (使用 SegmentedButton 模拟 Tab)"""
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_rowconfigure(1, weight=1)  # 内容区域扩展
        self.main_frame.grid_columnconfigure(0, weight=1)

        # --- 1. 创建 SegmentedButton (充当 Tab Header) ---
        # 定义 Tab 名称映射 (为了实时翻译，我们存储键，显示值)
        self.tab_names = {
            "log": _("msg_tab_log"),
            "config": _("msg_tab_config"),
            "build": _("msg_tab_build"),
            "led": _("msg_tab_led"),
            "terminal": _("msg_tab_apk_config")
        }

        self.tab_selector = ctk.CTkSegmentedButton(
            self.main_frame,
            values=list(self.tab_names.values()),
            variable=self.selected_tab,
            command=self._on_tab_switch,

            # --- 1. 尺寸与圆角优化 ---
            height=32,  # 缩小高度 (原40 -> 32)，更紧凑
            width=100,  # 限制宽度，避免按钮过宽
            corner_radius=8,  # 增加圆角 (原默认较小)，让按钮更柔和
            font=ctk.CTkFont(size=13),  # 字体稍微调小一点以适配新高度

            # --- 2. 颜色与间隔优化 ---
            # 背景色：设置为透明或与父容器一致，这样按钮之间会有“缝隙”感
            # fg_color="transparent",

            # 选中项：使用品牌色，圆角由 corner_radius 控制
            selected_color="#3498db",
            selected_hover_color="#2980b9",

            # 未选中项：使用浅灰色，与背景形成对比
            unselected_color="green",
            unselected_hover_color="gray",

            # --- 3. 边框优化 ---
            # 如果需要整体外边框，可以加这个，但通常透明背景更现代
            # border_width=0,
        )
        self.tab_selector.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")

        # --- 2. 创建 Container Frame (充当 Tab Content 显示区) ---
        self.content_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.content_container.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.content_container.grid_rowconfigure(0, weight=1)
        self.content_container.grid_columnconfigure(0, weight=1)

        # --- 3. 初始化所有 Tab 的 Frame (隐藏状态) ---
        self._create_tab_frames()

        # --- 4. 默认显示第一个 Tab ---
        if self.tab_names:
            first_tab_key = list(self.tab_names.keys())[0]
            self._show_tab(first_tab_key)

    def _create_tab_frames(self):
        """创建所有 Tab 对应的 Frame，但不直接显示"""
        # 使用一个字典来映射 "内部键" -> Frame
        # 注意：这里的键必须和 self.tab_names 的键对应

        # Tab 1: Log (保持原样)
        frame_log = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.log_textbox = ctk.CTkTextbox(
            frame_log, font=ctk.CTkFont(family="Consolas", size=12)
        )
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=10)
        self.tab_frames["log"] = frame_log

        # Tab 2: Config (保持原样)
        frame_config = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.scroll_frame = ctk.CTkScrollableFrame(
            frame_config, label_text=_("msg_config_list_title")
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        self.tab_frames["config"] = frame_config

        # Tab 3: Build Config (保持原样)
        frame_build = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self._init_build_config_page(frame_build)  # 注意：我们将原函数改造成接受父容器参数
        self.tab_frames["build"] = frame_build

        # Tab 4: LED Config (保持原样)
        frame_led = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self._init_led_config_page(frame_led)  # 注意：同上
        self.tab_frames["led"] = frame_led

        # Tab 5: 终端配置 (保持原样)
        frame_apk_config = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self._init_terminal_config(frame_apk_config)  # 注意：同上
        self.tab_frames["terminal"] = frame_apk_config

        # --- 将所有 Frame 放入容器，但先隐藏 ---
        for frame in self.tab_frames.values():
            frame.grid(row=0, column=0, sticky="nsew")

    def _on_tab_switch(self, value):
        """当 SegmentedButton 选项改变时触发"""
        # 这里 value 是显示的文本，我们需要反向查找键
        # 由于我们存储了 self.tab_names，我们可以遍历查找
        target_key = None
        for key, display_text in self.tab_names.items():
            if display_text == value:
                target_key = key
                break
        if target_key:
            self._show_tab(target_key)

    def _show_tab(self, tab_key):
        """隐藏所有 Frame，显示指定的 Frame"""
        for key, frame in self.tab_frames.items():
            frame.grid_remove()  # 隐藏但不销毁

        # 显示目标
        if tab_key in self.tab_frames:
            self.tab_frames[tab_key].grid()

            # 更新 SegmentedButton 的状态 (防止因代码触发导致 UI 不同步)
            display_text = self.tab_names.get(tab_key, "")
            self.selected_tab.set(display_text)

    def ask_model_dialog(self):
        # 1. 创建弹窗
        dialog = ctk.CTkToplevel(self)
        dialog.title(_("model_title"))
        dialog.geometry("300x150")
        dialog.transient(self)
        dialog.grab_set()

        # 2. 布局
        self.label_device_model = ctk.CTkLabel(dialog, text=_("label_device_model"), font=("Microsoft YaHei", 14))
        self.label_device_model.pack(pady=15)

        self.entry = ctk.CTkEntry(dialog, width=200, placeholder_text=_("placeholder_model_input"))
        self.entry.pack(pady=10)
        self.entry.focus_set()

        result = {"value": None}  # 用于接收结果

        # 3. 定义提交逻辑
        def submit():
            val = self.entry.get().strip()
            # if val:
            result["value"] = val
            dialog.destroy()
            # else:
            #     # 非空校验
            #     self.entry.configure(border_color="red")

        def cancel():
            result["value"] = None
            dialog.destroy()

        # 4. 按钮区域
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)

        self.msg_btn_cancel = ctk.CTkButton(btn_frame, text=_("msg_btn_cancel"), width=80, command=cancel)
        self.msg_btn_cancel.pack(side="left", padx=10)
        self.msg_btn_confirm = ctk.CTkButton(btn_frame, text=_("msg_btn_confirm"), width=80, command=submit)
        self.msg_btn_confirm.pack(side="right", padx=10)

        dialog.update_idletasks()
        w, h = dialog.winfo_width(), dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (w // 2)
        y = (dialog.winfo_screenheight() // 2) - (h // 2)
        dialog.geometry(f"{w}x{h}+{x}+{y}")

        # 5. 绑定回车键事件
        dialog.bind('<Return>', lambda event: submit())

        # 6. 等待窗口关闭 (阻塞在这里)
        self.wait_window(dialog)

        return result["value"]

    def refresh_ui_texts(self):
        """遍历并更新主要组件的文本 (已更新：支持 SegmentedButton 实时刷新)"""
        # 1. ⭐【关键】重新加载语言包，确保 _(...) 生效
        current_lang = i18n.current_lang
        # 这个调用至关重要，必须在所有 _("key") 调用之前
        if self.on_language_change == "中文":
            i18n.load_language("zh")
        elif self.on_language_change == "English":
            i18n.load_language("en")

        # 2. 更新 SegmentedButton (核心改进点)
        self._safe_refresh_config_view()
        new_tab_names = {
            "log": _("msg_tab_log"),
            "config": _("msg_tab_config"),
            "build": _("msg_tab_build"),
            "led": _("msg_tab_led"),
            "terminal": _("msg_tab_apk_config")
        }

        # 获取当前选中的键 (通过反向查找)
        current_display = self.selected_tab.get()
        current_key = None
        for k, v in self.tab_names.items():
            if v == current_display:
                current_key = k
                break

        # 更新内部映射
        self.tab_names = new_tab_names

        # --- 新增：更新 APK 类型选择器 ---
        # 1. 记录当前选中的值 (防止切换后选中状态丢失)
        current_selection = self.apk_type_seg.get()

        # 2. 重新构建 values 列表 (再次调用 _() 获取最新语言)
        new_values = [
            _("type_large_screen"),
            _("type_middle_screen"),
            _("type_small_screen"),
            _("type_none_screen"),
            _("type_custom_apk")
        ]
        self._filter_terminal_folders()
        self.apk_type_seg.configure(values=new_values)

        if self.current_apk_type == "大屏":
            self.apk_type_seg.set(_("type_large_screen"))
        elif self.current_apk_type == "中屏":
            self.apk_type_seg.set(_("type_middle_screen"))
        elif self.current_apk_type == "小屏":
            self.apk_type_seg.set(_("type_small_screen"))
        elif self.current_apk_type == "无屏":
            self.apk_type_seg.set(_("type_none_screen"))
        else:
            self.apk_type_seg.set(_("type_custom_apk"))

        self.tab_selector.configure(values=list(self.tab_names.values()))
        if current_key:
            self._show_tab(current_key)

        self.update_option_menus_on_language_change()

        if hasattr(self, 'opt_env'):
            self.opt_env.configure(command=None)

            new_env_options = []
            for key in ENV_CONF.keys():
                display_name = ENV_DISPLAY_NAMES.get(key, {}).get(current_lang, key)
                new_env_options.append(display_name)

            self.opt_env.configure(values=new_env_options)

            saved_env_id = "overseas"
            if PATH_SLCLIENT_JSON.exists():
                try:
                    with open(PATH_SLCLIENT_JSON, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    profile_data = data.get("profile", {})
                    config_dns = profile_data.get("dns")
                    config_context = profile_data.get("context")

                    for env_id, env_config in ENV_CONF.items():
                        env_ip_address = env_config.get("ip_address")
                        env_context = env_config.get("context")


                        if config_context and env_context and config_context == env_context:
                            if config_dns and env_ip_address:
                                if isinstance(config_dns, list):
                                    config_dns_str = ','.join(config_dns)
                                else:
                                    config_dns_str = str(config_dns) if config_dns else ""

                                dns_list = [addr.strip() for addr in env_ip_address.split(',')]

                                # 检查配置中的DNS是否包含在环境配置的IP地址列表中
                                if any(config_dns_str in dns_addr or dns_addr in config_dns_str for dns_addr in
                                       dns_list):
                                    matched_env_id = env_id
                                    break

                except Exception as e:
                    print(f"Error reading configuration file: {e}")
                    pass

            target_display_name = ENV_DISPLAY_NAMES.get(matched_env_id, {}).get(current_lang, matched_env_id)
            self.opt_env.set(target_display_name)

            self.opt_env.configure(command=self._on_env_selected)

        # 4. 更新其他组件 (保持原样)
        self.title(_("app_title"))
        self.logo_label.configure(text=_("sidebar_logo"))
        self.device_label.configure(text=_("lbl_device"))
        self.refresh_btn.configure(text=_("btn_refresh"))
        self.start_btn.configure(text=_("btn_start_listen") if not self.is_listening else _("btn_stop_listen"))
        self.mode_label.configure(text=_("lbl_mode"))
        self.clear_log_btn.configure(text=_("clear_log"))
        self.apk_select_label.configure(text=_("lbl_apk_type"))
        self.build_apk_btn.configure(text=_("btn_build"))
        self.env_custom.configure(text=_("env_custom"))
        self.decompile_apk_btn.configure(text=_("btn_decompile"))
        self.apk_title_label.configure(text=_("msg_terminal_config_title"))

        self.scroll_frame.configure(label_text=i18n.get("msg_config_list_title"))

        self.env_custom.configure(text=_("env_custom"))

        if hasattr(self, 'sound_title_label'):
            self.sound_title_label.configure(text=i18n.get("msg_card_sound"))
        if hasattr(self, 'map_title_label'):
            self.map_title_label.configure(text=i18n.get("msg_card_map"))

        self.use_btn.configure(text=_("use_btn"))
        self.lbl_title.configure(text=_("msg_card_apk_properties"))
        self.lbl_input_title.configure(text=_("msg_tab_input"))
        self.title_led_mode.configure(text=_("msg_card_input"))
        self.lbl_other.configure(text=_("msg_feature_dev"))
        self.frame_led_color.title_label.configure(text=_("msg_card_other"))
        self.frame_env.title_label.configure(text=_("msg_card_env"))
        self.frame_sound.title_label.configure(text=_("msg_card_sound"))
        self.frame_map.title_label.configure(text=_("msg_card_map"))
        self.frame_other.title_label.configure(text=_("msg_card_other"))
        self.lbl_server_node.configure(text=_("lbl_server_node"))
        self.lbl_login_type.configure(text=_("lbl_login_type"))
        self.lbl_map_source.configure(text=_("lbl_map_source"))

        self.lbl_ptt_press.configure(text=_("lbl_ptt_press"))
        self.lbl_ptt_release.configure(text=_("lbl_ptt_release"))
        self.lbl_sos_key.configure(text=_("lbl_sos_key"))
        self.btn_save_config.configure(text=_("btn_save_config"))
        self.btn_save_custom.configure(text=_("msg_save_btn"))
        self.codec.configure(text=_("codec"))
        self.audio.configure(text=_("audio"))
        self.play_channel.configure(text=_("play_channel"))
        self.rec_channel.configure(text=_("rec_channel"))

        try:
            if hasattr(self, 'model_dialog') and self.model_dialog.winfo_exists():
                self.model_dialog.title(_("model_title"))
            if hasattr(self, 'msg_btn_confirm') and self.msg_btn_confirm.winfo_exists():
                self.msg_btn_confirm.configure(text=_("msg_btn_confirm"))
            if hasattr(self, 'msg_btn_cancel') and self.msg_btn_cancel is not None:
                self.msg_btn_cancel.configure(text=_("msg_btn_cancel"))
            if hasattr(self, 'msg_btn_cancel') and self.msg_btn_cancel is not None:
                self.msg_btn_cancel.configure(text=_("msg_btn_cancel"))
            if hasattr(self, 'label_device_model') and self.label_device_model is not None:
                self.label_device_model.configure(text=_("label_device_model"))
            if hasattr(self, 'placeholder_model_input') and self.entry is not None:
                self.entry.configure(text=_("placeholder_model_input"))
            if hasattr(self, 'ok_btn') and self.ok_btn is not None:
                self.ok_btn.configure(text=_("btn_ok"))
            if hasattr(self, 'btn_dialog_ok') and self.btn_dialog_ok is not None:
                self.btn_dialog_ok.configure(text=_("confirm_button"))
            if hasattr(self, 'btn_dialog_cancel') and self.btn_dialog_cancel is not None:
                self.btn_dialog_cancel.configure(text=_("cancel_button"))

        except tkinter.TclError:
            pass

    def update_option_menus_on_language_change(self):
        """
        专门用于在语言切换时更新 CTkOptionMenu 的选项和选中值
        """
        self._is_updating_language = True

        # --- 更新登录方式下拉框 ---
        if hasattr(self, 'opt_login_type'):
            # a. 重新生成当前语言下的选项列表
            login_type_display_names = [LOGIN_TYPE_MAPPING[key][i18n.current_lang] for key in LOGIN_TYPE_MAPPING.keys()]
            self.opt_login_type.configure(values=login_type_display_names)

            # b. 根据存储的原始键，恢复当前选中的显示名称
            # 首先需要知道当前应该选中哪个存储键 (例如 "account", "serial")
            # 假设 slclient.json 文件中的值是权威的存储键
            current_login_mode_key = "account"  # 默认值
            if PATH_SLCLIENT_JSON.exists():
                try:
                    with open(PATH_SLCLIENT_JSON, "r", encoding="utf-8") as f:
                        slclient_data = json.load(f)
                    current_login_mode_key = slclient_data.get("profile", {}).get("login_mode", "account")
                except Exception as e:
                    print(f"[Warning] Failed to read login_mode for update: {e}")

            # c. 根据存储键，获取新语言下的显示名称，并设置
            new_display_name = LOGIN_TYPE_MAPPING.get(current_login_mode_key, {}).get(i18n.current_lang,
                                                                                      "Account Login")
            self.opt_login_type.set(new_display_name)
            # 可能还需要更新预览
            self._update_preview("login_type", new_display_name)

        # --- 如果还有其他 OptionMenu，也需要在这里更新 ---
        # 例如：
        # if hasattr(self, 'some_other_option_menu'):
        #     new_values = [i18n.get("key1"), i18n.get("key2")]
        #     self.some_other_option_menu.configure(values=new_values)
        #     # 然后根据该控件的逻辑状态恢复选中项
        #     # self.some_other_option_menu.set(...)

        if hasattr(self, 'opt_map_source'):
            # a. 重新生成当前语言下的选项列表
            map_source_display_names = [v["display_name"][i18n.current_lang] for v in MAP_CONFIG_TEMPLATES.values()]
            self.opt_map_source.configure(values=map_source_display_names)

            # b. 根据存储的原始键，恢复当前选中的显示名称
            current_map_source_key = "Google"  # 默认值
            if PATH_SLCLIENT_JSON.exists():
                try:
                    with open(PATH_SLCLIENT_JSON, "r", encoding="utf-8") as f:
                        slclient_data = json.load(f)

                    current_map_source_key = slclient_data.get("lbs", {}).get("map_type", "Google")
                    self.map_type = self.get_json_field(PATH_SLCLIENT_JSON, LBS_MAP_PYPE)
                    if self.map_coor == "wgs84" and self.map_type == "baidu":
                        current_map_source_key = "baidu_oversea"
                    elif self.map_coor == "bd09ll" and self.map_type == "baidu":
                        current_map_source_key = "baidu_domestic"
                    if current_map_source_key == "none":
                        current_map_source_key = "none"

                except Exception as e:
                    print(f"[Warning] Failed to read map_source for update: {e}")

            # c. 根据存储键，获取新语言下的显示名称，并设置
            new_display_name = MAP_CONFIG_TEMPLATES.get(current_map_source_key, {}).get("display_name", {}).get(
                i18n.current_lang)
            self.opt_map_source.set(new_display_name)

        # ⭐⭐⭐【关键修改】重置标志位
        self._is_updating_language = False

    def initial_env_check(self) -> None:

        if not self.env_checker.check_all(show_dialog=True):
            # self.status_label.configure(text="状态：环境缺失", text_color="red")
            self.device_var.set("等待环境修复")
            self.device_menu.configure(values=[])
            self.start_btn.configure(state="disabled")
        else:
            # self.status_label.configure(text="状态：环境就绪", text_color="green")
            self.start_btn.configure(state="normal")
            self.refresh_devices()
            self.after(100, self.refresh_config_view)

    def on_env_retry(self) -> None:
        self.append_log("\n[Info] Detecting environment...\n")
        if self.env_checker.check_all(show_dialog=False):
            self.append_log("[OK] Environmental passed.！\n")
            # self.status_label.configure(text=(_("status_env_ready")), text_color="green")
            self.start_btn.configure(state="normal")
            self.refresh_devices()
            self.after(100, self.refresh_config_view)
        else:
            self.env_checker.check_all(show_dialog=True)

    def refresh_devices(self) -> None:
        if not self.winfo_exists():
            return
        if not is_adb_installed():
            self.env_checker.check_all(show_dialog=True)
            return

        try:
            out = subprocess.check_output(["adb", "devices"], text=True, stderr=subprocess.DEVNULL,
                                          creationflags=subprocess.CREATE_NO_WINDOW
                                          )
            devs = [
                line.split()[0] for line in out.splitlines()
                if "\tdevice" in line and not line.startswith("List")
            ]
            current_val = self.device_var.get()
            self.device_menu.configure(values=devs if devs else ["no devices"])

            if devs:
                if current_val not in devs or current_val in ["未连接", "未检测到设备", "检测中...", "等待环境修复"]:
                    self.device_var.set(devs[0])
                    self.current_device = devs[0]
                else:
                    self.current_device = current_val
                # self.status_label.configure(text=f"状态：已连接\n{self.current_device}", text_color="green")
            else:
                self.device_var.set("no devices")
                self.current_device = ""
                # self.status_label.configure(text="no devices", text_color="red")
        except Exception:
            if self.winfo_exists():
                self.device_menu.configure(values=["ADB Error"])
            self.device_var.set("ADB Error")

    def on_device_change(self, selection: str) -> None:
        if selection not in ["未检测到设备", "ADB 错误"]:
            self.current_device = selection
        # self.status_label.configure(text=f"状态：已切换\n{selection}", text_color="green")

    def toggle_listen(self) -> None:
        if not self.winfo_exists():
            return
        if not is_adb_installed():
            messagebox.showerror("ERR", "ADB 环境丢失！")
            self.env_checker.check_all(show_dialog=True)
            return
        if not self.current_device or self.current_device in ["未检测到设备", "ADB 错误", "未连接"]:
            messagebox.showerror("ERR", "请先选择有效的 ADB 设备！")
            self.refresh_devices()
            return

        if self.is_listening:
            if self.backend:
                self.backend.stop_capture()
            self.is_listening = False
            self.start_btn.configure(text=_("btn_start_listen"), fg_color="green")
            # self.status_label.configure(text="状态：已停止", text_color="orange")
            self.mode_menu.configure(state="normal")
            self.device_menu.configure(state="normal")
        else:
            mode = self.mode_var.get()
            self.backend = SmartKeyBackend(
                self.current_device,
                log_callback=self.append_log,
                config_callback=self.refresh_config_view
            )
            if not self.backend.load_config():
                if not messagebox.askyesno("警告", "读取配置失败，是否使用空配置继续？"):
                    return
            self.is_listening = True
            self.start_btn.configure(text=_("btn_stop_listen"), fg_color="red")
            # self.status_label.configure(text="状态：监听中", text_color="green")
            self.mode_menu.configure(state="disabled")
            self.device_menu.configure(state="disabled")
            self.backend.start_capture(mode)

    def append_log(self, text: str) -> None:
        """线程安全的日志添加方法"""
        self.log_queue.put(text)

    def process_log_queue(self) -> None:
        """处理日志队列并更新 UI"""
        if not self.winfo_exists():
            return
        try:
            while True:
                try:
                    text = self.log_queue.get_nowait()
                    if self.log_textbox.winfo_exists():
                        self.log_textbox.insert("end", text)
                        self.log_textbox.see("end")
                except queue.Empty:
                    break
        except Exception:
            pass
        self.after(50, self.process_log_queue)

    def clear_log(self) -> None:
        if self.log_textbox.winfo_exists():
            self.log_textbox.delete("0.0", "end")

    def refresh_config_view(self) -> None:
        if not self.winfo_exists():
            return
        self.after(0, self._safe_refresh_config_view)

    def _safe_refresh_config_view(self) -> None:
        """刷新配置列表，并按虚拟键码(key)升序排列)"""
        if not self.winfo_exists():
            return

        try:
            # 1. 清空现有列表
            for widget in self.scroll_frame.winfo_children():
                try:
                    widget.destroy()
                except Exception:
                    pass

            # 2. 加载数据
            data = {}
            if self.backend and hasattr(self.backend, "data"):
                data = self.backend.data
            elif os.path.exists(JSON_FILE):
                try:
                    with open(JSON_FILE, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    pass

            intents = data.get("intent", {})
            stdkeys = data.get("stdkey", {})
            actions_data = data.get("action", {})

            # 3. 绘制表头 (国际化)
            headers = [
                i18n.get("msg_header_key_name"),  # "键名 (Key Name)"
                i18n.get("msg_header_event"),  # "事件类型"
                i18n.get("msg_header_vkey"),  # "虚拟keycode"
                i18n.get("msg_header_action"),  # "Intent Action"
                i18n.get("msg_header_cmd")  # "默认命令"
            ]
            for i, h in enumerate(headers):
                ctk.CTkLabel(
                    self.scroll_frame,
                    text=h,
                    font=ctk.CTkFont(weight="bold", size=13),
                    anchor="w"
                ).grid(row=0, column=i, padx=15, pady=15, sticky="w")

            # 4. 核心排序逻辑
            # 获取所有共有的键名 (确保数据完整)
            valid_names = set(stdkeys.keys()) & set(intents.keys())

            sortable_items = []
            for name in valid_names:
                sk = stdkeys.get(name, {})
                key_val = sk.get("key")

                if isinstance(key_val, int):
                    sort_key = key_val
                else:
                    sort_key = float('inf')

                sortable_items.append((name, sort_key))

            # 排序：升序 (Reverse=False)
            # 逻辑：新生成的 key 是更小的负数 (如 -1005)，旧的是较大的负数 (如 -1000)
            # 升序排列结果：-1005, -1004, ..., -1000 -> 新配置在最上面
            sortable_items.sort(key=lambda x: x[1], reverse=False)

            # 5. 渲染列表
            row_idx = 1
            for name, _ in sortable_items:
                if not self.winfo_exists():
                    return

                sk = stdkeys.get(name, {})
                ac = actions_data.get(name, {})
                info = intents.get(name, {})

                # 提取数据 (国际化 N/A)
                event_str = sk.get("event", i18n.get("msg_not_available"))  # "N/A" -> "不可用" 或 "N/A"
                key_val = sk.get("key", i18n.get("msg_not_available"))  # "N/A" -> "不可用" 或 "N/A"
                action_str = info.get("action", i18n.get("msg_default_placeholder"))  # "-" -> "默认占位符" 或 "-"

                # 提取命令 ID
                cmds = ac.get("default", [])
                if isinstance(cmds, list):
                    cmd_ids = [c.get("command", {}).get("id", "") for c in cmds if isinstance(c, dict)]
                    cmd_str = ", ".join(filter(None, cmd_ids))
                else:
                    cmd_str = i18n.get("msg_default_placeholder")  # "-" -> "默认占位符" 或 "-"

                if not cmd_str:
                    cmd_str = i18n.get("msg_default_placeholder")  # "-" -> "默认占位符" 或 "-"

                # 绘制行
                # 键名
                ctk.CTkLabel(
                    self.scroll_frame,
                    text=name,
                    anchor="w",
                    font=ctk.CTkFont(family="Consolas", size=12)  # 使用等宽字体方便阅读长名
                ).grid(row=row_idx, column=0, padx=15, pady=8, sticky="w")

                # 事件类型
                ctk.CTkLabel(
                    self.scroll_frame,
                    text=event_str,
                    anchor="w",
                    text_color="#7f8c8d"
                ).grid(row=row_idx, column=1, padx=15, pady=8, sticky="w")

                # 虚拟键码 (高亮显示)
                ctk.CTkLabel(
                    self.scroll_frame,
                    text=str(key_val),
                    anchor="w",
                    font=ctk.CTkFont(weight="bold"),
                    text_color="#e67e22"
                ).grid(row=row_idx, column=2, padx=15, pady=8, sticky="w")

                # Intent Action (蓝色)
                ctk.CTkLabel(
                    self.scroll_frame,
                    text=action_str,
                    anchor="w",
                    text_color="#3498db",
                    font=ctk.CTkFont(size=12)
                ).grid(row=row_idx, column=3, padx=15, pady=8, sticky="w")

                # 默认命令 (灰色)
                ctk.CTkLabel(
                    self.scroll_frame,
                    text=cmd_str,
                    anchor="w",
                    text_color="#95a5a6",
                    font=ctk.CTkFont(size=12)
                ).grid(row=row_idx, column=4, padx=15, pady=8, sticky="w")

                row_idx += 1

            # 可选：如果没有数据但循环没执行（理论上不会到这里）
            # if row_idx == 1:
            #     ctk.CTkLabel(self.scroll_frame, text=i18n.get("msg_no_valid_configs"), text_color="gray").grid(row=1, column=0, columnspan=5)

        except Exception as e:
            print(f"刷新配置视图出错: {e}")
            if self.winfo_exists():
                # 错误信息国际化
                err_lbl = ctk.CTkLabel(
                    self.scroll_frame,
                    text=i18n.get("msg_load_failed") + f": {str(e)}",
                    text_color="#c0392b"
                )
                err_lbl.grid(row=0, column=0, pady=20)

    def on_closing(self) -> None:
        if self.backend and self.is_listening:
            self.append_log("\n[Info] Stopping listening to close the program....\n")
            self.backend.stop_capture()
        time.sleep(0.5)
        self.destroy()

    def on_login_type_change(self, selected_val: str) -> None:
        """登录方式切换回调：更新预览 + 修改slclient.json"""
        self._update_preview("login_type", selected_val)

        if update_slclient_login_type(selected_val):
            self.append_log(f"[OK] The login method  changed to:{selected_val}\n")
            # self.status_label.configure(
            #     text=f"登录方式已更新为\n"
            #          f"{selected_val}",
            #     text_color="#27ae60"
            # )
        else:
            self.append_log(f"[Error] Failed to update the login mode: {selected_val}\n")

    def on_apk_type_change(self, value: str) -> None:
        self.current_apk_type = value
        # self.status_label.configure(text=f"状态：已选择 {value} APK", text_color="#d35400")
        self.append_log(f"[Info] APK type switched to：{value}\n")

    def _init_build_config_page(self, parent):
        """初始化打包配置页面"""
        # 主标题
        self.lbl_title = ctk.CTkLabel(
            parent,
            text=(_("msg_card_apk_properties")),  # 统一使用 i18n.get
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.lbl_title.pack(pady=(15, 10))

        # --- 主容器：使用 Grid 布局实现 2x2 ---
        # 错误修复：这里原来是 self.tab_build_config，现在改为使用传入的 parent
        grid_frame = ctk.CTkFrame(parent, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # 配置行列权重，确保四等分
        grid_frame.grid_columnconfigure(0, weight=1)
        grid_frame.grid_columnconfigure(1, weight=1)
        grid_frame.grid_rowconfigure(0, weight=1)
        grid_frame.grid_rowconfigure(1, weight=1)

        # --- 创建四个子模块卡片 ---
        # 1. 左上：环境配置
        self.frame_env = self._create_config_card(
            parent=grid_frame,
            # title="🌍 环境配置 (Environment)",
            title=i18n.get("msg_card_env"),
            row=0, col=0,
            content_func=self._build_env_content
        )
        # 2. 右上：声音配置
        self.frame_sound = self._create_config_card(
            parent=grid_frame,
            title=i18n.get("msg_card_sound"),
            row=0, col=1,
            content_func=self._build_sound_content
        )
        # 3. 左下：地图配置
        self.frame_map = self._create_config_card(
            parent=grid_frame,
            title=i18n.get("msg_card_map"),
            row=1, col=0,
            content_func=self._build_map_content
        )
        # 4. 右下：其他设置
        self.frame_other = self._create_config_card(
            parent=grid_frame,
            title=i18n.get("msg_card_other"),
            row=1, col=1,
            content_func=self._build_other_content
        )

        # 初始化时加载一次默认值
        self.after(500, self.load_all_configs)

    def _init_led_config_page(self, parent):
        """初始化按键LED配置页面 (修复版)"""
        # 1. 主标题
        self.lbl_input_title = ctk.CTkLabel(
            parent, text=_("msg_tab_input"), font=ctk.CTkFont(size=18, weight="bold")
        )
        self.lbl_input_title.pack(pady=(15, 10))

        # 2. 主容器：使用 Grid 布局实现 上下 1:1 平分
        # 错误修复：这里原来是 self.tab_input_led_config，现在改为使用传入的 parent
        grid_frame = ctk.CTkFrame(parent, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # 【关键步骤】配置行列权重
        grid_frame.grid_columnconfigure(0, weight=1)
        grid_frame.grid_rowconfigure(0, weight=1)
        grid_frame.grid_rowconfigure(1, weight=1)

        # 3. 创建上下两个子模块卡片
        # --- 上半部分：LED 模式/策略配置 ---
        self.frame_led_mode = self._create_config_card(
            parent=grid_frame,
            title=_("msg_card_input"),
            row=0, col=0,
            content_func=self._build_input_mode_content
        )
        self.title_led_mode = self.frame_led_mode.winfo_children()[0]
        # --- 下半部分：颜色与亮度配置 ---
        self.frame_led_color = self._create_config_card(
            parent=grid_frame,
            title=_("msg_card_other"),
            # title=_("msg_card_led"),
            row=1, col=0,
            content_func=self._build_led_color_content
        )

        # 4. 初始化加载 (可选)
        # self.after(500, self.load_led_configs)

    # 弹窗语言自定义
    def show_custom_message(self, title, message):
        win = ctk.CTkToplevel(self)
        win.title(title)
        win.geometry("320x160")
        win.resizable(False, False)

        win.attributes("-topmost", True)
        win.grab_set()

        # ===== 字体统一 =====
        title_font = ctk.CTkFont(size=15, weight="bold")
        text_font = ctk.CTkFont(size=13, weight="bold")

        # # ===== 标题 =====
        # title_label = ctk.CTkLabel(win, text=title, font=title_font)
        # title_label.pack(pady=(15, 5))

        # ===== 内容 =====
        label = ctk.CTkLabel(win, text=message, font=text_font, wraplength=280)
        label.pack(pady=10)

        # ===== 按钮 =====
        btn = ctk.CTkButton(
            win,
            text=_("btn_ok"),
            font=text_font,
            width=80,
            command=win.destroy
        )
        btn.pack(pady=10)

        # ===== 居中 =====
        win.update_idletasks()
        w, h = win.winfo_width(), win.winfo_height()
        x = (win.winfo_screenwidth() // 2) - (w // 2)
        y = (win.winfo_screenheight() // 2) - (h // 2)
        win.geometry(f"{w}x{h}+{x}+{y}")

        # ===== 提升到最前（防止被遮挡）=====
        win.lift()
        win.focus_force()

        # 回车关闭
        win.after(10, lambda: win.attributes("-topmost", False))
        # ESC关闭
        win.bind("<Return>", lambda e: win.destroy())

    def _init_terminal_config(self, parent):
        self.apk_title_label = ctk.CTkLabel(
            parent,
            text=_("msg_terminal_config_title"),
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.apk_title_label.pack(pady=(20, 10))

        # 搜索框
        search_frame = ctk.CTkFrame(parent, fg_color="transparent")
        search_frame.pack(pady=5, fill="x", padx=20)

        self.terminal_search_var = ctk.StringVar()

        search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text=_("placeholder_search_terminal"),
            textvariable=self.terminal_search_var,
            width=200
        )
        search_entry.pack(pady=5)

        # 滚动区域
        self.terminal_scroll_frame = ctk.CTkScrollableFrame(parent, width=800, height=500)
        self.terminal_scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # 数据 - 分别存储全部文件夹和显示的文件夹
        self.terminal_all_folders = []
        self.current_displayed_folders = []

        self._load_terminal_folders()

        # 绑定搜索（加防抖）
        self._search_after_id = None
        self.terminal_search_var.trace_add("write", self._on_search_change)
        search_entry.bind('<Return>', lambda e: self._filter_terminal_folders())

    def _load_terminal_folders(self):
        folder_path = "terminal_configs"
        Path(folder_path).mkdir(exist_ok=True)

        # 只在首次加载时扫描目录，后续使用缓存
        self.terminal_all_folders = [
            f for f in Path(folder_path).iterdir() if f.is_dir()
        ]

        # 初始化显示所有文件夹
        self.current_displayed_folders = self.terminal_all_folders.copy()
        self._render_terminal_folders(self.current_displayed_folders)

        # 根据当前搜索状态决定显示哪些文件夹
        search_term = self.terminal_search_var.get().lower()
        if not search_term:
            self.current_displayed_folders = self.terminal_all_folders.copy()
        else:
            self.current_displayed_folders = [
                f for f in self.terminal_all_folders
                if search_term in f.name.lower()
            ]

        self._render_terminal_folders(self.current_displayed_folders)

    def _render_terminal_folders(self, folders):
        # 清空 UI
        for widget in self.terminal_scroll_frame.winfo_children():
            widget.destroy()

        for index, folder in enumerate(folders):
            row = index // 6
            col = index % 6

            icon_frame = ctk.CTkFrame(
                self.terminal_scroll_frame,
                width=120,
                height=140,
                corner_radius=10
            )
            icon_frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

            self.terminal_scroll_frame.grid_columnconfigure(col, weight=1)

            # 图标
            ctk.CTkLabel(
                icon_frame,
                text="📁",
                font=ctk.CTkFont(size=24)
            ).pack(pady=(10, 5))

            # 名称
            name_label = ctk.CTkLabel(
                icon_frame,
                text=folder.name[:10] + ("..." if len(folder.name) > 10 else ""),
                font=ctk.CTkFont(size=12),
                wraplength=100
            )
            name_label.pack(pady=(0, 5))

            use_btn = ctk.CTkButton(
                icon_frame,
                text=_("use_btn"),
                width=80,
                height=25,
                command=lambda f=folder: self._use_terminal_config(f),
                fg_color="#1f6aa0",
                hover_color="#144870"
            )
            use_btn.pack(pady=(0, 10))
            self.use_btn = use_btn

        self.terminal_scroll_frame.update_idletasks()

    def _filter_terminal_folders(self):
        search_term = self.terminal_search_var.get().lower()

        if not search_term:
            self.current_displayed_folders = self.terminal_all_folders.copy()
        else:
            self.current_displayed_folders = [
                f for f in self.terminal_all_folders
                if search_term in f.name.lower()
            ]

        self._render_terminal_folders(self.current_displayed_folders)

        # 强制滚动到顶部
        self.after_idle(lambda: self.terminal_scroll_frame._parent_canvas.yview_moveto(0))

    def _on_search_change(self, *args):
        if self._search_after_id:
            self.after_cancel(self._search_after_id)

        self._search_after_id = self.after(50, self._filter_terminal_folders)



    def _use_terminal_config(self, folder_path):
        """
        使用终端配置替换到app_out中
        """
        # print(f"使用终端配置:{folder_path.name}")
        if not PATH_SLCLIENT_JSON.exists():
            messagebox.showerror("ERROR", f"Please unzip apk first")
            return False
        self.copy_terminal_files(folder_path)
        self.load_all_configs()
        self.load_and_echo_config_after_unzip()
        self.is_import = True

    def copy_terminal_files(self, folder_path):
        """
        点击按钮覆盖app_out
        """
        source_dir = Path(folder_path)

        # ===== 源路径 =====
        slclient_json = source_dir / "slclient.json"
        slclient_dir = source_dir / "slclient"
        led_json = slclient_dir / "led.json"
        input_json = slclient_dir / "input.json"
        reaction_json = slclient_dir / "reaction.json"

        try:
            # # ===== 检查源文件 =====
            # if not slclient_json.exists():
            #     raise FileNotFoundError(f"缺少文件: {slclient_json}")
            # if not led_json.exists():
            #     raise FileNotFoundError(f"缺少文件: {led_json}")
            # if not input_json.exists():
            #     raise FileNotFoundError(f"缺少文件: {input_json}")
            #
            # # ===== 检查目标目录 =====
            # if not PATH_ASS.exists():
            #     raise FileNotFoundError(f"目标目录不存在: {PATH_ASS}")
            #
            # if not PATH_SLCLIENT_JSON.exists():
            #     raise FileNotFoundError(f"目标目录不存在: {PATH_SLCLIENT_JSON}")

            # ===== 拷贝文件 =====
            shutil.copy2(slclient_json, PATH_ASS / "slclient.json")
            # print(f"[success] {slclient_json} -> {PATH_ASS}\n")

            shutil.copy2(led_json, PATH_SLCLIENT / "led.json")
            # print(f"[success] {led_json} -> {PATH_SLCLIENT}\n")

            shutil.copy2(input_json, PATH_SLCLIENT / "input.json")
            # print(f"[success] {input_json} -> {PATH_SLCLIENT}\n")

            shutil.copy2(reaction_json, PATH_SLCLIENT / "reaction.json")
            # print(f"[success] {input_json} -> {PATH_SLCLIENT}\n")

            self.append_log(f"[success] Imported {folder_path.name} Successfully\n")
            self.show_custom_message("Success", f"Imported \n"
                                                f"\n{folder_path.name}\n"
                                                f"\nSuccessfully !")

        except Exception as e:
            self.append_log(f"[ERROR]: {e}")

    def _build_input_mode_content(self, parent):
        """构建手动配置 PTT/SOS 按键的 UI (样式统一版)"""

        # --- 统一样式配置 ---
        label_width = 80
        entry_height = 32
        pad_x = 10
        pad_y = 8
        sticky_label = "w"
        sticky_entry = "ew"

        # --- 1. 按下 PTT (Press) ---
        self.lbl_ptt_press = ctk.CTkLabel(
            parent,
            text=_("lbl_ptt_press"),
            anchor="w",
            width=label_width
        )
        self.lbl_ptt_press.grid(row=0, column=0, padx=(pad_x, 5), pady=(pad_y, 2), sticky=sticky_label)

        self.entry_ptt_press = ctk.CTkEntry(
            parent,
            placeholder_text="Action for PTT_DOWN",
            height=entry_height
        )
        self.entry_ptt_press.grid(row=0, column=1, padx=(5, pad_x), pady=(pad_y, 2), sticky=sticky_entry)

        # --- 2. 抬起 PTT (Release) ---
        self.lbl_ptt_release = ctk.CTkLabel(
            parent,
            text=_("lbl_ptt_release"),
            anchor="w",
            width=label_width
        )
        self.lbl_ptt_release.grid(row=1, column=0, padx=(pad_x, 5), pady=2, sticky=sticky_label)

        self.entry_ptt_release = ctk.CTkEntry(
            parent,
            placeholder_text="Action for PTT_UP",
            height=entry_height
        )
        self.entry_ptt_release.grid(row=1, column=1, padx=(5, pad_x), pady=2, sticky=sticky_entry)

        # --- 3. SOS 按键 ---
        self.lbl_sos_key = ctk.CTkLabel(
            parent,
            text=_("lbl_sos_key"),
            anchor="w",
            width=label_width
        )
        self.lbl_sos_key.grid(row=2, column=0, padx=(pad_x, 5), pady=2, sticky=sticky_label)

        self.entry_sos = ctk.CTkEntry(
            parent,
            placeholder_text="Action for SOS",
            height=entry_height
        )
        self.entry_sos.grid(row=2, column=1, padx=(5, pad_x), pady=2, sticky=sticky_entry)

        # --- 4. 保存按钮 ---

        self.btn_save_config = ctk.CTkButton(
            parent,
            text=_("btn_save_config"),
            command=self._on_save_manual_keys,
            fg_color="#28a745",
            hover_color="#218838",
            height=28,
            width=25,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.btn_save_config.grid(row=3, column=0, columnspan=2, padx=pad_x, pady=(pad_y, 10), sticky="e")

        # 状态提示
        self.lbl_env_info = ctk.CTkLabel(
            parent,
            text="",
            text_color="gray",
            font=ctk.CTkFont(size=10),
            anchor="w"
        )
        self.lbl_env_info.grid(row=4, column=0, columnspan=2, padx=pad_x, pady=(pad_y, 10), sticky="w")

        # --- 布局权重配置 ---
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=0)

    def _on_save_manual_keys(self):
        """
        手动保存按键配置到 input.json
        支持：仅保存 PTT、仅保存 SOS、或同时保存
        """

        # 1. 获取输入值
        val_press = self.entry_ptt_press.get().strip()
        val_release = self.entry_ptt_release.get().strip()
        val_sos = self.entry_sos.get().strip()

        # 标记是否有有效输入
        has_ptt = bool(val_press and val_release)
        has_sos = bool(val_sos)

        # 【核心修改】组合校验：必须至少有一组有效数据
        if not has_ptt and not has_sos:
            self.lbl_env_info.configure(
                text="❌ 错误：请至少填写 PTT (按下 + 抬起) 或 SOS 其中一项！",
                text_color="#c0392b",
                font=ctk.CTkFont(size=12, weight="bold")
            )
            return

        # 如果只填了 PTT 的一部分，提示错误
        if (val_press and not val_release) or (not val_press and val_release):
            self.lbl_env_info.configure(
                text="❌ 错误：请输入 PTT 的按下和抬起 Action！",
                text_color="#c0392b",
                font=ctk.CTkFont(size=12, weight="bold")
            )
            return

        # 预初始化变量，防止未定义错误
        name_sos_down = None
        name_sos_up = None
        new_vkey_sos = None
        name_ptt_down = None
        name_ptt_up = None
        new_vkey_ptt = None

        try:
            # 2. 生成唯一标识
            timestamp_suffix = datetime.now().strftime("%Y%m%d%H%M%S")

            # 虚拟键码生成逻辑
            existing_codes = set()
            if os.path.exists(JSON_FILE):
                try:
                    with open(JSON_FILE, 'r', encoding='utf-8') as f:
                        temp_data = json.load(f)
                        for k, v in temp_data.get("stdkey", {}).items():
                            if isinstance(v.get("key"), int):
                                existing_codes.add(v["key"])
                except:
                    pass

            # --- 动态分配键码 ---
            # 只有当需要生成该配置时，才分配键码
            if has_ptt:
                new_vkey_ptt = -1000
                while new_vkey_ptt in existing_codes:
                    new_vkey_ptt -= 1
                existing_codes.add(new_vkey_ptt)

            if has_sos:
                new_vkey_sos = -1000
                while new_vkey_sos in existing_codes:
                    new_vkey_sos -= 1

            # 3. 构建新配置数据
            new_entries = {"stdkey": {}, "action": {}, "intent": {}}

            # --- A. 构建 PTT 配置 (如果有效) ---
            if has_ptt:
                name_ptt_down = f"many_ptt_down_{timestamp_suffix}"
                name_ptt_up = f"ptt_up_{timestamp_suffix}"

                new_entries["stdkey"][name_ptt_down] = {"event": "KEY_DOWN", "key": new_vkey_ptt}
                new_entries["stdkey"][name_ptt_up] = {"event": "KEY_UP", "key": new_vkey_ptt}

                new_entries["action"][name_ptt_down] = {
                    "default": [],
                    "member": [],
                    "new_call_in": []
                }
                new_entries["action"][name_ptt_up] = {
                    "default": [{"command": {"id": "STOP_SPEAK"}}],
                    "member": [],
                    "new_call_in": []
                }

                new_entries["intent"][name_ptt_down] = {"action": val_press}
                new_entries["intent"][name_ptt_up] = {"action": val_release}

            # --- B. 构建 SOS 配置 (如果有效) ---
            if has_sos:
                name_sos_down = f"sos_down_{timestamp_suffix}"
                name_sos_up = f"sos_up_{timestamp_suffix}"

                new_entries["stdkey"][name_sos_down] = {"event": "KEY_CLICK", "key": new_vkey_sos, "time": 3000}
                new_entries["stdkey"][name_sos_up] = {"event": "KEY_CLICK", "key": new_vkey_sos, "time": 3000}

                new_entries["intent"][name_sos_down] = {"action": val_sos}
                new_entries["intent"][name_sos_up] = {"action": val_sos}

            # 4. 读取并合并 input.json
            data = {}
            if os.path.exists(JSON_FILE):
                try:
                    with open(JSON_FILE, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except json.JSONDecodeError:
                    data = {"stdkey": {}, "action": {}, "intent": {}, "custom": []}
            else:
                data = {"stdkey": {}, "action": {}, "intent": {}, "custom": []}

            for k in ["stdkey", "action", "intent"]:
                if k not in data:
                    data[k] = {}
            if "custom" not in data:
                data["custom"] = []

            data["stdkey"].update(new_entries["stdkey"])
            data["action"].update(new_entries["action"])
            data["intent"].update(new_entries["intent"])

            # 5. 写回文件
            with open(JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # 保存成功后清空输入框
            if has_ptt:
                self.entry_ptt_press.delete(0, "end")
                self.entry_ptt_release.delete(0, "end")

            if has_sos:
                self.entry_sos.delete(0, "end")

            # 6. 成功反馈
            msg_lines = [f"✅ Configuration is saved"]
            if has_ptt:
                msg_lines.append(f"   🟢 PTT Key: {new_vkey_ptt} ({name_ptt_down}, {name_ptt_up})")
            if has_sos:
                msg_lines.append(f"   🔴 SOS Key: {new_vkey_sos} ({name_sos_down}, {name_sos_up})")

            final_msg = "\n".join(msg_lines)

            # self.lbl_env_info.configure(
            #     text="✅ 保存成功!",
            #     text_color="#27ae60",
            #     font=ctk.CTkFont(size=12, weight="bold")
            # )
            self.append_log(f"[Manual Save] {final_msg}\n")
            self.show_custom_message("Successfully", final_msg)

            if hasattr(self, '_safe_refresh_config_view'):
                self._safe_refresh_config_view()
            elif hasattr(self, 'refresh_config_view'):
                self.refresh_config_view()

        except Exception as e:
            error_msg = f"❌ ERROR：{str(e)}"
            self.lbl_env_info.configure(
                text=error_msg,
                text_color="#c0392b",
                font=ctk.CTkFont(size=12, weight="bold")
            )
            self.append_log(f"[Error] _on_save_manual_keys: {e}\n")
            messagebox.showerror("ERROR", error_msg)

    def _build_led_color_content(self, parent):
        """填充下半部分：颜色和亮度"""
        self.lbl_other = ctk.CTkLabel(
            parent,
            text=_("msg_feature_dev"),
            text_color="gray"
        )
        self.lbl_other.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="w")

        # ctk.CTkLabel(parent, text="LED 颜色 (Hex):", anchor="w").grid(row=0, column=0, sticky="w", pady=5)
        # self.entry_led_color = ctk.CTkEntry(parent, placeholder_text="#FF0000")
        # self.entry_led_color.grid(row=1, column=0, sticky="ew", pady=5)
        # self.entry_led_color.insert(0, "#00FF00")
        #
        # ctk.CTkLabel(parent, text="亮度 (0-255):", anchor="w").grid(row=2, column=0, sticky="w", pady=5)
        # self.slider_led_brightness = ctk.CTkSlider(parent, from_=0, to=255, number_of_steps=255)
        # self.slider_led_brightness.grid(row=3, column=0, sticky="ew", pady=5)
        # self.slider_led_brightness.set(200)

    def _create_config_card(self, parent, title, row, col, content_func):
        """辅助函数：创建一个带标题的卡片容器"""
        card = ctk.CTkFrame(parent, corner_radius=10, border_width=1, border_color="#3B8ED0")
        card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)  # 内容区域扩展

        # ✅ 每个卡片自带标题标签，永远可以更新
        card.title_label = ctk.CTkLabel(
            card, text=title, font=ctk.CTkFont(size=14, weight="bold"), anchor="w"
        )
        card.title_label.grid(row=0, column=0, padx=15, pady=10, sticky="w")

        content_frame = ctk.CTkFrame(card, fg_color="transparent")
        content_frame.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")
        content_frame.grid_columnconfigure(1, weight=1)
        content_func(content_frame)
        return card

    def _build_env_content(self, parent):
        """构建环境配置内容"""
        current_lang = i18n.current_lang

        base_options = []
        for key in ENV_CONF.keys():
            # 从 ENV_DISPLAY_NAMES 中取出对应的中文或英文显示名
            display_name = ENV_DISPLAY_NAMES.get(key, {}).get(current_lang, key)
            base_options.append(display_name)

        self.CUSTOM_OPTION_NAME = _("env_custom")

        # --- 2. 创建控件 ---

        # 标签
        self.lbl_server_node = ctk.CTkLabel(parent, text=_("lbl_server_node"), anchor="w")
        self.lbl_server_node.grid(
            row=0, column=0, padx=5, pady=10, sticky="w"
        )

        # 下拉菜单
        self.opt_env = ctk.CTkOptionMenu(
            parent,
            values=base_options,
            command=self._on_env_selected
        )
        self.opt_env.grid(row=0, column=1, padx=5, pady=10, sticky="ew")

        # 操作模式开关（隐藏，仅作为扩展）
        self.switch_custom_env = ctk.CTkSwitch(
            parent,
            text="启用手动编辑",
            command=self._toggle_custom_env_inputs,
            fg_color="#d35400",
            state="disabled"
        )
        self.switch_custom_env.grid_remove()

        self.env_custom = ctk.CTkLabel(parent, text=_("env_custom"), anchor="w")
        self.env_custom.grid(
            row=3, column=0, padx=5, pady=(5, 2), sticky="w"
        )

        # DNS 输入框
        ctk.CTkLabel(parent, text="DNS IP:", anchor="w").grid(
            row=4, column=0, padx=5, pady=(5, 2), sticky="w"
        )

        self.entry_custom_ip = ctk.CTkEntry(parent, state="normal")
        self.entry_custom_ip.grid(row=4, column=1, padx=5, pady=(5, 2), sticky="ew")

        # Context 输入框
        ctk.CTkLabel(parent, text="Context:", anchor="w").grid(
            row=5, column=0, padx=5, pady=(2, 10), sticky="w"
        )

        self.entry_custom_context = ctk.CTkEntry(parent, state="normal")
        self.entry_custom_context.grid(row=5, column=1, padx=5, pady=(2, 10), sticky="ew")

        # upgrade_url 输入框
        ctk.CTkLabel(parent, text="upgrade url:", anchor="w").grid(
            row=6, column=0, padx=5, pady=(2, 10), sticky="w"
        )

        self.entry_custom_upgrade = ctk.CTkEntry(parent, state="normal")
        self.entry_custom_upgrade.grid(row=6, column=1, padx=5, pady=(2, 10), sticky="ew")

        self.entry_custom_ip.bind("<FocusIn>", lambda e: self.on_dns_entry_focus_in(e))
        self.entry_custom_ip.bind("<FocusOut>", self.on_dns_entry_focus_out)

        self.entry_custom_context.bind("<FocusIn>", lambda e: self.on_context_entry_focus_in(e))
        self.entry_custom_context.bind("<FocusOut>", self.on_context_entry_focus_out)

        self.entry_custom_upgrade.bind("<FocusIn>", lambda e: self.on_upgrade_entry_focus_in(e))
        self.entry_custom_upgrade.bind("<FocusOut>", self.on_upgrade_entry_focus_out)

        # 回显默认文字
        # self.entry_custom_context.configure(state="normal")
        # self.entry_custom_context.delete(0, 'end')
        # self.entry_custom_context.insert(0, "demotext")
        # self.entry_custom_context.configure(state="disabled")

        # 登录方式下拉框
        self.lbl_login_type = ctk.CTkLabel(parent, text=_("lbl_login_type"), anchor="w")
        self.lbl_login_type.grid(
            row=2, column=0, padx=5, pady=10, sticky="w"
        )

        login_type_display_names = [LOGIN_TYPE_MAPPING[key][i18n.current_lang] for key in LOGIN_TYPE_MAPPING.keys()]
        self.opt_login_type = ctk.CTkOptionMenu(
            parent,
            values=login_type_display_names,  # 使用动态生成的列表
            command=self.on_login_type_change
        )
        # self.opt_login_type.set("账号登录")
        self.opt_login_type.grid(row=2, column=1, padx=5, pady=10, sticky="ew")

        # 保存按钮
        self.btn_save_custom = ctk.CTkButton(
            parent,
            text=_("msg_save_btn"),
            command=self._save_profile_changes,
            fg_color="#d35400",
            hover_color="#e67e22",
            height=28,
            font=ctk.CTkFont(weight="bold")
        )
        self.btn_save_custom.grid(row=7, column=0, columnspan=2, padx=5, pady=10, sticky="e")
        # 状态提示
        self.lbl_env_info = ctk.CTkLabel(
            parent,
            text="",
            text_color="gray",
            font=ctk.CTkFont(size=10),
            anchor="w"
        )
        self.lbl_env_info.grid(row=5, column=0, columnspan=2, padx=5, pady=(5, 10), sticky="w")

        saved = self.opt_env.get()

        if saved in base_options:
            self._on_env_selected(saved)
            return

        if base_options:
            self.opt_env.set(base_options[0])
            self._on_env_selected(base_options[0])

        else:
            self.opt_env.set(self.CUSTOM_OPTION_NAME)
            self._on_env_selected(self.CUSTOM_OPTION_NAME)

    def load_and_echo_config_after_unzip(self):
        """
        解压完成后从slclient.json加载配置并回显到输入框，以灰色字体显示
        """
        config_data = self._load_slclient_json()

        # 获取profile节点下的配置
        profile_config = config_data.get("profile", {})

        dns_list = profile_config.get("dns", [])
        if dns_list and isinstance(dns_list, list):
            first_dns = dns_list[0] if dns_list else ""
            if first_dns:
                self.entry_custom_ip.delete(0, "end")
                self.entry_custom_ip.insert(0, first_dns)
                self.entry_custom_ip.configure(text_color="gray")
                self.original_dns_value = first_dns

        context_value = profile_config.get("context", "")
        if context_value:
            self.entry_custom_context.delete(0, "end")
            self.entry_custom_context.insert(0, context_value)
            self.entry_custom_context.configure(text_color="gray")
            self.original_context_value = context_value

        upgrade_url = profile_config.get("upgrade_url", "")
        if upgrade_url:
            self.entry_custom_upgrade.delete(0, "end")
            self.entry_custom_upgrade.insert(0, upgrade_url)
            self.entry_custom_upgrade.configure(text_color="gray")
            self.original_upgrade_url = upgrade_url

        self.append_log("Configuration loaded and echoed successfully.\n")

    def on_dns_entry_focus_in(self, event):
        """DNS输入框获得焦点时的处理"""
        if self.entry_custom_ip.cget("text_color") == "gray":
            self.entry_custom_ip.delete(0, "end")
            self.entry_custom_ip.configure(text_color="black")

    def on_dns_entry_focus_out(self, event):
        """DNS输入框失去焦点时的处理 - 如果没有输入任何内容，恢复原始配置值"""
        current_content = self.entry_custom_ip.get().strip()
        if current_content == "":
            if hasattr(self, 'original_dns_value') and self.original_dns_value:
                self.entry_custom_ip.delete(0, "end")
                self.entry_custom_ip.insert(0, self.original_dns_value)
                self.entry_custom_ip.configure(text_color="gray")

    def on_context_entry_focus_in(self, event):
        """Context输入框获得焦点时的处理"""
        if self.entry_custom_context.cget("text_color") == "gray":
            self.entry_custom_context.delete(0, "end")
            self.entry_custom_context.configure(text_color="black")

    def on_context_entry_focus_out(self, event):
        """Context输入框失去焦点时的处理 - 如果没有输入任何内容，恢复原始配置值"""
        current_content = self.entry_custom_context.get().strip()
        if current_content == "":
            if hasattr(self, 'original_context_value') and self.original_context_value:
                self.entry_custom_context.delete(0, "end")
                self.entry_custom_context.insert(0, self.original_context_value)
                self.entry_custom_context.configure(text_color="gray")

    def on_upgrade_entry_focus_in(self, event):
        """Upgrade URL输入框获得焦点时的处理"""
        if self.entry_custom_upgrade.cget("text_color") == "gray":
            self.entry_custom_upgrade.delete(0, "end")
            self.entry_custom_upgrade.configure(text_color="black")

    def on_upgrade_entry_focus_out(self, event):
        """Upgrade URL输入框失去焦点时的处理 - 如果没有输入任何内容，恢复原始配置值"""
        current_content = self.entry_custom_upgrade.get().strip()
        if current_content == "":
            if hasattr(self, 'original_upgrade_url') and self.original_upgrade_url:
                self.entry_custom_upgrade.delete(0, "end")
                self.entry_custom_upgrade.insert(0, self.original_upgrade_url)
                self.entry_custom_upgrade.configure(text_color="gray")
            # else:
            #     self.entry_custom_upgrade.delete(0, "end")
            #     self.entry_custom_upgrade.insert(0, "请输入升级URL")
            #     self.entry_custom_upgrade.configure(text_color="gray")

    def _save_profile_changes(self):
        """
        将当前输入的 IP 和 Context 保存到 slclient.json 的 profile 节点中。
        专用于【独立部署】模式，不影响 ENV_CONF 中的预设节点（如海外/国内）。
        """
        if not PATH_SLCLIENT_JSON.exists():
            messagebox.showerror("ERROR", f"Please unzip apk first")
            return False

        new_ip = self.entry_custom_ip.get().strip()
        new_context = self.entry_custom_context.get().strip()
        upgrade_url = self.entry_custom_upgrade.get().strip()

        # 1. 基础验证：必须同时存在 IP 和 Context
        if not new_ip or not new_context:
            messagebox.showwarning("Error", "IP and Context must be entered！")
            return

        # 2. 格式验证（保持不变）
        # ip_part = new_ip.split(':')[0]
        # if not re.match(r'^\d{1,3}(\.\d{1,3}){3}$', ip_part) and not re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        #                                                                       ip_part):
        #     if not messagebox.askyesno("格式确认",
        #                                f"检测到的 IP/域名 '{new_ip}' 格式可能不标准。\n" f"确定要保存到独立部署配置吗？"):
        #         return

        try:
            json_path = PATH_SLCLIENT_JSON
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 3. 定位并修改 profile 节点
            if "profile" not in data:
                data["profile"] = {}

            profile = data["profile"]

            profile["context"] = new_context
            profile["dns"] = [new_ip]

            # ⭐⭐⭐ 核心修改：仅当 upgrade_url 非空时才更新 ⭐⭐⭐
            if upgrade_url:
                profile["upgrade_url"] = upgrade_url

            # 5. 写回文件
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            self.show_custom_message("Successfully", "saved successfully")

        except FileNotFoundError:
            error_msg = "❌ 错误：找不到配置文件路径。"
            self.lbl_env_info.configure(text=error_msg, text_color="#c0392b")
            messagebox.showerror("路径错误", error_msg)
        except PermissionError:
            error_msg = "❌ 错误：没有权限写入文件，请以管理员身份运行。"
            self.lbl_env_info.configure(text=error_msg, text_color="#c0392b")
            messagebox.showerror("权限错误", error_msg)
        except Exception as e:
            error_msg = f"❌ 保存失败: {str(e)}"
            self.lbl_env_info.configure(text=error_msg, text_color="#c0392b")
            messagebox.showerror("未知错误", error_msg)
            print(f"Save Error Details: {e}")

    def _build_sound_content(self, parent):
        """构建声音配置内容"""
        # 1. 背景音乐音量
        # ctk.CTkLabel(parent, text="BGM 音量:", anchor="w").grid(row=0, column=0, padx=5, pady=8, sticky="w")
        # self.slider_bgm = ctk.CTkSlider(parent, from_=0, to=100, number_of_steps=100,
        #                                 command=lambda v: self._update_preview("bgm", int(v)))
        # self.slider_bgm.grid(row=0, column=1, padx=5, pady=8, sticky="ew")
        # self.slider_bgm.set(80)  # 默认 80%
        #
        # lbl_bgm_val = ctk.CTkLabel(parent, text="80%", width=40, anchor="w")
        # lbl_bgm_val.grid(row=0, column=2, padx=5, pady=8, sticky="w")
        # # 绑定更新标签
        # self.slider_bgm.configure(
        #     command=lambda v: (self._update_preview("bgm", int(v)), lbl_bgm_val.configure(text=f"{int(v)}%")))

        # 2. 音效开关
        ctk.CTkLabel(parent, text="Tone:", anchor="w").grid(row=1, column=0, padx=5, pady=8, sticky="w")
        self.switch_tone_sfx = ctk.CTkSwitch(parent, text=" ",
                                             command=lambda: (
                                                 self._sync_tone_enabled_to_json(bool(self.switch_tone_sfx.get()))
                                             ))
        self.switch_tone_sfx.grid(row=1, column=1, padx=5, pady=6, sticky="w")
        self.switch_tone_sfx.select()  # 默认开启

        # 3. 语音编码
        self.codec = ctk.CTkLabel(parent, text=_("codec"), anchor="w")
        self.codec.grid(
            row=2, column=0, padx=5, pady=10, sticky="w"
        )

        self.opt_codec = ctk.CTkOptionMenu(
            parent,
            values=["amrnb", "evrc8k", "opus"],
            command=self._sync_codec_to_json
        )
        self.opt_codec.grid(row=2, column=1, padx=5, pady=8, sticky="ew")

        self.opt_codec.set("amrnb")

        # 4. 音频系统
        self.audio = ctk.CTkLabel(parent, text=_("audio"), anchor="w")
        self.audio.grid(
            row=3, column=0, padx=5, pady=10, sticky="w"
        )

        self.opt_audio = ctk.CTkOptionMenu(
            parent,
            values=["default", "sles", "oem"],
            command=self._sync_soundsystem_to_json
        )
        self.opt_audio.grid(row=3, column=1, padx=5, pady=8, sticky="ew")

        self.opt_audio.set("default")

        # 5. 播放通道
        self.play_channel = ctk.CTkLabel(parent, text=_("play_channel"), anchor="w")
        self.play_channel.grid(
            row=4, column=0, padx=5, pady=10, sticky="w"
        )

        self.opt_play = ctk.CTkOptionMenu(
            parent,
            values=["music", "voice"],
            command=self._sync_play_to_json
        )
        self.opt_play.grid(row=4, column=1, padx=5, pady=8, sticky="ew")

        self.opt_play.set("music")

        # 6. 录制通道
        self.rec_channel = ctk.CTkLabel(parent, text=_("rec_channel"), anchor="w")
        self.rec_channel.grid(
            row=5, column=0, padx=5, pady=8, sticky="w"
        )

        self.opt_rec = ctk.CTkOptionMenu(
            parent,
            values=["mic", "voice", "communication", "recognition"],
            command=self._sync_record_to_json
        )
        self.opt_rec.grid(row=5, column=1, padx=5, pady=10, sticky="ew")

        self.opt_rec.set("recognition")

    def _sync_codec_to_json(self, selected_codec: str) -> None:
        """
        【实时保存】当语音编码改变时，立即更新 slclient.json 中的 sound.codec
        :param selected_codec: 选中的编码字符串 (如 "amrnb", "opus")
        """
        if not PATH_SLCLIENT_JSON.exists():
            messagebox.showerror("ERROR", f"Please unzip apk first")
            return False
        try:
            data = self._load_slclient_json()

            if "sound" not in data:
                data["sound"] = {}

            current_val = data["sound"].get("codec")

            if current_val != selected_codec:
                data["sound"]["codec"] = selected_codec

                with open(PATH_SLCLIENT_JSON, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)

                self.append_log(f"[OK] Voice coding switched.: {selected_codec}\n")
                # self.status_label.configure(
                #     text=f"语音编码已切换为\n"
                #          f"{selected_codec}",
                #     text_color="#27ae60"
                # )
            else:
                pass

        except Exception as e:
            self.append_log(f"[Error] Failed to save speech coding.: {e}\n")

    def _sync_soundsystem_to_json(self, selected_codec: str) -> None:
        if not PATH_SLCLIENT_JSON.exists():
            messagebox.showerror("ERROR", f"Please unzip apk first")
            return False
        try:
            data = self._load_slclient_json()

            if "dsp" not in data:
                self.append_log("Error, SOUND node is missing")

            current_val = data["dsp"].get("provider")

            if current_val != selected_codec:
                data["dsp"]["provider"] = selected_codec

                with open(PATH_SLCLIENT_JSON, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)

                self.append_log(f"[OK] The audio system  switched.: {selected_codec}\n")
                # self.status_label.configure(
                #     text=f"音频系统已切换为\n"
                #          f"{selected_codec}",
                #     text_color="#27ae60"
                # )
            else:
                pass

        except Exception as e:
            self.append_log(f"[Error] Failed to save speech code: {e}\n")

    def _sync_play_to_json(self, selected_codec: str) -> None:
        if not PATH_SLCLIENT_JSON.exists():
            messagebox.showerror("ERROR", f"Please unzip apk first")
            return False
        try:
            data = self._load_slclient_json()

            if "dsp" not in data:
                self.append_log("Error, DSP node is missing")

            current_val = data["dsp"].get("play_stream")

            if current_val != selected_codec:
                data["dsp"]["play_stream"] = selected_codec

                with open(PATH_SLCLIENT_JSON, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)

                self.append_log(f"[OK] Playback channel switched: {selected_codec}\n")
                # self.status_label.configure(
                #     text=f"播放通道已切换为\n"
                #          f"{selected_codec}",
                #     text_color="#27ae60"
                # )
            else:
                pass

        except Exception as e:
            self.append_log(f"[Error] Failed to save speech code: {e}\n")

    def _sync_record_to_json(self, selected_codec: str) -> None:
        if not PATH_SLCLIENT_JSON.exists():
            messagebox.showerror("ERROR", f"Please unzip apk first")
            return False
        try:
            data = self._load_slclient_json()

            if "dsp" not in data:
                self.append_log("Error, DSP node is missing")

            current_val = data["dsp"].get("record_stream")

            if current_val != selected_codec:
                data["dsp"]["record_stream"] = selected_codec

                with open(PATH_SLCLIENT_JSON, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)

                self.append_log(f"[OK] Recording channels switched: {selected_codec}\n")
                # self.status_label.configure(
                #     text=f"Recording channel switched to\n"
                #          f"{selected_codec}",
                #     text_color="#27ae60"
                # )
            else:
                pass

        except Exception as e:
            self.append_log(f"[Error] Failed to save speech code: {e}\n")

    def _sync_tone_enabled_to_json(self, is_enabled: bool) -> None:
        """
        【实时保存】确保写入的是 JSON 标准的 true/false，而不是 0/1
        """
        if not PATH_SLCLIENT_JSON.exists():
            messagebox.showerror("ERROR", f"Please unzip apk first")
            return False
        try:
            data = self._load_slclient_json()

            json_value = bool(is_enabled)

            current_val = data["sound"].get("tone_enabled")
            if current_val != json_value:
                data["sound"]["tone_enabled"] = json_value

                with open(PATH_SLCLIENT_JSON, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)

                status = "开启" if json_value else "关闭"
                self.append_log(f"[OK] Tone sound effects have been{status}\n")

                # self.status_label.configure(
                #     text=f"Tone 音效已{status}",
                #     text_color="#27ae60"
                # )

        except Exception as e:
            self.append_log(f"[Error] Failed to save Tone switch: {e}\n")

    def _build_map_content(self, parent):
        """构建地图配置内容"""
        # 1. 地图源
        self.lbl_map_source = ctk.CTkLabel(parent, text=_("lbl_map_source"), anchor="w")
        self.lbl_map_source.grid(
            row=0, column=0, padx=5, pady=10, sticky="w"
        )

        # 动态生成当前语言下的显示名称列表
        map_source_display_names = [v["display_name"][i18n.current_lang] for v in MAP_CONFIG_TEMPLATES.values()]
        self.opt_map_source = ctk.CTkOptionMenu(
            parent, values=map_source_display_names, command=self.on_map_source_change
        )
        self.opt_map_source.grid(
            row=0, column=1, padx=5, pady=10, sticky="w"
        )

    def on_map_source_change(self, selected_display_name: str) -> None:
        """
            地图源变更回调
            :param selected_display_name: UI下拉框选中的显示名称 (如 "百度 [国内]")
            """
        # 从UI显示名称反向查找存储键

        if not PATH_SLCLIENT_JSON.exists():
            messagebox.showerror("ERROR", f"Please unzip apk first")
            return False

        selected_key = None
        for key, value in MAP_CONFIG_TEMPLATES.items():
            if value["display_name"]["zh"] == selected_display_name or value["display_name"][
                "en"] == selected_display_name:
                selected_key = key
                break

        # 获取实际的配置
        config = None
        if selected_key:
            config = MAP_CONFIG_TEMPLATES[selected_key]["config"]

        # 假设你有一个函数来更新地图源配置
        if selected_key:
            if update_slclient_map_type(selected_key):  # 传入存储键
                self._update_preview("map_source", selected_display_name)
                self.append_log(f"[OK] Map source has been updated to：{selected_display_name}\n")
            else:
                current = self.opt_map_source.get()
                messagebox.showwarning("警告", "配置更新失败，已恢复原设置")
        else:
            print(f"[Warning] Invalid map source selection: {selected_display_name}")
            messagebox.showwarning("警告", "无效的地图源选项")

    # # 2. 卫星图层
    # ctk.CTkLabel(parent, text="默认卫星图:", anchor="w").grid(row=1, column=0, padx=5, pady=10, sticky="w")
    # self.switch_satellite = ctk.CTkSwitch(parent, text="Satellite Mode", command=lambda: self._update_preview("satellite", self.switch_satellite.get()))
    # self.switch_satellite.grid(row=1, column=1, padx=5, pady=10, sticky="w")

    def _on_map_type_changed(self, map_type_ui: str):
        """地图类型变更回调"""
        if update_slclient_map_type(map_type_ui):
            self._update_preview("map_provider", map_type_ui)
            self.append_log(f"[OK] Map type has been updated to：{map_type_ui}\n")
            # self.status_label.configure(
            #     text=f"登录方式已更新为\n"
            #          f"{map_type_ui}",
            #     text_color="#27ae60"
            # )
        else:
            # 更新失败，恢复原值
            current = self.opt_map.get()
            messagebox.showwarning("警告", "配置更新失败，已恢复原设置")

    def _build_other_content(self, parent):
        """构建其他设置内容"""
        # # 1. 调试模式
        # ctk.CTkLabel(parent, text="调试模式 (Debug):", anchor="w").grid(row=0, column=0, padx=5, pady=10, sticky="w")
        # self.switch_debug = ctk.CTkSwitch(parent, text="Enable Logs", command=lambda: self._update_preview("debug", self.switch_debug.get()))
        # self.switch_debug.grid(row=0, column=1, padx=5, pady=10, sticky="w")
        #
        # # 2. 帧率限制
        # ctk.CTkLabel(parent, text="最大帧率 (FPS):", anchor="w").grid(row=1, column=0, padx=5, pady=10, sticky="w")
        # self.entry_fps = ctk.CTkEntry(parent, width=60, placeholder_text="60")
        # self.entry_fps.grid(row=1, column=1, padx=5, pady=10, sticky="w")
        # self.entry_fps.insert(0, "60")

        # --- TTS开关 ---
        ctk.CTkLabel(parent, text="TTS:", anchor="w").grid(row=1, column=0, padx=5, pady=8, sticky="w")
        self.switch_sfx = ctk.CTkSwitch(parent, text=" ",
                                        command=lambda: (
                                            self._sync_tts_enabled_to_json(bool(self.switch_sfx.get()))
                                        ))
        self.switch_sfx.grid(row=1, column=1, padx=5, pady=8, sticky="w")
        self.switch_sfx.deselect()  # 默认关闭

        # --- launcher开关---
        ctk.CTkLabel(parent, text="Launcher:", anchor="w").grid(
            row=2, column=0, padx=5, pady=8, sticky="w"
        )

        # 创建开关
        self.switch_launcher = ctk.CTkSwitch(
            parent,
            text="",
            command=lambda: self.modify_manifest(bool(self.switch_launcher.get()))
        )
        self.switch_launcher.grid(row=2, column=1, padx=5, pady=8, sticky="w")

    # -------------mainfest辅助构造函数----------
    def android_attr(self, name):
        return f"{{{ANDROID_NAMESPACE}}}{name}"

    def write_pretty_xml(self, tree, file_path):
        rough_string = ET.tostring(tree.getroot(), encoding='utf-8')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="    ")

        # 去除多余空行
        pretty_xml = "\n".join([line for line in pretty_xml.split('\n') if line.strip()])

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(pretty_xml)

    def modify_manifest(self, is_enabled: bool):
        """
        根据开关状态实时修改 AndroidManifest.xml
        :param is_enabled: True=添加 Launcher, False=移除 Launcher
        """
        manifest_path = PATH_MANIFEST_XML

        if not os.path.exists(manifest_path):
            self.append_log(" Error: Unable to find AndroidManifest.xml")
            if hasattr(self, 'switch_launcher'):
                self.switch_launcher.deselect()
            return

        try:
            ET.register_namespace("android", ANDROID_NAMESPACE)
            tree = ET.parse(manifest_path)
            root = tree.getroot()

            application = root.find("application")
            if application is None:
                self.append_log(" Error: Unable to find the <application>tag")
                self.switch_launcher.deselect()  # 复位
                return

            # 候选 Activity 列表
            candidate_activity_names = [
                "com.shanli.pocstar.SplashActivity",
                "com.shanlitech.ptt.SplashActivity",
                "com.shanlitech.noscreen.SplashActivity"
            ]

            target_activity = None
            found_activity_name = ""

            # 查找目标 Activity
            for activity in application.findall("activity"):
                name = activity.attrib.get(self.android_attr("name"), "")
                if name in candidate_activity_names:
                    target_activity = activity
                    found_activity_name = name
                    break

            if target_activity is None:
                self.append_log(f" Error: Target Activity not found (candidate:{candidate_activity_names})")
                self.switch_launcher.deselect()  # 复位
                return

            intent_filter = target_activity.find("intent-filter")
            if intent_filter is None:
                msg = f" Error：{found_activity_name} No<intent-filter>, cannot operate"
                self.append_log(msg)
                self.switch_launcher.deselect()  # 复位
                return

            home_category_elem = None
            for category in intent_filter.findall("category"):
                if category.attrib.get(self.android_attr("name")) == "android.intent.category.HOME":
                    home_category_elem = category
                    break

            has_home = (home_category_elem is not None)

            if is_enabled:
                if not has_home:
                    ET.SubElement(intent_filter, "category", {
                        self.android_attr("name"): "android.intent.category.HOME"
                    })
                    self.write_pretty_xml(tree, manifest_path)
                    self.append_log(f"[ok]  set to desktop as Launcher\n")
                    # self.status_label.configure(
                    #     text="设置桌面Launcher成功",
                    #     text_color="#27ae60"
                    # )

                else:
                    pass
            else:
                if has_home:
                    intent_filter.remove(home_category_elem)
                    self.write_pretty_xml(tree, manifest_path)
                    self.append_log(f"[ok] Launcher has  cancelled\n")
                    # self.status_label.configure(
                    #     text="取消桌面Launcher成功",
                    #     text_color="#27ae60"
                    # )
                else:
                    pass

        except Exception as e:
            self.append_log(f" operation failed：{e}")
            if hasattr(self, 'switch_launcher'):
                self.switch_launcher.deselect()

    def _sync_tts_enabled_to_json(self, is_enabled: bool) -> None:
        """
        【实时保存】确保写入的是 JSON 标准的 true/false，而不是 0/1
        """
        if not PATH_SLCLIENT_JSON.exists():
            messagebox.showerror("ERROR", f"Please unzip apk first")
            return False
        try:
            data = self._load_slclient_json()

            json_value = bool(is_enabled)

            current_val = data["tts"].get("enabled")
            if current_val != json_value:
                data["tts"]["enabled"] = json_value

                with open(PATH_SLCLIENT_JSON, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)

                status = "开启" if json_value else "关闭"
                self.append_log(f"[OK] tts  {status}\n")

                # self.status_label.configure(
                #     text=f"tts {status}",
                #     text_color="#27ae60"
                # )

        except Exception as e:
            self.append_log(f"[Error] Failed to save Tone switch: {e}\n")

    def _refresh_custom_inputs(self):
        """切换到独立部署模式时：清空历史内容，仅显示提示文字"""
        if self.opt_env.get() != self.CUSTOM_OPTION_NAME:
            return

        # 1. 强制清空输入框的历史内容
        self.entry_custom_ip.delete(0, 'end')
        self.entry_custom_context.delete(0, 'end')

        # 2. 设置占位符提示文字（清空后必显示）
        self.entry_custom_ip.configure(
            placeholder_text="Eg: 192.168.1:10200",
            placeholder_text_color="#95a5a6"
        )
        self.entry_custom_context.configure(
            placeholder_text="Eg: demoText",
            placeholder_text_color="#95a5a6"
        )

    def _toggle_custom_env_inputs(self):
        """处理开关的显隐逻辑"""
        is_on = self.switch_custom_env.get()

        if self.opt_env.get() != self.CUSTOM_OPTION_NAME:
            self.switch_custom_env.deselect()
            return

        if is_on:
            self.entry_custom_ip.configure(state="normal")
            self.entry_custom_context.configure(state="normal")
            self.btn_save_custom.grid(row=4, column=0, columnspan=2, padx=5, pady=10, sticky="ew")

            # ========== 读取 slclient.json 的 profile 并判断 ==========
            slclient_profile = None
            try:
                if PATH_SLCLIENT_JSON.exists():
                    with open(PATH_SLCLIENT_JSON, 'r', encoding='utf-8') as f:
                        slclient_data = json.load(f)
                        slclient_profile = slclient_data.get("profile", {})
            except Exception as e:
                self.lbl_env_info.configure(
                    text=f"ℹ读取 slclient.json 失败：{str(e)}",
                    text_color="orange"
                )

            if slclient_profile:
                profile_dns = slclient_profile.get("dns", [])
                profile_context = slclient_profile.get("context", "")
                profile_ip = profile_dns[0] if isinstance(profile_dns, list) and profile_dns else ""

                is_in_env_conf = False
                for env_name, env_config in ENV_CONF.items():
                    if env_config.get("ip_address") == profile_ip and env_config.get("context") == profile_context:
                        is_in_env_conf = True
                        break

                if not is_in_env_conf:
                    self.entry_custom_ip.delete(0, 'end')
                    self.entry_custom_context.delete(0, 'end')
                    self.entry_custom_ip.insert(0, profile_ip)
                    self.entry_custom_context.insert(0, profile_context)
                    return

            self._refresh_custom_inputs()

        else:
            self.entry_custom_ip.configure(state="disabled")
            self.entry_custom_context.configure(state="disabled")
            self.btn_save_custom.grid_remove()

            self.lbl_env_info.configure(
                text=f"ℹ未保存的修改已丢弃。",
                text_color="gray"
            )

    def _update_config_from_custom_inputs(self):
        """从手动输入框读取数据并更新内部配置"""
        ip = self.entry_custom_ip.get().strip()
        context = self.entry_custom_context.get().strip()

        if not ip or not context:
            self.lbl_env_info.configure(text="⚠️ 请完整填写 IP 和 Context", text_color="orange")
            # 即使为空也先存着，等打包时再报错或忽略
            self.current_env_config = {
                "name": "独立部署 (未配置)",
                "ip": ip,
                "context": context,
                "is_custom": True
            }
            return

        self.current_env_config = {
            "name": f"独立部署 ({ip})",
            "ip": ip,
            "context": context,
            "is_custom": True
        }
        self.lbl_env_info.configure(text=f"🔧 独立部署: {ip} | {context}", text_color="#3498db")

    def _sync_preset_node_to_json(self, node_name: str) -> None:
        """
        将选中的预设节点配置同步写入 slclient.json 的 profile 节点
        """

        if node_name == self.CUSTOM_OPTION_NAME:
            return  # 独立部署模式不在此处处理

        config = ENV_CONF.get(node_name, {})
        ip_address = config.get("ip_address", "")
        context = config.get("context", "")
        upgrade_url = config.get("upgrade_url", "")

        if not ip_address or not context or not upgrade_url:
            self.append_log(f"[Warn] Node {node_name} configuration is incomplete, writing is skipped。\n")
            return

        try:
            data = self._load_slclient_json()

            # 更新 profile 节点
            if "profile" not in data:
                data["profile"] = {}

            dns_list = ip_address.split(',')

            data["profile"]["dns"] = dns_list
            data["profile"]["context"] = context
            data["profile"]["upgrade_url"] = upgrade_url

            # 写回文件
            with open(PATH_SLCLIENT_JSON, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            # self.append_log(f"[OK] Node switched: {node_name}\n")
            # self.status_label.configure(
            #     text=f"Login method updated to\n"
            #          f"{node_name}",
            #     text_color="#27ae60"
            # )

        except Exception as e:
            # self.append_log(f"[Error] Failed to synchronize node configuration: {e}\n")
            return

    def _on_env_selected(self, selected_name):
        """当下拉菜单选择改变时触发 - 直接写入 Profile"""

        # 1. 反查 Key (根据显示名找到 'overseas' 或 'domestic_v2')
        selected_key = None
        current_lang = i18n.current_lang

        for key, names in ENV_DISPLAY_NAMES.items():
            if names.get(current_lang) == selected_name:
                selected_key = key
                break

        # 如果没找到对应的 Key，直接返回
        if not selected_key:
            return
        self._sync_preset_node_to_json(selected_key)

    def _get_env_key_from_display(self, display_name):
        for key, value in self.ENV_OPTIONS.items():
            if isinstance(value, dict):
                if display_name in value.values():
                    return key
            else:
                if display_name == value:
                    return key
        return display_name

    def _fill_env_inputs(self, dns_ip, context, readonly=True):
        self.entry_custom_ip.configure(state="normal")
        self.entry_custom_context.configure(state="normal")

        self.entry_custom_ip.delete(0, "end")
        self.entry_custom_ip.insert(0, dns_ip)

        self.entry_custom_context.delete(0, "end")
        self.entry_custom_context.insert(0, context)

        if readonly:
            self.entry_custom_ip.configure(state="disabled")
            self.entry_custom_context.configure(state="disabled")

    def _show_preset_info(self, node_name):
        """显示预设节点的只读信息"""
        config = ENV_CONF.get(node_name, {})
        ip_val = config.get('ip_address', 'N/A')
        ctx_val = config.get('context', 'N/A')

        if isinstance(ip_val, list):
            ip_val = ip_val[0] if ip_val else "N/A"

        # self.lbl_env_info.configure(
        #     text=f"✅ 模式：预设节点 [{node_name}]\nIP: {ip_val}\n"
        #          f" | Context: {ctx_val}",
        #     text_color="#27ae60",
        #     font=ctk.CTkFont(size=11)
        # )
        # # 确保输入框清空或禁用
        # self.entry_custom_ip.delete(0, 'end')
        # self.entry_custom_context.delete(0, 'end')

    def _update_preview(self, key, value):
        """通用配置更新回调，用于实时更新内存中的配置字典"""
        if not hasattr(self, 'build_config'):
            self.build_config = {}
        self.build_config[key] = value

    def load_all_configs(self) -> None:
        """加载所有配置（含slclient.json的login_mode）"""

        # 定义默认环境为 overseas
        default_env_key = "overseas"

        try:
            # 初始化变量
            login_mode_val = "account"
            map_source_val = "Google"
            current_env_key = default_env_key

            tts_enabled_val = False
            tone_enabled_val = True
            launcher_enabled_val = False

            codec_enabled_val = "amrnb"
            audio_enabled_val = "default"
            play_enabled_val = "music"
            rec_enabled_val = "recognition"

            # 只有当文件存在时才尝试读取
            if PATH_SLCLIENT_JSON.exists():
                with open(PATH_SLCLIENT_JSON, "r", encoding="utf-8") as f:
                    slclient_data = json.load(f)

                current_env_key = slclient_data.get("profile", {}).get("env_key", default_env_key)

                login_mode_val = slclient_data.get("profile", {}).get("login_mode", login_mode_val)
                map_source_val = slclient_data.get("lbs", {}).get("map_type", map_source_val)

                tts_enabled_val = slclient_data.get("tts", {}).get("enabled", False)
                tone_enabled_val = slclient_data.get("sound", {}).get("tone_enabled", True)

                codec_enabled_val = slclient_data.get("sound", {}).get("codec", codec_enabled_val)
                audio_enabled_val = slclient_data.get("dsp", {}).get("provider", audio_enabled_val)
                play_enabled_val = slclient_data.get("dsp", {}).get("play_stream", play_enabled_val)
                rec_enabled_val = slclient_data.get("dsp", {}).get("record_stream", rec_enabled_val)

            ui_env_val = ENV_DISPLAY_NAMES.get(current_env_key, {}).get(i18n.current_lang, "海外环境")

            ui_login_val = LOGIN_TYPE_MAPPING.get(login_mode_val, {}).get(i18n.current_lang, "账号登录")

            self.map_coor = self.get_json_field(PATH_SLCLIENT_JSON, LBS_COOR_PATH)

            if self.map_coor == "wgs84" and map_source_val == "baidu":
                map_source_val = "baidu_oversea"
            elif self.map_coor == "bd09ll" and map_source_val == "baidu":
                map_source_val = "baidu_domestic"

            ui_map_val = MAP_CONFIG_TEMPLATES.get(map_source_val, {}).get("display_name", {}).get(i18n.current_lang)

            if hasattr(self, 'opt_env'):
                self.opt_env.set(ui_env_val)
                self._update_preview("env", ui_env_val)

            self.opt_login_type.set(ui_login_val)
            self._update_preview("login_type", ui_login_val)

            if hasattr(self, 'opt_map_source'):
                self.opt_map_source.set(ui_map_val)
                self._update_preview("map_source", ui_map_val)

            if hasattr(self, 'switch_sfx'):
                if tts_enabled_val:
                    self.switch_sfx.select()
                else:
                    self.switch_sfx.deselect()

            if hasattr(self, 'switch_tone_sfx'):
                if tone_enabled_val:
                    self.switch_tone_sfx.select()
                else:
                    self.switch_tone_sfx.deselect()

            if hasattr(self, 'switch_launcher'):
                if launcher_enabled_val:
                    self.switch_launcher.select()
                else:
                    self.switch_launcher.deselect()

            if hasattr(self, 'opt_rec'):
                self.opt_rec.set(rec_enabled_val)

            if hasattr(self, 'opt_play'):
                self.opt_play.set(play_enabled_val)

            if hasattr(self, 'opt_audio'):
                self.opt_audio.set(audio_enabled_val)

            if hasattr(self, 'opt_codec'):
                self.opt_codec.set(codec_enabled_val)


        except Exception as e:
            self.append_log(f"[Warning] Failed to load configs, using default: {e}\n")
            try:
                default_display = ENV_DISPLAY_NAMES["overseas"].get(i18n.current_lang, "海外环境")
                if hasattr(self, 'opt_env'):
                    self.opt_env.set(default_display)
            except:
                pass

    # TODO 优化在打包时弹窗确认当前slclient的内容
    def _get_slclient_preview_data(self) -> dict:
        """
        收集所有模块的当前配置值。
        不依赖 build_config，直接从 GUI 控件读取以确保是最新值。
        """
        data = {}
        current_lang = i18n.current_lang

        # --- A. Profile (环境与登录) ---
        # 1. 环境
        selected_env_display = self.opt_env.get()
        env_key = "overseas"
        # 反查环境键名
        for key, names in ENV_DISPLAY_NAMES.items():
            if names.get(current_lang) == selected_env_display:
                env_key = key
                break

        if PATH_SLCLIENT_JSON.exists():
            try:
                with open(PATH_SLCLIENT_JSON, "r", encoding="utf-8") as f:
                    slclient_data = json.load(f)

                profile_data = slclient_data.get("profile", {})
                data["env_ip"] = profile_data.get("dns", "Default")
                data["context"] = profile_data.get("context", "pocstar")
                data["login_type"] = profile_data.get("login_type", self.opt_login_type.get())
            except Exception as e:
                print(f"Error reading slclient.json: {e}")
                data["env_ip"] = "Default"
                data["context"] = "pocstar"
                data["login_type"] = self.opt_login_type.get()
        else:
            data["env_ip"] = "Default"
            data["context"] = "pocstar"
            data["login_type"] = self.opt_login_type.get()

        # --- B. LBS (地图) ---
        data["map_source"] = self.opt_map_source.get()

        # --- C. Sound & DSP ---
        data["codec"] = self.opt_codec.get()
        data["tone_enabled"] = self.switch_tone_sfx.get()
        data["audio_provider"] = self.opt_audio.get()
        data["play_channel"] = self.opt_play.get()
        data["rec_channel"] = self.opt_rec.get()

        # --- D. TTS & Launcher ---
        data["tts_enabled"] = self.switch_sfx.get()
        data["launcher_home"] = self.switch_launcher.get()

        return data

    def apply_selected_config_to_slclient(self) -> bool:
        """
        打包时调用：弹窗确认当前 slclient 的内容。
        格式：键：值 (非 JSON)

        Returns:
            bool: True 表示用户确认，False 表示取消。
        """
        # 1. 获取数据
        raw_data = self._get_slclient_preview_data()

        lines = []

        # 环境信息
        ip_addresses = raw_data['env_ip']
        if isinstance(ip_addresses, list):
            ip_formatted = "\n".join([f"  - {ip}" for ip in ip_addresses])
        else:
            ips = str(ip_addresses).split(',')
            ip_formatted = "\n".join([f"  - {ip.strip()}" for ip in ips])

        lines.append("-" * 30)

        # 检查IP地址是否在预定义环境中
        found_env = None
        for env_id, env_config in ENV_CONF.items():
            env_ip_address = env_config.get("ip_address", "")
            if isinstance(env_ip_address, list):
                env_ips = env_ip_address
            else:
                env_ips = [addr.strip() for addr in str(env_ip_address).split(',')]

            current_ips = [addr.strip() for addr in str(raw_data['env_ip']).split(',')] if not isinstance(
                raw_data['env_ip'], list) else raw_data['env_ip']

            if any(ip in env_ips for ip in current_ips):
                found_env = env_id
                break

        if found_env:
            lines.append(f"IP:  \n{ip_formatted}")
            lines.append(f"Context:  {raw_data['context']}")
        else:
            lines.append(f"IP:  \n{ip_formatted}")
            lines.append(f"Context:  {raw_data['context']}")

        lbl_login_type = _("lbl_login_type")
        lines.append(f"{lbl_login_type}:  {raw_data['login_type']}\n")
        lines.append("-" * 30)

        # 地图
        lbl_map_source = _("lbl_map_source")
        lines.append(f"{lbl_map_source}:  {raw_data['map_source']}\n")
        lines.append("-" * 30)

        # 声音
        lines.append(f"Tone:  {'True' if raw_data['tone_enabled'] else 'False'}\n")
        lines.append("-" * 30)
        lines.append(f"Codec:  {raw_data['codec']}")
        lines.append(f"audio:  {raw_data['audio_provider']}")
        lines.append(f"Play channel:  {raw_data['play_channel']}")
        lines.append(f"Rec channel:  {raw_data['rec_channel']}\n")
        lines.append("-" * 30)

        # 其他
        lines.append(f"TTS:  {'True' if raw_data['tts_enabled'] else 'False'}")
        lines.append(f"Launcher:  {'True' if raw_data['launcher_home'] else 'False'}")

        # 拼接最终文本
        message_text = "\n".join(lines)

        # 3. 创建弹窗
        win = ctk.CTkToplevel(self)
        win.title(_("confirm_config_text"))
        win.geometry("400x550")
        win.resizable(True, True)

        win.attributes("-topmost", True)
        win.grab_set()

        # ===== 字体统一 =====
        title_font = ctk.CTkFont(size=15, weight="bold")
        text_font = ctk.CTkFont(size=13)

        # ===== 标题 =====
        package_config_title = ctk.CTkLabel(win, text=_("package_config_title"), font=title_font)
        package_config_title.pack(pady=(15, 5))

        # ===== 内容 (使用 Textbox 显示文本行) =====
        text_frame = ctk.CTkFrame(win, fg_color="transparent")
        text_frame.pack(padx=20, pady=10, fill="both", expand=True)

        textbox = ctk.CTkTextbox(text_frame, font=text_font, wrap="word")  # wrap="word" 自动换行
        textbox.pack(fill="both", expand=True)
        textbox.insert("0.0", message_text)
        textbox.configure(state="disabled")  # 只读

        # ===== 按钮 =====
        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(pady=10)

        result = {"confirmed": False}

        def on_ok():
            result["confirmed"] = True
            win.destroy()

        def on_cancel():
            result["confirmed"] = False
            win.destroy()

        # 取消按钮
        self.btn_dialog_cancel = ctk.CTkButton(
            btn_frame,
            text=_("cancel_button"),
            font=text_font,
            width=100,
            command=on_cancel,
            fg_color="gray"
        )
        self.btn_dialog_cancel.pack(side="left", padx=20)

        # 确认按钮
        self.btn_dialog_ok = ctk.CTkButton(
            btn_frame,
            text=_("confirm_button"),
            font=text_font,
            width=100,
            command=on_ok,
            fg_color="green"
        )
        self.btn_dialog_ok.pack(side="left", padx=20)

        # ===== 居中与置顶逻辑 =====
        # win.update_idletasks()
        # w, h = win.winfo_width(), win.winfo_height()
        # x = (win.winfo_screenwidth() // 2) - (w // 2)
        # y = (win.winfo_screenheight() // 2) - (h // 2)
        # win.geometry(f"{w}x{h}+{x}+{y}")

        win.lift()
        win.focus_force()
        win.after(10, lambda: win.attributes("-topmost", False))

        # 绑定按键
        win.bind("<Return>", lambda e: on_ok())
        win.bind("<Escape>", lambda e: on_cancel())

        # 4. 阻塞等待
        win.wait_window()

        return result.get("confirmed", False)



    # 在 App 类定义之前或 __init__ 中调用
    def load_slclient_config(self):
        """启动时从 slclient.json 加载配置更新 ENV_CONF"""
        if not PATH_SLCLIENT_JSON.exists():
            print(f"⚠️ not found {PATH_SLCLIENT_JSON}，Use default hard-coded configuration。")
            return

        try:
            with open(PATH_SLCLIENT_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 假设 JSON 中有 "profile" 节点，将其映射到 "海外环境"
            if "profile" in data:
                prof = data["profile"]
                # 更新全局 ENV_CONF 中的 "海外环境"
                # 注意：原代码中 ip_address 是字符串，这里如果 dns 是列表，取第一个
                dns_list = prof.get("dns", [])
                ip_val = dns_list[0] if isinstance(dns_list, list) and dns_list else prof.get("dns", "")

                ENV_CONF["海外环境"]["context"] = prof.get("context", "pocstar")
                ENV_CONF["海外环境"]["ip_address"] = ip_val

                print(f"✅ 已从 slclient.json 加载 profile 配置到 '海外环境'。")

        except Exception as e:
            print(f"❌ 加载 slclient.json 失败: {e}")

    # ==================== APK 工具链逻辑 ====================
    def get_version_info(self, yml_path):
        """获取 versionCode 和 versionName"""

        value = self.get_field_value_from_yml(PATH_YML, "versionInfo")
        if value:
            versionCode = value.get("versionCode")
            versionName = value.get("versionName")

            return versionCode, versionName

    def get_json_field(self, file_path: Path, field_path: List[str]) -> Any:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            temp_data = data
            for key in field_path:
                if isinstance(temp_data, dict):
                    temp_data = temp_data.get(key)
                else:
                    return None
            return temp_data
        except Exception:
            return None

    def set_json_field(self, file_path: Path, field_path: List[str], new_value: Any) -> bool:
        """
        读取 JSON 文件，根据路径修改指定字段的值，并保存回文件。

        Args:
            file_path: JSON 文件路径
            field_path: 字段路径列表，例如 ["ui", "launcherModule"]
            new_value: 要设置的新值

        Returns:
            bool: 操作成功返回 True，失败返回 False
        """
        try:
            if not file_path.exists():
                return False

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 2. 定位并修改数据
            temp_data = data
            for key in field_path[:-1]:
                if isinstance(temp_data, dict) and key in temp_data:
                    temp_data = temp_data[key]
                else:
                    return False

            target_key = field_path[-1]
            if isinstance(temp_data, dict):
                temp_data[target_key] = new_value
            else:
                return False

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            return True

        except Exception as e:
            return False

    def safe_remove(self, file_path: str, retries: int = 3) -> bool:
        """安全删除文件，带重试机制"""
        for i in range(retries):
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    self.append_log(f"[OK] Temporary file has been deleted")
                    return True
            except PermissionError:
                self.append_log(f"[Warn] File is occupied, wait 0.5 seconds and try again... ({i + 1}/{retries})\n")
                time.sleep(0.5)
            except Exception as e:
                self.append_log(f"[Error] Failed to delete file：{e}\n")
                return False
        return False

    def run_with_live_output(
            self,
            command: List[str],
            timeout: Optional[float] = None,
            encoding: Optional[str] = None
    ) -> int:
        """
        【核心改进】双线程读取 stdout/stderr 字节流，防止死锁，并实时推送到 GUI
        Args:
            command (List[str]): 要执行的命令列表。
            timeout (Optional[float], optional): 命令执行超时时间（秒）。None表示无限制。
            encoding (Optional[str], optional): 用于解码输出流的首选编码。默认为 'utf-8'。

        Returns:
            int: 子进程的返回码。如果发生异常或超时，则返回 -1。
        """
        start_time = time.time()
        # self.append_log(f"[CMD] {' '.join(command)}\n")

        # 准备跨平台的启动选项
        startupinfo = None
        creationflags = 0
        if platform.system() == "Windows":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            creationflags = subprocess.CREATE_NO_WINDOW

        #  启动子进程
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # 行缓冲
                universal_newlines=True,  # 确保返回字符串
                startupinfo=startupinfo,
                creationflags=creationflags,
                # 明确指定编码，处理乱码问题
                encoding=encoding
            )
        except FileNotFoundError:
            self.append_log(f"[ERROR] 找不到命令或文件: {command[0]}\n")
            return -1
        except Exception as e:
            self.append_log(f"[CRITICAL] 启动进程失败: {e}\n")
            return -1

        #  创建线程安全队列用于接收子进程输出
        log_queue = queue.Queue(maxsize=1000)

        def reader_thread(stream, prefix: str = ""):
            """读取子进程的一个输出流，并放入队列"""
            try:
                for line in iter(stream.readline, ""):
                    if line:
                        log_queue.put((prefix, line.rstrip('\n\r')))  # 将前缀和内容作为元组放入队列
                stream.close()
            except Exception as e:
                self.append_log(f"[ERROR] 读取子进程输出流时出错: {e}\n")
            finally:
                # 发送一个哨兵值，表示该流已读完
                log_queue.put((None, None))

        # 启动两个守护线程，分别读取 stdout 和 stderr
        t_out = threading.Thread(target=reader_thread, args=(process.stdout, ""), daemon=True)
        t_err = threading.Thread(target=reader_thread, args=(process.stderr, "[ERR] "), daemon=True)
        t_out.start()
        t_err.start()

        # 引入计时器
        streams_to_read = 2

        #  主循环：从队列中获取输出并更新GUI
        last_update_time = time.time()
        while streams_to_read > 0:
            try:
                item = log_queue.get(timeout=0.1)

                if item[0] is None and item[1] is None:
                    streams_to_read -= 1
                    continue

                prefix, line_content = item
                # 使用 after 方法将更新操作调度到主线程执行
                self.after(0, self.append_log, f"{prefix}{line_content}\n")

            except queue.Empty:
                # 检查主进程是否已经结束
                if process.poll() is not None:
                    remaining_timeout = timeout - (time.time() - start_time) if timeout else None
                    if remaining_timeout and remaining_timeout <= 0:
                        break
                    continue

                if timeout is not None and (time.time() - start_time) > timeout:
                    self.append_log(f"[TIMEOUT] 命令执行超时 ({timeout}s)，正在终止...\n")
                    process.terminate()
                    try:
                        process.wait(timeout=5)  # 给予5秒时间优雅关闭
                    except subprocess.TimeoutExpired:
                        process.kill()  # 强制杀死
                    return -1
            except Exception as e:
                self.append_log(f"[ERROR] 处理子进程输出时出错: {e}\n")
                traceback.print_exc()

        # 6. 等待读取线程完成
        t_out.join()
        t_err.join()

        # 7. 获取最终返回码
        returncode = process.wait()
        total_time = time.time() - start_time
        self.append_log(f"[Result] Command execution completed,  code：{returncode}\n")
        return returncode

    def _do_decompile_logic(self, output_dir: str = "app_out") -> bool:
        """
        【核心逻辑】实际执行反编译的代码。
        此函数可以被主线程调用，也可以被子线程调用。
        返回 True 表示成功，False 表示失败。
        """
        start_time = time.time()
        self.custom_apk_path = None

        apk_type = self.apk_type_seg.get()
        self.current_apk_type = apk_type

        # 1. 确定 APK 路径
        if apk_type in ["大屏", "Large"]:
            apk_path = "LargeApp.apk"

        elif apk_type in ["中屏", "Medium"]:
            apk_path = "LargeApp.apk"

        elif apk_type in ["小屏", "Small"]:
            apk_path = "SmallApp.apk"

        elif apk_type in ["无屏", "Screenless"]:
            apk_path = "Screenless.apk"

        elif apk_type in ["自定义", "Custom"]:

            selected_path = None
            self.after(0, lambda: None)

            apk_path = filedialog.askopenfilename(
                title="APK File",
                filetypes=[("APK File", "*.apk")]
            )

            if not apk_path:
                self.append_log("[Info] User cancelled APK selection.\n")
                return False
            self.custom_apk_path = apk_path

            self.append_log(f"[Info] Selected custom APK: {apk_path}\n")
        else:
            self.append_log("[Error] Unknown APK type, please check your selection\n")
            return False

        # 2. 清理旧目录
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir, ignore_errors=True)
            self.append_log(f"[Info] Clean up old catalog：{output_dir}\n")

        self.append_log("Extracting...\n")

        # 3. 执行命令
        command = [
            "java", "-jar", str(APKTOOL_JAR),
            "d", apk_path, "-s", "-o", output_dir
        ]

        exit_code = self.run_with_live_output(command)

        if exit_code == 0:
            end_time = time.time()

            if apk_type in ["中屏", "Middle APK"]:
                self.append_log("[Info] Middle screen mode detected. Updating config...\n")

                json_file = PATH_SLCLIENT_JSON
                field_path = ["ui", "launcherModule"]
                new_value = "middle"

                if self.set_json_field(json_file, field_path, new_value):
                    self.append_log(f"[Success] Auto-config: ui.launcherModule set to '{new_value}'\n")
                else:
                    self.append_log("[Warning] Config update failed after unzip.\n")

            self.load_and_echo_config_after_unzip()

            self.append_log(f"[SUCCESS] ✅  time spent: {(end_time - start_time):.2f}s\n")

        return exit_code == 0

    def decompile_apk(self, output_dir: str = "app_out") -> None:
        """
        【多线程入口】启动反编译任务，不阻塞 UI。
        """
        if hasattr(self, '_is_decompiling') and self._is_decompiling:
            self.append_log("[Info] 反编译正在进行中...\n")
            return

        self._is_decompiling = True

        def task():
            try:
                # 调用核心逻辑
                success = self._do_decompile_logic(output_dir)

                if success:
                    # 刷新一下配置
                    messagebox.showinfo("Success", "Decompile Apk Successful!")
                    self.after(500, self.load_all_configs)
                else:
                    return

            except Exception as e:
                self.append_log(f"\n[ERROR]: {str(e)}\n")
            finally:
                self._is_decompiling = False

        # 启动线程
        threading.Thread(target=task, daemon=True).start()

    def upload_apk(self):
        file_path = filedialog.askopenfilename(
            title="选择APK文件",
            filetypes=[("APK Files", "*.apk")]
        )

        if file_path:
            self.custom_apk_path = file_path
            self.show_custom_message("Tip", f"已选择APK:\n{file_path}")

    def build_apk(self) -> None:
        """主打包入口
            解压只要打包app_out即可
        """
        start_time = time.time()
        if not PATH_SLCLIENT_JSON.exists():
            messagebox.showerror("ERROR", f"Please unzip apk first")
            return False

        output_dir: str = "app_out"

        apk_type = self.apk_type_seg.get()
        self.current_apk_type = apk_type

        # 禁用按钮防止重复点击
        self.build_apk_btn.configure(state="disabled")

        def task():
            try:
                self.append_log(f"\n[Step 1]=== Start  package process ({apk_type}) ===\n")

                # # 1. 反编译
                # self.append_log("[Step 1] Decompiling APK...\n")
                # if not self.decompile_apk(apk_path, TEMP_DIR):
                #     raise Exception("Decompilation failed")
                #
                # else:
                #     self.append_log("[Step 2] successfully compiled\n")

                # 2. 更新版本信息
                # self.append_log("[Step 2] 正在更新版本信息...\n")
                # if os.path.exists(PATH_YML):
                #     self.update_version_info(PATH_YML)
                # else:
                #     self.append_log("[Warn] 未找到 apktool.yml，跳过版本更新\n")

                self.append_log("[Step 2] Getting device information...\n")
                # TODO 待完善弹窗的国际化翻译
                apply_selected = self.apply_selected_config_to_slclient()
                if not apply_selected:
                    return False

                model = self.ask_model_dialog()
                if model is None:
                    raise Exception("User cancels packaging")

                # 把 model 存入变量，供后面重命名使用,还需要写入devices的name中
                self.current_device_model = model
                if model:
                    field_path = ["device", "name"]
                    self.set_json_field(PATH_SLCLIENT_JSON, field_path, model)

                # 2.替换input.json
                if not self.is_import:
                    self.copy_files(PATH_INPUT_JSON_SRC, PATH_INPUT_JSON_DST)

                # 3. 构建未签名 APK
                self.append_log("\n[Step 3] Packing APK...\n")
                apktool_cmd = [
                    "java", "-jar", str(APKTOOL_JAR),
                    "b", TEMP_DIR, "-o", "app-unsigned-unaligned.apk"
                ]
                if self.run_with_live_output(apktool_cmd) != 0:
                    raise Exception("APK packaging failed")

                # 4. Zipalign 对齐
                self.append_log("[Step 4] Aligning APK...\n")
                zipalign_cmd = [
                    str(ZIPALIGN_EXE), "-v", "-p", "4",
                    "app-unsigned-unaligned.apk", "app-unsigned.apk"
                ]
                if self.run_with_live_output(zipalign_cmd) != 0:
                    raise Exception("APK alignment failed")

                self.safe_remove("app-unsigned-unaligned.apk")

                # 5. 签名
                self.append_log("\n[Step 5] Signing APK...\n")
                value_map = {"大屏": "large", "中屏": "middle", "小屏": "small"}
                key = value_map.get(apk_type, "large")

                # 从 slclient.json 获取实际类型
                json_val = self.get_json_field(PATH_SLCLIENT_JSON, LAUNCHER_MODULE_PATH)
                if json_val and json_val in KEYSTORE_CONFIG:
                    key = json_val
                    self.append_log(f"[Info] JSON configuration detected, signature type used：{key}\n")

                ks_info = KEYSTORE_CONFIG.get(key, KEYSTORE_CONFIG["large"])
                ks_path = ks_info["path"]
                ks_pass = ks_info["password"]

                if not os.path.exists(ks_path):
                    raise Exception(f"Signature file does not exist：{ks_path}")

                date_str = time.strftime("%Y_%m_%d", time.localtime())
                output_dir_path = PROJECT_PATH / date_str
                output_dir_path.mkdir(exist_ok=True)

                final_name = self.build_newname(PATH_YML) if os.path.exists(
                    PATH_YML) else f"app_{apk_type}_{date_str}.apk"
                output_apk_path = output_dir_path / final_name

                apksigner_cmd = [
                    str(APKSIGNER_BAT), "sign",
                    "--ks", str(ks_path),
                    "--ks-pass", f"pass:{ks_pass}",
                    "--out", str(output_apk_path),
                    "app-unsigned.apk"
                ]

                if self.run_with_live_output(apksigner_cmd) != 0:
                    raise Exception("APK signing failed")

                self.safe_remove("app-unsigned.apk")

                self.append_log(f"\n[SUCCESS] ✅  file location: {output_apk_path}\n")
                # 删除app_out文件夹
                shutil.rmtree(output_dir, ignore_errors=True)
                # 初始化界面
                self.load_all_configs()
                end_time = time.time()
                self.append_log(f"[SUCCESS] ✅  time spent: {(end_time - start_time):.2f}s\n")
                self.show_custom_message("SUCCESS", f"APK Safe: \n{output_apk_path}")

            except Exception as e:
                error_msg = f"[FAIL] ❌ {str(e)}"
                self.append_log(f"\n{error_msg}\n")
                # self.status_label.configure(text="状态：打包失败", text_color="red")
                messagebox.showerror("ERROR", error_msg)
            finally:
                self.build_apk_btn.configure(state="normal", text=_("btn_build"))
                # 还原导入标示，后续打包继续使用覆盖input.json
                self.is_import = False

        threading.Thread(target=task, daemon=True).start()

    def copy_files(self, source_dir_color, target_dir_color):
        if not os.path.isfile(source_dir_color):
            raise FileNotFoundError(f"资源文件不存在: {source_dir_color}")

        try:
            shutil.copy2(source_dir_color, target_dir_color)
            self.append_log(f"overwritten file：{source_dir_color} -> {target_dir_color}")
        except Exception as e:
            self.append_log(f"coverage failure：{e}")

    # ==================== 版本管理辅助函数 ====================

    def update_version_name(self, version_name: str) -> str:
        """将版本名中 'POCSTARS_' 后面的数字替换为当前时间戳"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pattern = r"(POCSTARS_)\d+$"
        new_version_name = re.sub(pattern, rf"\1{timestamp}", version_name)

        if new_version_name == version_name:
            self.append_log(f"[Warn] Number format that does not match to the end：{version_name}\n")
            return f"{version_name}_{timestamp}"
        return new_version_name

    def increment_version_code(self, version_code: Any) -> Any:
        try:
            return int(version_code) + 1
        except (ValueError, TypeError):
            return version_code

    def load_yml(self, yml_path: Path) -> Optional[Dict]:
        yaml = YAML()
        if not os.path.exists(yml_path):
            return None
        try:
            with open(yml_path, "r", encoding="utf-8") as f:
                return yaml.load(f)
        except Exception as e:
            self.append_log(f"[Error]Failed to load YAML：{e}\n")
            return None

    def update_version_info(self, yml_path: Path) -> None:
        yaml = YAML()

        def represent_none(self, data):
            return self.represent_scalar("tag:yaml.org,2002:null", "null")

        yaml.representer.add_representer(type(None), represent_none)

        data = self.load_yml(yml_path)
        if not data:
            return

        version_info = data.get("versionInfo", {})
        old_code = version_info.get("versionCode")
        old_name = version_info.get("versionName")

        if not old_code or not old_name:
            self.append_log("[Warn]Unable to obtain version information, skipping update\n")
            return

        new_code = self.increment_version_code(old_code)
        new_name = self.update_version_name(old_name)

        version_info["versionCode"] = new_code
        version_info["versionName"] = new_name

        with open(yml_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f)

        self.append_log(f"[Version]update successful：{old_name}->{new_name}, Code: {old_code}->{new_code}\n")

    def build_newname(self, yml_path: Path) -> str:
        try:
            launcher_module = self.get_json_field(PATH_SLCLIENT_JSON, LAUNCHER_MODULE_PATH)
            version_str = self.get_version_info(yml_path)[1]
            recorder_module = self.get_json_field(PATH_SLCLIENT_JSON, RECORDER_ENABLE_PATH)

            raw_model = getattr(self, 'current_device_model', 'Unknown')
            device_model = str(raw_model)

            if not device_model or device_model.strip() == "":
                new_version_name = version_str
            else:
                new_version_name = re.sub(r'(POCSTARS_)', r'\g<1>' + device_model + '_', version_str)
            if recorder_module:
                newname = 'RSAPP_' + str(new_version_name) + '.apk'

            elif launcher_module is None:
                newname = 'ASAPP_' + str(new_version_name) + '.apk'
            elif launcher_module == 'large':
                newname = 'BSAPP_' + str(new_version_name) + '.apk'
            elif launcher_module == 'middle':
                newname = 'MSAPP_' + str(new_version_name) + '.apk'
            elif launcher_module == 'small':
                newname = 'SSAPP_' + str(new_version_name) + '.apk'
            else:
                newname = 'NSAPP_' + str(new_version_name) + '.apk'

            self.append_log(f'[Info] Changed name to {newname}')
            return newname

        except Exception as e:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            self.append_log(f'[ERR]:{e}')
            return f"APP_test_{timestamp}.apk"

    def get_field_value_from_yml(self, yml_path: Path, field_name: str) -> Dict:
        data = self.load_yml(yml_path)
        field_value = data.get(field_name, {})
        if not field_value:
            return None
        return field_value


# ==================== 国际化多语言支持 ====================

class I18N:
    def __init__(self):
        self.current_lang = "en"  # 默认中文
        self.translations = {}
        self.locales_dir = "locales"
        self.load_language("en")

    def load_language(self, lang_code):
        """加载指定语言的 JSON 文件"""
        file_path = os.path.join(self.locales_dir, f"{lang_code}.json")
        if not os.path.exists(file_path):
            print(f"Warning: Language file {file_path} not found.")
            return False

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
            self.current_lang = lang_code
            return True
        except Exception as e:
            print(f"Error loading language file: {e}")
            return False

    def get(self, key, default=None):
        """获取翻译文本"""
        return self.translations.get(key, default if default else key)


# 全局实例
i18n = I18N()


def _(key):
    """快捷翻译函数"""
    return i18n.get(key)


if __name__ == "__main__":
    app = App()
    app.mainloop()

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
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Set, List, Any, Dict
import customtkinter as ctk
from tkinter import messagebox, filedialog
from ruamel.yaml import YAML
from ruamel.yaml.constructor import ConstructorError
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
    '海外环境': {'ip_address': 'sgdns.shanlipoc.com:10200', 'context': 'pocstar'},
    '国内环境2.0': {'ip_address': 'cndns.shanliptt.com:10200', 'context': 'show'},
}

DEFAULT_ENV = "海外环境"

LOGIN_TYPE_MAPPING = {
    "账号登录": "account",
    "IMEI登录": "serial",
    "ICCID登录": "iccid"
}

MAP_CONFIG_TEMPLATES = {
    "百度 [国内]": {
        "enabled": True,
        "report": True,
        "map_type": "baidu",
        "provider": "baidu",
        "coor": "bd09ll",
        "update_period_sec": 40,
        "report_period_sec": 40
    },
    "百度 [海外]": {
        "enabled": True,
        "report": True,
        "map_type": "baidu",
        "provider": "baidu",
        "coor": "wgs84",
        "update_period_sec": 40,
        "report_period_sec": 40
    },
    "谷歌": {
        "enabled": True,
        "report": True,
        "map_type": "google",
        "provider": "google",
        "coor": "wgs84",
        "update_period_sec": 40,
        "report_period_sec": 40
    },
    "GPS": {
        "enabled": True,
        "report": True,
        "map_type": "none",
        "provider": "default",
        "coor": "default",
        "update_period_sec": 40,
        "report_period_sec": 40
    }
}


# 关键文件路径
PATH_YML = PROJECT_PATH / "app_out" / "apktool.yml"
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
}

# 工具链路径
ZIPALIGN_EXE = PROJECT_PATH / "win" / "zipalign.exe"
APKSIGNER_BAT = PROJECT_PATH / "win" / "apksigner.bat"

# 业务常量
LAUNCHER_MODULE_PATH = ["ui", "launcherModule"]
DEFAULT_CUSTOM_LIST = [
    "join_next_group", "switch_group_name_tts", "switch_group_click",
    "join_prev_group", "new_call_in"
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
            timeout=15
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
            timeout=15
        )
        return result.returncode == 0
    except Exception:
        return False


def show_env_error_dialog(parent: ctk.CTk, missing_list: List[str]) -> None:
    """显示环境缺失的弹窗"""
    msg = "系统环境检查未通过，缺少以下组件：\n\n"
    if "ADB" in missing_list:
        msg += "❌ ADB (Android Debug Bridge)\n   " \
               "解决：解压Env中的ADB压缩包并进行安装，设置系统变量。\n"
    if "JAVA" in missing_list:
        msg += "❌ Java (JDK/JRE)\n   " \
               "解决：解压Env中的JDK压缩包并进行安装\n"
    msg += "\n请安装缺失组件后点击【重试检测】。"

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
            self.log_callback(f"[Error] 读取配置失败：{e}\n")
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
                self.log_callback(f"[OK] 配置已保存到 {JSON_FILE}\n")
            return True
        except Exception as e:
            self.log_callback(f"[Error] 保存失败：{e}\n")
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
                    stderr=subprocess.DEVNULL
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
                timeout=5
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
        mode_name = "防抖模式 (PTT)" if is_many_mode else "标准模式 (SOS)"

        self.log_callback(f"\n--- 启动监听 (模式：{mode_name}) ---\n")
        if self._clear_logcat():
            self.log_callback("[Info] 日志缓冲区已清空。\n"
                              "[tip]  如按下按键后无日志输出，已知键值请到终端配置中自行输入!!!")

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
                        self.log_callback(f"[Skip] Action '{action_str}' 已存在。\n")
                    continue

                last_process_time = current_time
                self.skip_count = 0

                match_k = re_keycode.search(line)
                code_info = f" (KeyCode: {match_k.group(1)})" if match_k else ""
                self.log_callback(f"\n[NEW] 捕获 Action: {action_str}{code_info}\n")

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
                self.log_callback(f"[OK] 已生成键位：{', '.join(created_keys)} (Key: {new_virtual_code})\n")

                if self.save_config(silent=True):
                    self.log_callback("[Auto-Save] ✅ 配置已保存。\n")
                    if self.config_callback:
                        self.config_callback()
                self.log_callback("\n")

        except Exception as e:
            if not self.stop_event.is_set():
                self.log_callback(f"\n[Error] 监听异常：{e}\n")
        finally:
            self._kill_process()
            self.is_running = False
            self.log_callback("\n[Info] 监听已停止。\n")

    def start_capture(self, key_type: str) -> None:
        """启动监听线程"""
        if self.is_running:
            self.log_callback("[Warning] 监听已在运行中。\n")
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
        messagebox.showerror("错误", f"slclient.json文件不存在：\n{PATH_SLCLIENT_JSON}")
        return False

    # 2. 映射UI值到JSON的login_mode值
    login_mode_val = LOGIN_TYPE_MAPPING.get(login_type_ui, "account")

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

def update_slclient_map_type(map_type_ui: str) -> bool:
    if not PATH_SLCLIENT_JSON.exists():
        messagebox.showerror("错误", f"slclient.json 文件不存在：\n{PATH_SLCLIENT_JSON}")
        return False

    if map_type_ui not in MAP_CONFIG_TEMPLATES:
        messagebox.showerror("错误", f"未知的地图类型：{map_type_ui}")
        return False

    lbs_config = MAP_CONFIG_TEMPLATES[map_type_ui]

    try:
        with open(PATH_SLCLIENT_JSON, "r", encoding="utf-8") as f:
            slclient_data = json.load(f)

        slclient_data["lbs"] = lbs_config

        with open(PATH_SLCLIENT_JSON, "w", encoding="utf-8") as f:
            json.dump(slclient_data, f, indent=2, ensure_ascii=False)

        return True

    except Exception as e:
        messagebox.showerror("修改失败", f"更新 slclient.json 出错：\n{str(e)}")
        traceback.print_exc()
        return False


# ==================== 前端 UI 类 ====================

class App(ctk.CTk):
    """主应用程序窗口"""

    def __init__(self):
        super().__init__()
        self.title("App Adaptation_1.3")
        self.geometry("1200x700")

        # 状态变量
        self.backend: Optional[SmartKeyBackend] = None
        self.current_device: str = ""
        self.log_queue: queue.Queue = queue.Queue()
        self.is_listening: bool = False
        self.env_checker: EnvChecker = EnvChecker(self)
        self.current_apk_type: str = "大屏"
        self.custom_apk_path = None


        # 事件绑定
        self.bind("<<EnvRetry>>", lambda e: self.on_env_retry())
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 打包配置状态管理
        self.build_config = {
            "env_type": "",      # 默认环境类型
            "map_source": "baidu",    # 默认地图
            "encoding": "amrnb"       # 默认编码
        }

        self.slclient_options = {}  # 存储从 slclient.json 解析出的可选值

        self._init_sidebar()
        self._init_main_area()

        # 启动定时任务
        self.after(100, self.process_log_queue)
        self.after(500, self.initial_env_check)
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
            self.append_log(f"[Warning] JSON 格式错误，将使用空配置: {e}\n")
        except Exception as e:
            self.append_log(f"[Error] 读取 JSON 文件失败: {e}\n")

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
        self.device_label = ctk.CTkLabel(self.sidebar_frame, text="ADB 设备:", anchor="w")
        self.device_label.grid(row=1, column=0, padx=20, pady=(10, 0))
        self.device_var = ctk.StringVar(value="检测中...")
        self.device_menu = ctk.CTkOptionMenu(
            self.sidebar_frame,
            variable=self.device_var,
            values=[],
            command=self.on_device_change
        )
        self.device_menu.grid(row=2, column=0, padx=20, pady=5)
        self.refresh_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="刷新设备",
            command=self.refresh_devices,
            height=30
        )
        self.refresh_btn.grid(row=3, column=0, padx=20, pady=5)

        # 监听模式
        self.mode_label = ctk.CTkLabel(self.sidebar_frame, text="监听模式:", anchor="w")
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
            text="开始监听",
            fg_color="green",
            command=self.toggle_listen
        )
        self.start_btn.grid(row=7, column=0, padx=20, pady=10)
        self.clear_log_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="清空日志",
            fg_color="gray",
            command=self.clear_log
        )
        self.clear_log_btn.grid(row=8, column=0, padx=20, pady=10)

        # APK 选择区域
        self.apk_select_label = ctk.CTkLabel(self.sidebar_frame, text="选择解压APK类型:", anchor="w")
        self.apk_select_label.grid(row=9, column=0, padx=20, pady=(15, 0))

        self.build_apk_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="解压apk",
            command=self.decompile_apk
        )
        self.build_apk_btn.grid(row=12, column=0, padx=20, pady=10)

        # self.build_apk_btn = ctk.CTkButton(
        #     self.sidebar_frame,
        #     text="上传自定义apk",
        #     command=self.upload_apk
        # )
        # self.build_apk_btn.grid(row=11, column=0, padx=20, pady=10)

        self.apk_type_seg = ctk.CTkSegmentedButton(
            self.sidebar_frame,
            values=["大屏", "小屏","自定义apk"],
            command=self.on_apk_type_change,
            height=30,
            fg_color="#3498db",
            selected_color="#27ae60",
            unselected_color="gray"
        )
        self.apk_type_seg.grid(row=11, column=0, padx=20, pady=5, sticky="ew")
        self.apk_type_seg.set("大屏")

        self.build_apk_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="打包 APK",
            fg_color="#d35400",
            hover_color="#e67e22",
            command=self.build_apk
        )
        self.build_apk_btn.grid(row=13, column=0, padx=20, pady=10)

        # 底部状态栏
        self.status_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="状态：初始化...",
            anchor="w",
            text_color="gray"
        )
        self.status_label.grid(row=100, column=0, padx=20, pady=(0, 20), sticky="s")

    def _init_main_area(self) -> None:
        """初始化主内容区"""
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        self.tab_log = self.tabview.add("实时日志")
        self.tab_config = self.tabview.add("配置列表")
        self.tab_build_config = self.tabview.add("终端配置")
        self.tab_input_led_config = self.tabview.add("按键配置")


        # self.load_slclient_config()

        self._init_sidebar()
        self._init_build_config_page()
        self._init_led_config_page()

        self.log_textbox = ctk.CTkTextbox(
            self.tab_log,
            font=ctk.CTkFont(family="Consolas", size=12)
        )
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=10)

        self.scroll_frame = ctk.CTkScrollableFrame(
            self.tab_config,
            label_text="当前已收录的键位映射 (input.json)"
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.scroll_frame.grid_columnconfigure(0, weight=1)

    # ==================== 事件处理回调 ====================

    def initial_env_check(self) -> None:
        if not self.env_checker.check_all(show_dialog=True):
            self.status_label.configure(text="状态：环境缺失", text_color="red")
            self.device_var.set("等待环境修复")
            self.device_menu.configure(values=[])
            self.start_btn.configure(state="disabled")
        else:
            self.status_label.configure(text="状态：环境就绪", text_color="green")
            self.start_btn.configure(state="normal")
            self.refresh_devices()
            self.after(100, self.refresh_config_view)

    def on_env_retry(self) -> None:
        self.append_log("\n[Info] 正在重新检测环境...\n")
        if self.env_checker.check_all(show_dialog=False):
            self.append_log("[OK] 环境检测通过！\n")
            self.status_label.configure(text="状态：环境就绪", text_color="green")
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
            out = subprocess.check_output(["adb", "devices"], text=True, stderr=subprocess.DEVNULL)
            devs = [
                line.split()[0] for line in out.splitlines()
                if "\tdevice" in line and not line.startswith("List")
            ]
            current_val = self.device_var.get()
            self.device_menu.configure(values=devs if devs else ["未检测到设备"])

            if devs:
                if current_val not in devs or current_val in ["未连接", "未检测到设备", "检测中...", "等待环境修复"]:
                    self.device_var.set(devs[0])
                    self.current_device = devs[0]
                else:
                    self.current_device = current_val
                self.status_label.configure(text=f"状态：已连接\n{self.current_device}", text_color="green")
            else:
                self.device_var.set("未检测到设备")
                self.current_device = ""
                self.status_label.configure(text="状态：无设备", text_color="red")
        except Exception:
            if self.winfo_exists():
                self.device_menu.configure(values=["ADB 错误"])
            self.device_var.set("ADB 错误")

    def on_device_change(self, selection: str) -> None:
        if selection not in ["未检测到设备", "ADB 错误"]:
            self.current_device = selection
        self.status_label.configure(text=f"状态：已切换\n{selection}", text_color="green")

    def toggle_listen(self) -> None:
        if not self.winfo_exists():
            return
        if not is_adb_installed():
            messagebox.showerror("错误", "ADB 环境丢失！")
            self.env_checker.check_all(show_dialog=True)
            return
        if not self.current_device or self.current_device in ["未检测到设备", "ADB 错误", "未连接"]:
            messagebox.showerror("错误", "请先选择有效的 ADB 设备！")
            self.refresh_devices()
            return

        if self.is_listening:
            if self.backend:
                self.backend.stop_capture()
            self.is_listening = False
            self.start_btn.configure(text="开始监听", fg_color="green")
            self.status_label.configure(text="状态：已停止", text_color="orange")
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
            self.start_btn.configure(text="停止监听", fg_color="red")
            self.status_label.configure(text="状态：监听中", text_color="green")
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
        self.after(100, self.process_log_queue)

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

            if not intents and not stdkeys:
                lbl = ctk.CTkLabel(
                    self.scroll_frame,
                    text="暂无配置数据。\n请点击“手动保存”添加配置。",
                    text_color="gray",
                    font=ctk.CTkFont(size=14)
                )
                lbl.grid(row=0, column=0, pady=40, columnspan=5)
                return

            # 3. 绘制表头
            headers = ["键名 (Key Name)", "事件类型", "虚拟keycode", "Intent Action", "默认命令"]
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

                # 提取数据
                event_str = sk.get("event", "N/A")
                key_val = sk.get("key", "N/A")
                action_str = info.get("action", "-")

                # 提取命令 ID
                cmds = ac.get("default", [])
                if isinstance(cmds, list):
                    cmd_ids = [c.get("command", {}).get("id", "") for c in cmds if isinstance(c, dict)]
                    cmd_str = ", ".join(filter(None, cmd_ids))
                else:
                    cmd_str = "-"

                if not cmd_str:
                    cmd_str = "-"

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
            if row_idx == 1:
                ctk.CTkLabel(self.scroll_frame, text="未找到有效的完整配置项。", text_color="gray").grid(row=1, column=0,
                                                                                                        columnspan=5)

        except Exception as e:
            print(f"刷新配置视图出错: {e}")
            if self.winfo_exists():
                err_lbl = ctk.CTkLabel(
                    self.scroll_frame,
                    text=f"加载失败: {str(e)}",
                    text_color="#c0392b"
                )
                err_lbl.grid(row=0, column=0, pady=20)

    def on_closing(self) -> None:
        if self.backend and self.is_listening:
            self.append_log("\n[Info] 正在停止监听以关闭程序...\n")
            self.backend.stop_capture()
        time.sleep(0.5)
        self.destroy()

    def on_login_type_change(self, selected_val: str) -> None:
        """登录方式切换回调：更新预览 + 修改slclient.json"""
        self._update_preview("login_type", selected_val)

        if update_slclient_login_type(selected_val):
            self.append_log(f"[OK] 已将登录方式改为:{selected_val}\n")
            self.status_label.configure(
                text=f"登录方式已更新为\n"
                     f"{selected_val}",
                text_color="#27ae60"
            )
        else:
            self.append_log(f"[Error] 未能更新slclient.json登录方式：{selected_val}\n")

    def on_apk_type_change(self, value: str) -> None:
        self.current_apk_type = value
        self.status_label.configure(text=f"状态：已选择 {value}", text_color="#d35400")
        self.append_log(f"[Info] APK 类型切换为：{value}\n")

    def _init_build_config_page(self) -> None:
        """初始化打包配置页面"""

        # 主标题
        lbl_title = ctk.CTkLabel(
            self.tab_build_config,
            text="APK属性配置",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl_title.pack(pady=(15, 10))

        # --- 主容器：使用 Grid 布局实现 2x2 ---
        grid_frame = ctk.CTkFrame(self.tab_build_config, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # 配置行列权重，确保四等分 (weight=1 表示平均分配空间)
        grid_frame.grid_columnconfigure(0, weight=1)
        grid_frame.grid_columnconfigure(1, weight=1)
        grid_frame.grid_rowconfigure(0, weight=1)
        grid_frame.grid_rowconfigure(1, weight=1)

        # --- 创建四个子模块卡片 ---

        # 1. 左上：环境配置
        self.frame_env = self._create_config_card(
            parent=grid_frame,
            title="🌍 环境配置 (Environment)",
            row=0, col=0,
            content_func=self._build_env_content
        )

        # 2. 右上：声音配置
        self.frame_sound = self._create_config_card(
            parent=grid_frame,
            title="🔊 声音配置 (Audio)",
            row=0, col=1,
            content_func=self._build_sound_content
        )

        # 3. 左下：地图配置
        self.frame_map = self._create_config_card(
            parent=grid_frame,
            title="🗺️地图配置 (Map)",
            row=1, col=0,
            content_func=self._build_map_content
        )

        # 4. 右下：其他设置
        self.frame_other = self._create_config_card(
            parent=grid_frame,
            title="⚙️ 其他设置 (Others)",
            row=1, col=1,
            content_func=self._build_other_content
        )

        # 初始化时加载一次默认值
        self.after(500, self.load_all_configs)

    def _init_led_config_page(self) -> None:
        """初始化按键LED配置页面 (上下平分布局)"""

        # 1. 主标题
        lbl_title = ctk.CTkLabel(
            self.tab_input_led_config,
            text="按键配置",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl_title.pack(pady=(15, 10))

        # 2. 主容器：使用 Grid 布局实现 上下 1:1 平分
        # fg_color="transparent" 让背景透明，与 Tab 背景融合
        grid_frame = ctk.CTkFrame(self.tab_input_led_config, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # 【关键步骤】配置行列权重
        # 只有 1 列 (column 0)，权重为 1 (占满宽度)
        grid_frame.grid_columnconfigure(0, weight=1)

        # 有 2 行 (row 0 和 row 1)，权重都为 1 -> 这意味着它们将平均分配高度 (50% : 50%)
        grid_frame.grid_rowconfigure(0, weight=1)
        grid_frame.grid_rowconfigure(1, weight=1)

        # 3. 创建上下两个子模块卡片

        # --- 上半部分：LED 模式/策略配置 ---
        self.frame_led_mode = self._create_config_card(
            parent=grid_frame,
            title="💡 按键 配置",
            row=0, col=0,
            content_func=self._build_input_mode_content
        )

        # --- 下半部分：颜色与亮度配置 ---
        self.frame_led_color = self._create_config_card(
            parent=grid_frame,
            title="🎨  其他配置",
            row=1, col=0,
            content_func=self._build_led_color_content
        )


        # 4. 初始化加载 (可选，如果需要从文件读取默认值)
        # self.after(500, self.load_led_configs)

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
        ctk.CTkLabel(
            parent,
            text="按下 PTT:",
            anchor="w",
            width=label_width
        ).grid(row=0, column=0, padx=(pad_x, 5), pady=(pad_y, 2), sticky=sticky_label)

        self.entry_ptt_press = ctk.CTkEntry(
            parent,
            placeholder_text="Action for PTT_DOWN",
            height=entry_height
        )
        self.entry_ptt_press.grid(row=0, column=1, padx=(5, pad_x), pady=(pad_y, 2), sticky=sticky_entry)

        # --- 2. 抬起 PTT (Release) ---
        ctk.CTkLabel(
            parent,
            text="抬起 PTT:",
            anchor="w",
            width=label_width
        ).grid(row=1, column=0, padx=(pad_x, 5), pady=2, sticky=sticky_label)

        self.entry_ptt_release = ctk.CTkEntry(
            parent,
            placeholder_text="Action for PTT_UP",
            height=entry_height
        )
        self.entry_ptt_release.grid(row=1, column=1, padx=(5, pad_x), pady=2, sticky=sticky_entry)

        # --- 3. SOS 按键 ---
        ctk.CTkLabel(
            parent,
            text="SOS 按键:",
            anchor="w",
            width=label_width
        ).grid(row=2, column=0, padx=(pad_x, 5), pady=2, sticky=sticky_label)

        self.entry_sos = ctk.CTkEntry(
            parent,
            placeholder_text="Action for SOS",
            height=entry_height
        )
        self.entry_sos.grid(row=2, column=1, padx=(5, pad_x), pady=2, sticky=sticky_entry)

        # --- 4. 保存按钮 ---

        btn_save = ctk.CTkButton(
            parent,
            text="➕ 保存配置",
            command=self._on_save_manual_keys,
            fg_color="#28a745",
            hover_color="#218838",
            height=28,
            width=25,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        btn_save.grid(row=3, column=0, columnspan=2, padx=pad_x, pady=(pad_y, 10), sticky="e")

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
            msg_lines = [f"✅ 配置已保存"]
            if has_ptt:
                msg_lines.append(f"   🟢 PTT Key: {new_vkey_ptt} ({name_ptt_down}, {name_ptt_up})")
            if has_sos:
                msg_lines.append(f"   🔴 SOS Key: {new_vkey_sos} ({name_sos_down}, {name_sos_up})")

            final_msg = "\n".join(msg_lines)

            self.lbl_env_info.configure(
                text="✅ 保存成功!",
                text_color="#27ae60",
                font=ctk.CTkFont(size=12, weight="bold")
            )
            self.append_log(f"[Manual Save] {final_msg}\n")
            messagebox.showinfo("成功", final_msg)

            if hasattr(self, '_safe_refresh_config_view'):
                self._safe_refresh_config_view()
            elif hasattr(self, 'refresh_config_view'):
                self.refresh_config_view()

        except Exception as e:
            error_msg = f"❌ 保存失败：{str(e)}"
            self.lbl_env_info.configure(
                text=error_msg,
                text_color="#c0392b",
                font=ctk.CTkFont(size=12, weight="bold")
            )
            self.append_log(f"[Error] _on_save_manual_keys: {e}\n")
            messagebox.showerror("错误", error_msg)



    def _build_led_color_content(self, parent):
        """填充下半部分：颜色和亮度"""
        ctk.CTkLabel(
            parent,
            text="（功能设计开发中…）",
            text_color="gray"
        ).grid(row=2, column=0, padx=10, pady=(0, 10), sticky="w")

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

        # 卡片内部布局
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)  # 内容区域可伸缩

        # 标题栏
        lbl_title = ctk.CTkLabel(
            card, text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        lbl_title.grid(row=0, column=0, padx=15, pady=10, sticky="w")

        # 内容容器 (由 content_func 填充)
        content_frame = ctk.CTkFrame(card, fg_color="transparent")
        content_frame.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")
        content_frame.grid_columnconfigure(1, weight=1)  # 让输入框撑开

        # 执行填充函数
        content_func(content_frame)

        return card

    def _build_env_content(self, parent):
        """构建环境配置内容"""

        # --- 1. 准备选项列表 ---
        base_options = list(ENV_CONF.keys())
        self.CUSTOM_OPTION_NAME = "独立部署"

        if base_options:
            env_options = base_options + [self.CUSTOM_OPTION_NAME]
        else:
            env_options = [self.CUSTOM_OPTION_NAME]

        # --- 2. 创建控件 ---

        # 标签
        ctk.CTkLabel(parent, text="服务器节点:", anchor="w").grid(
            row=0, column=0, padx=5, pady=10, sticky="w"
        )

        # 下拉菜单
        self.opt_env = ctk.CTkOptionMenu(
            parent,
            values=env_options,
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

        # DNS 输入框
        ctk.CTkLabel(parent, text="DNS IP:", anchor="w").grid(
            row=2, column=0, padx=5, pady=(5, 2), sticky="w"
        )

        self.entry_custom_ip = ctk.CTkEntry(parent, state="disabled")
        self.entry_custom_ip.grid(row=2, column=1, padx=5, pady=(5, 2), sticky="ew")

        # Context 输入框
        ctk.CTkLabel(parent, text="Context:", anchor="w").grid(
            row=3, column=0, padx=5, pady=(2, 10), sticky="w"
        )

        self.entry_custom_context = ctk.CTkEntry(parent, state="disabled")
        self.entry_custom_context.grid(row=3, column=1, padx=5, pady=(2, 10), sticky="ew")

        # 回显默认文字
        # self.entry_custom_context.configure(state="normal")
        # self.entry_custom_context.delete(0, 'end')
        # self.entry_custom_context.insert(0, "demotext")
        # self.entry_custom_context.configure(state="disabled")

        # 登录方式下拉框
        ctk.CTkLabel(parent, text="登录方式:", anchor="w").grid(
            row=4, column=0, padx=5, pady=10, sticky="w"
        )

        self.opt_login_type = ctk.CTkOptionMenu(
            parent,
            values=['账号登录', 'IMEI登录', 'ICCID登录'],

            command=self.on_login_type_change
        )
        self.opt_login_type.set("账号登录")
        self.opt_login_type.grid(row=4, column=1, padx=5, pady=10, sticky="ew")
        # 默认选中「账号」

        # 保存按钮（默认隐藏）
        self.btn_save_custom = ctk.CTkButton(
            parent,
            text="💾 保存",
            command=self._save_profile_changes,
            fg_color="#d35400",
            hover_color="#e67e22",
            height=28,
            font=ctk.CTkFont(weight="bold")
        )
        self.btn_save_custom.grid_remove()

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

    def _save_profile_changes(self):
        """
        将当前输入的 IP 和 Context 保存到 slclient.json 的 profile 节点中。
        专用于【独立部署】模式，不影响 ENV_CONF 中的预设节点（如海外/国内）。
        """

        new_ip = self.entry_custom_ip.get().strip()
        new_context = self.entry_custom_context.get().strip()

        # 1. 基础验证
        if not new_ip or not new_context:
            self.lbl_env_info.configure(
                text="❌ 错误：DNS IP 和 Context 不能为空！",
                text_color="#c0392b",
                font=ctk.CTkFont(size=12, weight="bold")
            )
            return

        ip_part = new_ip.split(':')[0]
        if not re.match(r'^\d{1,3}(\.\d{1,3}){3}$', ip_part) and not re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                                                                              ip_part):
            if not messagebox.askyesno("格式确认",
                                       f"检测到的 IP/域名 '{new_ip}' 格式可能不标准。\n"
                                       f"确定要保存到独立部署配置吗？"):
                return

        try:
            json_path = PATH_SLCLIENT_JSON

            # 如果文件不存在，创建一个新结构
            if not json_path.exists():
                data = {}
            else:
                # 读取现有 JSON
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

            # 3. 定位并修改 profile 节点
            if "profile" not in data:
                data["profile"] = {}

            # 更新数据
            data["profile"]["context"] = new_context
            data["profile"]["dns"] = [new_ip]  # 强制存为列表，符合 slclient 常见格式

            # 4. 写回文件
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            self.entry_custom_ip.delete(0,"end")
            self.entry_custom_context.delete(0, "end")



            # 6. 成功反馈
            # success_msg = (
            #     f"✅ 独立部署配置已保存!\n"
            #     f"- Context: {new_context}\n"
            #     f"- DNS: {new_ip}"
            # )
            # self.lbl_env_info.configure(
            #     text=success_msg,
            #     text_color="#27ae60",
            #     font=ctk.CTkFont(size=11, weight="bold")
            # )

            messagebox.showinfo("保存成功", "配置已写入")


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
        ctk.CTkLabel(parent, text="开启Tone:", anchor="w").grid(row=1, column=0, padx=5, pady=8, sticky="w")
        self.switch_sfx = ctk.CTkSwitch(parent, text=" ",
                                        command=lambda: (
                                            self._sync_tone_enabled_to_json(bool(self.switch_sfx.get()))
                                        ))
        self.switch_sfx.grid(row=1, column=1, padx=5, pady=8, sticky="w")
        self.switch_sfx.select()  # 默认开启

        # 3. 语音编码
        ctk.CTkLabel(parent, text="语音编码:", anchor="w").grid(
            row=2, column=0, padx=5, pady=10, sticky="w"
        )

        self.opt_sound = ctk.CTkOptionMenu(
            parent,
            values=["amrnb", "evrc8k", "opus"],
            command=self._sync_codec_to_json
        )
        self.opt_sound.grid(row=2, column=1, padx=5, pady=10, sticky="ew")

        self.opt_sound.set("amrnb")

        # 4. 音频系统
        ctk.CTkLabel(parent, text="音频系统:", anchor="w").grid(
            row=3, column=0, padx=5, pady=10, sticky="w"
        )

        self.opt_sound = ctk.CTkOptionMenu(
            parent,
            values=["default", "sles", "oem"],
            command=self._sync_soundsystem_to_json
        )
        self.opt_sound.grid(row=3, column=1, padx=5, pady=10, sticky="ew")

        self.opt_sound.set("default")

        # 5. 播放通道
        ctk.CTkLabel(parent, text="播放通道:", anchor="w").grid(
            row=4, column=0, padx=5, pady=10, sticky="w"
        )

        self.opt_sound = ctk.CTkOptionMenu(
            parent,
            values=["music", "voice"],
            command=self._sync_play_to_json
        )
        self.opt_sound.grid(row=4, column=1, padx=5, pady=10, sticky="ew")

        self.opt_sound.set("music")

        # 6. 录制通道
        ctk.CTkLabel(parent, text="录制通道:", anchor="w").grid(
            row=5, column=0, padx=5, pady=10, sticky="w"
        )

        self.opt_sound = ctk.CTkOptionMenu(
            parent,
            values=["mic", "voice", "communication","recognition"],
            command=self._sync_record_to_json
        )
        self.opt_sound.grid(row=5, column=1, padx=5, pady=10, sticky="ew")

        self.opt_sound.set("recognition")

    def _sync_codec_to_json(self, selected_codec: str) -> None:
        """
        【实时保存】当语音编码改变时，立即更新 slclient.json 中的 sound.codec
        :param selected_codec: 选中的编码字符串 (如 "amrnb", "opus")
        """
        try:
            data = self._load_slclient_json()

            if "sound" not in data:
                data["sound"] = {}

            current_val = data["sound"].get("codec")

            if current_val != selected_codec:
                data["sound"]["codec"] = selected_codec

                with open(PATH_SLCLIENT_JSON, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)

                self.append_log(f"[OK] 语音编码已切换: {selected_codec}\n")
                self.status_label.configure(
                    text=f"语音编码已切换为\n"
                         f"{selected_codec}",
                    text_color="#27ae60"
                )
            else:
                pass

        except Exception as e:
            self.append_log(f"[Error] 保存语音编码失败: {e}\n")

    def _sync_soundsystem_to_json(self, selected_codec: str) -> None:
        try:
            data = self._load_slclient_json()

            if "dsp" not in data:
                self.append_log("错误,丢失音频节点")

            current_val = data["dsp"].get("provider")

            if current_val != selected_codec:
                data["dsp"]["provider"] = selected_codec

                with open(PATH_SLCLIENT_JSON, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)

                self.append_log(f"[OK] 音频系统已切换: {selected_codec}\n")
                self.status_label.configure(
                    text=f"音频系统已切换为\n"
                         f"{selected_codec}",
                    text_color="#27ae60"
                )
            else:
                pass

        except Exception as e:
            self.append_log(f"[Error] 保存语音编码失败: {e}\n")

    def _sync_play_to_json(self, selected_codec: str) -> None:
        try:
            data = self._load_slclient_json()

            if "dsp" not in data:
                self.append_log("错误,丢失音频节点")

            current_val = data["dsp"].get("play_stream")

            if current_val != selected_codec:
                data["dsp"]["play_stream"] = selected_codec

                with open(PATH_SLCLIENT_JSON, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)

                self.append_log(f"[OK] 播放通道已切换: {selected_codec}\n")
                self.status_label.configure(
                    text=f"播放通道已切换为\n"
                         f"{selected_codec}",
                    text_color="#27ae60"
                )
            else:
                pass

        except Exception as e:
            self.append_log(f"[Error] 保存语音编码失败: {e}\n")

    def _sync_record_to_json(self, selected_codec: str) -> None:
        try:
            data = self._load_slclient_json()

            if "dsp" not in data:
                self.append_log("错误,丢失音频节点")

            current_val = data["dsp"].get("record_stream")

            if current_val != selected_codec:
                data["dsp"]["record_stream"] = selected_codec

                with open(PATH_SLCLIENT_JSON, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)

                self.append_log(f"[OK] 录制通道已切换: {selected_codec}\n")
                self.status_label.configure(
                    text=f"录制通道已切换为\n"
                         f"{selected_codec}",
                    text_color="#27ae60"
                )
            else:
                pass

        except Exception as e:
            self.append_log(f"[Error] 保存语音编码失败: {e}\n")

    def _sync_tone_enabled_to_json(self, is_enabled: bool) -> None:
        """
        【实时保存】确保写入的是 JSON 标准的 true/false，而不是 0/1
        """
        try:
            data = self._load_slclient_json()

            if "sound" not in data:
                data["sound"] = {}

            json_value = bool(is_enabled)

            current_val = data["sound"].get("tone_enabled")
            if current_val != json_value:
                data["sound"]["tone_enabled"] = json_value

                with open(PATH_SLCLIENT_JSON, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)

                status = "开启" if json_value else "关闭"
                self.append_log(f"[OK] Tone 音效已{status}\n")

                self.status_label.configure(
                    text=f"Tone 音效已{status}",
                    text_color="#27ae60"
                )

        except Exception as e:
            self.append_log(f"[Error] 保存 Tone 开关失败: {e}\n")

    def _build_map_content(self, parent):
        """构建地图配置内容"""
        # 1. 地图源
        ctk.CTkLabel(parent, text="地图数据源:", anchor="w").grid(
            row=0, column=0, padx=5, pady=10, sticky="w"
        )

        self.opt_map = ctk.CTkOptionMenu(
            parent,
            values=list(MAP_CONFIG_TEMPLATES.keys()),
            command=lambda v: self._on_map_type_changed(v)
        )
        self.opt_map.grid(row=0, column=1, padx=5, pady=10, sticky="ew")

        self.opt_map.set("谷歌")

        # # 2. 卫星图层
        # ctk.CTkLabel(parent, text="默认卫星图:", anchor="w").grid(row=1, column=0, padx=5, pady=10, sticky="w")
        # self.switch_satellite = ctk.CTkSwitch(parent, text="Satellite Mode", command=lambda: self._update_preview("satellite", self.switch_satellite.get()))
        # self.switch_satellite.grid(row=1, column=1, padx=5, pady=10, sticky="w")

    def _on_map_type_changed(self, map_type_ui: str):
        """地图类型变更回调"""
        if update_slclient_map_type(map_type_ui):
            self._update_preview("map_provider", map_type_ui)
            self.append_log(f"[OK] 地图类型已更新为：{map_type_ui}\n")
            self.status_label.configure(
                text=f"登录方式已更新为\n"
                     f"{map_type_ui}",
                text_color="#27ae60"
            )
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
        ctk.CTkLabel(parent, text="开启TTS:", anchor="w").grid(row=1, column=0, padx=5, pady=8, sticky="w")
        self.switch_sfx = ctk.CTkSwitch(parent, text=" ",
                                        command=lambda: (
                                            self._sync_tts_enabled_to_json(bool(self.switch_sfx.get()))
                                        ))
        self.switch_sfx.grid(row=1, column=1, padx=5, pady=8, sticky="w")
        self.switch_sfx.deselect()  # 默认关闭

        # --- launcher开关---
        ctk.CTkLabel(parent, text="设置为 Launcher:", anchor="w").grid(
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
    def android_attr(self,name):
        return f"{{{ANDROID_NAMESPACE}}}{name}"

    def write_pretty_xml(self,tree, file_path):
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
            self.append_log(" 错误：找不到 AndroidManifest.xml")
            if hasattr(self, 'switch_launcher'):
                self.switch_launcher.deselect()
            return

        try:
            ET.register_namespace("android", ANDROID_NAMESPACE)
            tree = ET.parse(manifest_path)
            root = tree.getroot()

            application = root.find("application")
            if application is None:
                self.append_log(" 错误：未找到 <application> 标签")
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
                self.append_log(f" 错误：未找到目标 Activity (候选:{candidate_activity_names})")
                self.switch_launcher.deselect()  # 复位
                return

            intent_filter = target_activity.find("intent-filter")
            if intent_filter is None:
                msg = f" 错误：{found_activity_name} 没有 <intent-filter>，无法操作"
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
                    self.append_log(f"[ok] 已设置 为桌面 Launcher\n")
                    self.status_label.configure(
                        text="设置桌面Launcher成功",
                        text_color="#27ae60"
                    )

                else:
                    pass
            else:
                if has_home:
                    intent_filter.remove(home_category_elem)
                    self.write_pretty_xml(tree, manifest_path)
                    self.append_log(f"[ok] 已取消 Launcher 权限\n")
                    self.status_label.configure(
                        text="取消桌面Launcher成功",
                        text_color="#27ae60"
                    )
                else:
                    pass

        except Exception as e:
            self.append_log(f" 操作失败：{e}")
            if hasattr(self, 'switch_launcher'):
                self.switch_launcher.deselect()

    def _sync_tts_enabled_to_json(self, is_enabled: bool) -> None:
        """
        【实时保存】确保写入的是 JSON 标准的 true/false，而不是 0/1
        """
        try:
            data = self._load_slclient_json()

            json_value = bool(is_enabled)

            current_val = data["tts"].get("enabled")
            if current_val != json_value:
                data["tts"]["enabled"] = json_value

                with open(PATH_SLCLIENT_JSON, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)

                status = "开启" if json_value else "关闭"
                self.append_log(f"[OK] tts 已{status}\n")

                self.status_label.configure(
                    text=f"tts已{status}",
                    text_color="#27ae60"
                )

        except Exception as e:
            self.append_log(f"[Error] 保存 Tone 开关失败: {e}\n")

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

    def _save_custom_env_to_file(self):
        """将当前输入的独立部署配置保存到 slclient.json"""
        import json
        import os

        ip = self.entry_custom_ip.get().strip()
        context = self.entry_custom_context.get().strip()

        # 1. 基础验证
        if not ip or not context:
            self.lbl_env_info.configure(
                text="❌ 错误：IP 和 Context 不能为空！",
                text_color="#c0392b",
                font=ctk.CTkFont(size=12, weight="bold")
            )
            return

        # 简单的 IP:Port 格式检查 (可选)
        if ":" not in ip:
            self.lbl_env_info.configure(
                text="⚠️ 提示：IP 格式建议为 'IP:端口' (如 192.168.1.1:8080)",
                text_color="#d35400",
                font=ctk.CTkFont(size=12)
            )
            # 这里不 return，允许用户强行保存，或者你可以根据需求 return

        # 2. 生成唯一的节点名称
        # 使用 "Custom_" + context 作为 key，避免冲突
        new_node_name = f"Custom_{context}"

        # 检查是否已存在同名节点
        if new_node_name in ENV_CONF:
            confirm = messagebox.askyesno(
                "节点已存在",
                f"名为 '{new_node_name}' 的配置已存在。\n是否覆盖现有配置？"
            )
            if not confirm:
                return

        # 3. 读取并更新 slclient.json
        try:
            json_path = "slclient.json"  # 确保路径正确，如果是相对路径则相对于脚本运行目录

            # 如果文件不存在，创建一个基础结构 (根据你的实际 JSON 结构调整)
            data = {}
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

            # 假设 JSON 结构是 { "nodes": { "name": {...} } } 或者直接是 { "name": {...} }
            # 请根据你实际的 slclient.json 结构调整下面的赋值逻辑
            # 这里假设结构是直接平铺的：{ "NodeName": { "ip_address": "...", "context": "..." } }
            # 如果你的结构嵌套在 "environments" 或其他键下，请相应修改，例如：data['environments'][new_node_name] = ...

            data[new_node_name] = {
                "ip_address": ip,
                "context": context,
                "description": "User Custom Environment"  # 可选描述
            }

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            # 4. 保存成功后的反馈
            self.lbl_env_info.configure(
                text=f"✅ 已保存: {new_node_name}",
                text_color="#27ae60",
                font=ctk.CTkFont(size=12, weight="bold")
            )

            # 5. 动态刷新内存和下拉菜单
            # 更新全局配置字典 (如果 ENV_CONF 是全局变量)
            ENV_CONF[new_node_name] = data[new_node_name]

            # 刷新下拉菜单选项
            current_options = list(self.opt_env.cget("values"))
            if new_node_name not in current_options:
                new_options = current_options + [new_node_name]
                self.opt_env.configure(values=new_options)
                self.opt_env.set(new_node_name)  # 自动选中新建的

            # 触发选中事件，应用新配置
            self._on_env_selected(new_node_name)

            # 可选：保存后自动切回“预设模式”并选中刚创建的项，或者保持独立部署模式
            # 这里选择保持独立部署模式但提示已保存，或者你可以选择自动关闭开关：
            # self.switch_custom_env.deselect()
            # self._toggle_custom_env_inputs()

        except Exception as e:
            self.lbl_env_info.configure(
                text=f"❌ 保存失败: {str(e)}",
                text_color="#c0392b",
                font=ctk.CTkFont(size=12)
            )
            print(f"Error saving config: {e}")

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

        if not ip_address or not context:
            self.append_log(f"[Warn] 节点 {node_name} 配置不完整，跳过写入。\n")
            return

        try:
            data = self._load_slclient_json()

            # 更新 profile 节点
            if "profile" not in data:
                data["profile"] = {}

            # 写入 DNS (列表格式) 和 Context
            data["profile"]["dns"] = [ip_address]
            data["profile"]["context"] = context

            # 写回文件
            with open(PATH_SLCLIENT_JSON, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            # self.append_log(f"[OK] 节点已切换: {node_name}\n")
            self.status_label.configure(
                text=f"登录方式已更新为\n"
                     f"{node_name}",
                text_color="#27ae60"
            )

        except Exception as e:
            # self.append_log(f"[Error] 同步节点配置到 JSON 失败: {e}\n")
            return

    def _on_env_selected(self, selected_name):
        """当下拉菜单选择改变时触发 - 核心路由"""
        if not hasattr(self, 'switch_custom_env'):
            return

        # 情况 A: 用户选择了预设节点 (海外/国内)
        self._sync_preset_node_to_json(selected_name)
        if selected_name != self.CUSTOM_OPTION_NAME:

            # 1. 关闭编辑模式
            if self.switch_custom_env.get():
                self.switch_custom_env.deselect()
                self._toggle_custom_env_inputs()
                self.btn_save_custom.grid_remove()


            # 2. 禁用开关
            self.switch_custom_env.configure(state="disabled")

            # 3. 获取预设配置
            preset = ENV_CONF.get(selected_name, {})

            dns_ip = preset.get("ip_address", "")
            context = preset.get("context", "")

            # 4. 先启用输入框才能写入
            self.entry_custom_ip.configure(state="normal")
            self.entry_custom_context.configure(state="normal")

            self.entry_custom_ip.delete(0, "end")
            self.entry_custom_ip.insert(0, dns_ip)

            self.entry_custom_context.delete(0, "end")
            self.entry_custom_context.insert(0, context)

            # 5. 写完再禁用
            self.entry_custom_ip.configure(state="disabled")
            self.entry_custom_context.configure(state="disabled")

            self._show_preset_info(selected_name)

        # 情况 B: 用户选择了 "独立部署 (Profile)"
        elif selected_name == self.CUSTOM_OPTION_NAME:
            # 1. 启用开关
            self.switch_custom_env.configure(state="normal", text="启用手动编辑")

            # 2. 自动开启编辑模式 (如果还没开)
            if not self.switch_custom_env.get():
                self.switch_custom_env.select()
                self._toggle_custom_env_inputs()  # 执行开启界面的逻辑
            else:
                # 如果已经是开启状态，刷新一下数据（防止切换回来数据没更新）
                self._refresh_custom_inputs()

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

    def _show_preset_info(self,node_name):
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
        # 读取slclient.json的login_mode并同步到UI
        if PATH_SLCLIENT_JSON.exists():
            try:
                with open(PATH_SLCLIENT_JSON, "r", encoding="utf-8") as f:
                    slclient_data = json.load(f)

                # 读取profile下的login_mode
                login_mode_val = slclient_data.get("profile", {}).get("login_mode", "account")

                # 反向映射：JSON的login_mode值 -> UI显示值
                reverse_mapping = {v: k for k, v in LOGIN_TYPE_MAPPING.items()}
                ui_val = reverse_mapping.get(login_mode_val, "账号登录")

                # 设置到下拉框
                self.opt_login_type.set(ui_val)
                self._update_preview("login_type", ui_val)

            except Exception as e:
                self.append_log(f"[Warning] 读取slclient.json的login_mode失败：{e}\n")
    # TODO 打包时获取配置写入
    def apply_selected_config_to_slclient(self) -> None:
        """打包时调用：收集所有四个模块的数据并写入 JSON"""
        if not PATH_SLCLIENT_JSON.exists():
            self.append_log("[Error] slclient.json 不存在，无法写入配置。\n")
            return

        try:
            with open(PATH_SLCLIENT_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if not hasattr(self, 'current_env_config'):
                self.append_log("[Error] 环境配置未初始化。\n")
                return

            cfg = self.current_env_config

            # 如果是独立部署模式，校验输入是否为空
            if cfg.get('is_custom'):
                if not cfg['ip'] or not cfg['context']:
                    self.append_log("[Error] 独立部署模式下，IP 和 Context 不能为空！请填写或关闭独立部署开关。\n")
                    # 可以选择弹窗提示或阻止打包
                    return
                self.append_log(f"[Info] 使用独立部署配置: {cfg['ip']}\n")

            # 写入逻辑 (与之前一致)
            if "network" not in data: data["network"] = {}
            data["network"]["server_ip"] = cfg['ip']
            data["network"]["context_path"] = cfg['context']

            # 如果有 ID 映射逻辑 (仅针对非自定义模式)
            if not cfg.get('is_custom') and "ui" in data:
                # 这里可以加入 NAME_TO_ID 逻辑
                pass

            # 2. 写入声音配置
            if hasattr(self, 'slider_bgm'):
                if "audio" not in data: data["audio"] = {}
                data["audio"]["bgm_volume"] = int(self.slider_bgm.get())
                data["audio"]["sfx_enabled"] = bool(self.switch_sfx.get())

            # 3. 写入地图配置
            if hasattr(self, 'opt_map'):
                if "map" not in data: data["map"] = {}
                data["map"]["provider"] = self.opt_map.get()
                data["map"]["satellite_default"] = bool(self.switch_satellite.get())

            # 4. 写入其他设置
            if hasattr(self, 'switch_debug'):
                if "system" not in data: data["system"] = {}
                data["system"]["debug_mode"] = bool(self.switch_debug.get())
                fps_val = getattr(self, 'entry_fps', None)
                if fps_val:
                    try:
                        data["system"]["max_fps"] = int(fps_val.get())
                    except:
                        data["system"]["max_fps"] = 60

            # 写回文件
            with open(PATH_SLCLIENT_JSON, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.append_log("[OK] 所有配置 (环境/声音/地图/其他) 已成功写入 slclient.json\n")

        except Exception as e:
            self.append_log(f"[Error] 写入 slclient.json 失败: {e}\n")
            import traceback
            traceback.print_exc()

    # 在 App 类定义之前或 __init__ 中调用
    def load_slclient_config(self):
        """启动时从 slclient.json 加载配置更新 ENV_CONF"""
        if not PATH_SLCLIENT_JSON.exists():
            print(f"⚠️ 未找到 {PATH_SLCLIENT_JSON}，使用默认硬编码配置。")
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

            # 如果有其他节点也可以在这里解析添加到 ENV_CONF
        except Exception as e:
            print(f"❌ 加载 slclient.json 失败: {e}")

    # 在 App.__init__ 中，在初始化 UI 之前调用
    # self.load_slclient_config() (如果定义为类方法) 或直接调用 load_slclient_config()

    # ==================== APK 工具链逻辑 ====================

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

    def safe_remove(self, file_path: str, retries: int = 3) -> bool:
        """安全删除文件，带重试机制"""
        for i in range(retries):
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    self.append_log(f"[OK] 已删除临时文件")
                    return True
            except PermissionError:
                self.append_log(f"[Warn] 文件被占用，等待 0.5 秒后重试... ({i + 1}/{retries})\n")
                time.sleep(0.5)
            except Exception as e:
                self.append_log(f"[Error] 删除文件失败：{e}\n")
                return False
        return False

    def run_with_live_output(self, command: List[str]) -> int:
        """
        【核心修复】双线程读取 stdout/stderr，防止死锁，并实时推送到 GUI
        """
        self.append_log(f"[CMD] {' '.join(command)}\n")

        try:
            startupinfo = None
            if platform.system() == "Windows":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )

            log_queue = queue.Queue()

            def reader_thread(stream, prefix=""):
                for line in iter(stream.readline, ""):
                    if line:
                        log_queue.put(prefix + line.strip())
                stream.close()

            t_out = threading.Thread(target=reader_thread, args=(process.stdout, ""), daemon=True)
            t_err = threading.Thread(target=reader_thread, args=(process.stderr, "[ERR] "), daemon=True)
            t_out.start()
            t_err.start()

            while t_out.is_alive() or t_err.is_alive():
                try:
                    line = log_queue.get(timeout=0.5)
                    self.after(0, self.append_log, line + "\n")
                except queue.Empty:
                    continue

            t_out.join()
            t_err.join()
            returncode = process.wait()
            self.append_log(f"[Result] 命令执行完毕，返回码：{returncode}\n")
            return returncode

        except Exception as e:
            self.append_log(f"[CRITICAL] 执行命令发生严重错误：{e}\n")
            traceback.print_exc()
            return -1

    def decompile_apk(self, output_dir: str = "app_out") -> bool:
        apk_type = self.apk_type_seg.get()
        self.current_apk_type = apk_type

        if apk_type == "大屏":
            apk_path = "LargeApp.apk"

        elif apk_type == "小屏":
            apk_path = "SmallApp.apk"

        elif apk_type == "自定义apk":

            if not self.custom_apk_path:
                choice = messagebox.askyesno("错误", "请先选择自定义APK")
                if choice:
                    self.upload_apk()
                else:
                    return
            apk_path = self.custom_apk_path

        if os.path.exists(output_dir):
            shutil.rmtree(output_dir, ignore_errors=True)
            self.append_log(f"[Info] 已清理旧目录：{output_dir}\n")

        command = [
            "java", "-jar", str(APKTOOL_JAR),
            "d", apk_path, "-s", "-o", output_dir
        ]
        exit_code = self.run_with_live_output(command)
        return exit_code == 0

    def upload_apk(self):
        file_path = filedialog.askopenfilename(
            title="选择APK文件",
            filetypes=[("APK Files", "*.apk")]
        )

        if file_path:
            self.custom_apk_path = file_path
            messagebox.showinfo("提示", f"已选择APK:\n{file_path}")

    def build_apk(self) -> None:
        """主打包入口
            解压只要打包app_out即可
        """
        output_dir: str = "app_out"

        apk_type = self.apk_type_seg.get()
        self.current_apk_type = apk_type

        if apk_type == "大屏":
            apk_path = "LargeApp.apk"

        elif apk_type == "小屏":
            apk_path = "SmallApp.apk"

        elif apk_type == "自定义apk":
            if not self.custom_apk_path:
                messagebox.askyesno("错误", "请先上传自定义APK")
                return
            apk_path = self.custom_apk_path



        # 禁用按钮防止重复点击
        self.build_apk_btn.configure(state="disabled", text="打包中...")
        self.status_label.configure(text="状态：正在打包...", text_color="#d35400")

        def task():
            try:
                self.append_log(f"\n===选中的apk{apk_path}===\n")
                self.append_log(f"\n=== 开始打包流程 ({apk_type}) ===\n")

                # # 1. 反编译
                # self.append_log("[Step 1] 正在反编译 APK...\n")
                # if not self.decompile_apk(TEMP_DIR):
                #     raise Exception("反编译失败")
                #
                # else:
                #     self.append_log("[Step 2] 编译成功\n")

                # 2. 更新版本信息
                # self.append_log("[Step 2] 正在更新版本信息...\n")
                # if os.path.exists(PATH_YML):
                #     self.update_version_info(PATH_YML)
                # else:
                #     self.append_log("[Warn] 未找到 apktool.yml，跳过版本更新\n")

                # 2.替换input.json
                self.copy_files(PATH_INPUT_JSON_SRC,PATH_INPUT_JSON_DST)

                # 3. 构建未签名 APK
                self.append_log("\n[Step 3] 正在打包 APK...\n")
                apktool_cmd = [
                    "java", "-jar", str(APKTOOL_JAR),
                    "b", TEMP_DIR, "-o", "app-unsigned-unaligned.apk"
                ]
                if self.run_with_live_output(apktool_cmd) != 0:
                    raise Exception("APK 打包失败")

                # 4. Zipalign 对齐
                self.append_log("[Step 4] 正在对齐APK...\n")
                zipalign_cmd = [
                    str(ZIPALIGN_EXE), "-v", "-p", "4",
                    "app-unsigned-unaligned.apk", "app-unsigned.apk"
                ]
                if self.run_with_live_output(zipalign_cmd) != 0:
                    raise Exception("APK 对齐失败")

                self.safe_remove("app-unsigned-unaligned.apk")

                # 5. 签名
                self.append_log("[Step 5] 正在签名 APK...\n")
                value_map = {"大屏": "large", "中屏": "middle", "小屏": "small"}
                key = value_map.get(apk_type, "large")

                # 从 slclient.json 获取实际类型
                json_val = self.get_json_field(PATH_SLCLIENT_JSON, LAUNCHER_MODULE_PATH)
                if json_val and json_val in KEYSTORE_CONFIG:
                    key = json_val
                    self.append_log(f"[Info] 检测到 JSON 配置，使用签名类型：{key}\n")

                ks_info = KEYSTORE_CONFIG.get(key, KEYSTORE_CONFIG["large"])
                ks_path = ks_info["path"]
                ks_pass = ks_info["password"]

                if not os.path.exists(ks_path):
                    raise Exception(f"签名文件不存在：{ks_path}")

                date_str = time.strftime("%Y_%m_%d", time.localtime())
                output_dir_path = PROJECT_PATH / date_str
                output_dir_path.mkdir(exist_ok=True)

                final_name = self.build_newname(PATH_YML) if os.path.exists(PATH_YML) else f"app_{apk_type}_{date_str}.apk"
                output_apk_path = output_dir_path / final_name

                apksigner_cmd = [
                    str(APKSIGNER_BAT), "sign",
                    "--ks", str(ks_path),
                    "--ks-pass", f"pass:{ks_pass}",
                    "--out", str(output_apk_path),
                    "app-unsigned.apk"
                ]

                if self.run_with_live_output(apksigner_cmd) != 0:
                    raise Exception("APK 签名失败")

                self.safe_remove("app-unsigned.apk")

                self.append_log(f"\n[SUCCESS] ✅ 打包完成!\n文件位置：{output_apk_path}\n")
                self.status_label.configure(text="状态：打包成功", text_color="green")
                # 删除app_out文件夹
                shutil.rmtree(output_dir, ignore_errors=True)
                messagebox.showinfo("成功", f"APK 打包成功！\n保存在：{output_apk_path}")

            except Exception as e:
                error_msg = f"[FAIL] ❌ 打包失败：{str(e)}"
                self.append_log(f"\n{error_msg}\n")
                self.status_label.configure(text="状态：打包失败", text_color="red")
                messagebox.showerror("错误", error_msg)
            finally:
                self.build_apk_btn.configure(state="normal", text="打包 APK")

        threading.Thread(target=task, daemon=True).start()

    def copy_files(self,source_dir_color, target_dir_color):
        if not os.path.isfile(source_dir_color):
            raise FileNotFoundError(f"资源文件不存在: {source_dir_color}")

        try:
            shutil.copy2(source_dir_color, target_dir_color)
            self.append_log(f"已覆盖文件：{source_dir_color} -> {target_dir_color}")
        except Exception as e:
            self.append_log(f"覆盖失败：{e}")

    # ==================== 版本管理辅助函数 ====================

    def update_version_name(self, version_name: str) -> str:
        """将版本名中 'POCSTARS_' 后面的数字替换为当前时间戳"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pattern = r"(POCSTARS_)\d+$"
        new_version_name = re.sub(pattern, rf"\1{timestamp}", version_name)

        if new_version_name == version_name:
            self.append_log(f"[Warn] 未匹配到 POCSTARS_ 结尾的数字格式，原始：{version_name}\n")
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
            self.append_log(f"[Error] 加载 YAML 失败：{e}\n")
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
            self.append_log("[Warn] 无法获取版本信息，跳过更新\n")
            return

        new_code = self.increment_version_code(old_code)
        new_name = self.update_version_name(old_name)

        version_info["versionCode"] = new_code
        version_info["versionName"] = new_name

        with open(yml_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f)

        self.append_log(f"[Version] 更新成功：{old_name}->{new_name}, Code: {old_code}->{new_code}\n")

    def build_newname(self, yml_path: Path) -> str:
        try:
            version_info = self.get_field_value_from_yml(yml_path, "versionInfo")
            version_name = version_info.get("versionName") if version_info else "unknown"
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            return f"APP_test_{timestamp}.apk"
        except Exception:
            return f"APP_{datetime.now().strftime('%Y%m%d%H%M%S')}.apk"

    def get_field_value_from_yml(self, yml_path: Path, field_name: str) -> Dict:
        data = self.load_yml(yml_path)
        if data:
            return data.get(field_name, {})
        return {}


if __name__ == "__main__":
    app = App()
    app.mainloop()
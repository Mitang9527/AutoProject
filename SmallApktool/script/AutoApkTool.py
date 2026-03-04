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
from tkinter import messagebox
from ruamel.yaml import YAML
from ruamel.yaml.constructor import ConstructorError

# ==================== 全局配置常量 ====================

# 路径配置
PROJECT_PATH = Path(os.getcwd())
JSON_FILE = "input.json"
TEMP_DIR = "app_out"
APKTOOL_JAR = "apktool.jar"

# 环境配置
ENV_CONF = {
    '国内环境': {'ip_address': 'cndns.shanliptt.com:10200', 'context': 'show'},
    '海外环境': {'ip_address': 'sgdns.shanlipoc.com:10200', 'context': 'pocstar'}
}

# 关键文件路径
PATH_YML = PROJECT_PATH / "app_out" / "apktool.yml"
PATH_SLCLIENT_JSON = PROJECT_PATH / "app_out" / "assets" / "slclient.json"
PATH_INPUT_JSON_SRC = "input.json"
PATH_INPUT_JSON_DST = PROJECT_PATH / "app_out" / "assets" / "slclient" / "input.json"

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
            timeout=3
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
            timeout=3
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
            self.log_callback("[Info] 日志缓冲区已清空。\n")

        try:
            kwargs = {
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "text": True,
                "bufsize": 1,
                "encoding": "utf-8",
                "errors": "ignore"
            }
            if platform.system() == "Windows":
                kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

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


# ==================== 前端 UI 类 ====================

class App(ctk.CTk):
    """主应用程序窗口"""

    def __init__(self):
        super().__init__()
        self.title("App Adaptation_1.0")
        self.geometry("1200x700")

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
        self.apk_select_label = ctk.CTkLabel(self.sidebar_frame, text="APK 类型:", anchor="w")
        self.apk_select_label.grid(row=9, column=0, padx=20, pady=(15, 0))

        self.apk_type_seg = ctk.CTkSegmentedButton(
            self.sidebar_frame,
            values=["大屏", "小屏"],
            command=self.on_apk_type_change,
            height=30,
            fg_color="#3498db",
            selected_color="#27ae60",
            unselected_color="gray"
        )
        self.apk_type_seg.grid(row=10, column=0, padx=20, pady=5, sticky="ew")
        self.apk_type_seg.set("大屏")

        self.build_apk_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="打包 APK",
            fg_color="#d35400",
            hover_color="#e67e22",
            command=self.build_apk
        )
        self.build_apk_btn.grid(row=11, column=0, padx=20, pady=10)

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
        self.tab_build_config = self.tabview.add("打包配置")
        self._init_build_config_page()

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
        if not self.winfo_exists():
            return
        try:
            for widget in self.scroll_frame.winfo_children():
                try:
                    widget.destroy()
                except Exception:
                    pass

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

            if not intents and not stdkeys:
                lbl = ctk.CTkLabel(self.scroll_frame, text="暂无配置数据。", text_color="gray")
                lbl.grid(row=0, column=0, pady=20)
                return

            headers = ["键名", "事件类型", "键值", "Action", "命令"]
            for i, h in enumerate(headers):
                ctk.CTkLabel(
                    self.scroll_frame,
                    text=h,
                    font=ctk.CTkFont(weight="bold"),
                    anchor="w"
                ).grid(row=0, column=i, padx=10, pady=10, sticky="w")

            row_idx = 1
            all_keys = set(stdkeys.keys()) | set(intents.keys())
            actions_data = data.get("action", {})

            for name in all_keys:
                if not self.winfo_exists():
                    return
                sk = stdkeys.get(name, {})
                ac = actions_data.get(name, {})
                info = intents.get(name, {})

                ctk.CTkLabel(self.scroll_frame, text=name, anchor="w").grid(
                    row=row_idx, column=0, padx=10, pady=5, sticky="w"
                )
                ctk.CTkLabel(self.scroll_frame, text=sk.get("event", "N/A"), anchor="w").grid(
                    row=row_idx, column=1, padx=10, pady=5, sticky="w"
                )
                ctk.CTkLabel(self.scroll_frame, text=str(sk.get("key", "N/A")), anchor="w").grid(
                    row=row_idx, column=2, padx=10, pady=5, sticky="w"
                )
                ctk.CTkLabel(
                    self.scroll_frame,
                    text=info.get("action", "-"),
                    anchor="w",
                    text_color="#3498db"
                ).grid(row=row_idx, column=3, padx=10, pady=5, sticky="w")

                cmds = ac.get("default", [])
                cmd_str = ", ".join([c.get("command", {}).get("id", "") for c in cmds]) if cmds else "-"
                ctk.CTkLabel(
                    self.scroll_frame,
                    text=cmd_str,
                    anchor="w",
                    text_color="gray"
                ).grid(row=row_idx, column=4, padx=10, pady=5, sticky="w")
                row_idx += 1
        except Exception:
            pass

    def on_closing(self) -> None:
        if self.backend and self.is_listening:
            self.append_log("\n[Info] 正在停止监听以关闭程序...\n")
            self.backend.stop_capture()
        time.sleep(0.5)
        self.destroy()

    def on_apk_type_change(self, value: str) -> None:
        self.current_apk_type = value
        self.status_label.configure(text=f"状态：已选择 {value} APK", text_color="#d35400")
        self.append_log(f"[Info] APK 类型切换为：{value}\n")

    def _init_build_config_page(self) -> None:
        """初始化打包配置页面"""
        header_lbl = ctk.CTkLabel(self.tab_build_config, text="APK 环境配置", font=ctk.CTkFont(size=16, weight="bold"))
        header_lbl.pack(pady=(20, 10))
        sub_lbl = ctk.CTkLabel(self.tab_build_config, text="以下选项将读取 slclient.json 并决定签名证书及最终配置", text_color="gray")
        sub_lbl.pack(pady=(0, 20))

        form_frame = ctk.CTkFrame(self.tab_build_config)
        form_frame.pack(fill="both", expand=True, padx=40, pady=10)
        form_frame.grid_columnconfigure(1, weight=1)

        # 1. APK 环境类型
        ctk.CTkLabel(form_frame, text="服务器环境:", anchor="w").grid(row=0, column=0, padx=20, pady=15, sticky="w")

        env_options = list(ENV_CONF.keys())
        self.opt_env = ctk.CTkOptionMenu(
            form_frame,
            values=env_options,
            command=self._on_env_selected
        )
        self.opt_env.grid(row=0, column=1, padx=20, pady=15, sticky="ew")
        self.opt_env.set(env_options[0])  # 默认选中第一个

        self._on_env_selected(env_options[0])

        # 2. 地图源
        ctk.CTkLabel(form_frame, text="地图:", anchor="w").grid(row=1, column=0, padx=20, pady=15, sticky="w")
        self.opt_map = ctk.CTkOptionMenu(form_frame, values=["baidu", "google"], command=lambda v: self._update_config("map_source", v))
        self.opt_map.grid(row=1, column=1, padx=20, pady=15, sticky="ew")

        # 3. 编码格式
        ctk.CTkLabel(form_frame, text="编码格式:", anchor="w").grid(row=2, column=0, padx=20, pady=15, sticky="w")
        self.opt_enc = ctk.CTkOptionMenu(form_frame, values=["opus", "evrc8k", "amrnb"], command=lambda v: self._update_config("encoding", v))
        self.opt_enc.grid(row=2, column=1, padx=20, pady=15, sticky="ew")

        # 刷新按钮
        # refresh_btn = ctk.CTkButton(form_frame, text="重新读取 slclient.json", command=self.load_slclient_options)
        # refresh_btn.grid(row=3, column=0, columnspan=2, pady=20)

        # 启动时自动加载一次
        self.after(500, self.load_slclient_options)

    def _on_env_selected(self,selected_name: str):
        """用户选择环境名称时，提取对应的 IP 和 Context"""
        if selected_name in ENV_CONF:
            config = ENV_CONF[selected_name]

            # 将完整的配置对象存入实例变量，供打包时使用
            self.current_env_config = {
                "name": selected_name,
                "ip": config['ip_address'],
                "context": config['context']
            }

            self.append_log(f"[Config] 已选择: {selected_name}\n")
            self.append_log(f"   -> IP: {config['ip_address']}\n")
            self.append_log(f"   -> Context: {config['context']}\n")
        else:
            self.append_log(f"[Error] 未找到环境配置: {selected_name}\n")

    def apply_selected_config_to_slclient(self) -> None:
        if not hasattr(self, 'current_env_config'):
            return

        with open(PATH_SLCLIENT_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)

        cfg = self.current_env_config


        # 1. 写入 IP
        if "network" not in data: data["network"] = {}
        data["network"]["server_ip"] = cfg['ip']  # 例如: cndns.shanliptt.com:10200

        # 2. 写入 Context
        data["network"]["context_path"] = cfg['context']  # 例如: show


        # 写回文件
        with open(PATH_SLCLIENT_JSON, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        self.append_log(f"[OK] 已直接更新配置:\n   IP: {cfg['ip']}\n   Context: {cfg['context']}\n")

    def load_slclient_options(self) -> None:
        """从 slclient.json 读取可用选项并更新 UI"""
        # default_envs = ["large", "middle", "small"]
        # default_maps = ["baidu", "google"]

        # env_options = default_envs
        # map_options = default_maps

        # 尝试解析真实文件
        if PATH_SLCLIENT_JSON.exists():
            try:
                with open(PATH_SLCLIENT_JSON, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 获取当前环境类型 (ui.launcherModule)
                current_env = self.get_json_field(PATH_SLCLIENT_JSON, LAUNCHER_MODULE_PATH)
                if current_env:
                    # 将当前值置顶，并合并默认列表去重
                    env_options = list(dict.fromkeys([current_env] + default_envs))

                # 获取当前地图 (map.provider) - 假设路径，可根据实际 json 结构调整
                current_map = self.get_json_field(PATH_SLCLIENT_JSON, ["map", "provider"])
                if current_map:
                    map_options = list(dict.fromkeys([current_map] + default_maps))

                self.append_log(f"[Config] 已加载 slclient.json 配置选项。\n")

            except Exception as e:
                self.append_log(f"[Warn] 读取 slclient.json 失败: {e}，使用默认选项。\n")
        else:
            self.append_log("[Info] 未找到 slclient.json (可能尚未反编译)，使用默认选项。\n")

        # 更新 UI 下拉框
        self.opt_env.configure(values=env_options)
        self.opt_map.configure(values=map_options)

        # 设置默认选中值
        if env_options:
            self.build_config["env_type"] = env_options[0]
            self.opt_env.set(env_options[0])
            self._update_config("env_type", env_options[0])  # 触发侧边栏更新

        if map_options:
            self.build_config["map_source"] = map_options[0]
            self.opt_map.set(map_options[0])

    def _update_config(self, key: str, value: str) -> None:
        """更新内部配置字典并刷新侧边栏显示"""
        self.build_config[key] = value
        self.append_log(f"[Config] 设置 {key} = {value}\n")

        # 更新侧边栏的状态提示
        if key == "env_type":
            type_map = {"large": "大屏", "middle": "中屏", "small": "小屏"}
            display_name = type_map.get(value, value)
            map_val = self.build_config.get('map_source', '未知')
            self.apk_status_label.configure(text=f"APK 配置:\n类型：{display_name}\n地图：{map_val}")

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

    def decompile_apk(self, apk_path: str, output_dir: str = "app_out") -> bool:
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir, ignore_errors=True)
            self.append_log(f"[Info] 已清理旧目录：{output_dir}\n")

        command = [
            "java", "-jar", str(APKTOOL_JAR),
            "d", apk_path, "-s", "-o", output_dir
        ]
        exit_code = self.run_with_live_output(command)
        return exit_code == 0

    def build_apk(self) -> None:
        """主打包入口"""
        output_dir: str = "app_out"

        apk_type = self.apk_type_seg.get()
        self.current_apk_type = apk_type

        apk_path = "LargeApp.apk" if apk_type == "大屏" else "SmallApp.apk"

        if not os.path.exists(apk_path):
            messagebox.showerror("错误", f"找不到 APK 文件：{apk_path}\n请确保该文件在当前目录下。")
            return

        # 禁用按钮防止重复点击
        self.build_apk_btn.configure(state="disabled", text="打包中...")
        self.status_label.configure(text="状态：正在打包...", text_color="#d35400")

        def task():
            try:
                self.append_log(f"\n=== 开始打包流程 ({apk_type}) ===\n")

                # 1. 反编译
                self.append_log("[Step 1] 正在反编译 APK...\n")
                if not self.decompile_apk(apk_path, TEMP_DIR):
                    raise Exception("反编译失败")

                else:
                    self.append_log("[Step 2] 编译成功\n")

                # 2. 更新版本信息
                # self.append_log("[Step 2] 正在更新版本信息...\n")
                # if os.path.exists(PATH_YML):
                #     self.update_version_info(PATH_YML)
                # else:
                #     self.append_log("[Warn] 未找到 apktool.yml，跳过版本更新\n")

                # 2.替换input.json
                self.copy_files(PATH_INPUT_JSON_SRC,PATH_INPUT_JSON_DST)

                # 3. 构建未签名 APK
                self.append_log("[Step 3] 正在打包 APK...\n")
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
                # shutil.rmtree(output_dir, ignore_errors=True)
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
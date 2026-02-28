import re
import subprocess
import json
import os
import time
import platform
import queue
import threading
import sys
import shutil
from datetime import datetime
from typing import Optional, Set
import customtkinter as ctk
from tkinter import messagebox

# ==================== 配置常量 ====================
JSON_FILE = "input.json"

DEFAULT_CUSTOM_LIST = [
    "join_next_group",
    "switch_group_name_tts",
    "switch_group_click",
    "join_prev_group",
    "new_call_in"
]

SKIP_FEEDBACK_INTERVAL = 5

DEBOUNCE_SECONDS = 1.5

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


# ==================== 环境检测模块 ====================

def check_command(cmd):
    """检查命令是否在系统 PATH 中"""
    return shutil.which(cmd) is not None

def is_adb_installed():
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

def is_java_installed():
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


def show_env_error_dialog(parent, missing_list):
    """显示环境缺失的弹窗"""
    msg = "系统环境检查未通过，缺少以下组件：\n\n"

    if "ADB" in missing_list:
        msg += "❌ ADB (Android Debug Bridge)\n"
        msg += "   用途：与安卓设备通信。\n"
        msg += "   解决：下载 'Platform Tools' 并添加到 PATH 环境变量。\n"

    if "JAVA" in missing_list:
        msg += "❌ Java (JDK/JRE)\n"
        msg += "   用途：运行部分 Java 工具链。\n"
        msg += "   解决：安装 JDK 17+ 并配置 JAVA_HOME。\n"
        msg += "   链接：https://adoptium.net/\n\n"

    msg += "请安装缺失组件后点击【重试检测】。"

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

    btn_retry = ctk.CTkButton(btn_frame, text="重试检测", command=on_retry, fg_color="green")
    btn_retry.pack(side="left", padx=10)

    btn_exit = ctk.CTkButton(btn_frame, text="退出程序", command=on_exit, fg_color="red")
    btn_exit.pack(side="left", padx=10)


class EnvChecker:
    """环境检查器类"""

    def __init__(self, parent_app):
        self.parent = parent_app
        self.check_count = 0

    def check_all(self, show_dialog=True):
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


# ==================== 后端逻辑类 ====================

class SmartKeyBackend:
    def __init__(self, device: str, log_callback: callable, config_callback: callable):
        self.device = device
        self.log_callback = log_callback
        self.config_callback = config_callback
        self.process: Optional[subprocess.Popen] = None
        self.stop_event = threading.Event()
        self.skip_count = 0
        self.is_running = False

        self.data = {}
        self.existing_actions: Set[str] = set()
        self.existing_codes: Set[int] = set()

    def load_config(self):
        if not os.path.exists(JSON_FILE):
            self.data = {
                "stdkey": {},
                "action": {},
                "intent": {},
                "custom": DEFAULT_CUSTOM_LIST.copy()
            }
            self.existing_actions = set()
            self.existing_codes = set()
            return True

        try:
            with open(JSON_FILE, 'r', encoding='utf-8') as f:
                self.data = json.load(f)

            self.existing_actions = {
                info.get("action") for name, info in self.data.get("intent", {}).items()
                if info.get("action")
            }
            self.existing_codes = {
                info.get("key") for name, info in self.data.get("stdkey", {}).items()
                if info.get("key") is not None
            }

            self.data.setdefault("stdkey", {})
            self.data.setdefault("action", {})
            self.data.setdefault("intent", {})
            self.data.setdefault("custom", DEFAULT_CUSTOM_LIST.copy())
            return True

        except Exception as e:
            self.log_callback(f"[Error] 读取配置失败：{e}\n")
            self.data = {
                "stdkey": {},
                "action": {},
                "intent": {},
                "custom": DEFAULT_CUSTOM_LIST.copy()
            }
            self.existing_actions = set()
            self.existing_codes = set()
            return False

    def save_config(self, silent=False):
        try:
            with open(JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            if not silent:
                self.log_callback(f"[OK] 配置已保存到 {JSON_FILE}\n")
            return True
        except Exception as e:
            self.log_callback(f"[Error] 保存失败：{e}\n")
            return False

    def _kill_process(self):
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
                except:
                    self.process.kill()
        except:
            pass
        finally:
            self.process = None

    def _clear_logcat(self):
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

    def _generate_standard_config(self, suffix: str, key_type: str, action_str: str, virtual_key: int, is_many: bool):
        result = {"stdkey": {}, "action": {}, "intent": {}}

        if key_type.lower() == "sos":
            current_sos_key = virtual_key

            # 【改动点 1】推导 up 广播，适配不同命名风格
            if action_str.endswith(".down"):
                up_action_str = action_str[:-5] + ".up"
            elif action_str.endswith("_down"):
                up_action_str = action_str[:-5] + "_up"
            elif "DOWN" in action_str:
                up_action_str = action_str.replace("DOWN", "UP")
            else:
                # 如果是长按广播 (longpress)，通常没有对应的 up，复用当前广播
                up_action_str = action_str

                # 【改动点 2】生成组内 Key 完全一致的 stdkey (sos, down_sos, up_sos)
            result["stdkey"] = {
                "sos": {
                    "key": current_sos_key,
                    "event": "KEY_LONG_PRESS",
                    "time": 3000
                },
                "down_sos": {
                    "key": current_sos_key,
                    "event": "KEY_DOWN"
                },
                "up_sos": {
                    "key": current_sos_key,
                    "event": "KEY_UP"
                }
            }

            # 【改动点 3】写入 TRIGGER_SOS 命令
            # result["action"] = {
            #     "sos": {
            #         "default": [{"command": {"id": "TRIGGER_SOS"}}],
            #         "member": [],
            #         "new_call_in": []
            #     },
            #     "down_sos": {
            #         "default": [{"command": {"id": "TRIGGER_SOS"}}],
            #         "member": [],
            #         "new_call_in": []
            #     },
            #     "up_sos": {
            #         "default": [],
            #         "member": [],
            #         "new_call_in": []
            #     }
            # }

            # 【改动点 4】关键：自动填入捕获到的广播到 intent，并标记 as_key=true (不再留空)
            result["intent"] = {
                "down_sos": {
                    "action": action_str,
                    "as_key": True
                },
                "up_sos": {
                    "action": up_action_str,
                    "as_key": True
                }
            }

        else:
            # === PTT 逻辑 (保持原样，完全不动) ===
            prefix = "ptt" if key_type.lower() == "ptt" else "sos"
            down_name = f"many_{prefix}_down_{suffix}" if is_many else f"{prefix}_down_{suffix}"
            up_name = f"{prefix}_up_{suffix}"

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

            # 保持原有逻辑：is_many 时 cmd_down_list 为空
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

    def _reader_thread(self, key_type: str):
        re_broadcast = re.compile(r"Sending.*broadcast\s+([\w\.]+)\s+from")
        re_keycode = re.compile(r"keyCode=(\d+)")
        last_process_time = 0
        is_many_mode = (key_type.lower() == "ptt")
        mode_name = "防抖模式 (PTT)" if is_many_mode else "标准模式 (SOS)"

        self.log_callback(f"\n--- 启动监听 (自动保存已启用): {key_type.upper()} ({mode_name}) ---\n")

        if self._clear_logcat():
            self.log_callback("[Info] 日志缓冲区已清空。\n")
        else:
            self.log_callback("[Warning] 清除日志失败，继续监听。\n")

        try:
            kwargs = {
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "text": True,
                "bufsize": 1,
                "encoding": 'utf-8',
                "errors": 'ignore'
            }
            if platform.system() == "Windows":
                kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

            cmd = [
                "adb", "-s", self.device, "logcat", "-v", "time",
                "ActivityManager:I", "InputReader:I", "*:S"
            ]

            self.process = subprocess.Popen(cmd, **kwargs)
            self.is_running = True

            while not self.stop_event.is_set():
                if self.process.poll() is not None:
                    break
                line = self.process.stdout.readline()
                if not line:
                    break
                if self.stop_event.is_set():
                    break

                match_b = re_broadcast.search(line)
                if not match_b:
                    continue

                action_str = match_b.group(1)
                current_time = time.time()

                if current_time - last_process_time < DEBOUNCE_SECONDS:
                    continue

                if action_str in self.existing_actions:
                    self.skip_count += 1
                    if self.skip_count % SKIP_FEEDBACK_INTERVAL == 0:
                        self.log_callback(f"[Skip] Action '{action_str}' 已存在 (累计跳过 {self.skip_count} 次)\n")
                    continue

                last_process_time = current_time
                self.skip_count = 0
                match_k = re_keycode.search(line)
                code_info = f" (KeyCode: {match_k.group(1)})" if match_k else ""

                msg = f"\n[NEW] 发现新 Action: {action_str}{code_info}\n[MODE] 类型：{key_type.upper()} -> {mode_name}\n"
                self.log_callback(msg)

                timestamp_suffix = datetime.now().strftime("%Y%m%d%H%M%S")
                new_virtual_code = -1000
                while new_virtual_code in self.existing_codes:
                    new_virtual_code -= 1

                new_entries = self._generate_standard_config(
                    timestamp_suffix, key_type, action_str, new_virtual_code,
                    is_many=is_many_mode
                )

                self.data["stdkey"].update(new_entries["stdkey"])
                self.data["action"].update(new_entries["action"])
                # 只有当 intent 不为空时才更新 (针对 SOS 情况，intent 为空则不覆盖)
                if new_entries["intent"]:
                    self.data["intent"].update(new_entries["intent"])

                # 对于 SOS，虽然不更新 action 字符串，但我们需要记录这个 key 已被使用，防止重复
                # 如果 intent 为空，我们手动将生成的 key 加入 existing_codes (上面已经做了)
                # 如果需要防止相同的 action_str 被重复处理，existing_actions 逻辑依然有效

                self.existing_actions.add(action_str)
                self.existing_codes.add(new_virtual_code)

                # 日志提示
                created_keys = list(new_entries['stdkey'].keys())
                if created_keys:
                    self.log_callback(f"[OK] 已收录键位定义：{', '.join(created_keys)} (Key: {new_virtual_code})\n")
                    if key_type.lower() == "sos":
                        self.log_callback("[Note] SOS 的 Intent Action 未自动填充，请手动在 input.json 中配置。\n")
                else:
                    self.log_callback("[OK] 配置已更新。\n")

                if self.save_config(silent=True):
                    self.log_callback(f"[Auto-Save] ✅ 配置已自动写入 input.json\n")
                    if self.config_callback:
                        self.config_callback()
                else:
                    self.log_callback(f"[Auto-Save] ❌ 自动保存失败！\n")
                self.log_callback("\n")

        except Exception as e:
            if not self.stop_event.is_set():
                self.log_callback(f"\n[Error] 监听线程异常：{e}\n")
        finally:
            self._kill_process()
            self.is_running = False
            self.log_callback("\n[Info] 监听已停止。\n")

    def start_capture(self, key_type: str):
        if self.is_running:
            self.log_callback("[Warning] 监听已在运行中。\n")
            return
        self.stop_event.clear()
        self.skip_count = 0
        self.load_config()
        t = threading.Thread(target=self._reader_thread, args=(key_type,), daemon=True)
        t.start()

    def stop_capture(self):
        self.stop_event.set()
        self._kill_process()


# ==================== 前端 UI 类 ====================

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SmartKey Configurator")
        self.geometry("1200x700")

        self.backend: Optional[SmartKeyBackend] = None
        self.current_device: str = ""
        self.log_queue = queue.Queue()
        self.is_listening = False
        self.env_checker = EnvChecker(self)

        self.bind("<<EnvRetry>>", lambda e: self.on_env_retry())

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # === 侧边栏 ===
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(10, weight=1)

        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="SmartKey\nConfigurator",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

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

        self.mode_label = ctk.CTkLabel(self.sidebar_frame, text="监听模式:", anchor="w")
        self.mode_label.grid(row=4, column=0, padx=20, pady=(5, 0))

        self.mode_var = ctk.StringVar(value="ptt")
        self.mode_menu = ctk.CTkOptionMenu(
            self.sidebar_frame,
            variable=self.mode_var,
            values=["ptt", "sos"]
        )
        self.mode_menu.grid(row=5, column=0, padx=20, pady=5)

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
        self.clear_log_btn.grid(row=9, column=0, padx=20, pady=10)

        self.status_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="状态：初始化...",
            anchor="w",
            text_color="gray"
        )
        self.status_label.grid(row=10, column=0, padx=20, pady=(0, 20), sticky="s")

        # === 主内容区 ===
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        self.tab_log = self.tabview.add("实时日志")
        self.tab_config = self.tabview.add("配置列表")

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

        self.after(100, self.process_log_queue)
        self.after(500, self.initial_env_check)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def initial_env_check(self):
        """启动时的环境检查"""
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

    def on_env_retry(self):
        """当用户点击弹窗的重试按钮时"""
        self.log_textbox.insert("end", "\n[Info] 正在重新检测环境...\n")
        if self.env_checker.check_all(show_dialog=False):
            self.log_textbox.insert("end", "[OK] 环境检测通过！\n")
            self.status_label.configure(text="状态：环境就绪", text_color="green")
            self.start_btn.configure(state="normal")
            self.refresh_devices()
            self.after(100, self.refresh_config_view)
        else:
            self.env_checker.check_all(show_dialog=True)

    def refresh_devices(self):
        if not self.winfo_exists():
            return
        if not is_adb_installed():
            self.env_checker.check_all(show_dialog=True)
            return

        try:
            out = subprocess.check_output(
                ["adb", "devices"],
                text=True,
                stderr=subprocess.DEVNULL
            )
            devs = [
                line.split()[0] for line in out.splitlines()
                if "\tdevice" in line and not line.startswith("List")
            ]
            current_val = self.device_var.get()
            self.device_menu.configure(values=devs if devs else ["未检测到设备"])

            if devs:
                if current_val not in devs and current_val not in ["未连接", "未检测到设备", "检测中...", "等待环境修复"]:
                    self.device_var.set(devs[0])
                    self.current_device = devs[0]
                elif current_val in ["未连接", "未检测到设备", "检测中...", "等待环境修复"]:
                    self.device_var.set(devs[0])
                    self.current_device = devs[0]
                else:
                    self.current_device = current_val
                self.status_label.configure(
                    text=f"状态：已连接\n {self.current_device}",
                    text_color="green"
                )
            else:
                self.device_var.set("未检测到设备")
                self.current_device = ""
                self.status_label.configure(text="状态：无设备", text_color="red")
        except Exception:
            if self.winfo_exists():
                self.device_menu.configure(values=["ADB 错误"])
            self.device_var.set("ADB 错误")

    def on_device_change(self, selection):
        if selection not in ["未检测到设备", "ADB 错误"]:
            self.current_device = selection
        self.status_label.configure(
            text=f"状态：已切换至 {selection}",
            text_color="green"
        )

    def toggle_listen(self):
        if not self.winfo_exists():
            return

        if not is_adb_installed():
            messagebox.showerror("错误", "ADB 环境丢失！请检查配置。")
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
            self.status_label.configure(text="状态：监听中 (自动保存)", text_color="green")
            self.mode_menu.configure(state="disabled")
            self.device_menu.configure(state="disabled")
            self.backend.start_capture(mode)

    def append_log(self, text: str):
        self.log_queue.put(text)

    def process_log_queue(self):
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
                    break
        except Exception:
            pass
        self.after(100, self.process_log_queue)

    def clear_log(self):
        if self.log_textbox.winfo_exists():
            self.log_textbox.delete("0.0", "end")

    def save_config_action(self):
        if not self.winfo_exists():
            return
        if not self.backend:
            messagebox.showinfo("提示", "尚未初始化后端。")
            return
        if self.backend.save_config(silent=False):
            messagebox.showinfo("成功", "配置已手动保存到 input.json")
            self.refresh_config_view()

    def refresh_config_view(self):
        if not self.winfo_exists():
            return
        self.after(0, self._safe_refresh_config_view)

    def _safe_refresh_config_view(self):
        if not self.winfo_exists():
            return
        try:
            for widget in self.scroll_frame.winfo_children():
                try:
                    widget.destroy()
                except Exception:
                    pass

            data = {}
            if self.backend and hasattr(self.backend, 'data'):
                data = self.backend.data
            else:
                if os.path.exists(JSON_FILE):
                    try:
                        with open(JSON_FILE, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                    except:
                        pass

            intents = data.get("intent", {})
            stdkeys = data.get("stdkey", {})
            actions = data.get("action", {})

            if not intents and not stdkeys:
                lbl = ctk.CTkLabel(self.scroll_frame, text="暂无配置数据。", text_color="gray")
                lbl.grid(row=0, column=0, pady=20)
                return

            headers = ["键名 (Key)", "事件类型", "虚拟键值", "Action 广播", "默认命令"]
            for i, h in enumerate(headers):
                lbl = ctk.CTkLabel(
                    self.scroll_frame,
                    text=h,
                    font=ctk.CTkFont(weight="bold"),
                    anchor="w"
                )
                lbl.grid(row=0, column=i, padx=10, pady=10, sticky="w")

            row_idx = 1
            # 遍历 stdkey 来显示所有键位（包括那些还没有 intent 的 SOS 键）
            all_keys = set(stdkeys.keys()) | set(intents.keys())

            for name in all_keys:
                if not self.winfo_exists():
                    return

                sk_info = stdkeys.get(name, {})
                ac_info = actions.get(name, {})
                info = intents.get(name, {})

                event_type = sk_info.get("event", "N/A")
                key_code = sk_info.get("key", "N/A")
                action_val = info.get("action", "未配置")
                as_key = "✅" if info.get("as_key") else "-"

                default_cmds = ac_info.get("default", [])
                cmd_str = ", ".join(
                    [c.get("command", {}).get("id", "Unknown") for c in default_cmds]
                ) if default_cmds else "None"

                try:
                    ctk.CTkLabel(self.scroll_frame, text=name, anchor="w").grid(
                        row=row_idx, column=0, padx=10, pady=5, sticky="w"
                    )
                    ctk.CTkLabel(self.scroll_frame, text=f"{event_type} {as_key}", anchor="w").grid(
                        row=row_idx, column=1, padx=10, pady=5, sticky="w"
                    )
                    ctk.CTkLabel(self.scroll_frame, text=str(key_code), anchor="w").grid(
                        row=row_idx, column=2, padx=10, pady=5, sticky="w"
                    )

                    action_color = "#3498db" if action_val != "未配置" else "gray"
                    ctk.CTkLabel(self.scroll_frame, text=action_val, anchor="w", text_color=action_color).grid(
                        row=row_idx, column=3, padx=10, pady=5, sticky="w"
                    )

                    ctk.CTkLabel(self.scroll_frame, text=cmd_str, anchor="w", text_color="gray").grid(
                        row=row_idx, column=4, padx=10, pady=5, sticky="w"
                    )
                    row_idx += 1
                except Exception:
                    break
        except Exception:
            pass

    def on_closing(self):
        if self.backend and self.is_listening:
            self.log_queue.put("\n[Info] 正在停止监听以关闭程序...\n")
            self.backend.stop_capture()
        time.sleep(0.5)
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
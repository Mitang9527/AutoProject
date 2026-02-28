import re
import subprocess
import json
import os
import time
import platform
import queue
import threading
import sys
from datetime import datetime
from typing import Optional, Dict, Set, List, Any

# 依赖检查
try:
    import customtkinter as ctk
    from tkinter import messagebox
except ImportError:
    print("错误: 未找到 customtkinter 库。请先运行: pip install customtkinter")
    sys.exit(1)

# ==================== 配置常量 ====================
JSON_FILE = "input.json"
DEFAULT_CUSTOM_LIST = [
    "join_next_group", "switch_group_name_tts", "switch_group_click",
    "join_prev_group", "new_call_in"
]
SKIP_FEEDBACK_INTERVAL = 5
DEBOUNCE_SECONDS = 1.5

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


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
            self.data = {"stdkey": {}, "action": {}, "intent": {}, "custom": DEFAULT_CUSTOM_LIST.copy()}
            self.existing_actions = set()
            self.existing_codes = set()
            return True
        try:
            with open(JSON_FILE, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            self.existing_actions = {info.get("action") for name, info in self.data.get("intent", {}).items() if
                                     info.get("action")}
            self.existing_codes = {info.get("key") for name, info in self.data.get("stdkey", {}).items() if
                                   info.get("key") is not None}
            self.data.setdefault("stdkey", {})
            self.data.setdefault("action", {})
            self.data.setdefault("intent", {})
            self.data.setdefault("custom", DEFAULT_CUSTOM_LIST.copy())
            return True
        except Exception as e:
            self.log_callback(f"[Error] 读取配置失败: {e}\n")
            self.data = {"stdkey": {}, "action": {}, "intent": {}, "custom": DEFAULT_CUSTOM_LIST.copy()}
            self.existing_actions = set()
            self.existing_codes = set()
            return False

    def save_config(self, silent=False):
        """
        silent: 如果为 True，不在日志中打印成功信息（用于自动保存防刷屏）
        """
        try:
            with open(JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            if not silent:
                self.log_callback(f"[OK] 配置已保存到 {JSON_FILE}\n")
            return True
        except Exception as e:
            self.log_callback(f"[Error] 保存失败: {e}\n")
            return False

    def _kill_process(self):
        if self.process is None: return
        try:
            if platform.system() == "Windows":
                subprocess.call(["taskkill", "/F", "/T", "/PID", str(self.process.pid)], stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
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
            subprocess.run(["adb", "-s", self.device, "logcat", "-c"], check=True, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=5)
            return True
        except Exception:
            return False

    def _generate_standard_config(self, suffix: str, key_type: str, action_str: str, virtual_key: int, is_many: bool):
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

        stdkey = {down_name: {"event": "KEY_DOWN", "key": virtual_key},
                  up_name: {"event": "KEY_UP", "key": virtual_key}}
        cmd_down_list = [] if is_many else [
            {"command": {"id": "START_SPEAK" if key_type.lower() == "ptt" else "TRIGGER_SOS"}}]
        cmd_up_id = "STOP_SPEAK" if key_type.lower() == "ptt" else "NONE"
        cmd_up_list = [{"command": {"id": cmd_up_id}}] if cmd_up_id != "NONE" else []
        action_data = {down_name: {"default": cmd_down_list, "member": [], "new_call_in": []},
                       up_name: {"default": cmd_up_list, "member": [], "new_call_in": []}}
        intent_data = {down_name: {"action": action_str}, up_name: {"action": up_action_str}}
        if key_type.lower() == "sos":
            intent_data[down_name]["as_key"] = True
            intent_data[up_name]["as_key"] = True
        return {"stdkey": stdkey, "action": action_data, "intent": intent_data}

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
            kwargs = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "text": True, "bufsize": 1,
                      "encoding": 'utf-8', "errors": 'ignore'}
            if platform.system() == "Windows": kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            cmd = ["adb", "-s", self.device, "logcat", "-v", "time", "ActivityManager:I", "InputReader:I", "*:S"]
            self.process = subprocess.Popen(cmd, **kwargs)
            self.is_running = True

            while not self.stop_event.is_set():
                if self.process.poll() is not None: break
                line = self.process.stdout.readline()
                if not line: break
                if self.stop_event.is_set(): break

                match_b = re_broadcast.search(line)
                if not match_b: continue

                action_str = match_b.group(1)
                current_time = time.time()

                if current_time - last_process_time < DEBOUNCE_SECONDS: continue

                if action_str in self.existing_actions:
                    self.skip_count += 1
                    if self.skip_count % SKIP_FEEDBACK_INTERVAL == 0:
                        self.log_callback(f"[Skip] Action '{action_str}' 已存在 (累计跳过 {self.skip_count} 次)\n")
                    continue

                # --- 发现新动作 ---
                last_process_time = current_time
                self.skip_count = 0
                match_k = re_keycode.search(line)
                code_info = f" (KeyCode: {match_k.group(1)})" if match_k else ""

                msg = f"\n[NEW] 发现新 Action: {action_str}{code_info}\n"
                msg += f"[MODE] 类型: {key_type.upper()} -> {mode_name}\n"
                self.log_callback(msg)

                timestamp_suffix = datetime.now().strftime("%Y%m%d%H%M%S")
                new_virtual_code = -1000
                while new_virtual_code in self.existing_codes: new_virtual_code -= 1

                new_entries = self._generate_standard_config(timestamp_suffix, key_type, action_str, new_virtual_code,
                                                             is_many=is_many_mode)

                # 更新内存
                self.data["stdkey"].update(new_entries["stdkey"])
                self.data["action"].update(new_entries["action"])
                self.data["intent"].update(new_entries["intent"])
                self.existing_actions.add(action_str)
                self.existing_codes.add(new_virtual_code)

                self.log_callback(f"[OK] 已收录: {list(new_entries['stdkey'].keys())[0]}\n")

                # 🔥🔥🔥 自动保存逻辑 🔥🔥🔥
                # silent=True 防止日志刷屏，只在出错时提示
                if self.save_config(silent=True):
                    self.log_callback(f"[Auto-Save] ✅ 配置已自动写入 input.json\n")
                    if self.config_callback:
                        self.config_callback()
                else:
                    self.log_callback(f"[Auto-Save] ❌ 自动保存失败！请手动点击保存按钮。\n")

                self.log_callback("\n")

        except Exception as e:
            if not self.stop_event.is_set(): self.log_callback(f"\n[Error] 监听线程异常: {e}\n")
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
        self.title("SmartKey Configurator - 自动保存版")
        self.geometry("1200x700")

        self.backend: Optional[SmartKeyBackend] = None
        self.current_device: str = ""
        self.log_queue = queue.Queue()
        self.is_listening = False
        self.stop_event_set = False

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # === 侧边栏 ===
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(10, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="SmartKey\nConfigurator",
                                       font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.device_label = ctk.CTkLabel(self.sidebar_frame, text="ADB 设备:", anchor="w")
        self.device_label.grid(row=1, column=0, padx=20, pady=(10, 0))

        self.device_var = ctk.StringVar(value="未连接")
        self.device_menu = ctk.CTkOptionMenu(self.sidebar_frame, variable=self.device_var, values=[],
                                             command=self.on_device_change)
        self.device_menu.grid(row=2, column=0, padx=20, pady=5)

        self.refresh_btn = ctk.CTkButton(self.sidebar_frame, text="刷新设备", command=self.refresh_devices, height=30)
        self.refresh_btn.grid(row=3, column=0, padx=20, pady=5)

        self.mode_label = ctk.CTkLabel(self.sidebar_frame, text="监听模式:", anchor="w")
        self.mode_label.grid(row=4, column=0, padx=20, pady=(20, 0))

        self.mode_var = ctk.StringVar(value="ptt")
        self.mode_menu = ctk.CTkOptionMenu(self.sidebar_frame, variable=self.mode_var, values=["ptt", "sos"])
        self.mode_menu.grid(row=5, column=0, padx=20, pady=5)

        self.mode_desc = ctk.CTkLabel(self.sidebar_frame, text="PTT: 防抖模式\nSOS: 标准模式", font=ctk.CTkFont(size=12),
                                      text_color="gray")
        self.mode_desc.grid(row=6, column=0, padx=20, pady=5)

        self.start_btn = ctk.CTkButton(self.sidebar_frame, text="开始监听", fg_color="green", command=self.toggle_listen)
        self.start_btn.grid(row=7, column=0, padx=20, pady=20)

        # 保存按钮依然保留，用于手动强制保存或重新保存
        self.save_btn = ctk.CTkButton(self.sidebar_frame, text="手动保存配置", command=self.save_config_action,
                                      fg_color="#1f6aa5")
        self.save_btn.grid(row=8, column=0, padx=20, pady=10)

        self.clear_log_btn = ctk.CTkButton(self.sidebar_frame, text="清空日志", fg_color="gray", command=self.clear_log)
        self.clear_log_btn.grid(row=9, column=0, padx=20, pady=10)

        self.status_label = ctk.CTkLabel(self.sidebar_frame, text="状态: 空闲 (自动保存开启)", anchor="w", text_color="gray")
        self.status_label.grid(row=10, column=0, padx=20, pady=(0, 20), sticky="s")

        # === 主内容区 ===
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        self.tab_log = self.tabview.add("实时日志")
        self.tab_config = self.tabview.add("配置列表")

        self.log_textbox = ctk.CTkTextbox(self.tab_log, font=ctk.CTkFont(family="Consolas", size=12))
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=10)

        self.scroll_frame = ctk.CTkScrollableFrame(self.tab_config, label_text="当前已收录的键位映射 (input.json)")
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        self.after(100, self.process_log_queue)
        self.refresh_devices()
        self.after(100, self.refresh_config_view)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def refresh_devices(self):
        if not self.winfo_exists(): return
        try:
            out = subprocess.check_output(["adb", "devices"], text=True, stderr=subprocess.DEVNULL)
            devs = [line.split()[0] for line in out.splitlines() if "\tdevice" in line and not line.startswith("List")]
            current_val = self.device_var.get()
            self.device_menu.configure(values=devs if devs else ["未检测到设备"])
            if devs:
                if current_val not in devs and current_val not in ["未连接", "未检测到设备"]:
                    self.device_var.set(devs[0]);
                    self.current_device = devs[0]
                elif current_val in ["未连接", "未检测到设备"]:
                    self.device_var.set(devs[0]);
                    self.current_device = devs[0]
                else:
                    self.current_device = current_val
                self.status_label.configure(text=f"状态: 已连接 {self.current_device} (自动保存)", text_color="green")
            else:
                self.device_var.set("未检测到设备");
                self.current_device = ""
                self.status_label.configure(text="状态: 无设备", text_color="red")
        except Exception:
            if self.winfo_exists(): self.device_menu.configure(values=["ADB 错误"]); self.device_var.set("ADB 错误")

    def on_device_change(self, selection):
        if selection not in ["未检测到设备", "ADB 错误"]: self.current_device = selection; self.status_label.configure(
            text=f"状态: 已切换至 {selection}", text_color="green")

    def toggle_listen(self):
        if not self.winfo_exists(): return
        if not self.current_device or self.current_device in ["未检测到设备", "ADB 错误", "未连接"]:
            messagebox.showerror("错误", "请先选择有效的 ADB 设备！");
            self.refresh_devices();
            return

        if self.is_listening:
            if self.backend: self.backend.stop_capture()
            self.is_listening = False
            self.start_btn.configure(text="开始监听", fg_color="green")
            self.status_label.configure(text="状态: 已停止", text_color="orange")
            self.mode_menu.configure(state="normal");
            self.device_menu.configure(state="normal")
        else:
            mode = self.mode_var.get()
            self.backend = SmartKeyBackend(self.current_device, log_callback=self.append_log,
                                           config_callback=self.refresh_config_view)
            if not self.backend.load_config():
                if not messagebox.askyesno("警告", "读取配置失败，是否使用空配置继续？"): return
            self.is_listening = True
            self.start_btn.configure(text="停止监听", fg_color="red")
            self.status_label.configure(text=f"状态: 监听中 (自动保存)", text_color="green")
            self.mode_menu.configure(state="disabled");
            self.device_menu.configure(state="disabled")
            self.backend.start_capture(mode)

    def append_log(self, text: str):
        self.log_queue.put(text)

    def process_log_queue(self):
        if not self.winfo_exists(): return
        try:
            while True:
                try:
                    text = self.log_queue.get_nowait()
                    if self.log_textbox.winfo_exists(): self.log_textbox.insert("end", text); self.log_textbox.see(
                        "end")
                except queue.Empty:
                    break
                except Exception:
                    break
        except Exception:
            pass
        self.after(100, self.process_log_queue)

    def clear_log(self):
        if self.log_textbox.winfo_exists(): self.log_textbox.delete("0.0", "end")

    def save_config_action(self):
        if not self.winfo_exists(): return
        if not self.backend:
            messagebox.showinfo("提示", "尚未初始化后端。");
            return
        if self.backend.save_config(silent=False): messagebox.showinfo("成功",
                                                                       "配置已手动保存到 input.json"); self.refresh_config_view()

    def refresh_config_view(self):
        if not self.winfo_exists(): return
        self.after(0, self._safe_refresh_config_view)

    def _safe_refresh_config_view(self):
        if not self.winfo_exists(): return
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
            intents = data.get("intent", {});
            stdkeys = data.get("stdkey", {});
            actions = data.get("action", {})
            if not intents:
                lbl = ctk.CTkLabel(self.scroll_frame, text="暂无配置数据。", text_color="gray");
                lbl.grid(row=0, column=0, pady=20);
                return
            headers = ["键名 (Key)", "事件类型", "虚拟键值", "Action 广播", "默认命令"]
            for i, h in enumerate(headers):
                lbl = ctk.CTkLabel(self.scroll_frame, text=h, font=ctk.CTkFont(weight="bold"), anchor="w");
                lbl.grid(row=0, column=i, padx=10, pady=10, sticky="w")
            row_idx = 1
            for name, info in intents.items():
                if not self.winfo_exists(): return
                action_val = info.get("action", "N/A");
                as_key = "✅" if info.get("as_key") else "-"
                sk_info = stdkeys.get(name, {});
                event_type = sk_info.get("event", "N/A");
                key_code = sk_info.get("key", "N/A")
                ac_info = actions.get(name, {});
                default_cmds = ac_info.get("default", [])
                cmd_str = ", ".join(
                    [c.get("command", {}).get("id", "Unknown") for c in default_cmds]) if default_cmds else "None"
                try:
                    ctk.CTkLabel(self.scroll_frame, text=name, anchor="w").grid(row=row_idx, column=0, padx=10, pady=5,
                                                                                sticky="w")
                    ctk.CTkLabel(self.scroll_frame, text=f"{event_type} {as_key}", anchor="w").grid(row=row_idx,
                                                                                                    column=1, padx=10,
                                                                                                    pady=5, sticky="w")
                    ctk.CTkLabel(self.scroll_frame, text=str(key_code), anchor="w").grid(row=row_idx, column=2, padx=10,
                                                                                         pady=5, sticky="w")
                    ctk.CTkLabel(self.scroll_frame, text=action_val, anchor="w", text_color="#3498db").grid(row=row_idx,
                                                                                                            column=3,
                                                                                                            padx=10,
                                                                                                            pady=5,
                                                                                                            sticky="w")
                    ctk.CTkLabel(self.scroll_frame, text=cmd_str, anchor="w", text_color="gray").grid(row=row_idx,
                                                                                                      column=4, padx=10,
                                                                                                      pady=5,
                                                                                                      sticky="w")
                    row_idx += 1
                except Exception:
                    break
        except Exception:
            pass

    def on_closing(self):
        self.stop_event_set = True
        if self.backend and self.is_listening:
            self.log_queue.put("\n[Info] 正在停止监听以关闭程序...\n")
            self.backend.stop_capture()
        time.sleep(0.5)
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
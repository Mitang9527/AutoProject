import os
import re
import subprocess
import time
import json
import threading
import platform
from datetime import datetime
from typing import Optional, Set, List, Any, Dict
from .constants import (
    PATH_INPUT_JSON_SRC,
    PATH_INPUT_JSON_DEFAULT,
    DEFAULT_CUSTOM_LIST,
    DEBOUNCE_SECONDS,
    SKIP_FEEDBACK_INTERVAL,
)


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
        """加载本地 input.json 配置，如果工作目录没有，则尝试从内置资源加载"""
        target_path = PATH_INPUT_JSON_SRC
        if not os.path.exists(target_path):
            if os.path.exists(PATH_INPUT_JSON_DEFAULT):
                target_path = PATH_INPUT_JSON_DEFAULT
            else:
                self.data = {
                    "stdkey": {},
                    "action": {},
                    "intent": {},
                    "custom": DEFAULT_CUSTOM_LIST.copy(),
                }
                self.existing_actions = set()
                self.existing_codes = set()
                return True

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)

            self.existing_actions = {
                info.get("action")
                for name, info in self.data.get("intent", {}).items()
                if info.get("action")
            }
            self.existing_codes = {
                info.get("key")
                for name, info in self.data.get("stdkey", {}).items()
                if info.get("key") is not None
            }

            self.data.setdefault("stdkey", {})
            self.data.setdefault("action", {})
            self.data.setdefault("intent", {})
            self.data.setdefault("custom", DEFAULT_CUSTOM_LIST.copy())
            return True

        except Exception as e:
            self.log_callback(f"[Error] Failed to read configuration: {e}\n")
            self.data = {
                "stdkey": {},
                "action": {},
                "intent": {},
                "custom": DEFAULT_CUSTOM_LIST.copy(),
            }
            self.existing_actions = set()
            self.existing_codes = set()
            return False

    def save_config(self, silent: bool = False) -> bool:
        """保存配置到 input.json"""
        try:
            with open(PATH_INPUT_JSON_SRC, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            if not silent:
                self.log_callback(
                    f"[OK] Configuration saved to {PATH_INPUT_JSON_SRC}\n"
                )
            return True
        except Exception as e:
            self.log_callback(f"[Error] Save failed: {e}\n")
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
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW
                        if platform.system() == "Windows"
                        else 0
                    ),
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
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
                ),
            )
            return True
        except Exception:
            return False

    def _generate_standard_config(
        self,
        suffix: str,
        key_type: str,
        action_str: str,
        virtual_key: int,
        is_many: bool,
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
            down_name = (
                f"many_{prefix}_down_{suffix}" if is_many else f"{prefix}_down_{suffix}"
            )
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
                up_name: {"event": "KEY_UP", "key": virtual_key},
            }

            cmd_down_list = (
                []
                if is_many
                else [
                    {
                        "command": {
                            "id": (
                                "START_SPEAK"
                                if key_type.lower() == "ptt"
                                else "TRIGGER_SOS"
                            )
                        }
                    }
                ]
            )
            cmd_up_id = "STOP_SPEAK" if key_type.lower() == "ptt" else "NONE"
            cmd_up_list = (
                [{"command": {"id": cmd_up_id}}] if cmd_up_id != "NONE" else []
            )

            action_data = {
                down_name: {"default": cmd_down_list, "member": [], "new_call_in": []},
                up_name: {"default": cmd_up_list, "member": [], "new_call_in": []},
            }

            intent_data = {
                down_name: {"action": action_str},
                up_name: {"action": up_action_str},
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
        is_many_mode = key_type.lower() == "ptt"
        mode_name = "PTT" if is_many_mode else "SOS"

        self.log_callback(f"\n--- Start monitoring (mode：{mode_name}) ---\n")
        if self._clear_logcat():
            self.log_callback(
                "[Info] Log buffer cleared。\n"
                "\n[tip]  If no log is output after pressing the button,\n"
                " please enter the known key value in the terminal configuration!!!\n"
            )

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
                kwargs["creationflags"] = (
                    subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
                )

            cmd = [
                "adb",
                "-s",
                self.device,
                "logcat",
                "-v",
                "time",
                "*:S",
                "ActivityManager:I",
            ]
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
                        self.log_callback(
                            f"[Skip] Action '{action_str}' already exists.\n"
                        )
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
                    timestamp_suffix,
                    key_type,
                    action_str,
                    new_virtual_code,
                    is_many=is_many_mode,
                )

                self.data["stdkey"].update(new_entries["stdkey"])
                self.data["action"].update(new_entries["action"])
                if new_entries["intent"]:
                    self.data["intent"].update(new_entries["intent"])

                self.existing_actions.add(action_str)
                self.existing_codes.add(new_virtual_code)

                created_keys = list(new_entries["stdkey"].keys())
                self.log_callback(
                    f"[OK] {', '.join(created_keys)} (Key: {new_virtual_code})\n"
                )

                if self.save_config(silent=True):
                    self.log_callback("[Auto-Save] ✅ Success.\n")
                    if self.config_callback:
                        self.config_callback()
                self.log_callback("\n")

        except Exception as e:
            if not self.stop_event.is_set():
                self.log_callback(f"\n[Error] {e}\n")
        finally:
            self._kill_process()
            self.is_running = False
            self.log_callback("\n[Info] Monitoring has stopped.\n")

    def start_capture(self, key_type: str) -> None:
        """启动监听线程"""
        if self.is_running:
            self.log_callback("[Warning] Monitoring is already running.\n")
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

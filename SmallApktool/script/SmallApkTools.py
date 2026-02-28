import re
import subprocess
import json
import os
import time
import sys
import platform
import shutil
from datetime import datetime
from threading import Thread, Event

# ==================== 配置常量 ====================
JSON_FILE = "input.json"
DEFAULT_CUSTOM_LIST = [
    "join_next_group", "switch_group_name_tts", "switch_group_click",
    "join_prev_group", "new_call_in"
]
SKIP_FEEDBACK_INTERVAL = 5
DEBOUNCE_SECONDS = 1.5


# ==================== 环境检测模块 ====================

def check_command_exists(cmd):
    """检查命令是否在环境变量中"""
    return shutil.which(cmd) is not None


def is_adb_installed():
    """检测 ADB 是否安装且可用"""
    if not check_command_exists("adb"):
        return False
    try:
        # 尝试运行 adb version，超时设为 3 秒
        result = subprocess.run(["adb", "version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3)
        return result.returncode == 0
    except Exception:
        return False


def is_java_installed():
    """检测 Java (JDK/JRE) 是否安装且可用"""
    # 检查 java 命令
    if not check_command_exists("java"):
        return False
    # 可选：检查 javac (编译器)，如果你后续需要编译 Java 代码，取消下面注释
    # if not check_command_exists("javac"):
    #     return False

    try:
        result = subprocess.run(["java", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3)
        return result.returncode == 0
    except Exception:
        return False


def prompt_missing_env(missing_list):
    """提示用户缺失的环境并提供指导"""
    print("\n" + "=" * 60)
    print("[错误] 系统环境检查未通过")
    print("=" * 60)

    if "ADB" in missing_list:
        print("❌ 未检测到 ADB (Android Debug Bridge)")
        print("   解决方法:")
        print("   1. 下载 Android SDK Platform Tools:")
        print("      https://developer.android.com/studio/releases/platform-tools")
        print("   2. 解压并将文件夹路径添加到系统 PATH 环境变量。")
        print("   3. 重启终端验证：输入 'adb version' 应显示版本号。")
        print("")

    if "JAVA" in missing_list:
        print("❌ 未检测到 Java (JDK/JRE)")
        print("   解决方法:")
        print("   1. 下载并安装 JDK 17 或更高版本:")
        print("      https://adoptium.net/ 或 https://www.oracle.com/java/technologies/downloads/")
        print("   2. 安装后确保 JAVA_HOME 已配置，且 'java' 命令可用。")
        print("   3. 重启终端验证：输入 'java -version' 应显示版本号。")
        print("")

    print("=" * 60)
    choice = input("安装完成后，按 [回车] 重试检测，或输入 'q' 退出: ").strip().lower()
    if choice == 'q':
        print("程序已退出。")
        sys.exit(0)
    return True


def ensure_environment():
    """主入口：确保所有环境就绪"""
    while True:
        missing = []
        if not is_adb_installed():
            missing.append("ADB")
        if not is_java_installed():
            missing.append("JAVA")

        if not missing:
            print("[OK] 环境检查通过：ADB 和 Java 均已就绪。")
            return True

        prompt_missing_env(missing)
        # 循环继续，重新检测


# ==================== 工具类 (SmallApkTools) ====================

class SmallApkTools:
    def __init__(self, device):
        self.device = device
        self.process = None
        self.stop_event = Event()
        self.skip_count = 0

    def load_existing_config(self):
        if not os.path.exists(JSON_FILE):
            return {"stdkey": {}, "action": {}, "intent": {}, "custom": DEFAULT_CUSTOM_LIST.copy()}, set(), set()
        try:
            with open(JSON_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            existing_actions = {info.get("action") for name, info in data.get("intent", {}).items() if
                                info.get("action")}
            existing_codes = {info.get("key") for name, info in data.get("stdkey", {}).items() if
                              info.get("key") is not None}
            data.setdefault("stdkey", {})
            data.setdefault("action", {})
            data.setdefault("intent", {})
            data.setdefault("custom", DEFAULT_CUSTOM_LIST.copy())
            return data, existing_actions, existing_codes
        except Exception as e:
            print(f"\n[Error] 读取配置失败: {e}")
            return {"stdkey": {}, "action": {}, "intent": {}, "custom": DEFAULT_CUSTOM_LIST.copy()}, set(), set()

    def save_incremental_config(self, data, new_entries, suffix, action_name, mode_str):
        try:
            data["stdkey"].update(new_entries["stdkey"])
            data["action"].update(new_entries["action"])
            data["intent"].update(new_entries["intent"])
            with open(JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.skip_count = 0
            print(f"\n[OK] [{mode_str}] 已自动保存：{suffix}")
            print(f"     绑定 Action: {action_name}")
            print(f"     新增键名: {', '.join(list(new_entries['stdkey'].keys()))}")
            if "防抖" in mode_str:
                print(f"     注意：default 命令已置空，交由 App 层过滤重复广播。")
            else:
                print(f"     注意：已配置标准命令，立即触发业务逻辑。")
            print("")
            return True
        except Exception as e:
            print(f"\n[Error] 保存失败: {e}")
            return False

    def _kill_process(self):
        if self.process is None:
            return
        try:
            if platform.system() == "Windows":
                subprocess.call(["taskkill", "/F", "/T", "/PID", str(self.process.pid)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
        except subprocess.TimeoutExpired:
            print("[Warning] 清除日志超时。")
            return False
        except Exception as e:
            print(f"[Warning] 清除日志失败: {e}")
            return False

    def _reader_thread(self, key_type, data, existing_actions, existing_codes):
        re_broadcast = re.compile(r"Sending.*broadcast\s+([\w\.]+)\s+from")
        re_keycode = re.compile(r"keyCode=(\d+)")
        last_process_time = 0

        is_many_mode = (key_type.lower() == "ptt")
        mode_name = "防抖模式 (many)" if is_many_mode else "正常模式"

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

            cmd = ["adb", "-s", self.device, "logcat", "-v", "time", "ActivityManager:I", "InputReader:I", "*:S"]
            self.process = subprocess.Popen(cmd, **kwargs)

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

                if action_str in existing_actions:
                    self.skip_count += 1
                    if self.skip_count % SKIP_FEEDBACK_INTERVAL == 0:
                        print(f"\n[Skip] Action '{action_str}' 已收录 (累计跳过 {self.skip_count} 次)，继续监听...")
                    continue

                # --- 发现新动作 ---
                last_process_time = current_time
                self.skip_count = 0

                match_k = re_keycode.search(line)
                code_info = f" (KeyCode: {match_k.group(1)})" if match_k else ""

                print(f"\n[New] 发现新 Action: {action_str}{code_info}")
                print(f"[Auto] 检测到类型: {key_type.upper()} -> 启用【{mode_name}】")

                timestamp_suffix = datetime.now().strftime("%Y%m%d%H%M%S")
                print(f"[Auto] 生成后缀：{timestamp_suffix} | 正在保存...")

                new_virtual_code = -1000
                while new_virtual_code in existing_codes:
                    new_virtual_code -= 1

                new_entries = self._generate_standard_config(
                    timestamp_suffix, key_type, action_str, new_virtual_code, is_many=is_many_mode
                )

                mode_str = "防抖模式" if is_many_mode else "标准模式"
                if self.save_incremental_config(data, new_entries, timestamp_suffix, action_str, mode_str):
                    existing_actions.add(action_str)
                    existing_codes.add(new_virtual_code)

        except Exception as e:
            if not self.stop_event.is_set():
                print(f"\n[Error] 读取线程异常: {e}")
        finally:
            self._kill_process()

    def start_logcat_capture(self, key_type):
        is_many_mode = (key_type.lower() == "ptt")
        mode_desc = "PTT 启用防抖 (many)" if is_many_mode else "SOS 启用标准模式"

        print(f"\n--- 启动全自动采集模式：{key_type.upper()} ({mode_desc}) ---")

        print("[Info] 正在清除设备旧日志 (adb logcat -c)...")
        if self._clear_logcat():
            print("[OK] 日志缓冲区已清空，准备监听新事件。")
        else:
            print("[Warning] 清除日志失败或超时，将继续监听。")

        print("[Info] 正在加载现有配置...")
        data, existing_actions, existing_codes = self.load_existing_config()
        print(f"[Info] 当前已收录 {len(existing_actions)} 个唯一的 Action。")

        if is_many_mode:
            print(f"[Tip] PTT DOWN 将配置为 many_ptt_down_xxx (default 置空)。")
        else:
            print(f"[Tip] SOS DOWN 将配置为 sos_down_xxx (default 含 TRIGGER_SOS)。")
        print(f"[Tip] 按 Ctrl+C 停止监听并返回菜单。\n")

        self.stop_event.clear()
        self.skip_count = 0

        t = Thread(target=self._reader_thread, args=(key_type, data, existing_actions, existing_codes), daemon=True)
        t.start()

        try:
            while t.is_alive():
                t.join(timeout=1.0)
        except KeyboardInterrupt:
            print("\n\n[!] 接收到 Ctrl+C 信号，正在停止...")
        finally:
            self.stop_event.set()
            t.join(timeout=2.0)
            self._kill_process()
            if self.skip_count > 0:
                print(f"[Summary] 本次会话共跳过 {self.skip_count} 次已存在的 Action。")
            print("[Info] 已安全退出到菜单。")

    def _generate_standard_config(self, suffix, key_type, action_str, virtual_key, is_many=False):
        prefix = "ptt" if key_type.lower() == "ptt" else "sos"
        if is_many:
            down_name = f"many_{prefix}_down_{suffix}"
        else:
            down_name = f"{prefix}_down_{suffix}"
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

        if is_many:
            cmd_down_list = []
        else:
            cmd_id = "START_SPEAK" if key_type.lower() == "ptt" else "TRIGGER_SOS"
            cmd_down_list = [{"command": {"id": cmd_id}}]

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

        return {"stdkey": stdkey, "action": action_data, "intent": intent_data}


# ==================== 辅助函数 ====================

def get_devices():
    try:
        out = subprocess.check_output(["adb", "devices"], text=True, stderr=subprocess.DEVNULL)
        return [line.split()[0] for line in out.splitlines() if "\tdevice" in line and not line.startswith("List")]
    except Exception:
        return []


def choose_device():
    while True:
        devs = get_devices()
        if not devs:
            print("\n[Warning] 当前未检测到任何 ADB 设备。")
            print("请检查 USB 连接或开发者选项。")
            print("操作: [回车] 刷新设备列表, 'q' 退出")
            if input().strip().lower() == 'q':
                return None
            continue

        if len(devs) == 1:
            return devs[0]

        print("\n检测到多个设备，请选择:")
        for i, d in enumerate(devs):
            print(f"  [{i}] {d}")
        try:
            idx = int(input("输入序号: "))
            if 0 <= idx < len(devs):
                return devs[idx]
            else:
                print("无效序号，请重试。")
        except ValueError:
            print("输入无效，请输入数字序号。")


# ==================== 主流程 ====================

def run(device):
    # 实例化工具
    tool = SmallApkTools(device)
    print(f"\n[OK] 已连接设备：{device}\n")

    while True:
        # 每次循环前可以快速检查一下 ADB 是否还活着（可选）
        if not is_adb_installed():
            print("\n[Error] ADB 环境丢失！请检查是否被卸载或环境变量变更。")
            if not ensure_environment():
                break

        print("--- 云适配采集工具 ---")
        print(f"当前设备: {device}")
        print("1. 刷新设备列表")
        print("2. 采集 PTT (对讲键)")
        print("3. 采集 SOS (紧急键)")
        print("q. 退出程序")

        choice = input("请选择操作: ").strip().lower()

        if choice == '1':
            devs = get_devices()
            print(f"\n当前在线设备: {devs if devs else '无'}")
            if devs and device not in devs:
                new_dev = choose_device()
                if new_dev:
                    device = new_dev
                    tool = SmallApkTools(device)
                    print(f"[OK] 已切换至设备: {device}")
        elif choice == '2':
            tool.start_logcat_capture("ptt")
        elif choice == '3':
            tool.start_logcat_capture("sos")
        elif choice == 'q':
            print("再见！")
            break
        else:
            print("无效选项，请重新输入。")


if __name__ == "__main__":
    print("正在初始化环境检查...")
    # 1. 确保环境就绪 (ADB + Java)
    if not ensure_environment():
        sys.exit(1)

    # 2. 选择设备
    dev = choose_device()

    # 3. 运行主程序
    if dev:
        try:
            run(dev)
        except KeyboardInterrupt:
            print("\n程序被用户中断。")
    else:
        print("未选择设备，程序退出。")
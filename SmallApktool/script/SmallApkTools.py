import os
import re
import subprocess
import json
from graphlib import TopologicalSorter


class SmallApkTools:
    def __init__(self, device):
        self.device = device
        self.stdkey = {}
        self.action = {}
        self.intent = {}

    def start_logcat_capture(self, key_name, key_value=None):
        """
        动态捕获用户按键的 down/up 事件，只匹配 intent action 格式:
        android.intent.action.<KEY>.down / android.intent.action.<KEY>.up
        """
        print(f"\n请按下 {key_name.upper()} 键...")
        captured_down = captured_up = False
        detected_action_down = detected_action_up = None

        # 避免多余日志干扰
        subprocess.run(["adb", "-s", device, "logcat", "-c"], check=True, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)

        cmd = ["adb", "-s", self.device, "logcat"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="ignore")

        regex = re.compile(rf"android\.intent\.action\.{key_name}\.(down|up)", re.IGNORECASE)

        try:
            for line in proc.stdout:
                line_strip = line.strip()
                match = regex.search(line_strip)
                if match:
                    event = match.group(1).lower()

                    if event == "down" and not captured_down:
                        detected_action_down = f"android.intent.action.{key_name.upper()}.down"
                        captured_down = True
                        print(f"{key_name.upper()} DOWN 捕获成功: {detected_action_down}")

                    elif event == "up" and not captured_up:
                        detected_action_up = f"android.intent.action.{key_name.upper()}.up"
                        captured_up = True
                        print(f"{key_name.upper()} UP 捕获成功: {detected_action_up}")

                if captured_down and captured_up:
                    break
        finally:
            proc.terminate()

        if not (captured_down and captured_up):
            retry = input(f"{key_name.upper()} 未完全捕获，是否重试? (y/n): ").strip().lower()
            if retry == "y":
                return self.start_logcat_capture(key_name, key_value)
            else:
                print(f"{key_name.upper()} 采集取消")
                return None

        # 捕获成功，添加到内部 JSON 结构
        key_val = key_value or -1
        self._add_event(f"{key_name}_down", "KEY_DOWN", key_val, detected_action_down)
        self._add_event(f"{key_name}_up", "KEY_UP", key_val, detected_action_up)
        return True

    # TODO待完善ipnut.json的输入
    def _add_event(self, key_name, event_type, key_value, intent_action, as_key=False):
        # stdkey
        if key_name not in self.stdkey:
            self.stdkey[key_name] = {"event": event_type, "key": key_value}

        # TODO需要补充sos的事件
        # action
        if key_name not in self.action:
            cmd_id = "START_SPEAK" if "DOWN" in event_type else "STOP_SPEAK"
            self.action[key_name] = {"default": [{"command": {"id": cmd_id}}]}

        # intent
        if key_name not in self.intent:
            self.intent[key_name] = {"action": intent_action}
            if as_key:
                self.intent[key_name]["as_key"] = True

    def save_input_json(self, filename="input.json"):
        data = {
            "stdkey": self.stdkey,
            "custom": [],
            "action": self.action,
            "intent": self.intent
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n{filename} 已生成")


# ==================== 辅助函数 ====================

def get_devices():
    out = subprocess.getoutput("adb devices")
    devices = []
    for line in out.splitlines():
        if "\tdevice" in line:
            devices.append(line.split()[0])
    return devices


def choose_device():
    while True:
        devices = get_devices()
        if not devices:
            print("当前没有设备连接!\n按回车刷新\n输入q退出")
            cmd = input().strip().lower()
            if cmd == "q":
                return None
            continue
        if len(devices) == 1:
            return devices[0]
        for i, d in enumerate(devices):
            print(f"{i}: {d}")
        try:
            idx = int(input("请选择设备序号："))
            return devices[idx]
        except:
            print("请输入正确序号")


# ==================== 主流程 ====================

def run(device):
    print(f"\n当前选中设备: {device}\n")
    tool = SmallApkTools(device)

    while True:
        print("\n请选择操作：")
        print("1: 刷新设备状态")
        print("2: 开始日志采集")
        print("q: 退出")
        choice = input("输入你的选择: ").strip().lower()

        if choice == "1":
            devices = get_devices()
            print(f"当前连接设备: {devices if devices else '无设备'}")

        elif choice == "2":
            for key_name, default_key_value in [("ptt", -1), ("sos", -2)]:
                print(f"\n请按下 {key_name.upper()} 键进行采集...")
                success = tool.start_logcat_capture(key_name, default_key_value)
                if not success:
                    print(f"{key_name.upper()} 采集未完成，已跳过")

            tool.save_input_json()

        elif choice == "q":
            break
        else:
            print("请输入有效选项")


if __name__ == "__main__":
    device = choose_device()
    if device:
        run(device)

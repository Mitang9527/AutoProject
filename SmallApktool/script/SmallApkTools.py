import os
import re
import subprocess
import json
import time
from graphlib import TopologicalSorter


class SmallApkTools:
    def __init__(self, device):
        self.device = device
        self.stdkey = {}
        self.action = {}
        self.intent = {}

    # TODO 需要将按键剥离出来逐个获取！
    def start_logcat_capture(self, key_name, key_value=None):
        """
        动态捕获用户按键的 down/up 事件，只匹配 intent action 格式:
        android.intent.action.<KEY>.down / android.intent.action.<KEY>.up
        """
        print(f"\n请按下 {key_name.upper()} 键...")
        captured_down = captured_up = False
        detected_action_down = detected_action_up = None

        while not (captured_down and captured_up):
            broadcast_events = self.get_broadcast()

            if broadcast_events is None:
                return []

            for broadcast_event in broadcast_events:
                print(f"捕获到广播事件: {broadcast_event}")

                if key_name.lower() in broadcast_event or "down" in broadcast_event:
                    if not captured_down:
                        captured_down = True
                        detected_action_down = broadcast_event
                        print(f"{key_name.upper()} DOWN 捕获成功: {detected_action_down}")


                elif key_name.lower() in broadcast_event or "up" in broadcast_event:
                    if not captured_up:
                        captured_up = True
                        detected_action_up = broadcast_event
                        print(f"{key_name.upper()} UP 捕获成功: {detected_action_up}")

        # 捕获成功，添加到内部 JSON 结构
        # TODO 重新编写逻辑，需要根据选择写入
        key_val = key_value or -1
        self._add_event(f"{key_name}_down", "KEY_DOWN", key_val, detected_action_down)
        self._add_event(f"{key_name}_up", "KEY_UP", key_val, detected_action_up)
        return True

    # TODO待完善ipnut.json的输入
    def _add_event(self, key_name, event_type, key_value, intent_action, as_key=False):
        # stdkey
        if key_name not in self.stdkey:
            self.stdkey[key_name] = {"event": event_type, "key": key_value}

        # TODO需要补充不需要sos的逻辑处理
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

    # TODO 需要优化主动关掉进程的方法
    def get_broadcast(self, timeout=5):
        """
        获取并返回匹配的广播事件
        """
        try:
            subprocess.run(["adb", "-s", device, "logcat", "-c"], check=True, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)

            cmd = ['adb', 'logcat', '-v', 'time', '*:D', '|', 'grep', 'Broadcast']
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8', errors='ignore')

            broadcast_regex = re.compile(r'(?<=broadcast\s)(.*?)(?=\sfrom\s)')
            broadcasts = set()

            start_time = time.time()
            max_iterations = 10000
            iterations = 0

            while True:
                if time.time() - start_time > timeout:
                    process.terminate()
                    break

                # 读取每一行日志
                line = process.stdout.readline()
                if line == '' and process.poll() is not None:
                    break
                if line:
                    match = broadcast_regex.search(line)
                    if match:
                        broadcast_event = match.group(0)
                        print(f"Found broadcast: {broadcast_event}")
                        broadcasts.add(broadcast_event)

                iterations += 1
                if iterations >= max_iterations:
                    break

            return list(broadcasts) if broadcasts else None

        except Exception as e:
            print(f"发生错误: {e}")
            return None

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
        print("3: 开始广播测试")
        print("q: 退出")
        choice = input("输入你的选择: ").strip().lower()

        if choice == "1":
            devices = get_devices()
            print(f"当前连接设备: {devices if devices else '无设备'}")

        elif choice == "2":
            all_successful = True
            for key_name, default_key_value in [("ptt", -1), ("sos", -2)]:
                print(f"\n请按下 {key_name.upper()} 键进行采集...")
                success = tool.start_logcat_capture(key_name, default_key_value)
                if not success:
                    print(f"{key_name.upper()} 采集未完成，已跳过")
                    all_successful = False

            if all_successful:
                tool.save_input_json()

        elif choice == "3":
            tool.get_broadcast()


        elif choice == "q":
            break
        else:
            print("请输入有效选项")


if __name__ == "__main__":
    device = choose_device()
    if device:
        run(device)

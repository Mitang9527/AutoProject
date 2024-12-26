import os
import subprocess
import time
from datetime import datetime


class AdbTest:
    def __init__(self, device, case):
        self.device_name = device
        self.local_pth = os.getcwd()
        self.case = case
        self.package_name = None
        self.cached_flow_data = None

    def select_package(self):
        if self.package_name is None:
            self.package_name = str(self.filter_apk())
        return self.package_name

    def get_screenshot(self):
        pic_name = datetime.now().strftime("%Y%m%d_%H%M%S") + "_screenshot.jpeg"
        os.system(f"adb -s {self.device_name} exec-out screencap -p > {os.path.join(self.local_pth, pic_name)}")
        print(f'图片已保存到：{os.path.join(self.local_pth, pic_name)}')

    def get_record(self, case):
        remote_pth = "/sdcard/Pictures/Screenshots"
        cmd = f'adb -s {self.device_name} shell ls -rt {remote_pth}'
        text = os.popen(cmd).read()
        if text == "":
            remote_pth = "/sdcard/DCIM/Screenshots"
            cmd = f'adb -s {self.device_name} shell ls -rt {remote_pth}'
            text = os.popen(cmd)
        print(remote_pth)
        mp4_pth = []
        for m in text.split("\n"):
            if m.endswith("mp4"):
                mp4_pth.append(m)
        mp4_pth = mp4_pth[::-1]

        if "-" in case:
            try:
                video_num = case.split("-")[-1]
                recv_cmd = f'adb -s {self.device_name} pull {os.path.join(remote_pth, mp4_pth[int(video_num)])} {self.local_pth}'
                os.system(recv_cmd)
                print(f'录屏保存地址：{self.local_pth}/{mp4_pth[int(video_num)]}')
            except Exception:
                print(f'\033[0;31m\n输入错误，请检查序号，返回上一级!\n\033[0m')
        else:
            for t in range(len(mp4_pth)):
                print(f'{t} {mp4_pth[t]}')
            try:
                down_num = input("选择你想下载的录屏：")
                recv_cmd = f'adb -s {self.device_name} pull {os.path.join(remote_pth, mp4_pth[int(down_num)])} {self.local_pth}'
                os.system(recv_cmd)
                print(f'录屏保存地址：{self.local_pth}/{mp4_pth[int(down_num)]}')
            except Exception:
                print(f'\033[0;31m\n输入错误，请检查序号，返回上一级!\n\033[0m')

    def record_log(self):
        cs = self.case.split(" ")
        if len(cs) == 1:
            log_name = datetime.now().strftime("%Y%m%d_%H%M%S") + "_log.log"
            print("日志记录中，结束请按Control + C")
            try:
                os.system(f'adb -s {self.device_name} logcat > {log_name}')
            except KeyboardInterrupt:
                pass
            print(f"日志记录结束，日志存储地址为：{os.path.join(self.local_pth, log_name)}")
        else:
            self.run_cmd(f"adb -s {self.device_name} logcat ")

    def run_cmd(self, cmd):
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        cases = self.analyze_params()
        while True:
            stdout_line = process.stdout.readline()
            if not stdout_line:
                break
            else:
                for t in cases:
                    if type(t) is dict:
                        if f'{list(t.keys())[0]}:' and t[list(t.keys())[0]] in stdout_line:
                            print(stdout_line)
                    elif t in stdout_line:
                        print(stdout_line)

    def analyze_params(self):
        cs = self.case.split(" ")
        logs_tag = []
        for c in range(len(cs)):
            if c == 0:
                pass
            elif ":" in cs[c]:
                tag = cs[c].split(":")[0]
                kw = ":".join(cs[c].split(":")[1:])
                logs_tag.append({tag: kw})
            else:
                logs_tag.append(cs[c])
        return logs_tag

    def clean_app(self):
        packname = self.select_package()
        try:
            with os.popen(f'adb -s {self.device_name} shell pm clear {packname}') as cl_res:
                result = cl_res.read()
                if "Success" not in result:
                    print(f'\033[0;31m\n清除数据失败，具体原因可参考以下排查方法：\n'
                          f'检查设备连接是否正常、应用是否存在以及相关权限设置等情况\n\033[0m')
                else:
                    print(f'已清除{packname}的数据')

        except Exception as e:
            print("执行清除应用数据操作出现异常:", str(e))

    def kill_app(self):
        packname = self.select_package()
        try:
            with os.popen(f'adb -s {self.device_name} shell am force-stop {packname}') as cl_res:
                result = cl_res.read()
                if "" not in result:
                    print(f'\033[0;31m\n结束进程失败，具体原因可参考以下排查方法：\n'
                          f'检查设备连接是否正常、应用是否存在以及相关权限设置等情况\n\033[0m')
                else:
                    print(f'已结束{packname}的进程')

        except Exception as e:
            print("执行操作出现异常:", str(e))

    def input_text(self):
        text = self.case.split(" ")[1:]
        input_cmd = f"adb -s {self.device_name} shell am broadcast -a ADB_INPUT_TEXT --es msg '{text}'"
        switch_input_method = "adb shell ime set com.android.adbkeyboard/.AdbIME"
        sw_res = os.popen(switch_input_method)
        if "selected" not in sw_res.read():
            print(f'\033[0;31m\n输入法切换失败，请检查是否安装adbkeyboard \n\033[0m')
        else:
            os.system(input_cmd)

    def filter_apk(self):
        packname_list = get_packname()
        if not packname_list:
            print("查询包名错误")
            return None

        for index, p_name in enumerate(packname_list, start=0):
            print(f"{index}: {p_name}")

        while True:
            try:
                num = int(input("请选择要操作的包名对应的序号: \n"))
                if 0 <= num < len(packname_list):
                    packname = packname_list[num]
                    return packname
                else:
                    print("输入的序号超出范围，请重新输入合法的序号。")
            except ValueError:
                print("请输入合法的数字序号。")

    def install_pkg(self):
        r = os.popen(f"adb -s {self.device_name} install " + self.case)
        result = r.read()
        if "Success" not in result:
            print(f'\033[0;31m\n安装失败 {result} \n\033[0m')
        else:
            print("安装成功")

    def uninstall_pkg(self):
        packname = self.select_package()
        try:
            r = os.popen(f"adb -s {self.device_name} uninstall " + packname)
            result = r.read()
            if "Success" not in result:
                print(f'\033[0;31m\n卸载失败 {result} \n\033[0m')
            else:
                print(f"已将{packname}成功卸载")

        except Exception as e:
            print("执行卸载应用数据操作出现异常:", str(e))

    def change_pkg_env(self, ):
        account = input("请输入账号:")
        password = input("请输入密码:")
        ip_address = input("请输入登录环境:")
        context = input("请输入登录版本:")
        adb_cmd = " ".join(["adb",
                            "shell", "am", "broadcast",
                            "-a", "com.echat.config",
                            "--es", "account", account,
                            "--es", "pwd", password,
                            "--es", "dns", ip_address,
                            "--es", "context", context])
        try:
            adb_res = os.popen(adb_cmd).read()
            if 'result=0' not in adb_res:
                print("参数写入错误")

            else:
                print(f"已更改环境参数为{ip_address},版本为{context},账号为{account}")

        except Exception as e:
            print("发生错误:", str(e))

    def start_apk(self):
        packname = self.select_package()
        try:
            res = os.popen("adb shell am start " + packname)
            result = res.read()
            if "Error" not in result:
                print(f"{packname}启动成功")
            else:
                print(f"{packname}启动失败"+result)

        except Exception as e:
            print("启动app发生错误:", str(e))

#参考：https://www.cnblogs.com/liyuanhong/articles/11376302.html
    def flow_monitor(self):
        if self.cached_flow_data is None:

            package = self.select_package()
            cmd = f'adb shell dumpsys package {package} | findstr userId'
            out = os.popen(cmd).read()
            try:
                if out:
                    userId = out.split('userId=')[1]
                    cmd1 = f'adb shell cat /proc/net/xt_qtaguid/stats | findstr {userId}]'  # 通过uid区分app
                    rmnetup, rmnetdown, wifiup, wifidown = 0, 0, 0, 0
                    result = os.popen(cmd1).readlines()
                    for line in result:  # 可能有多行线程wifi或者移动网络值
                        if 'rmnet' in line and "0x0" in line:  # 蜂窝数据流量
                            rmnetup = round(rmnetup + int(line.split(' ')[5]) / 1024, 2)
                            rmnetdown = round(rmnetdown + int(line.split(' ')[7]) / 1024, 2)

                        elif 'wlan' in line and "0x0" in line:  # wifi数据流量
                            wifiup = round(wifiup + int(line.split(' ')[5])/1024, 2)
                            wifidown = round(wifidown + int(line.split(' ')[7])/1024, 2)
                            """
                            参数说明
                            rmnetup:  移动流量上行数据
                            rmnetdown:  流量下行数据
                            wifiup:  wifi上行数据
                            wifidown:  wifi下行数据。
                            """
                    return rmnetup, rmnetdown, wifiup, wifidown
                else:
                    print('没有userId')

            except Exception as e:
                print("")
        else:
            return self.cached_flow_data

    def run_flow_monitor(self):
        # 获取初始流量数据
        initial_flow_res = self.flow_monitor()  # 获取初始流量数据
        start_flow_res_0 = initial_flow_res[0]  # 初始移动网络上行流量
        start_flow_res_1 = initial_flow_res[1]  # 初始移动网络下行流量
        start_flow_res_2 = initial_flow_res[2]  # 初始WiFi上行流量
        start_flow_res_3 = initial_flow_res[3]  # 初始WiFi下行流量

        start_time = time.time()
        try:
            while True:
                flow_res = self.flow_monitor()  # 获取当前流量数据
                print(f'{datetime.now()}: 流量上行数据为 {flow_res[0]}Kb 流量下行数据为 {flow_res[1]}Kb | '
                      f'wifi上行数据为 {flow_res[2]}Kb wifi下行数据为 {flow_res[-1]}Kb')
                time.sleep(3)
        except KeyboardInterrupt:
            end_time = time.time()
            elapsed_time = end_time - start_time

            # 获取结束时的流量数据
            end_flow_res = self.flow_monitor()
            end_flow_res_0 = end_flow_res[0]  # 结束时的移动网络上行流量
            end_flow_res_1 = end_flow_res[1]  # 结束时的移动网络下行流量
            end_flow_res_2 = end_flow_res[2]  # 结束时的WiFi上行流量
            end_flow_res_3 = end_flow_res[3]  # 结束时的WiFi下行流量

            # 计算流量变化
            rmnet_up_change = round(end_flow_res_0 - start_flow_res_0, 2)
            rmnet_down_change = round(end_flow_res_1 - start_flow_res_1, 2)
            wifi_up_change = round(end_flow_res_2 - start_flow_res_2, 2)
            wifi_down_change = round(end_flow_res_3 - start_flow_res_3, 2)

            # 输出流量变化情况
            print("\n流量监控已停止。")
            print(f"总监控时间: {elapsed_time:.2f} 秒")
            print(f"移动网络上行流量变化: {rmnet_up_change} Kb")
            print(f"移动网络下行流量变化: {rmnet_down_change} Kb")
            print(f"WiFi上行流量变化: {wifi_up_change} Kb")
            print(f"WiFi下行流量变化: {wifi_down_change} Kb")

    def adb_monkey(self):
        """
        参数说明：
        -p <your-package-name>: 指定应用的包名。
        --throttle <milliseconds>: 设置事件之间的延迟时间（毫秒）。
        -v -v: 设置日志级别，-v 越多，日志越详细。
        --ignore-crashes: 忽略崩溃事件。
        --ignore-timeouts: 忽略超时事件。
        --ignore-security-exceptions: 忽略安全异常。
        --ignore-native-crashes: 忽略本地崩溃。
        --monitor-native-crashes: 监控并报告本地崩溃。
        -s <seed>: 设置随机数生成器的种子值。
        <event-count>: 指定 Monkey 运行的事件总数。
        """
        throttle = input("设置事件之间的延迟时间(毫秒):")
        verbose = "-v -v -v"
        ignore_crashes = "--ignore-crashes"
        ignore_timeouts = "--ignore-timeouts"
        ignore_security_exceptions = "--ignore-security-exceptions"
        ignore_native_crashes = "--ignore-native-crashes"
        monitor_native_crashes = "--monitor-native-crashes"
        seed = input("设置随机数生成器的种子值:")
        events = input("指定 Monkey 运行的事件总数:")
        package_name = self.filter_apk()

        command = " ".join([
            "adb", "shell", "monkey",
            "-p", str(package_name),
            "--throttle", throttle,
            verbose,
            ignore_crashes,
            ignore_timeouts,
            ignore_security_exceptions,
            ignore_native_crashes,
            monitor_native_crashes,
            "-s", seed,
            events
        ])

        try:
            adb_res = os.popen(command).read()

        except Exception as e:
            print("发生错误", str(e))

    def language_setting(self):
        os.popen("adb shell am start -a android.settings.LOCALE_SETTINGS")

def run(device_name):
    try:
        while True:
            print(f"\n当前选择的设备系统为：Android 设备为：{device_name}\n")
            case = input("adb测试工具0.6：\n"
                         "----------------------***截图功能***--------------------\n"
                         "gs：获取设备截图到本地\n"
                         "----------------------***常用功能***--------------------\n"
                         "直接拖拽安装包到命令行，按下回车即可安装\n"
                         "uninstall：卸载应用\n"
                         "clean：清除应用数据\n"
                         "kill：结束应用进程\n"
                         "change:更改环境和写入账号\n"
                         "start:启动app\n"
                         "----------------------***查看日志***--------------------\n"
                         "log：将全量日志输出到文件中\n"
                         "rl tag:kw tag:关键字方式获取tag和关键字的交集，仅输出tag和关键字同时存在的日志\n"
                         "rl kw kw1 kw2 该方式只要命中关键字就输出日志\n"
                         "----------------------***其他功能***--------------------\n"
                         "in：切换到AdbKeyboard键盘后可输入中英文，否则只能输入英文，单次只能输入一个中间不能有空格\n"
                         "language: 切换系统语言设置\n"
                         "monkey: monkey测试\n"
                         "flow: 流量监控\n"                                                  
                         "按下 Ctrl+C 退出\n").strip()

            test = AdbTest(device_name, case)

            if case == "gs":
                test.get_screenshot()

            elif case.startswith("log"):
                test.record_log()

            elif case == "clean":
                test.clean_app()

            elif case == "start":
                test.start_apk()

            elif case.startswith("in"):
                test.input_text()

            elif case.startswith("language"):
                test.language_setting()

            elif case.startswith("uninstall"):
                test.uninstall_pkg()

            elif case.startswith("change"):
                test.change_pkg_env()

            elif case.startswith("kill"):
                test.kill_app()

            elif case.startswith("monkey"):
                test.adb_monkey()

            elif case.startswith("flow"):
                test.run_flow_monitor()

            elif case.endswith("apk"):
                test.install_pkg()

    except KeyboardInterrupt:
        pass


def get_device():
    devices = []
    adb_cmd = "adb devices"
    adb_res = os.popen(adb_cmd).read()
    if "" == adb_res:
        print("adb_env_err")
    else:
        adb_arr = adb_res.strip().replace("List of devices attached\n", "").replace("\tdevice", "").split("\n")
        for ad in adb_arr:
            devices.append(ad)
    return devices


def get_packname():
    packnames = []
    adb_cmd = " adb shell pm list packages -3"
    # adb_cmd = "adb shell pm list packages |findstr li"
    # adb_cmd = "adb shell pm list packages"
    adb_res = os.popen(adb_cmd).read()
    if "" == adb_res:
        print("adb_packname_err")
    else:
        lines = adb_res.strip().split('\n')
        packnames = list(map(lambda x: x[len("package:"):], lines))
    return packnames


if __name__ == '__main__':
    if len(get_device()) == 0:
        print(f'\033[0;31m\n当前没有设备连接，请检查！!\n\033[0m')
    else:
        if len(get_device()) == 1:
            run(get_device()[0])
        else:
            try:
                for d in range(len(get_device())):
                    print(d, get_device()[d])
                ch = input("请选择要操作的设备序号：\n")
                device_name = get_device()[int(ch)]
                run(device_name)
            except Exception as e:
                print(f'\033[0;31m\n请选择正确序号!\n\033[0m')

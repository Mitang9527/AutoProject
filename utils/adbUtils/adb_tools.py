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
        print(f'ͼƬ�ѱ��浽��{os.path.join(self.local_pth, pic_name)}')

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
                print(f'¼�������ַ��{self.local_pth}/{mp4_pth[int(video_num)]}')
            except Exception:
                print(f'\033[0;31m\n�������������ţ�������һ��!\n\033[0m')
        else:
            for t in range(len(mp4_pth)):
                print(f'{t} {mp4_pth[t]}')
            try:
                down_num = input("ѡ���������ص�¼����")
                recv_cmd = f'adb -s {self.device_name} pull {os.path.join(remote_pth, mp4_pth[int(down_num)])} {self.local_pth}'
                os.system(recv_cmd)
                print(f'¼�������ַ��{self.local_pth}/{mp4_pth[int(down_num)]}')
            except Exception:
                print(f'\033[0;31m\n�������������ţ�������һ��!\n\033[0m')

    def record_log(self):
        cs = self.case.split(" ")
        if len(cs) == 1:
            log_name = datetime.now().strftime("%Y%m%d_%H%M%S") + "_log.log"
            print("��־��¼�У������밴Control + C")
            try:
                os.system(f'adb -s {self.device_name} logcat > {log_name}')
            except KeyboardInterrupt:
                pass
            print(f"��־��¼��������־�洢��ַΪ��{os.path.join(self.local_pth, log_name)}")
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
                    print(f'\033[0;31m\n�������ʧ�ܣ�����ԭ��ɲο������Ų鷽����\n'
                          f'����豸�����Ƿ�������Ӧ���Ƿ�����Լ����Ȩ�����õ����\n\033[0m')
                else:
                    print(f'�����{packname}������')

        except Exception as e:
            print("ִ�����Ӧ�����ݲ��������쳣:", str(e))

    def kill_app(self):
        packname = self.select_package()
        try:
            with os.popen(f'adb -s {self.device_name} shell am force-stop {packname}') as cl_res:
                result = cl_res.read()
                if "" not in result:
                    print(f'\033[0;31m\n��������ʧ�ܣ�����ԭ��ɲο������Ų鷽����\n'
                          f'����豸�����Ƿ�������Ӧ���Ƿ�����Լ����Ȩ�����õ����\n\033[0m')
                else:
                    print(f'�ѽ���{packname}�Ľ���')

        except Exception as e:
            print("ִ�в��������쳣:", str(e))

    def input_text(self):
        text = self.case.split(" ")[1:]
        input_cmd = f"adb -s {self.device_name} shell am broadcast -a ADB_INPUT_TEXT --es msg '{text}'"
        switch_input_method = "adb shell ime set com.android.adbkeyboard/.AdbIME"
        sw_res = os.popen(switch_input_method)
        if "selected" not in sw_res.read():
            print(f'\033[0;31m\n���뷨�л�ʧ�ܣ������Ƿ�װadbkeyboard \n\033[0m')
        else:
            os.system(input_cmd)

    def filter_apk(self):
        packname_list = get_packname()
        if not packname_list:
            print("��ѯ��������")
            return None

        for index, p_name in enumerate(packname_list, start=0):
            print(f"{index}: {p_name}")

        while True:
            try:
                num = int(input("��ѡ��Ҫ�����İ�����Ӧ�����: \n"))
                if 0 <= num < len(packname_list):
                    packname = packname_list[num]
                    return packname
                else:
                    print("�������ų�����Χ������������Ϸ�����š�")
            except ValueError:
                print("������Ϸ���������š�")

    def install_pkg(self):
        r = os.popen(f"adb -s {self.device_name} install " + self.case)
        result = r.read()
        if "Success" not in result:
            print(f'\033[0;31m\n��װʧ�� {result} \n\033[0m')
        else:
            print("��װ�ɹ�")

    def uninstall_pkg(self):
        packname = self.select_package()
        try:
            r = os.popen(f"adb -s {self.device_name} uninstall " + packname)
            result = r.read()
            if "Success" not in result:
                print(f'\033[0;31m\nж��ʧ�� {result} \n\033[0m')
            else:
                print(f"�ѽ�{packname}�ɹ�ж��")

        except Exception as e:
            print("ִ��ж��Ӧ�����ݲ��������쳣:", str(e))

    def change_pkg_env(self, ):
        account = input("�������˺�:")
        password = input("����������:")
        ip_address = input("�������¼����:")
        context = input("�������¼�汾:")
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
                print("����д�����")

            else:
                print(f"�Ѹ��Ļ�������Ϊ{ip_address},�汾Ϊ{context},�˺�Ϊ{account}")

        except Exception as e:
            print("��������:", str(e))

    def start_apk(self):
        packname = self.select_package()
        try:
            res = os.popen("adb shell am start " + packname)
            result = res.read()
            if "Error" not in result:
                print(f"{packname}�����ɹ�")
            else:
                print(f"{packname}����ʧ��"+result)

        except Exception as e:
            print("����app��������:", str(e))

#�ο���https://www.cnblogs.com/liyuanhong/articles/11376302.html
    def flow_monitor(self):
        if self.cached_flow_data is None:

            package = self.select_package()
            cmd = f'adb shell dumpsys package {package} | findstr userId'
            out = os.popen(cmd).read()
            try:
                if out:
                    userId = out.split('userId=')[1]
                    cmd1 = f'adb shell cat /proc/net/xt_qtaguid/stats | findstr {userId}]'  # ͨ��uid����app
                    rmnetup, rmnetdown, wifiup, wifidown = 0, 0, 0, 0
                    result = os.popen(cmd1).readlines()
                    for line in result:  # �����ж����߳�wifi�����ƶ�����ֵ
                        if 'rmnet' in line and "0x0" in line:  # ������������
                            rmnetup = round(rmnetup + int(line.split(' ')[5]) / 1024, 2)
                            rmnetdown = round(rmnetdown + int(line.split(' ')[7]) / 1024, 2)

                        elif 'wlan' in line and "0x0" in line:  # wifi��������
                            wifiup = round(wifiup + int(line.split(' ')[5])/1024, 2)
                            wifidown = round(wifidown + int(line.split(' ')[7])/1024, 2)
                            """
                            ����˵��
                            rmnetup:  �ƶ�������������
                            rmnetdown:  ������������
                            wifiup:  wifi��������
                            wifidown:  wifi�������ݡ�
                            """
                    return rmnetup, rmnetdown, wifiup, wifidown
                else:
                    print('û��userId')

            except Exception as e:
                print("")
        else:
            return self.cached_flow_data

    def run_flow_monitor(self):
        # ��ȡ��ʼ��������
        initial_flow_res = self.flow_monitor()  # ��ȡ��ʼ��������
        start_flow_res_0 = initial_flow_res[0]  # ��ʼ�ƶ�������������
        start_flow_res_1 = initial_flow_res[1]  # ��ʼ�ƶ�������������
        start_flow_res_2 = initial_flow_res[2]  # ��ʼWiFi��������
        start_flow_res_3 = initial_flow_res[3]  # ��ʼWiFi��������

        start_time = time.time()
        try:
            while True:
                flow_res = self.flow_monitor()  # ��ȡ��ǰ��������
                print(f'{datetime.now()}: ������������Ϊ {flow_res[0]}Kb ������������Ϊ {flow_res[1]}Kb | '
                      f'wifi��������Ϊ {flow_res[2]}Kb wifi��������Ϊ {flow_res[-1]}Kb')
                time.sleep(3)
        except KeyboardInterrupt:
            end_time = time.time()
            elapsed_time = end_time - start_time

            # ��ȡ����ʱ����������
            end_flow_res = self.flow_monitor()
            end_flow_res_0 = end_flow_res[0]  # ����ʱ���ƶ�������������
            end_flow_res_1 = end_flow_res[1]  # ����ʱ���ƶ�������������
            end_flow_res_2 = end_flow_res[2]  # ����ʱ��WiFi��������
            end_flow_res_3 = end_flow_res[3]  # ����ʱ��WiFi��������

            # ���������仯
            rmnet_up_change = round(end_flow_res_0 - start_flow_res_0, 2)
            rmnet_down_change = round(end_flow_res_1 - start_flow_res_1, 2)
            wifi_up_change = round(end_flow_res_2 - start_flow_res_2, 2)
            wifi_down_change = round(end_flow_res_3 - start_flow_res_3, 2)

            # ��������仯���
            print("\n���������ֹͣ��")
            print(f"�ܼ��ʱ��: {elapsed_time:.2f} ��")
            print(f"�ƶ��������������仯: {rmnet_up_change} Kb")
            print(f"�ƶ��������������仯: {rmnet_down_change} Kb")
            print(f"WiFi���������仯: {wifi_up_change} Kb")
            print(f"WiFi���������仯: {wifi_down_change} Kb")

    def adb_monkey(self):
        """
        ����˵����
        -p <your-package-name>: ָ��Ӧ�õİ�����
        --throttle <milliseconds>: �����¼�֮����ӳ�ʱ�䣨���룩��
        -v -v: ������־����-v Խ�࣬��־Խ��ϸ��
        --ignore-crashes: ���Ա����¼���
        --ignore-timeouts: ���Գ�ʱ�¼���
        --ignore-security-exceptions: ���԰�ȫ�쳣��
        --ignore-native-crashes: ���Ա��ر�����
        --monitor-native-crashes: ��ز����汾�ر�����
        -s <seed>: ���������������������ֵ��
        <event-count>: ָ�� Monkey ���е��¼�������
        """
        throttle = input("�����¼�֮����ӳ�ʱ��(����):")
        verbose = "-v -v -v"
        ignore_crashes = "--ignore-crashes"
        ignore_timeouts = "--ignore-timeouts"
        ignore_security_exceptions = "--ignore-security-exceptions"
        ignore_native_crashes = "--ignore-native-crashes"
        monitor_native_crashes = "--monitor-native-crashes"
        seed = input("���������������������ֵ:")
        events = input("ָ�� Monkey ���е��¼�����:")
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
            print("��������", str(e))

    def language_setting(self):
        os.popen("adb shell am start -a android.settings.LOCALE_SETTINGS")

def run(device_name):
    try:
        while True:
            print(f"\n��ǰѡ����豸ϵͳΪ��Android �豸Ϊ��{device_name}\n")
            case = input("adb���Թ���0.6��\n"
                         "----------------------***��ͼ����***--------------------\n"
                         "gs����ȡ�豸��ͼ������\n"
                         "----------------------***���ù���***--------------------\n"
                         "ֱ����ק��װ���������У����»س����ɰ�װ\n"
                         "uninstall��ж��Ӧ��\n"
                         "clean�����Ӧ������\n"
                         "kill������Ӧ�ý���\n"
                         "change:���Ļ�����д���˺�\n"
                         "start:����app\n"
                         "----------------------***�鿴��־***--------------------\n"
                         "log����ȫ����־������ļ���\n"
                         "rl tag:kw tag:�ؼ��ַ�ʽ��ȡtag�͹ؼ��ֵĽ����������tag�͹ؼ���ͬʱ���ڵ���־\n"
                         "rl kw kw1 kw2 �÷�ʽֻҪ���йؼ��־������־\n"
                         "----------------------***��������***--------------------\n"
                         "in���л���AdbKeyboard���̺��������Ӣ�ģ�����ֻ������Ӣ�ģ�����ֻ������һ���м䲻���пո�\n"
                         "language: �л�ϵͳ��������\n"
                         "monkey: monkey����\n"
                         "flow: �������\n"                                                  
                         "���� Ctrl+C �˳�\n").strip()

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
        print(f'\033[0;31m\n��ǰû���豸���ӣ����飡!\n\033[0m')
    else:
        if len(get_device()) == 1:
            run(get_device()[0])
        else:
            try:
                for d in range(len(get_device())):
                    print(d, get_device()[d])
                ch = input("��ѡ��Ҫ�������豸��ţ�\n")
                device_name = get_device()[int(ch)]
                run(device_name)
            except Exception as e:
                print(f'\033[0;31m\n��ѡ����ȷ���!\n\033[0m')

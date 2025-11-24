import os
import shutil
import subprocess
import sys
import time
import requests
from tqdm import tqdm

from utils.apktoolUtils.get_json_data import get_json_field
from utils.apktoolUtils.increment_version_info import update_version_info, build_newname
from utils.logUtils.logControl import INFO, ERROR
from utils.readFilesUtils.get_path import get_project
from utils.timeUtils.time_control import now_time_day

# === apktool依赖 ===
APKTOOL_URL = "https://bitbucket.org/iBotPeaches/apktool/downloads/apktool_2.9.3.jar"
APKTOOL_JAR = "apktool.jar"

# ===  签名文件配置  ===
project_path = get_project()# 获取当前项目路径
keystore_big_path = project_path  / 'cert' / 'shanli.jks' #大中屏签名文件
keystore_small_path = project_path / 'cert' / 'shanlitech.keystore'   #小屏签名文件

keystore_config = {
        'large': {'path': keystore_big_path, 'password': '123456'},
        'middle': {'path': keystore_big_path, 'password': '123456'},
        'small': {'path': keystore_small_path, 'password': 'Lgsj829517'},
        'none': {'path': keystore_small_path, 'password': 'Lgsj829517'}
    }

# ===   app_out路径文件夹   ====
folder_path = project_path / 'app_out'

# ===   zipalign配置路径   ====
Zipalign_JAR = project_path / 'win' / 'zipalign.exe'

# ===   apksigner配置路径   ====
APKsigner_JAR = project_path / 'win' / 'apksigner.bat'

# ===   apktool.yml配置路径   ====
yml_path = project_path / 'app_out' / 'apktool.yml'

# ===   slclient配置路径   ====
file_path = project_path / 'app_out' / 'assets' / 'slclient.json'
launcherModule = ['ui', 'launcherModule']

# ===   Led配置路径   ====
Led_json = project_path / 'app_out' / 'assets' /'slclient'/ 'led.json'

# ===   input配置路径   ====
input_json = project_path / 'app_out' / 'assets' /'slclient'/ 'input.json'

# ===   reaction配置路径   ====
reaction_json = project_path / 'app_out' / 'assets' /'slclient'/ 'reaction.json'

def is_java_installed():
    try:
        result = subprocess.run(["java", "-version"], creationflags=subprocess.CREATE_NO_WINDOW, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def prompt_java_installation():
    print(" 未检测到 Java 安装。")
    print("请先安装 Java Runtime Environment (JRE) 或 Java Development Kit (JDK)。")
    print(" 官方下载地址：https://www.oracle.com/java/technologies/javase-downloads.html")
    sys.exit(1)

def download_apktool(url, filename):
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    chunk_size = 1024

    with open(filename, "wb") as f, tqdm(
        desc=f"正在下载 {filename}",
        total=total_size,
        unit='B',
        unit_scale=True,
        unit_divisor=1024
    ) as bar:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                bar.update(len(chunk))

def ensure_apktool_installed(jar_path=APKTOOL_JAR):
    if not os.path.exists(jar_path):
        INFO.logger.info(f"准备下载 apktool.jar 到：{jar_path}")
        try:
            download_apktool(APKTOOL_URL, jar_path)
            INFO.logger.info(" apktool.jar 下载完成。")
        except Exception as e:
            INFO.logger.info(" 下载失败：", e)
            sys.exit(1)
    else:
        INFO.logger.info(" apktool.jar 已存在,正在解压。")

def run_with_live_output(command):
    process = subprocess.Popen(command, creationflags=subprocess.CREATE_NO_WINDOW, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            INFO.logger.info(f" {line.strip()}")
    return process.returncode

def decompile_apk(apk_path, output_dir="app_out"):
    if not is_java_installed():
        prompt_java_installation()

    ensure_apktool_installed()

    if os.path.exists(output_dir):
        shutil.rmtree(output_dir, ignore_errors=True)

    command = ["java", "-jar", APKTOOL_JAR, "d", apk_path, "-s", "-o", output_dir]

    INFO.logger.info(f"\n 正在反编译 APK：{apk_path}")
    start_time = time.time()
    exit_code = run_with_live_output(command)
    elapsed = time.time() - start_time

    if exit_code == 0:
        INFO.logger.info(f"成功：输出目录 {output_dir}（耗时 {elapsed:.1f} 秒）")
        return True
    else:
        ERROR.logger.error(" 失败：apktool 或 Java 问题")
        return False

def rename_file(output_path, new_name):
    """
    将指定文件重命名
    参数:
        old_path: 原文件完整路径
        new_name: 新文件名
    返回:
        新文件完整路径
    """
    dir_path = os.path.dirname(output_path)
    new_path = os.path.join(dir_path, new_name)

    if not os.path.exists(output_path):
        raise FileNotFoundError(f"文件不存在：{output_path}")

    os.rename(output_path, new_path)
    return new_path

def build_and_sign_apk(project_dir='app_out', output_apk='app.apk'):

    start_time = time.time()
    update_version_info(yml_path)

    try:
        INFO.logger.info("正在使用 apktool 反编译并构建 APK...")
        apktool_cmd = ["java", "-jar", APKTOOL_JAR, "b", project_dir, "-o", "app-unsigned-unaligned.apk"]
        returncode = run_with_live_output(apktool_cmd)
        if returncode != 0:
            ERROR.logger.error("打包失败，请检查资源修改是否正确")
            return

        INFO.logger.info("打包成功")

        zipalign_cmd = [Zipalign_JAR, "-v", "-p", "4", "app-unsigned-unaligned.apk", "app-unsigned.apk"]
        returncode = run_with_live_output(zipalign_cmd)
        if returncode != 0:
            ERROR.logger.error("APK 对齐失败")
            return

        # 删除未对齐的 APK 文件
        os.remove("app-unsigned-unaligned.apk")

        INFO.logger.info("APK 打包成功，正在进行 APK 签名...")
        # 使用 apksigner 对 APK 文件进行签名
        value = get_json_field(file_path, launcherModule)

        if value is None:
            INFO.logger.info("多合一版本 默认使用大屏文件签名")
            value = 'large'

        keystore_info = keystore_config.get(value)

        keystore_path = keystore_info['path']
        keystore_password = keystore_info['password']


        date_str = now_time_day()
        output_dir = os.path.join(project_path, date_str)
        os.makedirs(output_dir, exist_ok=True)

        output_apk_path = os.path.join(output_dir, output_apk)

        apksigner_cmd = [
            APKsigner_JAR, "sign",
            "--ks", keystore_path,
            "--ks-pass", f"pass:{keystore_password}",
            "--out", output_apk_path,
            "app-unsigned.apk"
        ]
        returncode = run_with_live_output(apksigner_cmd)

        if returncode != 0:
            ERROR.logger.error("APK 签名失败")
            return
        # 删除未签名的 APK 文件
        os.remove("app-unsigned.apk")

        # 重命名操作
        new_name = build_newname(file_path, launcherModule, yml_path)
        new_path = rename_file(output_apk_path, new_name)
        elapsed = time.time() - start_time
        INFO.logger.info(f"APK 文件已成功打包并签名:{new_path},耗时 {elapsed:.1f} 秒,")

    except Exception as e:
        ERROR.logger.error(f"发生错误: {e}")

def open_folder(folder_path):
    if os.path.exists(folder_path):
        os.startfile(folder_path)
    else:
        ERROR.logger.error(f"路径不存在:{folder_path}")

def get_sha1(apk_path):
    cmd = ["keytool", "-printcert", "-jarfile", apk_path]

    try:
        result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            output = result.decode("utf-8")
        except UnicodeDecodeError:
            output = result.decode("gbk", errors="ignore")

        # 解析 SHA1
        sha1 = None
        for line in output.splitlines():
            if "SHA1:" in line:
                sha1 = line.split("SHA1:")[1].strip()
                break

        if sha1:
            content = f"证书 SHA1:\n{sha1}" if sha1 else "未获取到 SHA1 值"
            return content
        else:
            print("未找到 SHA1 值")
            return None

    except subprocess.CalledProcessError as e:
        print("执行 keytool 出错:", e.output.decode(errors="ignore"))
        return None












import os
import shutil
import subprocess
import sys
import time
import requests
from tqdm import tqdm


from utils.logUtils.logControl import INFO, ERROR
from utils.readFilesUtils.get_path import get_project

# === 配置日志，让INFO和ERROR同时输出到log_box和控制台 ===

APKTOOL_URL = "https://bitbucket.org/iBotPeaches/apktool/downloads/apktool_2.9.3.jar"
APKTOOL_JAR = "apktool.jar"


project_path = get_project()  # 获取当前项目路径
keystore_big_path = project_path / 'cert' / 'shanli.jks'
keystore_small_path = project_path / 'cert' / 'shanlitech.keystore'


def is_java_installed():
    try:
        result = subprocess.run(["java", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def prompt_java_installation():
    print(" 未检测到 Java 安装。")
    print("请先安装 Java Runtime Environment (JRE) 或 Java Development Kit (JDK)。")
    print(" 官方下载地址：https://www.oracle.com/java/technologies/javase-downloads.html")
    sys.exit(1)

def download_with_tqdm(url, filename):
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
            download_with_tqdm(APKTOOL_URL, jar_path)
            INFO.logger.info(" apktool.jar 下载完成。")
        except Exception as e:
            INFO.logger.info(" 下载失败：", e)
            sys.exit(1)
    else:
        INFO.logger.info(" apktool.jar 已存在。")

def run_with_live_output(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
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

def build_and_sign_big_apk(project_dir='app_out', output_apk='app.apk', keystore_path=keystore_big_path,
                       keystore_password='123456'):
    try:
        INFO.logger.info("正在使用 apktool 反编译并构建 APK...")
        apktool_cmd = ["java", "-jar", APKTOOL_JAR, "b", project_dir, "-o", "app-unsigned-unaligned.apk"]
        returncode = run_with_live_output(apktool_cmd)
        if returncode != 0:
            ERROR.logger.error("打包失败，请检查资源修改是否正确")
            return

        INFO.logger.info("打包成功")

        zipalign_cmd = ["zipalign.exe", "-v", "-p", "4", "app-unsigned-unaligned.apk", "app-unsigned.apk"]
        returncode = run_with_live_output(zipalign_cmd)
        if returncode != 0:
            ERROR.logger.error("APK 对齐失败")
            return

        # 删除未对齐的 APK 文件
        os.remove("app-unsigned-unaligned.apk")

        INFO.logger.info("APK 打包成功，正在进行 APK 签名...")

        # Step 3: 使用 apksigner 对 APK 文件进行签名
        apksigner_cmd = [
            "apksigner.bat", "sign", "--ks", keystore_path, "--ks-pass", f"pass:{keystore_password}",
            "--out", output_apk, "app-unsigned.apk"
        ]
        returncode = run_with_live_output(apksigner_cmd)
        if returncode != 0:
            ERROR.logger.error("APK 签名失败")
            return

        # 删除未签名的 APK 文件
        os.remove("app-unsigned.apk")

        INFO.logger.info(f"APK 文件已成功构建并签名：{output_apk}")

    except Exception as e:
        ERROR.logger.error(f"发生错误: {e}")

def build_and_sign_small_apk_(project_dir='app_out', output_apk='SSAPP_app.apk', keystore_path=keystore_small_path,
                          keystore_password='Lgsj829517'):
    try:
        INFO.logger.info("正在使用 apktool 反编译并构建 APK...")
        apktool_cmd = ["apktool.bat", "b", "--use-aapt2", "-o", "app-unsigned-unaligned.apk", project_dir]
        returncode = run_with_live_output(apktool_cmd)
        if returncode != 0:
            ERROR.logger.error("打包失败，请检查资源修改是否正确")
            return

        INFO.logger.info("打包成功，正在进行 APK 对齐...")

        zipalign_cmd = ["zipalign.exe", "-v", "-p", "4", "app-unsigned-unaligned.apk", "app-unsigned.apk"]
        returncode = run_with_live_output(zipalign_cmd)
        if returncode != 0:
            ERROR.logger.error("APK 对齐失败")
            return


        os.remove("app-unsigned-unaligned.apk")

        INFO.logger.info("APK 对齐成功，正在进行 APK 签名...")

        # Step 3: 使用 apksigner 对 APK 文件进行签名
        apksigner_cmd = [
            "apksigner.bat", "sign", "--ks", keystore_path, "--ks-pass", f"pass:{keystore_password}",
            "--out", output_apk, "app-unsigned.apk"
        ]
        returncode = run_with_live_output(apksigner_cmd)
        if returncode != 0:
            ERROR.logger.error("APK 签名失败")
            return

        # 删除未签名的 APK 文件
        os.remove("app-unsigned.apk")

        INFO.logger.info(f"APK 文件已成功构建并签名：{output_apk}")

    except Exception as e:
        ERROR.logger.error(f"发生错误: {e}")





from tkinter import filedialog
import os
import threading
from functools import partial

from utils.adbUtils.adb_tools import AdbTest
from utils.apktoolUtils.apkUtils import decompile_apk, build_and_sign_apk, file_path, Led_json, input_json, \
    reaction_json, open_folder, folder_path, get_sha1
from utils.apktoolUtils.changeSkin import exchange_res, source_dir, target_dir, update_colors_in_target_xml, \
    source_color_file, target_color_file, replace_app_name
from utils.apktoolUtils.get_json_data import load_json, save_json
from utils.customtkinterUtils.customtkinterUtils import CustomApp
from utils.logUtils.logControl import INFO, ERROR
import subprocess

TEMP_DIR = "app_out"
DRAWABLE_DIR = os.path.join(TEMP_DIR, "res", "drawable")


# === 初始化主窗口 ===
root = CustomApp()
root.title("APKTool2.2")

# === 日志显示框 ===
log_box = root.textbox

# === json文件显示框 ===
json_box = root.json_textbox

# === 配置日志，让INFO和ERROR同时输出到log_box和控制台 ===
INFO.add_tkinter_handler(log_box)
ERROR.add_tkinter_handler(log_box)

# === 选择 APK并安装 ===
def choose_install_apk():
    apk_path = filedialog.askopenfilename(title="请选择一个apk进行安装", filetypes=[("APK 文件", "*.apk")])
    if not apk_path:
        return
    INFO.logger.info(f"选择了 APK 文件：{apk_path}")

    def task():
        success = AdbTest.install_pkg()
        if success:
            INFO.logger.info("APK安装成功")
        else:
            ERROR.logger.error("安装失败")

    threading.Thread(target=task, daemon=True).start()
# === 选择 APK并反编译 ===
def choose_apk():
    apk_path = filedialog.askopenfilename(title="请选择解压APK", filetypes=[("APK 文件", "*.apk")])
    if not apk_path:
        return
    INFO.logger.info(f"选择了 APK 文件：{apk_path}")

    def task():
        success = decompile_apk(apk_path, TEMP_DIR)
        if success:
            INFO.logger.info("APK 解包完成")
        else:
            ERROR.logger.error("解包失败")

    threading.Thread(target=task, daemon=True).start()

def choose_template_apk():
    apk_path = filedialog.askopenfilename(title="请选择资源APK文件夹", filetypes=[("APK 文件", "*.apk")])

    if not apk_path:
        return
    INFO.logger.info(f"选择了 资源APK 文件：{apk_path}")

    def task():
        success = decompile_apk(apk_path, output_dir="app_out1")
        if success:
            INFO.logger.info("APK 解包完成")
        else:
            ERROR.logger.error("解包失败")

    threading.Thread(target=task, daemon=True).start()

# === 选择slcilent.json ===
current_json_file_path = None


def open_cilent_json(file_path):
    global current_json_file_path
    current_json_file_path = file_path
    data = load_json(file_path)
    json_box.delete("1.0", "end")
    json_box.insert("1.0", data)


# === 定义路径 ===
json_paths = {
    "slcilent_json": file_path,
    "LED_json": Led_json,
    "input_json": input_json,
    "reaction_json": reaction_json,
}


def optionmenu_callback(selection):
    path = json_paths.get(selection)
    if path:
        open_cilent_json(path)


# === 保存按钮 ===
def save_json_button():
    global current_json_file_path
    json_str = json_box.get("1.0", "end").strip()
    save_json(current_json_file_path, json_str)
    open_cilent_json(current_json_file_path)


# === 构建新 APK ===
def build_new_apk():
    output_path = "app.apk"

    def task():
        try:
            INFO.logger.info("正在打包 APK ...")
            build_and_sign_apk(TEMP_DIR, output_path)

        except Exception as e:
            ERROR.logger.error(f"异常：{e}")

    threading.Thread(target=task, daemon=True).start()


def change_skin():
    try:
        exchange_res(source_dir, target_dir)
        update_colors_in_target_xml(source_color_file, target_color_file)
        replace_app_name(source_dir, target_dir)
        build_new_apk()

    except Exception as e:
        ERROR.logger.error(f"异常：{e}")

def get_apk_sha1():
    apk_path = filedialog.askopenfilename(
        title="请选择APK",
        filetypes=[("APK 文件", "*.apk")]
    )
    sha1_ctx = get_sha1(apk_path)
    root.show_message("APK SHA1", sha1_ctx)

# === adbtools按钮分布 ===
root.create_middle_button(text="安装APK",row=1,command=choose_install_apk)

# === 按钮分布 ===
root.create_sidebar_button(text="解压APK",row=1, command=choose_apk)
root.create_sidebar_button(text="解压资源APK",row=2, command=choose_template_apk)
root.create_sidebar_button(text="打包 APK", row=3, command=build_new_apk)
root.create_sidebar_button(text="一键换肤", row=4, command=change_skin)
root.create_optionmenu(values=["slcilent_json", "input_json", "reaction_json", "LED_json"],
                       row=5, command=optionmenu_callback)
root.create_sidebar_button(text="查看sha1值", row=6, command=get_apk_sha1)
root.create_sidebar_button(text="打开资源文件夹", row=7, command=lambda: open_folder(folder_path))
root.save_json_button.configure(command=partial(save_json_button))
root.mainloop()

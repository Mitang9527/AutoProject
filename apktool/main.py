from tkinter import filedialog
import os
import threading
from utils.apktoolUtils.apkUtils import decompile_apk, build_and_sign_apk
from utils.apktoolUtils.changeSkin import exchange_res, source_dir, target_dir, update_colors_in_target_xml, \
    source_color_file, target_color_file, replace_app_name
from utils.customtkinterUtils.customtkinterUtils import CustomApp
from utils.logUtils.logControl import INFO, ERROR

TEMP_DIR = "app_out"
DRAWABLE_DIR = os.path.join(TEMP_DIR, "res", "drawable")

# === 初始化主窗口 ===
root = CustomApp()
root.title("APKTool")

# === 日志显示框 ===
log_box = root.textbox

# === 配置日志，让INFO和ERROR同时输出到log_box和控制台 ===
INFO.add_tkinter_handler(log_box)
ERROR.add_tkinter_handler(log_box)

# === 选择 APK并反编译 ===
def choose_apk():
    apk_path = filedialog.askopenfilename(title="请选择解压APK文件夹",filetypes=[("APK 文件", "*.apk")])
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
    apk_path = filedialog.askopenfilename(title="请选择资源APK文件夹",filetypes=[("APK 文件", "*.apk")])

    if not apk_path:
        return
    INFO.logger.info(f"选择了 资源APK 文件：{apk_path}")

    def task():
        success = decompile_apk(apk_path, output_dir = "app_out1")
        if success:
            INFO.logger.info("APK 解包完成")
        else:
            ERROR.logger.error("解包失败")

    threading.Thread(target=task, daemon=True).start()

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


# === 顶部按钮 ===
root.sidebar_button_1.configure(text="解压APK", command=choose_apk)
root.sidebar_button_2.configure(text="解压资源APK", command=choose_template_apk)
root.sidebar_button_3.configure(text="打包 APK", command=build_new_apk,state="normal")
root.sidebar_button_4.configure(text="一键换肤", command=change_skin)
root.mainloop()

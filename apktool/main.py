import tkinter as tk
from tkinter import filedialog, scrolledtext
import os
import threading

from utils.apktoolUtils.apkUtils import decompile_apk, build_and_sign_apk
from utils.logUtils.logControl import INFO, ERROR

TEMP_DIR = "app_out"
DRAWABLE_DIR = os.path.join(TEMP_DIR, "res", "drawable")


# === 初始化主窗口 ===
root = tk.Tk()
root.title("APKToolV1.0")
root.geometry("1000x700")

# === 日志显示框 ===
log_box = scrolledtext.ScrolledText(root, height=15, font=("Courier", 10), state='disabled')
log_box.pack(fill='both', padx=10, pady=10)

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

# === 顶部按钮 ===
btn_frame = tk.Frame(root)
btn_frame.pack(side="top", pady=10)
tk.Button(btn_frame, text="解压 APK", font=("Arial", 12), command=choose_apk).pack(side="left", padx=20)
tk.Button(btn_frame, text="解压 资源APK", font=("Arial", 12), command=choose_template_apk).pack(side="left", padx=20)
tk.Button(btn_frame, text="打包 APK", font=("Arial", 12), command=build_new_apk).pack(side="left", padx=20)

log_box.pack(side="bottom", fill="x", padx=10, pady=5)

root.mainloop()

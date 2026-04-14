import shutil
import subprocess
import platform
import sys
from typing import List
import customtkinter as ctk
from .i18n import _


def check_command(cmd: str) -> bool:
    """检查命令是否在系统 PATH 中"""
    return shutil.which(cmd) is not None


def is_adb_installed() -> bool:
    """检测 ADB 是否安装且可运行"""
    if not check_command("adb"):
        return False
    try:
        result = subprocess.run(
            ["adb", "version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
            creationflags=(
                subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            ),
        )
        return result.returncode == 0
    except Exception:
        return False


def is_java_installed() -> bool:
    """检测 Java 是否安装且可运行"""
    if not check_command("java"):
        return False
    try:
        result = subprocess.run(
            ["java", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
            creationflags=(
                subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            ),
        )
        return result.returncode == 0
    except Exception:
        return False


def show_env_error_dialog(parent: ctk.CTk, missing_list: List[str]) -> None:
    """显示环境缺失的弹窗"""
    msg = "System environment check failed:\n\n"
    if "ADB" in missing_list:
        msg += (
            "❌ ADB (Android Debug Bridge)\n   "
            "Decompress and install ADB compressed package in Env\n"
            ", and set system variables.\n"
        )
    if "JAVA" in missing_list:
        msg += (
            "❌ Java (JDK/JRE)\n   "
            "Solution: extract the JDK compressed package in Env and install it.\n"
        )
    msg += "\nPlease install the missing components and click [Retry Detection]."

    dialog = ctk.CTkToplevel(parent)
    dialog.title("环境缺失警告")
    dialog.geometry("500x400")
    dialog.transient(parent)
    dialog.grab_set()

    lbl = ctk.CTkLabel(dialog, text=msg, justify="left", anchor="nw")
    lbl.pack(padx=20, pady=20, fill="both", expand=True)

    btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_frame.pack(pady=20)

    def on_retry():
        dialog.destroy()
        parent.event_generate("<<EnvRetry>>")

    def on_exit():
        dialog.destroy()
        parent.quit()
        sys.exit(0)

    ctk.CTkButton(btn_frame, text="重试检测", command=on_retry, fg_color="green").pack(
        side="left", padx=10
    )
    ctk.CTkButton(btn_frame, text="退出程序", command=on_exit, fg_color="red").pack(
        side="left", padx=10
    )


class EnvChecker:
    """环境检查器类"""

    def __init__(self, parent_app: ctk.CTk):
        self.parent = parent_app

    def check_all(self, show_dialog: bool = True) -> bool:
        missing = []
        if not is_adb_installed():
            missing.append("ADB")
        if not is_java_installed():
            missing.append("JAVA")

        if missing:
            if show_dialog:
                self.parent.after(
                    0, lambda: show_env_error_dialog(self.parent, missing)
                )
            return False
        return True

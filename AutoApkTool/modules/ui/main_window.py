import os
import re
import subprocess
import sys
import json
import time
import queue
import shutil
import platform
import threading
import tkinter
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Set, List, Any, Dict
import customtkinter as ctk
from tkinter import messagebox, filedialog

from ..constants import (
    RESOURCE_PATH,
    WORKSPACE_PATH,
    TEMP_PATH,
    JSON_FILE,
    APKTOOL_JAR,
    APK_LARGE,
    APK_SMALL,
    APK_SCREENLESS,
    ENV_CONF,
    ENV_DISPLAY_NAMES,
    LOGIN_TYPE_MAPPING,
    MAP_CONFIG_TEMPLATES,
    LAUNCHER_MODULE_PATH,
    RECORDER_ENABLE_PATH,
    PATH_SLCLIENT_JSON,
    PATH_YML,
    APKSIGNER_BAT,
    ZIPALIGN_EXE,
    KEYSTORE_CONFIG,
    LBS_COOR_PATH,
    LBS_MAP_PYPE,
    ANDROID_NAMESPACE,
    PATH_MANIFEST_XML,
    PATH_ASS,
    PATH_SLCLIENT,
    PATH_INPUT_JSON_SRC,
    PATH_INPUT_JSON_DST,
    TEMP_DIR,
)
from ..i18n import i18n, _
from ..env_checker import EnvChecker, is_adb_installed
from ..backend import SmartKeyBackend
from ..utils import *
from ..apk_tools import *


class App(ctk.CTk):
    """主应用程序窗口"""

    def __init__(self):
        super().__init__()
        self.title(_("app_title"))
        self.geometry("1200x700")

        # 添加标志跟踪是否是环境预设值
        self.is_default_dns = False
        self.is_default_context = False
        self.is_default_upgrade = False

        # 添加标志跟踪是否是已有配置导入
        self.is_import = False

        # 状态变量
        self.backend: Optional[SmartKeyBackend] = None
        self.current_device: str = ""
        self.log_queue: queue.Queue = queue.Queue()
        self.is_listening: bool = False
        self.env_checker: EnvChecker = EnvChecker(self)
        self.current_apk_type: str = "大屏"

        # 事件绑定
        self.bind("<<EnvRetry>>", lambda e: self.on_env_retry())
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 打包配置状态管理
        self.build_config = {"env_type": "", "map_source": "baidu", "encoding": "amrnb"}
        self.slclient_options = {}

        # --- 新增：用于存储 Tab 的 Frame 引用 ---
        self.tab_frames = {}

        # --- 新增：SegmentedButton 的变量 ---
        self.selected_tab = ctk.StringVar(value="")

        self._init_sidebar()
        self._init_main_area()

        # 启动定时任务
        self.after(50, self.process_log_queue)
        self.after(200, self.initial_env_check)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ------------------辅助函数------------------------
    def _load_slclient_json(self) -> dict:
        return load_slclient_json()

    # ------------------UI函数------------------------

    def _init_sidebar(self) -> None:
        """初始化侧边栏"""
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(100, weight=1)

        # Logo
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="App\nAdaptation",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # 设备选择
        self.device_label = ctk.CTkLabel(
            self.sidebar_frame, text=_("lbl_device"), anchor="w"
        )
        self.device_label.grid(row=1, column=0, padx=20, pady=(10, 0))
        self.device_var = ctk.StringVar(value=(_("status_detecting")))
        self.device_menu = ctk.CTkOptionMenu(
            self.sidebar_frame,
            variable=self.device_var,
            values=[],
            command=self.on_device_change,
        )
        self.device_menu.grid(row=2, column=0, padx=20, pady=5)
        self.refresh_btn = ctk.CTkButton(
            self.sidebar_frame,
            text=_("btn_refresh"),
            command=self.refresh_devices,
            height=30,
        )
        self.refresh_btn.grid(row=3, column=0, padx=20, pady=5)

        # 监听模式
        self.mode_label = ctk.CTkLabel(
            self.sidebar_frame, text=_("lbl_mode"), anchor="w"
        )
        self.mode_label.grid(row=4, column=0, padx=20, pady=(5, 0))
        self.mode_var = ctk.StringVar(value="ptt")
        self.mode_menu = ctk.CTkOptionMenu(
            self.sidebar_frame, variable=self.mode_var, values=["ptt", "sos"]
        )
        self.mode_menu.grid(row=5, column=0, padx=20, pady=5)

        # 控制按钮
        self.start_btn = ctk.CTkButton(
            self.sidebar_frame,
            text=_("btn_start_listen"),
            fg_color="green",
            command=self.toggle_listen,
        )
        self.start_btn.grid(row=7, column=0, padx=20, pady=10)
        self.clear_log_btn = ctk.CTkButton(
            self.sidebar_frame,
            text=_("clear_log"),
            fg_color="gray",
            command=self.clear_log,
        )
        self.clear_log_btn.grid(row=8, column=0, padx=20, pady=10)

        # APK 选择区域
        self.apk_select_label = ctk.CTkLabel(
            self.sidebar_frame, text=_("lbl_apk_type"), anchor="w"
        )
        self.apk_select_label.grid(row=9, column=0, padx=20, pady=(15, 0))

        self.decompile_apk_btn = ctk.CTkButton(
            self.sidebar_frame, text=_("btn_decompile"), command=self.decompile_apk
        )
        self.decompile_apk_btn.grid(row=12, column=0, padx=20, pady=10)

        self.apk_type_seg = ctk.CTkSegmentedButton(
            self.sidebar_frame,
            values=[
                _("type_large_screen"),
                _("type_middle_screen"),
                _("type_small_screen"),
                _("type_none_screen"),
                _("type_custom_apk"),
            ],
            command=self.on_apk_type_change,
            height=30,
            fg_color="#3498db",
            selected_color="#27ae60",
            unselected_color="gray",
        )
        self.apk_type_seg.grid(row=11, column=0, padx=20, pady=5, sticky="ew")
        self.apk_type_seg.set(_("type_large_screen"))

        self.build_apk_btn = ctk.CTkButton(
            self.sidebar_frame,
            text=_("btn_build"),
            fg_color="#d35400",
            hover_color="#e67e22",
            command=self.build_apk,
        )
        self.build_apk_btn.grid(row=13, column=0, padx=20, pady=10)

        # 语言选择
        self.lang_var = ctk.StringVar(value="English")
        self.lang_menu = ctk.CTkOptionMenu(
            self.sidebar_frame,
            variable=self.lang_var,
            values=["中文", "English"],
            command=self.on_language_change,
        )
        self.lang_menu.grid(row=101, column=0, padx=20, pady=8)

    def on_language_change(self, selection):
        lang_code = "zh" if selection == "中文" else "en"
        if i18n.load_language(lang_code):
            self.refresh_ui_texts()

    def _init_main_area(self) -> None:
        """初始化主内容区 (使用 SegmentedButton 模拟 Tab)"""
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.tab_names = {
            "log": _("msg_tab_log"),
            "config": _("msg_tab_config"),
            "build": _("msg_tab_build"),
            "led": _("msg_tab_led"),
            "terminal": _("msg_tab_apk_config"),
        }

        self.tab_selector = ctk.CTkSegmentedButton(
            self.main_frame,
            values=list(self.tab_names.values()),
            variable=self.selected_tab,
            command=self._on_tab_switch,
            height=32,
            width=100,
            corner_radius=8,
            font=ctk.CTkFont(size=13),
            selected_color="#3498db",
            selected_hover_color="#2980b9",
            unselected_color="green",
            unselected_hover_color="gray",
        )
        self.tab_selector.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")

        self.content_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.content_container.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.content_container.grid_rowconfigure(0, weight=1)
        self.content_container.grid_columnconfigure(0, weight=1)

        self._create_tab_frames()

        if self.tab_names:
            first_tab_key = list(self.tab_names.keys())[0]
            self._show_tab(first_tab_key)

    def _create_tab_frames(self):
        from .tabs import (
            create_log_tab,
            create_config_tab,
            create_build_tab,
            create_led_tab,
            create_terminal_tab,
        )

        self.tab_frames["log"] = create_log_tab(self, self.content_container)
        self.tab_frames["config"] = create_config_tab(self, self.content_container)
        self.tab_frames["build"] = create_build_tab(self, self.content_container)
        self.tab_frames["led"] = create_led_tab(self, self.content_container)
        self.tab_frames["terminal"] = create_terminal_tab(self, self.content_container)

        for frame in self.tab_frames.values():
            frame.grid(row=0, column=0, sticky="nsew")

    def _on_tab_switch(self, value):
        target_key = None
        for key, display_text in self.tab_names.items():
            if display_text == value:
                target_key = key
                break
        if target_key:
            self._show_tab(target_key)

    def _show_tab(self, tab_key):
        for key, frame in self.tab_frames.items():
            frame.grid_remove()

        if tab_key in self.tab_frames:
            self.tab_frames[tab_key].grid()
            display_text = self.tab_names.get(tab_key, "")
            self.selected_tab.set(display_text)

    def ask_model_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title(_("model_title"))
        dialog.geometry("300x150")
        dialog.transient(self)
        dialog.grab_set()

        self.label_device_model = ctk.CTkLabel(
            dialog, text=_("label_device_model"), font=("Microsoft YaHei", 14)
        )
        self.label_device_model.pack(pady=15)

        self.entry = ctk.CTkEntry(
            dialog, width=200, placeholder_text=_("placeholder_model_input")
        )
        self.entry.pack(pady=10)
        self.entry.focus_set()

        result = {"value": None}

        def submit():
            val = self.entry.get().strip()
            result["value"] = val
            dialog.destroy()

        def cancel():
            result["value"] = None
            dialog.destroy()

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)

        self.msg_btn_cancel = ctk.CTkButton(
            btn_frame, text=_("msg_btn_cancel"), width=80, command=cancel
        )
        self.msg_btn_cancel.pack(side="left", padx=10)
        self.msg_btn_confirm = ctk.CTkButton(
            btn_frame, text=_("msg_btn_confirm"), width=80, command=submit
        )
        self.msg_btn_confirm.pack(side="right", padx=10)

        dialog.update_idletasks()
        w, h = dialog.winfo_width(), dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (w // 2)
        y = (dialog.winfo_screenheight() // 2) - (h // 2)
        dialog.geometry(f"{w}x{h}+{x}+{y}")

        dialog.bind("<Return>", lambda event: submit())
        self.wait_window(dialog)
        return result["value"]

    def refresh_ui_texts(self):
        current_lang = i18n.current_lang
        self._safe_refresh_config_view()
        new_tab_names = {
            "log": _("msg_tab_log"),
            "config": _("msg_tab_config"),
            "build": _("msg_tab_build"),
            "led": _("msg_tab_led"),
            "terminal": _("msg_tab_apk_config"),
        }

        current_display = self.selected_tab.get()
        current_key = None
        for k, v in self.tab_names.items():
            if v == current_display:
                current_key = k
                break

        self.tab_names = new_tab_names

        new_values = [
            _("type_large_screen"),
            _("type_middle_screen"),
            _("type_small_screen"),
            _("type_none_screen"),
            _("type_custom_apk"),
        ]
        self._filter_terminal_folders()
        self.apk_type_seg.configure(values=new_values)

        if self.current_apk_type == "大屏":
            self.apk_type_seg.set(_("type_large_screen"))
        elif self.current_apk_type == "中屏":
            self.apk_type_seg.set(_("type_middle_screen"))
        elif self.current_apk_type == "小屏":
            self.apk_type_seg.set(_("type_small_screen"))
        elif self.current_apk_type == "无屏":
            self.apk_type_seg.set(_("type_none_screen"))
        else:
            self.apk_type_seg.set(_("type_custom_apk"))

        self.tab_selector.configure(values=list(self.tab_names.values()))
        if current_key:
            self._show_tab(current_key)

        self.update_option_menus_on_language_change()

        if hasattr(self, "opt_env"):
            self.opt_env.configure(command=None)
            new_env_options = []
            for key in ENV_CONF.keys():
                display_name = ENV_DISPLAY_NAMES.get(key, {}).get(current_lang, key)
                new_env_options.append(display_name)
            self.opt_env.configure(values=new_env_options)

            matched_env_id = "overseas"
            if PATH_SLCLIENT_JSON.exists():
                try:
                    with open(PATH_SLCLIENT_JSON, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    profile_data = data.get("profile", {})
                    config_dns = profile_data.get("dns")
                    config_context = profile_data.get("context")

                    for env_id, env_config in ENV_CONF.items():
                        env_ip_address = env_config.get("ip_address")
                        env_context = env_config.get("context")
                        if (
                            config_context
                            and env_context
                            and config_context == env_context
                        ):
                            config_dns_str = (
                                ",".join(config_dns)
                                if isinstance(config_dns, list)
                                else str(config_dns)
                            )
                            dns_list = [
                                addr.strip() for addr in env_ip_address.split(",")
                            ]
                            if any(
                                config_dns_str in dns_addr or dns_addr in config_dns_str
                                for dns_addr in dns_list
                            ):
                                matched_env_id = env_id
                                break
                except:
                    pass

            target_display_name = ENV_DISPLAY_NAMES.get(matched_env_id, {}).get(
                current_lang, matched_env_id
            )
            self.opt_env.set(target_display_name)
            self.opt_env.configure(command=self._on_env_selected)

        self.title(_("app_title"))
        self.logo_label.configure(text=_("sidebar_logo"))
        self.device_label.configure(text=_("lbl_device"))
        self.refresh_btn.configure(text=_("btn_refresh"))
        self.start_btn.configure(
            text=(
                _("btn_start_listen") if not self.is_listening else _("btn_stop_listen")
            )
        )
        self.mode_label.configure(text=_("lbl_mode"))
        self.clear_log_btn.configure(text=_("clear_log"))
        self.apk_select_label.configure(text=_("lbl_apk_type"))
        self.build_apk_btn.configure(text=_("btn_build"))
        self.env_custom.configure(text=_("env_custom"))
        self.decompile_apk_btn.configure(text=_("btn_decompile"))
        self.apk_title_label.configure(text=_("msg_terminal_config_title"))
        self.scroll_frame.configure(label_text=i18n.get("msg_config_list_title"))
        self.use_btn.configure(text=_("use_btn"))
        self.lbl_title.configure(text=_("msg_card_apk_properties"))
        self.lbl_input_title.configure(text=_("msg_tab_input"))
        self.title_led_mode.configure(text=_("msg_card_input"))
        self.lbl_other.configure(text=_("msg_feature_dev"))
        self.frame_led_color.title_label.configure(text=_("msg_card_other"))
        self.frame_env.title_label.configure(text=_("msg_card_env"))
        self.frame_sound.title_label.configure(text=_("msg_card_sound"))
        self.frame_map.title_label.configure(text=_("msg_card_map"))
        self.frame_other.title_label.configure(text=_("msg_card_other"))
        self.lbl_server_node.configure(text=_("lbl_server_node"))
        self.lbl_login_type.configure(text=_("lbl_login_type"))
        self.lbl_map_source.configure(text=_("lbl_map_source"))
        self.lbl_ptt_press.configure(text=_("lbl_ptt_press"))
        self.lbl_ptt_release.configure(text=_("lbl_ptt_release"))
        self.lbl_sos_key.configure(text=_("lbl_sos_key"))
        self.btn_save_config.configure(text=_("btn_save_config"))
        self.btn_save_custom.configure(text=_("msg_save_btn"))
        self.codec.configure(text=_("codec"))
        self.audio.configure(text=_("audio"))
        self.play_channel.configure(text=_("play_channel"))
        self.rec_channel.configure(text=_("rec_channel"))

    def update_option_menus_on_language_change(self):
        self._is_updating_language = True

        current_lang = i18n.current_lang

        if hasattr(self, "opt_login_type"):
            login_type_display_names = [
                v[current_lang] for v in LOGIN_TYPE_MAPPING.values()
            ]
            self.opt_login_type.configure(values=login_type_display_names)
            current_login_mode_key = "account"
            if PATH_SLCLIENT_JSON.exists():
                try:
                    with open(PATH_SLCLIENT_JSON, "r", encoding="utf-8") as f:
                        slclient_data = json.load(f)
                    current_login_mode_key = slclient_data.get("profile", {}).get(
                        "login_mode", "account"
                    )
                except:
                    pass
            new_display_name = LOGIN_TYPE_MAPPING.get(current_login_mode_key, {}).get(
                current_lang, "Account Login"
            )
            self.opt_login_type.set(new_display_name)

        if hasattr(self, "opt_map_source"):
            map_source_display_names = [
                v["display_name"][current_lang] for v in MAP_CONFIG_TEMPLATES.values()
            ]
            self.opt_map_source.configure(values=map_source_display_names)
            current_map_source_key = "Google"
            if PATH_SLCLIENT_JSON.exists():
                try:
                    with open(PATH_SLCLIENT_JSON, "r", encoding="utf-8") as f:
                        slclient_data = json.load(f)
                    current_map_source_key = slclient_data.get("lbs", {}).get(
                        "map_type", "Google"
                    )
                    map_coor = get_json_field(PATH_SLCLIENT_JSON, LBS_COOR_PATH)
                    if map_coor == "wgs84" and current_map_source_key == "baidu":
                        current_map_source_key = "baidu_oversea"
                    elif map_coor == "bd09ll" and current_map_source_key == "baidu":
                        current_map_source_key = "baidu_domestic"
                except:
                    pass
            new_display_name = (
                MAP_CONFIG_TEMPLATES.get(current_map_source_key, {})
                .get("display_name", {})
                .get(current_lang)
            )
            self.opt_map_source.set(new_display_name)
        self._is_updating_language = False

    def initial_env_check(self) -> None:
        if not self.env_checker.check_all(show_dialog=True):
            self.device_var.set("等待环境修复")
            self.device_menu.configure(values=[])
            self.start_btn.configure(state="disabled")
        else:
            self.start_btn.configure(state="normal")
            self.refresh_devices()
            self.after(100, self.refresh_config_view)

    def on_env_retry(self) -> None:
        self.append_log("\n[Info] Detecting environment...\n")
        if self.env_checker.check_all(show_dialog=False):
            self.append_log("[OK] Environmental check passed!\n")
            self.start_btn.configure(state="normal")
            self.refresh_devices()
            self.after(100, self.refresh_config_view)
        else:
            self.env_checker.check_all(show_dialog=True)

    def refresh_devices(self) -> None:
        if not self.winfo_exists():
            return
        if not is_adb_installed():
            self.env_checker.check_all(show_dialog=True)
            return
        try:
            out = subprocess.check_output(
                ["adb", "devices"],
                text=True,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            devs = [
                line.split()[0]
                for line in out.splitlines()
                if "\tdevice" in line and not line.startswith("List")
            ]
            current_val = self.device_var.get()
            self.device_menu.configure(values=devs if devs else ["no devices"])
            if devs:
                if current_val not in devs or current_val in [
                    "未连接",
                    "未检测到设备",
                    "检测中...",
                    "等待环境修复",
                ]:
                    self.device_var.set(devs[0])
                    self.current_device = devs[0]
                else:
                    self.current_device = current_val
            else:
                self.device_var.set("no devices")
                self.current_device = ""
        except:
            if self.winfo_exists():
                self.device_menu.configure(values=["ADB Error"])
            self.device_var.set("ADB Error")

    def on_device_change(self, selection: str) -> None:
        if selection not in ["未检测到设备", "ADB 错误"]:
            self.current_device = selection

    def toggle_listen(self) -> None:
        if not self.winfo_exists():
            return
        if not is_adb_installed():
            messagebox.showerror("ERR", "ADB 环境丢失！")
            self.env_checker.check_all(show_dialog=True)
            return
        if not self.current_device or self.current_device in [
            "未检测到设备",
            "ADB 错误",
            "未连接",
        ]:
            messagebox.showerror("ERR", "请先选择有效的 ADB 设备！")
            self.refresh_devices()
            return

        if self.is_listening:
            if self.backend:
                self.backend.stop_capture()
            self.is_listening = False
            self.start_btn.configure(text=_("btn_start_listen"), fg_color="green")
            self.mode_menu.configure(state="normal")
            self.device_menu.configure(state="normal")
        else:
            mode = self.mode_var.get()
            self.backend = SmartKeyBackend(
                self.current_device,
                log_callback=self.append_log,
                config_callback=self.refresh_config_view,
            )
            if not self.backend.load_config():
                if not messagebox.askyesno(
                    "警告", "读取配置失败，是否使用空配置继续？"
                ):
                    return
            self.is_listening = True
            self.start_btn.configure(text=_("btn_stop_listen"), fg_color="red")
            self.mode_menu.configure(state="disabled")
            self.device_menu.configure(state="disabled")
            self.backend.start_capture(mode)

    def append_log(self, text: str) -> None:
        self.log_queue.put(text)

    def process_log_queue(self) -> None:
        if not self.winfo_exists():
            return
        try:
            while True:
                try:
                    text = self.log_queue.get_nowait()
                    if hasattr(self, "log_textbox") and self.log_textbox.winfo_exists():
                        self.log_textbox.insert("end", text)
                        self.log_textbox.see("end")
                except queue.Empty:
                    break
        except:
            pass
        self.after(50, self.process_log_queue)

    def clear_log(self) -> None:
        if hasattr(self, "log_textbox") and self.log_textbox.winfo_exists():
            self.log_textbox.delete("0.0", "end")

    def refresh_config_view(self) -> None:
        if not self.winfo_exists():
            return
        self.after(0, self._safe_refresh_config_view)

    def _safe_refresh_config_view(self) -> None:
        if not self.winfo_exists():
            return
        try:
            for widget in self.scroll_frame.winfo_children():
                try:
                    widget.destroy()
                except:
                    pass
            data = {}
            if self.backend and hasattr(self.backend, "data") and self.backend.data:
                data = self.backend.data
            else:
                load_path = PATH_INPUT_JSON_SRC
                if not os.path.exists(load_path):
                    load_path = PATH_INPUT_JSON_DEFAULT

                if os.path.exists(load_path):
                    try:
                        with open(load_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                    except:
                        pass

            headers = [
                i18n.get("msg_header_key_name"),
                i18n.get("msg_header_event"),
                i18n.get("msg_header_vkey"),
                i18n.get("msg_header_action"),
                i18n.get("msg_header_cmd"),
            ]
            for i, h in enumerate(headers):
                ctk.CTkLabel(
                    self.scroll_frame,
                    text=h,
                    font=ctk.CTkFont(weight="bold", size=13),
                    anchor="w",
                ).grid(row=0, column=i, padx=15, pady=15, sticky="w")

            formatted_items = get_formatted_key_configs(data)
            row_idx = 1

            for name, event_str, key_val, action_str, cmd_str in formatted_items:
                if not self.winfo_exists():
                    return

                ctk.CTkLabel(
                    self.scroll_frame,
                    text=name,
                    anchor="w",
                    font=ctk.CTkFont(family="Consolas", size=12),
                ).grid(row=row_idx, column=0, padx=15, pady=8, sticky="w")
                ctk.CTkLabel(
                    self.scroll_frame, text=event_str, anchor="w", text_color="#7f8c8d"
                ).grid(row=row_idx, column=1, padx=15, pady=8, sticky="w")
                ctk.CTkLabel(
                    self.scroll_frame,
                    text=str(key_val),
                    anchor="w",
                    font=ctk.CTkFont(weight="bold"),
                    text_color="#e67e22",
                ).grid(row=row_idx, column=2, padx=15, pady=8, sticky="w")
                ctk.CTkLabel(
                    self.scroll_frame,
                    text=action_str,
                    anchor="w",
                    text_color="#3498db",
                    font=ctk.CTkFont(size=12),
                ).grid(row=row_idx, column=3, padx=15, pady=8, sticky="w")
                ctk.CTkLabel(
                    self.scroll_frame,
                    text=cmd_str,
                    anchor="w",
                    text_color="#95a5a6",
                    font=ctk.CTkFont(size=12),
                ).grid(row=row_idx, column=4, padx=15, pady=8, sticky="w")
                row_idx += 1
        except Exception as e:
            if self.winfo_exists():
                ctk.CTkLabel(
                    self.scroll_frame,
                    text=i18n.get("msg_load_failed") + f": {str(e)}",
                    text_color="#c0392b",
                ).grid(row=0, column=0, pady=20)

    def on_closing(self) -> None:
        if self.backend and self.is_listening:
            self.backend.stop_capture()
        time.sleep(0.5)
        self.destroy()

    def on_login_type_change(self, selected_val: str) -> None:
        self._update_preview("login_type", selected_val)
        if update_slclient_login_type(selected_val):
            self.append_log(f"[OK] The login method changed to: {selected_val}\n")
        else:
            self.append_log(
                f"[Error] Failed to update the login mode: {selected_val}\n"
            )

    def on_apk_type_change(self, value: str) -> None:
        self.current_apk_type = value
        self.append_log(f"[Info] APK type switched to: {value}\n")

    def show_custom_message(self, title, message):
        win = ctk.CTkToplevel(self)
        win.title(title)
        win.geometry("320x160")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        win.grab_set()
        text_font = ctk.CTkFont(size=13, weight="bold")
        ctk.CTkLabel(win, text=message, font=text_font, wraplength=280).pack(pady=10)
        ctk.CTkButton(
            win, text=_("btn_ok"), font=text_font, width=80, command=win.destroy
        ).pack(pady=10)
        win.update_idletasks()
        w, h = win.winfo_width(), win.winfo_height()
        x, y = (win.winfo_screenwidth() // 2) - (w // 2), (
            win.winfo_screenheight() // 2
        ) - (h // 2)
        win.geometry(f"{w}x{h}+{x}+{y}")
        win.lift()
        win.focus_force()
        win.bind("<Return>", lambda e: win.destroy())

    def _on_search_change(self, *args):
        if hasattr(self, "_search_after_id") and self._search_after_id:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(50, self._filter_terminal_folders)

    def _filter_terminal_folders(self):
        search_term = self.terminal_search_var.get().lower()
        self.current_displayed_folders = (
            [f for f in self.terminal_all_folders if search_term in f.name.lower()]
            if search_term
            else self.terminal_all_folders.copy()
        )
        from .tabs import render_terminal_folders

        render_terminal_folders(self, self.current_displayed_folders)
        self.after_idle(
            lambda: self.terminal_scroll_frame._parent_canvas.yview_moveto(0)
        )

    def _use_terminal_config(self, folder_path):
        if not PATH_SLCLIENT_JSON.exists():
            messagebox.showerror("ERROR", f"Please unzip apk first")
            return False
        self.copy_terminal_files(folder_path)
        self.load_all_configs()
        self.load_and_echo_config_after_unzip()
        self.is_import = True

    def copy_terminal_files(self, folder_path):
        source_dir = Path(folder_path)
        try:
            copy_terminal_configs_from_folder(source_dir)
            self.append_log(f"[Success] Imported {folder_path.name} successfully\n")
            self.show_custom_message(
                "Success", f"Imported \n\n{folder_path.name}\n\nsuccessfully!"
            )
        except Exception as e:
            self.append_log(f"[Error]: {e}\n")

    def _on_save_manual_keys(self):
        val_press, val_release, val_sos = (
            self.entry_ptt_press.get().strip(),
            self.entry_ptt_release.get().strip(),
            self.entry_sos.get().strip(),
        )
        has_ptt, has_sos = bool(val_press and val_release), bool(val_sos)
        if not has_ptt and not has_sos:
            self.lbl_env_info.configure(
                text="❌ 错误：请至少填写 PTT (按下 + 抬起) 或 SOS 其中一项！",
                text_color="#c0392b",
                font=ctk.CTkFont(size=12, weight="bold"),
            )
            return
        if (val_press and not val_release) or (not val_press and val_release):
            self.lbl_env_info.configure(
                text="❌ 错误：请输入 PTT 的按下和抬起 Action！",
                text_color="#c0392b",
                font=ctk.CTkFont(size=12, weight="bold"),
            )
            return
        try:
            result = save_manual_keys_to_json(val_press, val_release, val_sos)
            if result:
                if has_ptt:
                    self.entry_ptt_press.delete(0, "end")
                    self.entry_ptt_release.delete(0, "end")
                if has_sos:
                    self.entry_sos.delete(0, "end")

                msg_lines = ["✅ Configuration is saved"]
                if has_ptt:
                    msg_lines.append(f"   🟢 PTT Key: {result['ptt_key']}")
                if has_sos:
                    msg_lines.append(f"   🔴 SOS Key: {result['sos_key']}")
                final_msg = "\n".join(msg_lines)

                self.append_log(f"[Manual Save] {final_msg}\n")
                self.show_custom_message("Successfully", final_msg)
                self._safe_refresh_config_view()
        except Exception as e:
            self.append_log(f"[Error] _on_save_manual_keys: {e}\n")
            messagebox.showerror("ERROR", f"❌ ERROR：{str(e)}")

    def _save_profile_changes(self):
        if not PATH_SLCLIENT_JSON.exists():
            messagebox.showerror("ERROR", f"Please unzip apk first")
            return False
        new_ip, new_context, upgrade_url = (
            self.entry_custom_ip.get().strip(),
            self.entry_custom_context.get().strip(),
            self.entry_custom_upgrade.get().strip(),
        )
        if not new_ip or not new_context:
            messagebox.showwarning("Error", "IP and Context must be entered！")
            return
        try:
            update_slclient_profile(
                dns=[new_ip],
                context=new_context,
                upgrade_url=upgrade_url if upgrade_url else None,
            )
            self.show_custom_message("Successfully", "saved successfully")
        except Exception as e:
            messagebox.showerror("Error", f"❌ 保存失败: {str(e)}")

    def _sync_codec_to_json(self, selected_codec: str) -> None:
        if not PATH_SLCLIENT_JSON.exists():
            return
        try:
            if slclient_set_sound_codec(selected_codec):
                self.append_log(f"[OK] Voice coding switched: {selected_codec}\n")
        except Exception:
            pass

    def _sync_soundsystem_to_json(self, selected_codec: str) -> None:
        if not PATH_SLCLIENT_JSON.exists():
            return
        try:
            if slclient_set_dsp_provider(selected_codec):
                self.append_log(f"[OK] Audio system switched: {selected_codec}\n")
        except Exception:
            pass

    def _sync_play_to_json(self, selected_codec: str) -> None:
        if not PATH_SLCLIENT_JSON.exists():
            return
        try:
            if slclient_set_play_stream(selected_codec):
                self.append_log(f"[OK] Playback channel switched: {selected_codec}\n")
        except Exception:
            pass

    def _sync_record_to_json(self, selected_codec: str) -> None:
        if not PATH_SLCLIENT_JSON.exists():
            return
        try:
            if slclient_set_record_stream(selected_codec):
                self.append_log(f"[OK] Recording channels switched: {selected_codec}\n")
        except Exception:
            pass

    def _sync_tone_enabled_to_json(self, is_enabled: bool) -> None:
        if not PATH_SLCLIENT_JSON.exists():
            return
        try:
            json_value = bool(is_enabled)
            if slclient_set_tone_enabled(json_value):
                self.append_log(
                    f"[OK] Tone sound effects have been {'Enabled' if json_value else 'Disabled'}\n"
                )
        except Exception:
            pass

    def on_map_source_change(self, selected_display_name: str) -> None:
        if not PATH_SLCLIENT_JSON.exists():
            messagebox.showerror("ERROR", f"Please unzip apk first")
            return
        selected_key = next(
            (
                k
                for k, v in MAP_CONFIG_TEMPLATES.items()
                if v["display_name"]["zh"] == selected_display_name
                or v["display_name"]["en"] == selected_display_name
            ),
            None,
        )
        if selected_key and update_slclient_map_type(selected_key):
            self._update_preview("map_source", selected_display_name)
            self.append_log(
                f"[OK] Map source has been updated to: {selected_display_name}\n"
            )
        else:
            messagebox.showwarning("警告", "配置更新失败或无效的地图源")

    def modify_manifest(self, is_enabled: bool):
        modify_manifest(is_enabled, self.append_log)

    def _sync_tts_enabled_to_json(self, is_enabled: bool) -> None:
        if not PATH_SLCLIENT_JSON.exists():
            return
        try:
            json_value = bool(is_enabled)
            if slclient_set_tts_enabled(json_value):
                self.append_log(f"[OK] TTS {'Enabled' if json_value else 'Disabled'}\n")
        except Exception:
            pass

    def _on_env_selected(self, selected_name):
        current_lang = i18n.current_lang
        selected_key = next(
            (
                k
                for k, names in ENV_DISPLAY_NAMES.items()
                if names.get(current_lang) == selected_name
            ),
            None,
        )
        if selected_key:
            config = ENV_CONF.get(selected_key, {})
            ip_address, context, upgrade_url = (
                config.get("ip_address", ""),
                config.get("context", ""),
                config.get("upgrade_url", ""),
            )
            if not ip_address or not context or not upgrade_url:
                return
            try:
                update_slclient_profile(
                    dns=ip_address.split(","),
                    context=context,
                    upgrade_url=upgrade_url,
                    env_key=selected_key,
                )
            except Exception:
                pass

    def _update_preview(self, key, value):
        self.build_config[key] = value

    def load_all_configs(self) -> None:
        try:
            login_mode_val, map_source_val, current_env_key = (
                "account",
                "Google",
                "overseas",
            )
            tts_enabled_val, tone_enabled_val, launcher_enabled_val = False, True, False
            codec_enabled_val, audio_enabled_val, play_enabled_val, rec_enabled_val = (
                "amrnb",
                "default",
                "music",
                "recognition",
            )
            if PATH_SLCLIENT_JSON.exists():
                slclient_data = load_slclient_json()
                p = slclient_data.get("profile", {})
                current_env_key = p.get("env_key", current_env_key)
                login_mode_val = p.get("login_mode", login_mode_val)
                map_source_val = slclient_data.get("lbs", {}).get(
                    "map_type", map_source_val
                )
                tts_enabled_val = slclient_data.get("tts", {}).get("enabled", False)
                tone_enabled_val = slclient_data.get("sound", {}).get(
                    "tone_enabled", True
                )
                codec_enabled_val = slclient_data.get("sound", {}).get(
                    "codec", codec_enabled_val
                )
                audio_enabled_val = slclient_data.get("dsp", {}).get(
                    "provider", audio_enabled_val
                )
                play_enabled_val = slclient_data.get("dsp", {}).get(
                    "play_stream", play_enabled_val
                )
                rec_enabled_val = slclient_data.get("dsp", {}).get(
                    "record_stream", rec_enabled_val
                )
            self.map_coor = get_json_field(PATH_SLCLIENT_JSON, LBS_COOR_PATH)
            if self.map_coor == "wgs84" and map_source_val == "baidu":
                map_source_val = "baidu_oversea"
            elif self.map_coor == "bd09ll" and map_source_val == "baidu":
                map_source_val = "baidu_domestic"
            ui_env_val = ENV_DISPLAY_NAMES.get(current_env_key, {}).get(
                i18n.current_lang, "海外环境"
            )
            ui_login_val = LOGIN_TYPE_MAPPING.get(login_mode_val, {}).get(
                i18n.current_lang, "账号登录"
            )
            ui_map_val = (
                MAP_CONFIG_TEMPLATES.get(map_source_val, {})
                .get("display_name", {})
                .get(i18n.current_lang)
            )
            if hasattr(self, "opt_env"):
                self.opt_env.set(ui_env_val)
                self._update_preview("env", ui_env_val)
            self.opt_login_type.set(ui_login_val)
            self._update_preview("login_type", ui_login_val)
            if hasattr(self, "opt_map_source"):
                self.opt_map_source.set(ui_map_val)
                self._update_preview("map_source", ui_map_val)
            if hasattr(self, "switch_sfx"):
                (
                    self.switch_sfx.select()
                    if tts_enabled_val
                    else self.switch_sfx.deselect()
                )
            if hasattr(self, "switch_tone_sfx"):
                (
                    self.switch_tone_sfx.select()
                    if tone_enabled_val
                    else self.switch_tone_sfx.deselect()
                )
            if hasattr(self, "opt_rec"):
                self.opt_rec.set(rec_enabled_val)
            if hasattr(self, "opt_play"):
                self.opt_play.set(play_enabled_val)
            if hasattr(self, "opt_audio"):
                self.opt_audio.set(audio_enabled_val)
            if hasattr(self, "opt_codec"):
                self.opt_codec.set(codec_enabled_val)
        except Exception as e:
            self.append_log(f"[Warning] Failed to load configs, using default: {e}\n")

    def decompile_apk(self, output_dir: str = "app_out") -> None:
        if hasattr(self, "_is_decompiling") and self._is_decompiling:
            return
        self._is_decompiling = True

        def task():
            try:
                apk_type = self.apk_type_seg.get()
                self.current_apk_type = apk_type
                if apk_type in ["大屏", "Large"]:
                    apk_path = APK_LARGE
                elif apk_type in ["中屏", "Medium"]:
                    apk_path = APK_LARGE
                elif apk_type in ["小屏", "Small"]:
                    apk_path = APK_SMALL
                elif apk_type in ["无屏", "Screenless"]:
                    apk_path = APK_SCREENLESS
                elif apk_type in ["自定义", "Custom"]:
                    apk_path = filedialog.askopenfilename(
                        title="APK File", filetypes=[("APK File", "*.apk")]
                    )
                    if not apk_path:
                        return False
                else:
                    return False
                if os.path.exists(output_dir):
                    shutil.rmtree(output_dir, ignore_errors=True)
                self.append_log("Extracting...\n")
                if (
                    run_with_live_output(
                        self,
                        [
                            "java",
                            "-jar",
                            str(APKTOOL_JAR),
                            "d",
                            apk_path,
                            "-s",
                            "-o",
                            output_dir,
                        ],
                    )
                    == 0
                ):
                    if apk_type in ["中屏", "Medium"]:
                        set_json_field(
                            PATH_SLCLIENT_JSON, ["ui", "launcherModule"], "middle"
                        )
                        self.append_log(f"[Success] Auto-config: ui.launcherModule alread set\n")
                    self.load_and_echo_config_after_unzip()
                    messagebox.showinfo("Success", "Decompile Apk Successful!")
                    self.after(500, self.load_all_configs)
            except Exception as e:
                self.append_log(f"\n[ERROR]: {str(e)}\n")
            finally:
                self._is_decompiling = False

        threading.Thread(target=task, daemon=True).start()

    def build_apk(self) -> None:
        if not PATH_SLCLIENT_JSON.exists():
            messagebox.showerror("ERROR", f"Please unzip apk first")
            return False
        self.build_apk_btn.configure(state="disabled")

        def task():
            try:
                if not self.apply_selected_config_to_slclient():
                    return False
                model = self.ask_model_dialog()
                if model is None:
                    raise Exception("User cancels packaging")
                self.current_device_model = model
                if model:
                    set_json_field(PATH_SLCLIENT_JSON, ["device", "name"], model)

                if not self.is_import:
                    # 确定 input.json 的源路径
                    json_src = PATH_INPUT_JSON_SRC
                    if not json_src.exists():
                        json_src = PATH_INPUT_JSON_DEFAULT

                    if json_src.exists():
                        try:
                            PATH_INPUT_JSON_DST.parent.mkdir(
                                parents=True, exist_ok=True
                            )
                            shutil.copy2(json_src, PATH_INPUT_JSON_DST)
                            self.append_log(
                                f"[Info] Sync config file: {json_src.name} -> {PATH_INPUT_JSON_DST}\n"
                            )
                        except Exception as e:
                            self.append_log(f"[Error] Failed to sync input.json: {e}\n")

                if (
                    run_with_live_output(
                        self,
                        [
                            "java",
                            "-jar",
                            str(APKTOOL_JAR),
                            "b",
                            TEMP_DIR,
                            "-o",
                            "app-unsigned-unaligned.apk",
                        ],
                    )
                    != 0
                ):
                    raise Exception("APK packaging failed")
                if (
                    run_with_live_output(
                        self,
                        [
                            str(ZIPALIGN_EXE),
                            "-v",
                            "-p",
                            "4",
                            "app-unsigned-unaligned.apk",
                            "app-unsigned.apk",
                        ],
                    )
                    != 0
                ):
                    raise Exception("APK alignment failed")
                safe_remove(self, "app-unsigned-unaligned.apk")
                json_val = get_json_field(PATH_SLCLIENT_JSON, LAUNCHER_MODULE_PATH)
                ks_info = KEYSTORE_CONFIG.get(
                    json_val if json_val in KEYSTORE_CONFIG else "large",
                    KEYSTORE_CONFIG["large"],
                )
                date_str = time.strftime("%Y_%m_%d")
                (WORKSPACE_PATH / date_str).mkdir(exist_ok=True)
                final_name = (
                    self.build_newname(PATH_YML)
                    if os.path.exists(PATH_YML)
                    else f"app_{self.apk_type_seg.get()}_{date_str}.apk"
                )
                output_apk_path = WORKSPACE_PATH / date_str / final_name
                if (
                    run_with_live_output(
                        self,
                        [
                            str(APKSIGNER_BAT),
                            "sign",
                            "--ks",
                            str(ks_info["path"]),
                            "--ks-pass",
                            f"pass:{ks_info['password']}",
                            "--out",
                            str(output_apk_path),
                            "app-unsigned.apk",
                        ],
                    )
                    != 0
                ):
                    raise Exception("APK signing failed")
                safe_remove(self, "app-unsigned.apk")
                safe_remove(self, "input.json")
                shutil.rmtree(TEMP_PATH, ignore_errors=True)
                self.load_all_configs()
                self.show_custom_message("SUCCESS", f"APK Safe: \n{output_apk_path}")
            except Exception as e:
                messagebox.showerror("ERROR", f"[FAIL] ❌ {str(e)}")
            finally:
                self.build_apk_btn.configure(state="normal", text=_("btn_build"))
                self.is_import = False

        threading.Thread(target=task, daemon=True).start()

    def build_newname(self, yml_path: Path) -> str:
        try:
            version_str = get_version_info(yml_path)[1]
            device_model = str(getattr(self, "current_device_model", ""))
            new_version_name = (
                re.sub(r"(POCSTARS_)", r"\g<1>" + device_model + "_", version_str)
                if device_model
                else version_str
            )
            launcher_module = get_json_field(PATH_SLCLIENT_JSON, LAUNCHER_MODULE_PATH)
            prefix = (
                "RSAPP_"
                if get_json_field(PATH_SLCLIENT_JSON, RECORDER_ENABLE_PATH)
                else (
                    "ASAPP_"
                    if launcher_module is None
                    else {"large": "BSAPP_", "middle": "MSAPP_", "small": "SSAPP_"}.get(
                        launcher_module, "NSAPP_"
                    )
                )
            )
            return f"{prefix}{new_version_name}.apk"
        except:
            return f"APP_test_{datetime.now().strftime('%Y%m%d%H%M%S')}.apk"

    def _get_slclient_preview_data(self) -> dict:
        """
        收集所有模块的当前配置值。
        不依赖 build_config，直接从 GUI 控件读取以确保是最新值。
        """
        data = {}
        current_lang = i18n.current_lang

        # --- A. Profile (环境与登录) ---
        # 1. 环境
        selected_env_display = (
            self.opt_env.get() if hasattr(self, "opt_env") else "海外环境"
        )
        env_key = "overseas"
        # 反查环境键名
        for key, names in ENV_DISPLAY_NAMES.items():
            if names.get(current_lang) == selected_env_display:
                env_key = key
                break

        if PATH_SLCLIENT_JSON.exists():
            try:
                with open(PATH_SLCLIENT_JSON, "r", encoding="utf-8") as f:
                    slclient_data = json.load(f)

                profile_data = slclient_data.get("profile", {})
                data["env_ip"] = profile_data.get("dns", "Default")
                data["context"] = profile_data.get("context", "pocstar")
                data["login_type"] = profile_data.get(
                    "login_type",
                    (
                        self.opt_login_type.get()
                        if hasattr(self, "opt_login_type")
                        else "account"
                    ),
                )
            except Exception as e:
                print(f"Error reading slclient.json: {e}")
                data["env_ip"] = "Default"
                data["context"] = "pocstar"
                data["login_type"] = (
                    self.opt_login_type.get()
                    if hasattr(self, "opt_login_type")
                    else "account"
                )
        else:
            data["env_ip"] = "Default"
            data["context"] = "pocstar"
            data["login_type"] = (
                self.opt_login_type.get()
                if hasattr(self, "opt_login_type")
                else "account"
            )

        # --- B. LBS (地图) ---
        data["map_source"] = (
            self.opt_map_source.get() if hasattr(self, "opt_map_source") else "Google"
        )

        # --- C. Sound & DSP ---
        data["codec"] = self.opt_codec.get() if hasattr(self, "opt_codec") else "amrnb"
        data["tone_enabled"] = (
            self.switch_tone_sfx.get() if hasattr(self, "switch_tone_sfx") else True
        )
        data["audio_provider"] = (
            self.opt_audio.get() if hasattr(self, "opt_audio") else "default"
        )
        data["play_channel"] = (
            self.opt_play.get() if hasattr(self, "opt_play") else "music"
        )
        data["rec_channel"] = (
            self.opt_rec.get() if hasattr(self, "opt_rec") else "recognition"
        )

        # --- D. TTS & Launcher ---
        data["tts_enabled"] = (
            self.switch_sfx.get() if hasattr(self, "switch_sfx") else False
        )
        data["launcher_home"] = (
            self.switch_launcher.get() if hasattr(self, "switch_launcher") else False
        )

        return data

    def apply_selected_config_to_slclient(self) -> bool:
        """
        打包时调用：弹窗确认当前 slclient 的内容。
        格式：键：值 (非 JSON)

        Returns:
            bool: True 表示用户确认，False 表示取消。
        """
        # 1. 获取数据
        raw_data = self._get_slclient_preview_data()

        lines = []

        # 环境信息
        ip_addresses = raw_data["env_ip"]
        if isinstance(ip_addresses, list):
            ip_formatted = "\n".join([f"  - {ip}" for ip in ip_addresses])
        else:
            ips = str(ip_addresses).split(",")
            ip_formatted = "\n".join([f"  - {ip.strip()}" for ip in ips])

        lines.append("-" * 30)

        # 检查IP地址是否在预定义环境中
        found_env = None
        for env_id, env_config in ENV_CONF.items():
            env_ip_address = env_config.get("ip_address", "")
            if isinstance(env_ip_address, list):
                env_ips = env_ip_address
            else:
                env_ips = [addr.strip() for addr in str(env_ip_address).split(",")]

            current_ips = (
                [addr.strip() for addr in str(raw_data["env_ip"]).split(",")]
                if not isinstance(raw_data["env_ip"], list)
                else raw_data["env_ip"]
            )

            if any(ip in env_ips for ip in current_ips):
                found_env = env_id
                break

        if found_env:
            lines.append(f"IP:  \n{ip_formatted}")
            lines.append(f"Context:  {raw_data['context']}")
        else:
            lines.append(f"IP:  \n{ip_formatted}")
            lines.append(f"Context:  {raw_data['context']}")

        lbl_login_type = _("lbl_login_type")
        lines.append(f"{lbl_login_type}:  {raw_data['login_type']}\n")
        lines.append("-" * 30)

        # 地图
        lbl_map_source = _("lbl_map_source")
        lines.append(f"{lbl_map_source}:  {raw_data['map_source']}\n")
        lines.append("-" * 30)

        # 声音
        lines.append(f"Tone:  {'True' if raw_data['tone_enabled'] else 'False'}\n")
        lines.append("-" * 30)
        lines.append(f"Codec:  {raw_data['codec']}")
        lines.append(f"audio:  {raw_data['audio_provider']}")
        lines.append(f"Play channel:  {raw_data['play_channel']}")
        lines.append(f"Rec channel:  {raw_data['rec_channel']}\n")
        lines.append("-" * 30)

        # 其他
        lines.append(f"TTS:  {'True' if raw_data['tts_enabled'] else 'False'}")
        lines.append(f"Launcher:  {'True' if raw_data['launcher_home'] else 'False'}")

        # 拼接最终文本
        message_text = "\n".join(lines)

        # 3. 创建弹窗
        win = ctk.CTkToplevel(self)
        win.title(_("confirm_config_text"))
        win.geometry("400x550")
        win.resizable(True, True)

        win.attributes("-topmost", True)
        win.grab_set()

        # ===== 字体统一 =====
        title_font = ctk.CTkFont(size=15, weight="bold")
        text_font = ctk.CTkFont(size=13)

        # ===== 标题 =====
        package_config_title = ctk.CTkLabel(
            win, text=_("package_config_title"), font=title_font
        )
        package_config_title.pack(pady=(15, 5))

        # ===== 内容 (使用 Textbox 显示文本行) =====
        text_frame = ctk.CTkFrame(win, fg_color="transparent")
        text_frame.pack(padx=20, pady=10, fill="both", expand=True)

        textbox = ctk.CTkTextbox(
            text_frame, font=text_font, wrap="word"
        )  # wrap="word" 自动换行
        textbox.pack(fill="both", expand=True)
        textbox.insert("0.0", message_text)
        textbox.configure(state="disabled")  # 只读

        # ===== 按钮 =====
        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(pady=10)

        result = {"confirmed": False}

        def on_ok():
            result["confirmed"] = True
            win.destroy()

        def on_cancel():
            result["confirmed"] = False
            win.destroy()

        # 取消按钮
        self.btn_dialog_cancel = ctk.CTkButton(
            btn_frame,
            text=_("cancel_button"),
            font=text_font,
            width=100,
            command=on_cancel,
            fg_color="gray",
        )
        self.btn_dialog_cancel.pack(side="left", padx=20)

        # 确认按钮
        self.btn_dialog_ok = ctk.CTkButton(
            btn_frame,
            text=_("confirm_button"),
            font=text_font,
            width=100,
            command=on_ok,
            fg_color="green",
        )
        self.btn_dialog_ok.pack(side="left", padx=20)

        win.lift()
        win.focus_force()
        win.after(10, lambda: win.attributes("-topmost", False))

        # 绑定按键
        win.bind("<Return>", lambda e: on_ok())
        win.bind("<Escape>", lambda e: on_cancel())

        # 4. 阻塞等待
        win.wait_window()

        return result.get("confirmed", False)

    def load_and_echo_config_after_unzip(self):
        config_data = load_slclient_json()
        p = config_data.get("profile", {})
        for field, entry in [
            ("dns", "entry_custom_ip"),
            ("context", "entry_custom_context"),
            ("upgrade_url", "entry_custom_upgrade"),
        ]:
            val = p.get(field)
            if val:
                v = val[0] if isinstance(val, list) and val else val
                getattr(self, entry).delete(0, "end")
                getattr(self, entry).insert(0, v)
                getattr(self, entry).configure(text_color="gray")

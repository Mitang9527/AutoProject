import os
import customtkinter as ctk
from pathlib import Path
from ..constants import (
    RESOURCE_PATH,
    WORKSPACE_PATH,
    PATH_SLCLIENT_JSON,
    PATH_YML,
    APKSIGNER_BAT,
    ENV_CONF,
    ENV_DISPLAY_NAMES,
    LOGIN_TYPE_MAPPING,
    MAP_CONFIG_TEMPLATES,
)
from ..i18n import i18n, _
from ..utils import (
    get_formatted_key_configs,
    copy_terminal_configs_from_folder,
)


def create_log_tab(app, parent):
    frame_log = ctk.CTkFrame(parent, fg_color="transparent")
    app.log_textbox = ctk.CTkTextbox(
        frame_log, font=ctk.CTkFont(family="Consolas", size=12)
    )
    app.log_textbox.pack(fill="both", expand=True, padx=10, pady=10)
    return frame_log


def create_config_tab(app, parent):
    frame_config = ctk.CTkFrame(parent, fg_color="transparent")
    app.scroll_frame = ctk.CTkScrollableFrame(
        frame_config, label_text=_("msg_config_list_title")
    )
    app.scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
    app.scroll_frame.grid_columnconfigure(0, weight=1)
    return frame_config


def create_build_tab(app, parent):
    frame_build = ctk.CTkFrame(parent, fg_color="transparent")
    app.lbl_title = ctk.CTkLabel(
        frame_build,
        text=_("msg_card_apk_properties"),
        font=ctk.CTkFont(size=18, weight="bold"),
    )
    app.lbl_title.pack(pady=(15, 10))
    grid_frame = ctk.CTkFrame(frame_build, fg_color="transparent")
    grid_frame.pack(fill="both", expand=True, padx=20, pady=10)
    grid_frame.grid_columnconfigure(0, weight=1)
    grid_frame.grid_columnconfigure(1, weight=1)
    grid_frame.grid_rowconfigure(0, weight=1)
    grid_frame.grid_rowconfigure(1, weight=1)

    app.frame_env = create_config_card(
        app, grid_frame, _("msg_card_env"), 0, 0, build_env_content
    )
    app.frame_sound = create_config_card(
        app, grid_frame, _("msg_card_sound"), 0, 1, build_sound_content
    )
    app.frame_map = create_config_card(
        app, grid_frame, _("msg_card_map"), 1, 0, build_map_content
    )
    app.frame_other = create_config_card(
        app, grid_frame, _("msg_card_other"), 1, 1, build_other_content
    )

    return frame_build


def create_led_tab(app, parent):
    frame_led = ctk.CTkFrame(parent, fg_color="transparent")
    app.lbl_input_title = ctk.CTkLabel(
        frame_led, text=_("msg_tab_input"), font=ctk.CTkFont(size=18, weight="bold")
    )
    app.lbl_input_title.pack(pady=(15, 10))
    grid_frame = ctk.CTkFrame(frame_led, fg_color="transparent")
    grid_frame.pack(fill="both", expand=True, padx=20, pady=10)
    grid_frame.grid_columnconfigure(0, weight=1)
    grid_frame.grid_rowconfigure(0, weight=1)
    grid_frame.grid_rowconfigure(1, weight=1)

    app.frame_led_mode = create_config_card(
        app, grid_frame, _("msg_card_input"), 0, 0, build_input_mode_content
    )
    app.title_led_mode = app.frame_led_mode.winfo_children()[0]
    app.frame_led_color = create_config_card(
        app, grid_frame, _("msg_card_other"), 1, 0, build_led_color_content
    )
    return frame_led


def create_terminal_tab(app, parent):
    frame_apk_config = ctk.CTkFrame(parent, fg_color="transparent")
    app.apk_title_label = ctk.CTkLabel(
        frame_apk_config,
        text=_("msg_terminal_config_title"),
        font=ctk.CTkFont(size=20, weight="bold"),
    )
    app.apk_title_label.pack(pady=(20, 10))
    search_frame = ctk.CTkFrame(frame_apk_config, fg_color="transparent")
    search_frame.pack(pady=5, fill="x", padx=20)
    app.terminal_search_var = ctk.StringVar()
    search_entry = ctk.CTkEntry(
        search_frame,
        placeholder_text=_("placeholder_search_terminal"),
        textvariable=app.terminal_search_var,
        width=200,
    )
    search_entry.pack(pady=5)
    app.terminal_scroll_frame = ctk.CTkScrollableFrame(
        frame_apk_config, width=800, height=500
    )
    app.terminal_scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

    terminal_configs_path = RESOURCE_PATH / "terminal_configs"
    app.terminal_all_folders = (
        [f for f in terminal_configs_path.iterdir() if f.is_dir()]
        if terminal_configs_path.exists()
        else []
    )
    app.current_displayed_folders = app.terminal_all_folders.copy()
    render_terminal_folders(app, app.current_displayed_folders)
    app.terminal_search_var.trace_add("write", app._on_search_change)
    search_entry.bind("<Return>", lambda e: app._filter_terminal_folders())
    return frame_apk_config


def create_config_card(app, parent, title, row, col, content_func):
    card = ctk.CTkFrame(
        parent, corner_radius=10, border_width=1, border_color="#3B8ED0"
    )
    card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
    card.grid_columnconfigure(0, weight=1)
    card.grid_rowconfigure(1, weight=1)
    card.title_label = ctk.CTkLabel(
        card, text=title, font=ctk.CTkFont(size=14, weight="bold"), anchor="w"
    )
    card.title_label.grid(row=0, column=0, padx=15, pady=10, sticky="w")
    content_frame = ctk.CTkFrame(card, fg_color="transparent")
    content_frame.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")
    content_frame.grid_columnconfigure(1, weight=1)
    content_func(app, content_frame)
    return card


def build_env_content(app, parent):
    current_lang = app.lang_var.get()
    base_options = [
        ENV_DISPLAY_NAMES.get(k, {}).get("zh" if current_lang == "中文" else "en", k)
        for k in ENV_CONF.keys()
    ]
    app.lbl_server_node = ctk.CTkLabel(parent, text=_("lbl_server_node"), anchor="w")
    app.lbl_server_node.grid(row=0, column=0, padx=5, pady=10, sticky="w")
    app.opt_env = ctk.CTkOptionMenu(
        parent, values=base_options, command=app._on_env_selected
    )
    app.opt_env.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
    app.env_custom = ctk.CTkLabel(parent, text=_("env_custom"), anchor="w")
    app.env_custom.grid(row=3, column=0, padx=5, pady=(5, 2), sticky="w")
    ctk.CTkLabel(parent, text="DNS IP:", anchor="w").grid(
        row=4, column=0, padx=5, pady=(5, 2), sticky="w"
    )
    app.entry_custom_ip = ctk.CTkEntry(parent)
    app.entry_custom_ip.grid(row=4, column=1, padx=5, pady=(5, 2), sticky="ew")
    ctk.CTkLabel(parent, text="Context:", anchor="w").grid(
        row=5, column=0, padx=5, pady=(2, 10), sticky="w"
    )
    app.entry_custom_context = ctk.CTkEntry(parent)
    app.entry_custom_context.grid(row=5, column=1, padx=5, pady=(2, 10), sticky="ew")
    ctk.CTkLabel(parent, text="upgrade url:", anchor="w").grid(
        row=6, column=0, padx=5, pady=(2, 10), sticky="w"
    )
    app.entry_custom_upgrade = ctk.CTkEntry(parent)
    app.entry_custom_upgrade.grid(row=6, column=1, padx=5, pady=(2, 10), sticky="ew")
    app.lbl_login_type = ctk.CTkLabel(parent, text=_("lbl_login_type"), anchor="w")
    app.lbl_login_type.grid(row=2, column=0, padx=5, pady=10, sticky="w")
    login_type_display_names = [
        LOGIN_TYPE_MAPPING[key]["zh" if current_lang == "中文" else "en"]
        for key in LOGIN_TYPE_MAPPING.keys()
    ]
    app.opt_login_type = ctk.CTkOptionMenu(
        parent, values=login_type_display_names, command=app.on_login_type_change
    )
    app.opt_login_type.grid(row=2, column=1, padx=5, pady=10, sticky="ew")
    app.btn_save_custom = ctk.CTkButton(
        parent,
        text=_("msg_save_btn"),
        command=app._save_profile_changes,
        fg_color="#d35400",
        hover_color="#e67e22",
        height=28,
        font=ctk.CTkFont(weight="bold"),
    )
    app.btn_save_custom.grid(row=7, column=0, columnspan=2, padx=5, pady=10, sticky="e")
    app.lbl_env_info = ctk.CTkLabel(
        parent, text="", text_color="gray", font=ctk.CTkFont(size=10), anchor="w"
    )
    app.lbl_env_info.grid(
        row=5, column=0, columnspan=2, padx=5, pady=(5, 10), sticky="w"
    )


def build_sound_content(app, parent):
    ctk.CTkLabel(parent, text="Tone:", anchor="w").grid(
        row=1, column=0, padx=5, pady=8, sticky="w"
    )
    app.switch_tone_sfx = ctk.CTkSwitch(
        parent,
        text=" ",
        command=lambda: app._sync_tone_enabled_to_json(bool(app.switch_tone_sfx.get())),
    )
    app.switch_tone_sfx.grid(row=1, column=1, padx=5, pady=6, sticky="w")
    app.switch_tone_sfx.select()
    app.codec = ctk.CTkLabel(parent, text=_("codec"), anchor="w")
    app.codec.grid(row=2, column=0, padx=5, pady=10, sticky="w")
    app.opt_codec = ctk.CTkOptionMenu(
        parent, values=["amrnb", "evrc8k", "opus"], command=app._sync_codec_to_json
    )
    app.opt_codec.grid(row=2, column=1, padx=5, pady=8, sticky="ew")
    app.audio = ctk.CTkLabel(parent, text=_("audio"), anchor="w")
    app.audio.grid(row=3, column=0, padx=5, pady=10, sticky="w")
    app.opt_audio = ctk.CTkOptionMenu(
        parent, values=["default", "sles", "oem"], command=app._sync_soundsystem_to_json
    )
    app.opt_audio.grid(row=3, column=1, padx=5, pady=8, sticky="ew")
    app.play_channel = ctk.CTkLabel(parent, text=_("play_channel"), anchor="w")
    app.play_channel.grid(row=4, column=0, padx=5, pady=10, sticky="w")
    app.opt_play = ctk.CTkOptionMenu(
        parent, values=["music", "voice"], command=app._sync_play_to_json
    )
    app.opt_play.grid(row=4, column=1, padx=5, pady=8, sticky="ew")
    app.rec_channel = ctk.CTkLabel(parent, text=_("rec_channel"), anchor="w")
    app.rec_channel.grid(row=5, column=0, padx=5, pady=8, sticky="w")
    app.opt_rec = ctk.CTkOptionMenu(
        parent,
        values=["mic", "voice", "communication", "recognition"],
        command=app._sync_record_to_json,
    )
    app.opt_rec.grid(row=5, column=1, padx=5, pady=10, sticky="ew")


def build_map_content(app, parent):
    app.lbl_map_source = ctk.CTkLabel(parent, text=_("lbl_map_source"), anchor="w")
    app.lbl_map_source.grid(row=0, column=0, padx=5, pady=10, sticky="w")
    map_source_display_names = [
        v["display_name"]["zh" if app.lang_var.get() == "中文" else "en"]
        for v in MAP_CONFIG_TEMPLATES.values()
    ]
    app.opt_map_source = ctk.CTkOptionMenu(
        parent, values=map_source_display_names, command=app.on_map_source_change
    )
    app.opt_map_source.grid(row=0, column=1, padx=5, pady=10, sticky="w")


def build_other_content(app, parent):
    ctk.CTkLabel(parent, text="TTS:", anchor="w").grid(
        row=1, column=0, padx=5, pady=8, sticky="w"
    )
    app.switch_sfx = ctk.CTkSwitch(
        parent,
        text=" ",
        command=lambda: app._sync_tts_enabled_to_json(bool(app.switch_sfx.get())),
    )
    app.switch_sfx.grid(row=1, column=1, padx=5, pady=8, sticky="w")
    ctk.CTkLabel(parent, text="Launcher:", anchor="w").grid(
        row=2, column=0, padx=5, pady=8, sticky="w"
    )
    app.switch_launcher = ctk.CTkSwitch(
        parent,
        text="",
        command=lambda: app.modify_manifest(bool(app.switch_launcher.get())),
    )
    app.switch_launcher.grid(row=2, column=1, padx=5, pady=8, sticky="w")


def build_input_mode_content(app, parent):
    app.lbl_ptt_press = ctk.CTkLabel(
        parent, text=_("lbl_ptt_press"), anchor="w", width=80
    )
    app.lbl_ptt_press.grid(row=0, column=0, padx=(10, 5), pady=(8, 2), sticky="w")
    app.entry_ptt_press = ctk.CTkEntry(
        parent, placeholder_text="Action for PTT_DOWN", height=32
    )
    app.entry_ptt_press.grid(row=0, column=1, padx=(5, 10), pady=(8, 2), sticky="ew")
    app.lbl_ptt_release = ctk.CTkLabel(
        parent, text=_("lbl_ptt_release"), anchor="w", width=80
    )
    app.lbl_ptt_release.grid(row=1, column=0, padx=(10, 5), pady=2, sticky="w")
    app.entry_ptt_release = ctk.CTkEntry(
        parent, placeholder_text="Action for PTT_UP", height=32
    )
    app.entry_ptt_release.grid(row=1, column=1, padx=(5, 10), pady=2, sticky="ew")
    app.lbl_sos_key = ctk.CTkLabel(parent, text=_("lbl_sos_key"), anchor="w", width=80)
    app.lbl_sos_key.grid(row=2, column=0, padx=(10, 5), pady=2, sticky="w")
    app.entry_sos = ctk.CTkEntry(parent, placeholder_text="Action for SOS", height=32)
    app.entry_sos.grid(row=2, column=1, padx=(5, 10), pady=2, sticky="ew")
    app.btn_save_config = ctk.CTkButton(
        parent,
        text=_("btn_save_config"),
        command=app._on_save_manual_keys,
        fg_color="#28a745",
        hover_color="#218838",
        height=28,
        width=25,
        font=ctk.CTkFont(size=13, weight="bold"),
    )
    app.btn_save_config.grid(
        row=3, column=0, columnspan=2, padx=10, pady=(8, 10), sticky="e"
    )
    parent.grid_columnconfigure(1, weight=1)
    parent.grid_columnconfigure(0, weight=0)


def build_led_color_content(app, parent):
    app.lbl_other = ctk.CTkLabel(parent, text=_("msg_feature_dev"), text_color="gray")
    app.lbl_other.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="w")


def render_terminal_folders(app, folders):
    for widget in app.terminal_scroll_frame.winfo_children():
        widget.destroy()
    for index, folder in enumerate(folders):
        row, col = index // 6, index % 6
        icon_frame = ctk.CTkFrame(
            app.terminal_scroll_frame, width=120, height=140, corner_radius=10
        )
        icon_frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        app.terminal_scroll_frame.grid_columnconfigure(col, weight=1)
        ctk.CTkLabel(icon_frame, text="📁", font=ctk.CTkFont(size=24)).pack(
            pady=(10, 5)
        )
        ctk.CTkLabel(
            icon_frame,
            text=folder.name[:10] + ("..." if len(folder.name) > 10 else ""),
            font=ctk.CTkFont(size=12),
            wraplength=100,
        ).pack(pady=(0, 5))
        app.use_btn = ctk.CTkButton(
            icon_frame,
            text=_("use_btn"),
            width=80,
            height=25,
            command=lambda f=folder: app._use_terminal_config(f),
            fg_color="#1f6aa0",
            hover_color="#144870",
        )
        app.use_btn.pack(pady=(0, 10))

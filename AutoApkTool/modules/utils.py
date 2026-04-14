import os
import json
import re
import shutil
import time
import traceback
import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path
from typing import List, Any, Optional, Dict
from tkinter import messagebox
from ruamel.yaml import YAML
from datetime import datetime
from .constants import (
    PATH_SLCLIENT_JSON,
    LOGIN_TYPE_MAPPING,
    MAP_CONFIG_TEMPLATES,
    LBS_COOR_PATH,
    LBS_MAP_PYPE,
    ANDROID_NAMESPACE,
    PATH_MANIFEST_XML,
    PATH_ASS,
    PATH_SLCLIENT,
    PATH_INPUT_JSON_SRC,
    PATH_INPUT_JSON_DEFAULT,
)
from .i18n import i18n, _

# ==================== slclient.json处理 ====================


def update_slclient_login_type(login_type_ui: str) -> bool:
    """
    更新slclient.json中的profile.login_mode字段
    """
    if not PATH_SLCLIENT_JSON.exists():
        messagebox.showerror("ERROR", f"Please unzip apk first")
        return False

    login_mode_val = "account"  # 默认值
    for storage_key, names_dict in LOGIN_TYPE_MAPPING.items():
        if (
            names_dict.get("zh") == login_type_ui
            or names_dict.get("en") == login_type_ui
        ):
            login_mode_val = storage_key
            break

    try:
        with open(PATH_SLCLIENT_JSON, "r", encoding="utf-8") as f:
            slclient_data = json.load(f)

        slclient_data.setdefault("profile", {})["login_mode"] = login_mode_val

        with open(PATH_SLCLIENT_JSON, "w", encoding="utf-8") as f:
            json.dump(slclient_data, f, indent=2, ensure_ascii=False)

        return True

    except Exception as e:
        messagebox.showerror("修改失败", f"更新slclient.json出错：\n{str(e)}")
        traceback.print_exc()
        return False


def update_slclient_map_type(map_source_key: str) -> bool:
    """
    更新slclient.json中的地图源配置
    """
    if not PATH_SLCLIENT_JSON.exists():
        print(f"[Error] File not found: {PATH_SLCLIENT_JSON}")
        return False

    try:
        with open(PATH_SLCLIENT_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)

        template_config = MAP_CONFIG_TEMPLATES.get(map_source_key)
        if not template_config:
            print(f"[Error] No template found for key: {map_source_key}")
            return False

        if "lbs" not in data:
            data["lbs"] = {}
        data["lbs"].update(template_config["config"])

        with open(PATH_SLCLIENT_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        return True

    except Exception as e:
        print(f"[Error] Failed to update slclient.json: {e}")
        return False


def get_json_field(file_path: Path, field_path: List[str]) -> Any:
    try:
        if not file_path.exists():
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        temp_data = data
        for key in field_path:
            if isinstance(temp_data, dict):
                temp_data = temp_data.get(key)
            else:
                return None
        return temp_data
    except Exception:
        return None


def set_json_field(file_path: Path, field_path: List[str], new_value: Any) -> bool:
    try:
        if not file_path.exists():
            return False

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        temp_data = data
        for key in field_path[:-1]:
            if isinstance(temp_data, dict) and key in temp_data:
                temp_data = temp_data[key]
            else:
                return False

        target_key = field_path[-1]
        if isinstance(temp_data, dict):
            temp_data[target_key] = new_value
        else:
            return False

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        return True

    except Exception as e:
        return False


def load_slclient_json() -> dict:
    json_path = PATH_SLCLIENT_JSON
    data = {}

    if not json_path.exists():
        return data

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                data = json.loads(content)
    except Exception:
        pass

    return data


def save_slclient_json(data: dict, *, indent: int = 4) -> bool:
    if not PATH_SLCLIENT_JSON.exists():
        return False
    try:
        with open(PATH_SLCLIENT_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        return True
    except Exception:
        return False


def update_slclient_profile(
    *,
    dns: List[str],
    context: str,
    upgrade_url: Optional[str] = None,
    env_key: Optional[str] = None,
) -> bool:
    if not PATH_SLCLIENT_JSON.exists():
        return False
    try:
        data = load_slclient_json()
        profile = data.setdefault("profile", {})
        profile["dns"] = dns
        profile["context"] = context
        if upgrade_url is not None:
            profile["upgrade_url"] = upgrade_url
        if env_key is not None:
            profile["env_key"] = env_key
        return save_slclient_json(data, indent=4)
    except Exception:
        return False


def slclient_set_sound_codec(codec: str) -> bool:
    if not PATH_SLCLIENT_JSON.exists():
        return False
    try:
        data = load_slclient_json()
        if data.get("sound", {}).get("codec") == codec:
            return True
        data.setdefault("sound", {})["codec"] = codec
        return save_slclient_json(data, indent=4)
    except Exception:
        return False


def slclient_set_dsp_provider(provider: str) -> bool:
    if not PATH_SLCLIENT_JSON.exists():
        return False
    try:
        data = load_slclient_json()
        if data.get("dsp", {}).get("provider") == provider:
            return True
        data.setdefault("dsp", {})["provider"] = provider
        return save_slclient_json(data, indent=4)
    except Exception:
        return False


def slclient_set_play_stream(play_stream: str) -> bool:
    if not PATH_SLCLIENT_JSON.exists():
        return False
    try:
        data = load_slclient_json()
        if data.get("dsp", {}).get("play_stream") == play_stream:
            return True
        data.setdefault("dsp", {})["play_stream"] = play_stream
        return save_slclient_json(data, indent=4)
    except Exception:
        return False


def slclient_set_record_stream(record_stream: str) -> bool:
    if not PATH_SLCLIENT_JSON.exists():
        return False
    try:
        data = load_slclient_json()
        if data.get("dsp", {}).get("record_stream") == record_stream:
            return True
        data.setdefault("dsp", {})["record_stream"] = record_stream
        return save_slclient_json(data, indent=4)
    except Exception:
        return False


def slclient_set_tone_enabled(is_enabled: bool) -> bool:
    if not PATH_SLCLIENT_JSON.exists():
        return False
    try:
        data = load_slclient_json()
        json_value = bool(is_enabled)
        if data.get("sound", {}).get("tone_enabled") == json_value:
            return True
        data.setdefault("sound", {})["tone_enabled"] = json_value
        return save_slclient_json(data, indent=4)
    except Exception:
        return False


def slclient_set_tts_enabled(is_enabled: bool) -> bool:
    if not PATH_SLCLIENT_JSON.exists():
        return False
    try:
        data = load_slclient_json()
        json_value = bool(is_enabled)
        if data.get("tts", {}).get("enabled") == json_value:
            return True
        data.setdefault("tts", {})["enabled"] = json_value
        return save_slclient_json(data, indent=4)
    except Exception:
        return False


def copy_terminal_configs_from_folder(source_dir: Path) -> None:
    """
    从指定终端配置文件夹导入配置到打包目录
    """
    shutil.copy2(source_dir / "slclient.json", PATH_ASS / "slclient.json")
    shutil.copy2(source_dir / "slclient" / "led.json", PATH_SLCLIENT / "led.json")
    shutil.copy2(source_dir / "slclient" / "input.json", PATH_SLCLIENT / "input.json")
    shutil.copy2(
        source_dir / "slclient" / "reaction.json",
        PATH_SLCLIENT / "reaction.json",
    )


def get_formatted_key_configs(data: dict) -> list:
    """
    解析 JSON 数据并返回格式化后的按键配置列表，供 UI 渲染
    返回列表元素格式：(name, event_str, key_val, action_str, cmd_str)
    按 key_val 升序排列
    """
    intents = data.get("intent", {})
    stdkeys = data.get("stdkey", {})
    actions_data = data.get("action", {})

    valid_names = set(stdkeys.keys()) & set(intents.keys())
    sortable_items = []

    for name in valid_names:
        sk = stdkeys.get(name, {})
        key_val = sk.get("key")
        sortable_items.append(
            (name, key_val if isinstance(key_val, int) else float("inf"))
        )

    sortable_items.sort(key=lambda x: x[1], reverse=False)

    formatted_items = []
    for name, _ in sortable_items:
        sk = stdkeys.get(name, {})
        ac = actions_data.get(name, {})
        info = intents.get(name, {})

        event_str = sk.get("event", i18n.get("msg_not_available"))
        key_val = sk.get("key", i18n.get("msg_not_available"))
        action_str = info.get("action", i18n.get("msg_default_placeholder"))
        cmds = ac.get("default", [])

        cmd_str = (
            ", ".join(
                filter(
                    None,
                    [
                        c.get("command", {}).get("id", "")
                        for c in cmds
                        if isinstance(c, dict)
                    ],
                )
            )
            if isinstance(cmds, list)
            else i18n.get("msg_default_placeholder")
        )
        if not cmd_str:
            cmd_str = i18n.get("msg_default_placeholder")

        formatted_items.append((name, event_str, key_val, action_str, cmd_str))

    return formatted_items


def save_manual_keys_to_json(
    val_press: str, val_release: str, val_sos: str
) -> Optional[Dict]:
    """
    将手动输入的 PTT 和 SOS 按键写入 backend 的 input.json/reaction.json 中
    （实际写入到 PATH_INPUT_JSON_SRC）
    返回包含新分配 key 值的字典，如果失败或无内容则返回 None
    """
    has_ptt, has_sos = bool(val_press and val_release), bool(val_sos)
    if not has_ptt and not has_sos:
        return None

    timestamp_suffix = datetime.now().strftime("%Y%m%d%H%M%S")
    existing_codes = set()
    source_path = PATH_INPUT_JSON_SRC
    if not os.path.exists(source_path):
        source_path = PATH_INPUT_JSON_DEFAULT

    if os.path.exists(source_path):
        try:
            with open(source_path, "r", encoding="utf-8") as f:
                temp_data = json.load(f)
                for v in temp_data.get("stdkey", {}).values():
                    if isinstance(v.get("key"), int):
                        existing_codes.add(v["key"])
        except Exception:
            pass

    new_vkey_ptt = None
    if has_ptt:
        new_vkey_ptt = -1000
        while new_vkey_ptt in existing_codes:
            new_vkey_ptt -= 1
        existing_codes.add(new_vkey_ptt)

    new_vkey_sos = None
    if has_sos:
        new_vkey_sos = -1000
        while new_vkey_sos in existing_codes:
            new_vkey_sos -= 1

    new_entries = {"stdkey": {}, "action": {}, "intent": {}}
    if has_ptt:
        name_ptt_down, name_ptt_up = (
            f"many_ptt_down_{timestamp_suffix}",
            f"ptt_up_{timestamp_suffix}",
        )
        (
            new_entries["stdkey"][name_ptt_down],
            new_entries["stdkey"][name_ptt_up],
        ) = {"event": "KEY_DOWN", "key": new_vkey_ptt}, {
            "event": "KEY_UP",
            "key": new_vkey_ptt,
        }
        (
            new_entries["action"][name_ptt_down],
            new_entries["action"][name_ptt_up],
        ) = {"default": [], "member": [], "new_call_in": []}, {
            "default": [{"command": {"id": "STOP_SPEAK"}}],
            "member": [],
            "new_call_in": [],
        }
        (
            new_entries["intent"][name_ptt_down],
            new_entries["intent"][name_ptt_up],
        ) = {
            "action": val_press
        }, {"action": val_release}

    if has_sos:
        name_sos_down, name_sos_up = (
            f"sos_down_{timestamp_suffix}",
            f"sos_up_{timestamp_suffix}",
        )
        new_entries["stdkey"][name_sos_down] = new_entries["stdkey"][name_sos_up] = {
            "event": "KEY_CLICK",
            "key": new_vkey_sos,
            "time": 3000,
        }
        new_entries["intent"][name_sos_down] = new_entries["intent"][name_sos_up] = {
            "action": val_sos
        }

    data = {"stdkey": {}, "action": {}, "intent": {}, "custom": []}
    load_path = PATH_INPUT_JSON_SRC
    if not os.path.exists(load_path):
        load_path = PATH_INPUT_JSON_DEFAULT

    if os.path.exists(load_path):
        try:
            with open(load_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass

    for k in ["stdkey", "action", "intent"]:
        data.setdefault(k, {}).update(new_entries[k])

    with open(PATH_INPUT_JSON_SRC, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return {"ptt_key": new_vkey_ptt, "sos_key": new_vkey_sos}


def get_current_custom_list() -> List[str]:
    """获取当前 input.json 中的 custom 列表"""
    load_path = PATH_INPUT_JSON_SRC
    if not os.path.exists(load_path):
        load_path = PATH_INPUT_JSON_DEFAULT

    if os.path.exists(load_path):
        try:
            with open(load_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("custom", [])
        except Exception:
            pass
    return []


def update_custom_list(new_list: List[str]):
    """更新 input.json 中的 custom 列表"""
    data = {}
    load_path = PATH_INPUT_JSON_SRC
    if not os.path.exists(load_path):
        load_path = PATH_INPUT_JSON_DEFAULT

    if os.path.exists(load_path):
        try:
            with open(load_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass

    data["custom"] = new_list
    with open(PATH_INPUT_JSON_SRC, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ==================== Manifest 辅助函数 ====================


def android_attr(name):
    return f"{{{ANDROID_NAMESPACE}}}{name}"


def write_pretty_xml(tree, file_path):
    rough_string = ET.tostring(tree.getroot(), encoding="utf-8")
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="    ")

    pretty_xml = "\n".join([line for line in pretty_xml.split("\n") if line.strip()])

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(pretty_xml)


def modify_manifest(is_enabled: bool, log_callback=None):
    manifest_path = PATH_MANIFEST_XML

    if not os.path.exists(manifest_path):
        if log_callback:
            log_callback(" Error: Unable to find AndroidManifest.xml")
        return

    try:
        ET.register_namespace("android", ANDROID_NAMESPACE)
        tree = ET.parse(manifest_path)
        root = tree.getroot()

        application = root.find("application")
        if application is None:
            if log_callback:
                log_callback(" Error: Unable to find the <application>tag")
            return

        candidate_activity_names = [
            "com.shanli.pocstar.SplashActivity",
            "com.shanlitech.ptt.SplashActivity",
            "com.shanlitech.noscreen.SplashActivity",
        ]

        target_activity = None
        found_activity_name = ""

        for activity in application.findall("activity"):
            name = activity.attrib.get(android_attr("name"), "")
            if name in candidate_activity_names:
                target_activity = activity
                found_activity_name = name
                break

        if target_activity is None:
            if log_callback:
                log_callback(
                    f" Error: Target Activity not found (candidate:{candidate_activity_names})"
                )
            return

        intent_filter = target_activity.find("intent-filter")
        if intent_filter is None:
            if log_callback:
                log_callback(
                    f" Error：{found_activity_name} No<intent-filter>, cannot operate"
                )
            return

        home_category_elem = None
        for category in intent_filter.findall("category"):
            if (
                category.attrib.get(android_attr("name"))
                == "android.intent.category.HOME"
            ):
                home_category_elem = category
                break

        has_home = home_category_elem is not None

        if is_enabled:
            if not has_home:
                ET.SubElement(
                    intent_filter,
                    "category",
                    {android_attr("name"): "android.intent.category.HOME"},
                )
                write_pretty_xml(tree, manifest_path)
                if log_callback:
                    log_callback(f"[ok]  set to desktop as Launcher\n")
        else:
            if has_home:
                intent_filter.remove(home_category_elem)
                write_pretty_xml(tree, manifest_path)
                if log_callback:
                    log_callback(f"[ok] Launcher has  cancelled\n")

    except Exception as e:
        if log_callback:
            log_callback(f" operation failed：{e}")


# ==================== YAML 辅助函数 ====================


def load_yml(yml_path: Path) -> Optional[Dict]:
    yaml = YAML()
    if not os.path.exists(yml_path):
        return None
    try:
        with open(yml_path, "r", encoding="utf-8") as f:
            return yaml.load(f)
    except Exception:
        return None


def update_version_info(yml_path: Path, log_callback=None) -> None:
    yaml = YAML()

    def represent_none(self, data):
        return self.represent_scalar("tag:yaml.org,2002:null", "null")

    yaml.representer.add_representer(type(None), represent_none)

    data = load_yml(yml_path)
    if not data:
        return

    version_info = data.get("versionInfo", {})
    old_code = version_info.get("versionCode")
    old_name = version_info.get("versionName")

    if not old_code or not old_name:
        if log_callback:
            log_callback(
                "[Warn]Unable to obtain version information, skipping update\n"
            )
        return

    new_code = int(old_code) + 1

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    pattern = r"(POCSTARS_)\d+$"
    new_name = re.sub(pattern, rf"\1{timestamp}", old_name)
    if new_name == old_name:
        new_name = f"{old_name}_{timestamp}"

    version_info["versionCode"] = new_code
    version_info["versionName"] = new_name

    with open(yml_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f)

    if log_callback:
        log_callback(
            f"[Version]update successful：{old_name}->{new_name}, Code: {old_code}->{new_code}\n"
        )

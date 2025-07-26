# -*- coding: utf-8 -*-
import os
import re
from ruamel.yaml import YAML, CommentedMap
from ruamel.yaml.constructor import ConstructorError

from utils.apktoolUtils.getData import get_json_field
from utils.logUtils.logControl import INFO, ERROR


def get_field_value_from_yml(yml_path, field_name):
    """从 apktool.yml 文件中获取指定字段的值"""
    if not os.path.exists(yml_path):
        ERROR.logger.error("apktool.yml 文件不存在，跳过版本处理")
        return None, None

    yaml = YAML()

    try:
        with open(yml_path, "r", encoding="utf-8") as f:
            data = yaml.load(f)
    except ConstructorError as e:
        ERROR.logger.error(f"解析YAML时遇到未知tag，尝试忽略处理：{e}")

        class IgnoreUnknownTagsLoader(yaml.constructor.SafeConstructor):
            def construct_undefined(self, node):
                return None

        yaml.Constructor = IgnoreUnknownTagsLoader
        with open(yml_path, "r", encoding="utf-8") as f:
            data = yaml.load(f)

    if data is None:
        ERROR.logger.error("apktool.yml 内容为空或解析失败")
        return None, None

    field_value = data.get(field_name, {})
    if not field_value:
        ERROR.logger.error(f"apktool.yml中没有{field_name}]")
        return None
    return field_value

def get_version_info(yml_path):
    """获取 versionCode 和 versionName"""

    value = get_field_value_from_yml(yml_path, "versionInfo")
    if value:
        versionCode = value.get("versionCode")
        versionName = value.get("versionName")

        return versionCode, versionName

def increment_version_code(version_code):
    """自增 versionCode"""
    try:
        version_code = int(version_code)
        return version_code + 1
    except (ValueError, TypeError) as e:
        ERROR.logger.warning(f"versionCode 处理失败：{e}")
        return version_code

def increment_version_name(version_name):
    """自增 versionName"""

    #匹配最后一个 _ 后的数字并进行自增
    pattern = r"^(.*_)(\d+)([^_]*)$"
    m = re.match(pattern, version_name)
    if m:
        prefix = m.group(1)
        last_num = int(m.group(2))
        last_num += 1
        version_name = f"{prefix}{last_num}"
        return version_name
    else:
        ERROR.logger.error(f"versionName 格式不匹配：{version_name}")

def update_version_info(yml_path):
    """更新版本信息：自增 versionCode 和 versionName"""

    # 先读取整个YML内容
    yaml = YAML()

    # 设置：强制写出 None
    def represent_none(self, data):
        return self.represent_scalar('tag:yaml.org,2002:null', 'null')
    yaml.representer.add_representer(type(None), represent_none)

    with open(yml_path, "r", encoding="utf-8") as f:
        data = yaml.load(f)

    if data is None:
        ERROR.logger.error("apktool.yml 内容为空或解析失败")
        return

    # 获取旧版本信息
    versionInfo = data.get("versionInfo", {})
    version_code = versionInfo.get("versionCode")
    version_name = versionInfo.get("versionName")

    if not version_code or not version_name:
        ERROR.logger.error("无法获取 versionCode 或 versionName，跳过版本更新")
        return

    # 版本自增函数，示例
    new_version_code = increment_version_code(version_code)
    new_version_name = increment_version_name(version_name)

    # 更新版本信息
    versionInfo["versionCode"] = new_version_code
    versionInfo["versionName"] = new_version_name


    # 写回文件
    with open(yml_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f)

    INFO.logger.info(f"版本名称更新:{new_version_name},版本号更新:{new_version_code}!")
    return new_version_code, new_version_name

def build_newname(file_path, field_path, yml_path):
    launcher_module = get_json_field(file_path,field_path)
    new_version_name = get_version_info(yml_path)[1]

    try:
        if launcher_module is None:
            ERROR.logger.error("未能获取到 launcherModule 字段值")
            return None

        elif launcher_module == 'large':
            newname = 'BSAPP_' + str(new_version_name) + '.apk'

        elif launcher_module == 'middle':
            newname = 'MSAPP_' + str(new_version_name) + '.apk'

        elif launcher_module == 'small':
            newname = 'SSAPP_' + str(new_version_name) + '.apk'

        else:
            newname = 'NSAPP_' + str(new_version_name) + '.apk'
        INFO.logger.info(f'已更改名称为{newname}')
        return newname

    except Exception as e:
        ERROR.logger.error(f'更改名称错误:{e}')


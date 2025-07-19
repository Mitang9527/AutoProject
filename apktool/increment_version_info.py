# -*- coding: utf-8 -*-
import os
import re
from ruamel.yaml import YAML
from ruamel.yaml.constructor import ConstructorError
from utils.logUtils.logControl import INFO, ERROR

def increment_version_info(yml_path):
    if not os.path.exists(yml_path):
        ERROR.logger.error("apktool.yml 文件不存在，跳过版本处理")
        return

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
        return


    version_info = data.get("versionInfo", {})
    if not version_info:
        ERROR.logger.error("apktool.yml中没有versionInfo")
        return

    # versionCode 自增
    try:
        version_code = int(version_info.get("versionCode", "1"))
        version_info["versionCode"] = str(version_code + 1)
    except Exception as e:
        INFO.logger.warning(f"versionCode 处理失败：{e}")

    # versionName 修改末尾数字（SL_后面的数字自增）
    version_name = version_info.get("versionName", "")

    pattern = r"^(.*_SL_)(\d+)$"
    m = re.match(pattern, version_name)
    if m:
        prefix = m.group(1)
        last_num = int(m.group(2))
        last_num += 1
        new_version = f"{prefix}{last_num}"
        version_info["versionName"] = new_version
        INFO.logger.info(f"版本更新为 versionCode={version_info['versionCode']}, versionName={new_version}")
    else:
        INFO.logger.warning(f"versionName 格式不匹配，跳过更新：{version_name}")


    with open(yml_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f)



increment_version_info(r"D:\Code\AutoProject\apktool\app_out\AndroidManifest.xml")

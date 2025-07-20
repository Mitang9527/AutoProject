import os
import xml.etree.ElementTree as ET
from xml.dom import minidom

from utils.logUtils.logControl import INFO, ERROR

# 命名空间（确保与 manifest 中一致）
ANDROID_NAMESPACE = "http://schemas.android.com/apk/res/android"

# 构造 Android 属性全名
def android_attr(name):
    return f"{{{ANDROID_NAMESPACE}}}{name}"

# 使用 minidom 美化写入 XML 文件
def write_pretty_xml(tree, file_path):
    rough_string = ET.tostring(tree.getroot(), encoding='utf-8')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="    ")

    # 去除多余空行
    pretty_xml = "\n".join([line for line in pretty_xml.split('\n') if line.strip()])

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(pretty_xml)

def modify_manifest(manifest_path):
    if not os.path.exists(manifest_path):
        ERROR.logger.error(" 找不到 AndroidManifest.xml，路径错误")
        return

    try:
        ET.register_namespace("android", ANDROID_NAMESPACE)
        tree = ET.parse(manifest_path)
        root = tree.getroot()

        application = root.find("application")
        if application is None:
            ERROR.logger.error(" 未找到 <application> 标签")
            return

        target_activity_name = "com.shanli.pocstar.SplashActivity"
        target_activity = None

        # 查找目标 Activity
        for activity in application.findall("activity"):
            name = activity.attrib.get(android_attr("name"), "")
            if name == target_activity_name:
                target_activity = activity
                break

        if target_activity is None:
            ERROR.logger.error(f" 未找到 Activity：{target_activity_name}")
            return

        # 获取或查找 intent-filter
        intent_filter = target_activity.find("intent-filter")
        if intent_filter is None:
            ERROR.logger.error(f" {target_activity_name} 未找到 <intent-filter>")
            return

        # 判断是否已有 HOME 类别
        has_home = any(
            category.attrib.get(android_attr("name")) == "android.intent.category.HOME"
            for category in intent_filter.findall("category")
        )

        if not has_home:
            ET.SubElement(intent_filter, "category", {
                android_attr("name"): "android.intent.category.HOME"
            })
            write_pretty_xml(tree, manifest_path)
            INFO.logger.info(" 已添加 launcher category 到 SplashActivity")
        else:
            INFO.logger.info(" 已存在 launcher category，无需添加")

    except Exception as e:
        ERROR.logger.error(f" 修改 AndroidManifest.xml 出错：{e}")



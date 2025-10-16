import os
import shutil
from pathlib import Path
from utils.logUtils.logControl import INFO, ERROR
from utils.readFilesUtils.get_path import get_project
import xml.etree.ElementTree as ET

# ===  皮肤资源文件路径&Values资源路径  ===
project_path = get_project()
target_dir = project_path / 'app_out' / 'res'  # 目标文件夹
source_dir = project_path / 'app_out1' / 'res'  # 资源文件夹

target_dir_color = project_path / 'app_out' / 'res' / 'values' / 'colors.xml'   # 目标color
source_dir_color = project_path / 'app_out1' / 'res' / 'values' / 'colors.xml'     # 资源color

folders_to_cover = ["mipmap", "mipmap-hdpi", "mipmap-ldpi", "mipmap-mdpi", "mipmap-xhdpi", "mipmap-xxhdpi"]

# ===  皮肤颜色资源路径  ===
target_color_file = project_path / 'app_out' / 'res' / 'values' / 'colors.xml'  # 目标文件夹
source_color_file = project_path / 'app_out1' / 'res' / 'values' / 'colors.xml'  # 资源文件夹


def exchange_res(source_dir, target_dir):
    if all(f.exists() and f.is_dir() for f in [source_dir, target_dir]):
        for folder_name in folders_to_cover:
            source_folder = source_dir / folder_name
            target_folder = target_dir / folder_name

            if all(f.exists() and f.is_dir() for f in [source_dir, target_dir]):
                for item in source_folder.iterdir():
                    target_item = target_folder / item.name
                    if item.is_dir():
                        shutil.copytree(item, target_item, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, target_item)
                INFO.logger.info(f"已覆盖文件夹：{folder_name}")
            else:
                ERROR.logger.error(f"目标文件夹 {folder_name} 不存在")
    else:
        ERROR.logger.error("资源文件夹不存在")

def copy_res(source_dir_color,target_dir_color):
    if not os.path.isfile(source_dir_color):
        raise FileNotFoundError(f"资源文件不存在: {source_dir_color}")

    try:
        shutil.copy2(source_dir_color, target_dir_color)
        print(f"复制完成：{source_dir_color} -> {target_dir_color}")
    except Exception as e:
        print(f"复制失败：{e}")


def get_color_value_from_xml(file_path, color_name):
    """从 XML 文件中获取指定 color 的值"""
    tree = ET.parse(file_path)
    root = tree.getroot()

    for color in root.findall('color'):
        if color.get('name') == color_name:
            return color.text

    return None

#TODO 会造成color标签的丢失，可以直接替换color文件
def update_colors_in_target_xml(source_color_file, target_color_file):
    # 获取源文件中的两个颜色值
    color_primary = get_color_value_from_xml(source_color_file, "pocstar_colorPrimary")
    color_primary_alpha = get_color_value_from_xml(source_color_file, "pocstar_colorPrimaryAlpha")

    if color_primary is None or color_primary_alpha is None:
        ERROR.logger.error("未能找到需要的颜色值，确保源文件中有这两个 color 标签。")
        return

    # 解析目标文件
    target_tree = ET.parse(target_color_file)
    target_root = target_tree.getroot()

    # 遍历目标文件中的 color 标签并进行替换
    for color in target_root.findall('color'):
        color_name = color.get('name')
        if color_name == "pocstar_colorPrimary":
            color.text = color_primary
            INFO.logger.info(f"更新 {color_name} to {color_primary}")
        elif color_name == "pocstar_colorPrimaryAlpha":
            color.text = color_primary_alpha
            INFO.logger.info(f"更新 {color_name} to {color_primary_alpha}")

    # 保存修改后的目标文件
    target_tree.write(target_color_file, encoding="UTF-8", xml_declaration=True)
    INFO.logger.info(f"Successfully updated the colors in {target_color_file}")

def copy_res(source_dir_color,target_dir_color):
    if not os.path.isfile(source_dir_color):
        raise FileNotFoundError(f"资源文件不存在: {source_dir_color}")

    try:
        shutil.copy2(source_dir_color, target_dir_color)
        print(f"复制完成：{source_dir_color} -> {target_dir_color}")
    except Exception as e:
        print(f"复制失败：{e}")

def replace_app_name(source_dir, target_dir):
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file == "strings.xml":
                source_file_path = Path(root) / file

                try:
                    tree = ET.parse(source_file_path)
                    root_element = tree.getroot()

                    for elem in root_element.findall("string"):
                        if elem.get("name") == "app_name":
                            new_app_name = elem.text

                            # 获取相对路径
                            relative_path = source_file_path.relative_to(source_dir)
                            target_file_path = target_dir / relative_path

                            if target_file_path.exists():
                                try:
                                    # 读取目标 XML
                                    target_tree = ET.parse(target_file_path)
                                    target_root = target_tree.getroot()

                                    for target_elem in target_root.findall("string"):
                                        if target_elem.get("name") == "app_name":
                                            target_elem.text = new_app_name
                                            INFO.logger.info(f"更新：{target_file_path} -> app_name = {new_app_name}")
                                            break
                                    else:
                                        ERROR.logger.error(f"未找到 app_name 字段：{target_file_path}")

                                    target_tree.write(target_file_path, encoding="utf-8", xml_declaration=True)
                                except Exception as e:
                                    INFO.logger.info(f"处理失败：{target_file_path} 错误：{e}")
                            else:
                                ERROR.logger.error(f"未找到目标文件：{target_file_path}")

                except ET.ParseError:
                    INFO.logger.info(f"XML解析失败：{source_file_path}")
                except Exception as e:
                    ERROR.logger.error(f"出错：{source_file_path} 错误：{e}")

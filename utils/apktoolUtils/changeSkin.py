import shutil
from utils.logUtils.logControl import INFO, ERROR
from utils.readFilesUtils.get_path import  get_project_root
import xml.etree.ElementTree as ET


# ===  皮肤资源文件路径  ===
project_path = get_project_root()
target_dir = project_path /'apktool' / 'app_out' / 'res'  # 目标文件夹
source_dir = project_path /'apktool' / 'app_out1' / 'res'  # 资源文件夹


folders_to_cover = ["mipmap", "mipmap-hdpi", "mipmap-ldpi", "mipmap-mdpi", "mipmap-xhdpi", "mipmap-xxhdpi"]

# ===  皮肤颜色资源路径  ===
target_color_file = project_path /'apktool' / 'app_out' / 'res' / 'values' / 'colors.xml'
source_color_file = project_path /'apktool' / 'app_out1' / 'res' / 'values' / 'colors.xml'

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

def get_color_value_from_xml(file_path, color_name):
    """从 XML 文件中获取指定 color 的值"""
    tree = ET.parse(file_path)
    root = tree.getroot()

    for color in root.findall('color'):
        if color.get('name') == color_name:
            return color.text

    return None

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
            INFO.logger.info(f"Updated {color_name} to {color_primary}")
        elif color_name == "pocstar_colorPrimaryAlpha":
            color.text = color_primary_alpha
            INFO.logger.info(f"Updated {color_name} to {color_primary_alpha}")

    # 保存修改后的目标文件
    target_tree.write(target_color_file, encoding="UTF-8", xml_declaration=True)
    INFO.logger.info(f"Successfully updated the colors in {target_color_file}")

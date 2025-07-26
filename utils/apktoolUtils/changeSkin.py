import shutil

from utils.logUtils.logControl import INFO, ERROR
from utils.readFilesUtils.get_path import get_project

project_path = get_project()
target_dir = project_path / 'app_out' / 'res'  # 目标文件夹
source_dir = project_path / 'app_out1' / 'res'  # 资源文件夹

color_dir = project_path / 'app_out' / 'res' / 'values'

folders_to_cover = ["mipmap", "mipmap-hdpi", "mipmap-ldpi", "mipmap-mdpi", "mipmap-xhdpi", "mipmap-xxhdpi"]


def exchange_res():
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
                ERROR.loggin.error(f"目标文件夹 {folder_name} 不存在")
    else:
        ERROR.loggin.error("资源文件夹不存在")

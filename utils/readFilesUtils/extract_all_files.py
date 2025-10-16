import os
import shutil

from utils.logUtils.logControl import INFO, ERROR


def extract_all_files(src_folder, dst_folder):
    try:
        # 确保目标文件夹存在
        if not os.path.exists(dst_folder):
            os.makedirs(dst_folder)

        # 遍历源文件夹中的所有内容（包括子文件夹）
        for root, dirs, files in os.walk(src_folder):
            for file in files:
                src_file_path = os.path.join(root, file)  # 源文件的完整路径

                # 构建目标文件的完整路径
                dst_file_path = os.path.join(dst_folder, file)

                # 复制文件到目标文件夹
                shutil.copy(src_file_path, dst_file_path)

                print(f"Copied {src_file_path} to {dst_file_path}")

    except Exception as e:
        print(f"Error: {e}")

def copy_files(source_dir_color, target_dir_color):
    if not os.path.isfile(source_dir_color):
        raise FileNotFoundError(f"资源文件不存在: {source_dir_color}")

    try:
        shutil.copy2(source_dir_color, target_dir_color)
        INFO.logger.info(f"已覆盖文件：{source_dir_color} -> {target_dir_color}")
    except Exception as e:
        ERROR.logger.error(f"覆盖失败：{e}")

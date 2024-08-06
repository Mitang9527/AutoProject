import datetime
import os
import shutil


def copy_and_modify_files(src_dirs, dst_dirs, file_ext=".dat", minute_add=10):
    """
    从源目录修改文件时间，然后复制特定扩展名的文件到目标目录。

    参数:
    - src_dirs: 源目录列表。
    - dst_dirs: 目标目录列表（与src_dirs对应）。
    - file_ext: 要处理的文件扩展名（默认为".dat"）。
    - minute_add: 要增加的分钟数（默认为10）。
    """
    for src_dir, dst_dir in zip(src_dirs, dst_dirs):
        # 遍历每个源目录中的文件
        for filename in os.listdir(src_dir):
            if filename.endswith(file_ext):
                src_path = os.path.join(src_dir, filename)  # 源文件路径

                # 修改文件时间
                modified_time = os.path.getmtime(src_path)
                new_time = datetime.fromtimestamp(modified_time) + datetime.timedelta(minutes=minute_add)
                os.utime(src_path, (os.path.getatime(src_path), new_time.timestamp()))

                # 复制文件到目标目录
                dst_path = os.path.join(dst_dir, filename)  # 目标文件路径
                shutil.copy(src_path, dst_path)
        print(f"Copied {src_dirs} to {dst_dirs}")
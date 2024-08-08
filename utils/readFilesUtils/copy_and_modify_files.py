#自动增加文件名称且复制，输出日志
import os

import shutil
from datetime import datetime, timedelta

def wlog(log_str, logfile=""):
    """
    记录日志到文件中，带有时间戳。

    参数：
    - log_str: 要记录的日志消息。
    - logfile: 可选，日志文件名（默认为空字符串）。

    日志文件将存储在 './logs/' 目录下，文件名基于当前日期。
    """
    # 格式化日志消息，加上当前时间戳
    txt = f"\n {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {log_str}"
    # 日志文件目录路径
    path = "./logs/"
    # 如果日志目录不存在，则创建
    if not os.path.exists(path):
        os.makedirs(path, 0o777, True)
    # 定义带有当前日期的日志文件路径
    logfile = f"{path}{logfile}{datetime.now().strftime('%Y%m%d')}.log"
    # 写入日志消息到文件
    with open(logfile, "a+") as f:
        f.write(txt)

def copy_and_modify_files(src_dirs, dst_dirs, file_ext=".dat", minute_add=2):
    """
    从源目录修改文件时间，然后复制特定扩展名的文件到目标目录。

    参数:
    - src_dirs: 源目录列表。
    - dst_dirs: 目标目录列表（与src_dirs对应）。
    - file_ext: 要处理的文件扩展名（默认为".dat"）。
    - minute_add: 要增加的分钟数（默认为10）。
    """
    for src_dir, dst_dir in zip(src_dirs, dst_dirs):
        # 如果目标目录不存在，则创建
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir, 0o777, True)

        # 遍历每个源目录中的文件
        for filename in os.listdir(src_dir):
            if filename.endswith(file_ext):
                src_path = os.path.join(src_dir, filename)  # 源文件路径
                dst_path = os.path.join(dst_dir, filename)  # 目标文件路径

                try:
                    # 获取文件的最后修改时间
                    modified_time = os.path.getmtime(src_path)
                    new_time = datetime.fromtimestamp(modified_time) + timedelta(minutes=minute_add)

                    # 修改文件的访问时间和修改时间
                    os.utime(src_path, (os.path.getatime(src_path), new_time.timestamp()))

                    # 复制文件到目标目录
                    shutil.copy(src_path, dst_path)

                    # 记录操作日志
                    wlog(f"Copied {src_path} to {dst_path}")

                except Exception as e:
                    wlog(f"Error copying {src_path} to {dst_path}: {str(e)}")

        wlog(f"Processed {src_dir}")

#删除多个目录下的文件
def delete_files_in_directory(directories):
    """
    删除多个目录下的所有文件和子目录。

    参数:
    - directories: 包含多个目录路径的列表或元组。
    """
    for directory in directories:
        # 确保目录存在
        if not os.path.exists(directory):
            print(f"目录 '{directory}' 不存在。")
            continue

        # 遍历目录中的所有文件和子目录
        for root, dirs, files in os.walk(directory):
            # 删除文件
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    print(f"已删除文件: {file_path}")
                except Exception as e:
                    print(f"删除文件 '{file_path}' 时出错: {str(e)}")

            # 删除子目录
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    shutil.rmtree(dir_path)
                    print(f"已删除目录及其内容: {dir_path}")
                except Exception as e:
                    print(f"删除目录 '{dir_path}' 及其内容时出错: {str(e)}")

        print(f"已完成删除目录 '{directory}' 下的所有文件和子目录。")


src_dirs = ["./source_dir1", "./source_dir2"]
dst_dirs = ["./destination_dir1", "./destination_dir2"]
copy_and_modify_files(src_dirs, dst_dirs)
#删除实例用法
delete_files_in_directory(src_dirs)

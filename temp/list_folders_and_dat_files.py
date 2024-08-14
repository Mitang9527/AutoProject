#win系统遍历全部文件夹筛选出dat并且运行一次自动全部加10分钟

import os
import re
from datetime import datetime, timedelta

def find_folders_with_dat(root_folder):
    """
    递归查找包含 .dat 文件的文件夹。

    参数:
    - root_folder: str, 要开始搜索的根文件夹路径。

    返回:
    - list of str: 包含 .dat 文件的文件夹路径列表。
    """
    folders_with_dat = []

    for root, dirs, files in os.walk(root_folder):
        for file in files:
            if file.lower().endswith(".dat"):
                folders_with_dat.append(root)
                break  # 只添加包含 .dat 文件的文件夹一次

    return folders_with_dat


def process_folder(root_folder):
    """
    处理文件夹中的文件，自动将文件名中的时间增加十分钟，并处理分钟数大于50时的小时数自动增加。

    参数:
    - root_folder: str, 要处理的根文件夹路径。
    """
    try:
        # 匹配文件名的正则表达式模式，例如 "HHMMSS.dat"
        filename_pattern = r'(\d{6})(\.\w+)$'

        for root, dirs, files in os.walk(root_folder):
            for filename in files:
                old_filepath = os.path.join(root, filename)

                # 检查文件是否与模式匹配
                match = re.match(filename_pattern, filename)
                if match:
                    # 从匹配的文件名中提取时间部分
                    time_str = match.group(1)  # 时间部分，例如 "123456"
                    extension = match.group(2)  # 扩展名，例如 ".dat"

                    # 将时间部分解析为 datetime 对象（假设日期部分为当前日期）
                    now = datetime.now()
                    datetime_str = f"{now.strftime('%Y%m%d')} {time_str}"
                    dt = datetime.strptime(datetime_str, '%Y%m%d %H%M%S')

                    # 增加十分钟
                    dt += timedelta(minutes=10)

                    # 检查分钟数是否超过60，自动调整小时数
                    if dt.minute >= 60:
                        dt = dt.replace(minute=dt.minute % 60)
                        dt += timedelta(hours=1)

                    # 生成新的时间字符串
                    new_time_str = dt.strftime('%H%M%S')
                    # 构造新文件名
                    new_filename = f"{new_time_str}{extension}"
                    new_filepath = os.path.join(root, new_filename)

                    # 重命名文件
                    os.rename(old_filepath, new_filepath)
                    print(f"Renamed '{old_filepath}' to '{new_filepath}'")

    except Exception as e:
        print(f"Error processing folder '{root_folder}': {e}")

if __name__ == '__main__':
    root_folder = input("将整个文件夹一起拉过来: ").strip()  # 用户手动输入根文件夹路径
    process_folder(root_folder)


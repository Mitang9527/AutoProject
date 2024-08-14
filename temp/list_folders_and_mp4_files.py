# 实现批量修改文件夹以及子文件夹下的MP4命名
#改进了输入为空实际输出为空的问题
import os
import re


def find_folders_with_mp4(root_folder):
    """
    递归查找包含 .mp4 文件的文件夹。

    参数:
    - root_folder: str, 要开始搜索的根文件夹路径。

    返回:
    - list of str: 包含 .mp4 文件的文件夹路径列表。
    """
    folders_with_mp4 = []

    for root, dirs, files in os.walk(root_folder):
        for file in files:
            if file.lower().endswith(".mp4"):
                folders_with_mp4.append(root)
                break  # 只添加包含 .mp4 文件的文件夹一次

    return folders_with_mp4


def process_folder(root_folder, new_month=None, new_day=None, new_hour1=None, new_hour2=None):
    """
    处理文件夹以根据用户输入重命名文件。

    参数：
    - root_folder: str，开始搜索和处理的根文件夹的路径。
    - new_month：str，用于重命名的新月份。
    - new_day：str，用于重命名的新日期。
    - new_hour1：str，用于重命名的新 hour1。
    - new_hour2：str，用于重命名的新 hour2。
    """
    try:
        # 匹配文件名的正则表达式模式，例如“YYYY-MM-DD_HHMMSS_HHMMSS.ext”
        filename_pattern = r'^(.*?)(\d{4}-\d{2}-\d{2}_)(\d{6}_)(\d{6})(\.\w+)$'

        for root, dirs, files in os.walk(root_folder):
            for filename in files:
                old_filepath = os.path.join(root, filename)

                # 检查文件是否与模式匹配
                match = re.match(filename_pattern, filename)
                if match:
                    # 从匹配的文件名中提取部分
                    prefix = match.group(1)
                    date_part = match.group(2)  # Date part
                    time1_part = match.group(3)  # First time part
                    time2_part = match.group(4)  # Second time part
                    extension = match.group(5)

                    # 构造新文件名的日期部分
                    new_date_part = date_part[:5]
                    if new_month:
                        new_date_part += f"{new_month}-"
                    else:
                        new_date_part += date_part[5:7] + "-"
                    if new_day:
                        new_date_part += f"{new_day}_"
                    else:
                        new_date_part += date_part[8:10] + "_"

                    # 构造新文件名的时间部分
                    new_time1_part = time1_part
                    if new_hour1:
                        new_time1_part = f"{new_hour1}{time1_part[2:6]}"
                    elif time1_part.endswith("_"):  # 处理原始文件名中末尾可能存在的下划线
                        new_time1_part = time1_part[:-1]  # 去除末尾的下划线

                    new_time2_part = time2_part
                    if new_hour2:
                        new_time2_part = f"{new_hour2}{time2_part[2:]}"

                    # 构造新文件名
                    new_filename = f"{prefix}{new_date_part}{new_time1_part}_{new_time2_part}{extension}"
                    new_filepath = os.path.join(root, new_filename)

                    # 重命名文件
                    os.rename(old_filepath, new_filepath)
                    print(f"Renamed '{old_filepath}' to '{new_filepath}'")

    except Exception as e:
        print(f"Error processing folder '{root_folder}': {e}")


def list_folders_and_mp4_files(root_folder):
    """
    列出包含 .mp4 文件及其文件名的文件夹，并根据用户输入修改文件名。

    参数：
    - root_folder: str，开始搜索的根文件夹的路径。
    """
    folders_with_mp4 = find_folders_with_mp4(root_folder)

    if folders_with_mp4:
        print(f"Found {len(folders_with_mp4)} folder(s) containing .mp4 files:")
        for folder in folders_with_mp4:
            print(f"Folder: {folder}")
            mp4_files = [file for file in os.listdir(folder) if file.lower().endswith(".mp4")]
            if mp4_files:
                print(f"  Found {len(mp4_files)} .mp4 file(s):")
                for mp4_file in mp4_files:
                    print(f"  - {mp4_file}")
                print()

        # 提示用户确认新的月份、日期和时间（保留原数值）
        current_date_part = mp4_files[0][5:10]
        current_time1_part = mp4_files[0][11:13]
        current_time2_part = mp4_files[0][18:20]

        new_month = input(f"确认新的月份 (当前值: {current_date_part[0:2]}) (留空保持原数值): ").strip() or None
        new_day = input(f"确认新的日期 (当前值: {current_date_part[3:5]}) (留空保持原数值): ").strip() or None
        new_hour1 = input(f"确认新的小时1 (当前值: {current_time1_part[:2]}) (留空保持原数值): ").strip() or None
        new_hour2 = input(f"确认新的小时2 (当前值: {current_time2_part[:2]}) (留空保持原数值): ").strip() or None

        # 处理每个文件夹根据用户输入
        for folder in folders_with_mp4:
            process_folder(folder, new_month, new_day, new_hour1, new_hour2)

    else:
        print("No folders containing .mp4 files found.")

def open_folder(root_folder):
    try:
        os.startfile(root_folder)
    except Exception as e:
        print(f"Failed to open folder: {e}")


if __name__ == "__main__":
    root_folder = input("将整个文件夹一起拉过来: ").strip()  # 用户手动输入根文件夹路径
    # root_folder = r'C:\Users\EDY\Desktop\测试资源\视频物料\hmgy'
    list_folders_and_mp4_files(root_folder)
    open_folder(root_folder)
#将源文件夹包括子文件夹全部解包到目标文件夹下
import os
import shutil


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


# 示例用法
src_folder = r'C:\Users\EDY\Desktop\新建文件夹 (2)'  # 替换为实际的源文件夹路径
dst_folder = r'C:\Users\EDY\Desktop\新建文件夹 (3)'  # 替换为实际的目标文件夹路径

extract_all_files(src_folder, dst_folder)
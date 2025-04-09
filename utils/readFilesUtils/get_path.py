import os
import sys
from pathlib import Path

def get_script_root() -> Path:
    """
    获取当前脚本所在的根目录。
    通过向上查找，直到找到脚本所在目录的上级目录。
    :return: 项目根目录的路径
    """
    # 获取当前脚本的绝对路径
    script_path = Path(__file__).resolve()

    # 返回当前脚本所在的目录的上级目录
    return script_path.parent

def get_project() -> Path:
    """
    :return: 当前脚本路径
    """
    current_path = Path(os.getcwd())
    return current_path

def get_project_root() -> Path:
    """
    获取项目的最根目录，假设根目录下有特定的标识文件，如 '.git' 目录或 'README.md' 等。
    :return: 项目根目录的路径
    """
    current_path = Path(__file__).resolve()  # 获取当前脚本的绝对路径

    # 向上遍历，直到找到根目录（根据实际需求可以根据某个标识文件来判断）
    while current_path != current_path.parent:  # 当目录不是根目录时
        if (current_path / '.git').exists() or (current_path / 'README.md').exists():
            # 找到了标识文件，返回当前目录作为根目录
            return current_path
        current_path = current_path.parent  # 向上一级目录移动

    return current_path

def get_absolute_path(path):
    """
        返回文件的绝对路径
        如果路径包含起点（例如Unix '/'），则使用指定的起点
        而不是当前工作目录。文件路径的起点是
        允许以波浪号“~”开头，它将被用户的主目录替换。
    """
    fp, fn = os.path.split(path)
    if not fp:
        fp = os.getcwd()
    fp = os.path.abspath(os.path.expanduser(fp))
    return os.path.join(fp, fn)


def get_program_directory():
    """ 获取程序运行所在目录 """
    if getattr(sys, 'frozen', False):
        # 如果是打包后的可执行文件
        base_path = sys._MEIPASS  # 获取打包后的临时路径
    else:
        # 如果是开发中的脚本
        base_path = os.path.dirname(os.path.realpath(__file__))  # 获取当前脚本的目录

    return base_path



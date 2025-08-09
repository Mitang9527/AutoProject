import json
from utils.logUtils.logControl import ERROR


def load_json(file_path: str):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        pretty_json = json.dumps(data, indent=4, ensure_ascii=False)
        return pretty_json

    except Exception as e:
        ERROR.logger.error("打开失败", f"无法读取 JSON 文件：\n{e}")
        return False

def save_json(file_path: str):
    pass


def get_json_field(file_path, field_path):
    """
    获取指定 JSON 文件中的字段值

    :param file_path: JSON 文件路径
    :param field_path: 字段路径（以列表形式传入，如 ['ui', 'launcherModule']）
    :return: 字段值
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        temp_data = data
        for key in field_path:
            temp_data = temp_data[key]

        return temp_data

    except KeyError as e:
        ERROR.logger.error(f"字段 '{e.args[0]}' 不存在！")
        return None
    except json.JSONDecodeError as e:
        ERROR.logger.error(f"JSON 格式错误: {e}")
        return None
    except Exception as e:
        ERROR.logger.error(f"发生错误: {e}")
        return None

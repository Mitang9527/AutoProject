import json
from utils.logUtils.logControl import ERROR, INFO

def load_json(file_path: str):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    except Exception as e:
        ERROR.logger.error(f'发生错误{e}')

def save_json(file_path, json_str) -> bool:
    """
    保存 JSON 字符串到文件，先校验格式。

    :param file_path: 保存文件路径
    :param json_str: JSON 字符串
    :return: 成功返回 True，失败返回 False
    """
    try:
        # 从传入的字符串解析，校验格式
        data = json.loads(json_str)

        # 格式化写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        INFO.logger.info(f"{file_path} 保存成功")
        return True
    except json.JSONDecodeError as e:
        ERROR.logger.error(f"JSON 格式错误: {e}")
        return False
    except Exception as e:
        ERROR.logger.error(f"保存文件出错: {e}")
        return False

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

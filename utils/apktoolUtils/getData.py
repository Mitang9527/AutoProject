import json

from utils.logUtils.logControl import ERROR


def get_json_field(file_path, field_path):
    """
    获取指定 JSON 文件中的字段值

    :param file_path: JSON 文件路径
    :param field_path: 字段路径（以列表形式传入，如 ['ui', 'launcherModule']）
    :return: 字段值
    """
    try:
        # 读取 JSON 文件
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 获取 field_path 对应的字段值
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

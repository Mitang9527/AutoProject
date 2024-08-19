import os
import ast
import yaml
from typing import Any, Dict, List, Union
from utils.readFilesUtils.regularControl import regular

class GetYamlData:
    """ 获取 yaml 文件中的数据 """

    def __init__(self, file_dir: str):
        self.file_dir = str(file_dir)

    def get_yaml_data(self) -> Union[Dict[str, Any], List[Any]]:
        """
        获取 yaml 中的数据
        :return: 解析后的数据，可以是字典或列表
        """
        if os.path.exists(self.file_dir):
            with open(self.file_dir, 'r', encoding='utf-8') as data:
                res = yaml.load(data, Loader=yaml.FullLoader)
        else:
            raise FileNotFoundError("文件路径不存在")
        return res

    def write_yaml_data(self, key: str, value: Any) -> int:
        """
        更改 yaml 文件中的值, 并且保留注释内容
        :param key: 字典的 key
        :param value: 写入的值
        :return: 如果找到并更改了值，返回 1，否则返回 0
        """
        with open(self.file_dir, 'r', encoding='utf-8') as file:
            lines = [line for line in file.readlines() if line.strip()]

        with open(self.file_dir, 'w', encoding='utf-8') as file:
            flag = 0
            for line in lines:
                left_str = line.split(":")[0].strip()
                if key == left_str and '#' not in line:
                    newline = f"{left_str}: {value}"
                    file.write(f'{newline}\n')
                    flag = 1
                else:
                    file.write(f'{line}')
            return flag

    def convert_dict_to_list(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        将字典转换为包含字典项的列表
        :param data: 输入的字典
        :return: 包含字典项的列表
        """
        return [{"name": k, "config": v} for k, v in data.items()]

class GetCaseData(GetYamlData):
    """ 获取测试用例中的数据 """

    def get_different_formats_yaml_data(self) -> List[Any]:
        """
        获取兼容不同格式的yaml数据
        :return: 返回所有数据
        """
        yaml_data = self.get_yaml_data()
        if isinstance(yaml_data, dict):
            return self.convert_dict_to_list(yaml_data)
        elif isinstance(yaml_data, list):
            return yaml_data
        else:
            raise ValueError("不支持的 YAML 数据格式")

    def get_yaml_case_data(self) -> Any:
        """
        获取测试用例数据, 转换成指定数据格式
        :return: 转换后的数据
        """
        yaml_data = self.get_yaml_data()
        re_data = regular(str(yaml_data))
        return ast.literal_eval(re_data)

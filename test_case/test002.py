import yaml
from common.setting import ensure_path_sep

# 配置文件名
config_name = "config.yaml"
file_path = ensure_path_sep("\\common\\" + config_name)

# 读取 YAML 文件内容
with open(file_path, 'r', encoding='utf-8') as file:
    yaml_data = yaml.load(file, Loader=yaml.FullLoader)

# 提取 'ConnectClient' 字段
connect_client_data = yaml_data.get('ConnectClient', [])

# 打印每个字典中的 'name' 字段
print("ConnectClient 中的 name 字段内容：")
for client in connect_client_data:
    name = client.get('name')
    print(name)



from utils.otherUtils.ConnectServer.ParamikoSSH import SSHClient, connect_to_servers
from utils.readFilesUtils.yamlControl import GetYamlData
from common.setting import ensure_path_sep
from utils.otherUtils.models import Config
import sys

args = sys.argv
config_name = "config.yaml"
if len(args) > 1 and "config.yaml" in args[1]:
    config_name = args[1]

print(f">>>>>>>>>>>>> load config file: {config_name} >>>>>>>>>>>>>>")

# 加载配置文件
yaml_data = GetYamlData(ensure_path_sep("\\common\\" + config_name)).get_yaml_data()
config = Config(**yaml_data)

# 获取服务器列表并连接
config_file_path = ensure_path_sep("\\common\\" + config_name)
clients = connect_to_servers(config_file_path)


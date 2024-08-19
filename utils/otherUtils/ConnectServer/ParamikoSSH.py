import sys

import paramiko
import yaml
from common.setting import ensure_path_sep
from utils.readFilesUtils.yamlControl import GetYamlData
from utils.otherUtils.models import Config
from utils.logUtils.logControl import INFO, ERROR



class SSHClient:

    def __init__(self, server_config):
        """
        初始化 SSHClient 实例

        :param server_config: 包含服务器配置信息的字典
        """
        self.name = server_config.get('name', 'default_name')
        self.hostname = server_config.get('host')
        self.username = server_config.get('user')
        self.password = server_config.get('password')
        self.port = server_config.get('port', 22)
        self.client = None
        self.switch = server_config.get('Switch', False)

        if self.switch:
            self.connect()
        else:
            ERROR.logger.error(f'无法连接至 {self.name} {self.hostname}, 因为开关关闭')

    def connect(self):
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(hostname=self.hostname,
                                username=self.username,
                                password=self.password,
                                port=self.port)
            INFO.logger.info(f"已连接至 {self.name} {self.hostname}")
        except Exception as e:
            ERROR.logger.error(f"无法连接至 {self.name} {self.hostname}: {e}")

    def execute_command(self, command):
        """
        在 SSH 服务器上执行命令

        :param command: 要执行的命令
        :return: 命令的输出和错误信息
        """
        if self.client is None:
            raise Exception("未建立连接。请先检查 connect()。.")
        stdin, stdout, stderr = self.client.exec_command(command)
        return stdout.read().decode(), stderr.read().decode()

    def close(self):
        """
        关闭 SSH 连接
        """
        if self.client:
            self.client.close()
            INFO.logger.info(f"已关闭  {self.name} {self.hostname} 连接")


def connect_to_servers(config_file):
    # 读取 YAML 文件
    with open(config_file, 'r', encoding='utf-8') as file:
        yaml_data = yaml.safe_load(file)

    # 获取所有服务器的配置
    servers = yaml_data['ConnectClient']

    # 遍历每个服务器的配置
    clients = []
    for server in servers:
        ssh_client = SSHClient(server)  # 这里传递了 server 配置字典
        clients.append(ssh_client)

    return clients


args = sys.argv
config_name = "config.yaml"
if len(args) > 1 and "config.yaml" in args[1]:
    config_name = args[1]

yaml_data = GetYamlData(ensure_path_sep("\\common\\" + config_name)).get_yaml_data()
config = Config(**yaml_data)

# 获取服务器列表并实例化 SSHClient
clients_config = yaml_data.get('ConnectClient', [])
clients = [SSHClient(config) for config in clients_config]

# # 获取服务器列表并连接
# config_name = "config.yaml"
# config_file_path = ensure_path_sep("\\common\\" + config_name)
# clients = connect_to_servers(config_file_path)
#
# # 使用每个客户端
# for client in clients:
#     client.connect()
#     stdout, stderr = client.execute_command('python3 /script/sstygsc.py')
#     print("STDOUT:", stdout)
#     print("STDERR:", stderr)
#     client.close()







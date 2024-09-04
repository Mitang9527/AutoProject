import subprocess
import sys

import paramiko
import yaml

from common.setting import ensure_path_sep
from utils import yaml_data
from utils.logUtils.logControl import INFO, ERROR, WARNING
from utils.otherUtils.models import Config
from utils.readFilesUtils.yamlControl import GetYamlData
from utils.timeUtils.time_control import now_time_day



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
            INFO.logger.info(f"{self.name}:{self.hostname} 开关为True,开始连接服务器...")
            # self.connect()
        else:
            WARNING.logger.warning(f'{self.name}:{self.hostname}, 开关未打开')

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
            raise Exception("未建立连接,请先检查服务器状态.")
        stdin, stdout, stderr = self.client.exec_command(command)


        # stdin 是一个 ChannelFile 对象，用于向远程进程发送输入（如果需要）。
        # stdout 是一个 ChannelFile 对象，用于读取远程进程的标准输出。
        # stderr 是一个 ChannelFile 对象，用于读取远程进程的标准错误输出。

        return (stdout.read().decode(),
                stderr.read().decode())

    def close(self):
        """
        关闭 SSH 连接
        """
        if self.client:
            self.client.close()
            INFO.logger.info(f"已关闭:{self.name}：{self.hostname} 连接")


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


# 获取服务器列表并实例化 SSHClient
clients_config = yaml_data.get('ConnectClient', [])
clients = [SSHClient(config) for config in clients_config]

# # 遍历客户端列表筛选开关状态
# for client in clients:
#     if client.switch:
#         client.connect()
#
#         stdout, stderr = client.execute_command('python3 /home/lzroot/yzssly_scipt.py')
#         print("STDOUT:", stdout)
#         print("STDERR:", stderr)
#         client.close()
#TODO 待定方案

# for client in clients:
#     if client.switch:
#         client.connect()
#         process = subprocess.Popen(
#             ['python', r'.\script\hmgy_scipt.py'],
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE,
#             text=True,
#             bufsize=1,  # 行缓冲
#             universal_newlines=True,  # 处理换行符
#             encoding='utf-8' #指定编码utf8
#         )
#
#         # 实时读取并打印 stdout 和 stderr
#         try:
#             for line in iter(process.stdout.readline, ''):
#                 print(f"STDOUT: {line.strip()}")
#             for line in iter(process.stderr.readline, ''):
#                 print(f"STDERR: {line.strip()}")
#         except Exception as e:
#             print(f"Error: {e}")
#
#         finally:
#             # 确保流和进程被正确关闭
#             process.stdout.close()
#             process.stderr.close()
#             process.wait()
#     client.close()










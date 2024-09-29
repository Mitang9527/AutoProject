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

    def execute_command(self, command, timeout=60):
        """
        在 SSH 服务器上执行命令

        :param command: 要执行的命令
        :param timeout: 命令执行的超时时间（秒）
        :return: 命令的输出和错误信息
        """
        if self.client:
            try:
                # 执行命令
                stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)

                # 读取输出
                stdout_output = stdout.read().decode()
                stderr_output = stderr.read().decode()

                # 确保流关闭
                stdout.channel.shutdown_read()
                stderr.channel.shutdown_read()

                if stderr_output:
                    print(f"错误信息: {stderr_output}")

                return stdout_output, stderr_output

            except paramiko.SSHException as e:
                raise Exception(f"SSH 执行命令时出现错误: {e}")
            except Exception as e:
                raise Exception(f"执行命令时出现异常: {e}")

        else:
            raise Exception("未建立连接，请先检查服务器状态。")

    def execute_python_script(self,script_path):
        """
            执行一个Python脚本并实时打印其标准输出和错误输出。
            :param script_path: 要执行的Python脚本的路径。
            """
        try:
            # 使用subprocess启动一个子进程来执行Python脚本
            process = subprocess.Popen(
                ['python3', script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # 行缓冲
                universal_newlines=True,  # 处理换行符
                encoding='utf-8'  # 指定编码为utf-8
            )

            # 实时读取并打印标准输出
            for line in iter(process.stdout.readline, ''):
                print(f"STDOUT: {line.strip()}")

            # 实时读取并打印错误输出
            for line in iter(process.stderr.readline, ''):
                print(f"STDERR: {line.strip()}")

        except Exception as e:
            print(f"Error: {e}")

        finally:
            # 确保流和进程被正确关闭
            process.stdout.close()
            process.stderr.close()
            process.wait()

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

# 遍历客户端列表筛选开关状态
for client in clients:
    if client.switch:
        client.connect()
        stdout, stderr = client.execute_command('python3 /home/lzroot/hmgy_scipt.py')
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        client.close()










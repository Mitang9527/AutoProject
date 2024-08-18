import paramiko
from utils import config
from utils.logUtils.logControl import INFO, ERROR


class SSHClient():

        def __init__(self):

            self.hostname = config.ConnectClient.host
            self.username = config.ConnectClient.user
            self.password = config.ConnectClient.password
            self.port = config.ConnectClient.port
            self.client = None

            if not config.ConnectClient.switch:
                ERROR.logger.error(f'无法连接至{self.hostname}'+'，请检查配置文件')
                return

            self.connect()

        def connect(self):


            try:
                self.client = paramiko.SSHClient()
                self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.client.connect(hostname = self.hostname,
                                    username=self.username,
                                    password=self.password,
                                    port=self.port)
                INFO.logger.info(f"Connected to {self.hostname}")
            except Exception as e:
                ERROR.logger.error(f"Failed to connect to {self.hostname}: {e}")

        def execute_command(self, command):
            """
            在 SSH 服务器上执行命令

            :param command: 要执行的命令
            :return: 命令的输出和错误信息
            """
            if self.client is None:
                raise Exception("未建立连接。请先检查 connect()。.")
            stdin, stdout, stderr = self.client.exec_command(command)
            return stdout.read().decode(),\
                   stderr.read().decode()

        def close(self):
            """
            关闭 SSH 连接
            """
            if self.client:
                self.client.close()
                print(f"Connection to {self.hostname} closed")



# 使用示例
# ssh_client = SSHClient()
# ssh_client.connect()
# stdout, stderr = ssh_client.execute_command('python3 /script/sstygsc.py')
# print("STDOUT:", stdout)
# print("STDERR:", stderr)
# ssh_client.close()

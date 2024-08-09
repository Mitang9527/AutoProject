import paramiko
from utils import config

class SSHClient:

    if config.ConnectClient.switch:
        def __init__(self,hostname, username, password, port=22):
            """
            初始化 SSHClient 类
            :param type: 服务器类型
            :param hostname: 服务器地址
            :param username: SSH 用户名
            :param password: SSH 密码
            :param port: SSH 端口，默认是22
            """
            self.hostname = config.SSHConnectClient.host
            self.username = config.SSHConnectClient.user
            self.password = config.SSHConnectClient.password
            self.port = config.SSHConnectClient.port
            self.client = None

        def connect(self):
            """
            连接到 SSH 服务器
            """
            try:
                self.client = paramiko.SSHClient()
                self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.client.connect(self.hostname, username=self.username, password=self.password, port=self.port)
                print(f"Connected to {self.hostname}")
            except Exception as e:
                print(f"Failed to connect to {self.hostname}: {e}")

        def execute_command(self, command):
            """
            在 SSH 服务器上执行命令

            :param command: 要执行的命令
            :return: 命令的输出和错误信息
            """
            if self.client is None:
                raise Exception("Connection not established. Call connect() first.")
            stdin, stdout, stderr = self.client.exec_command(command)
            return stdout.read().decode(), stderr.read().decode()

        def close(self):
            """
            关闭 SSH 连接
            """
            if self.client:
                self.client.close()
                print(f"Connection to {self.hostname} closed")

# 使用示例
ssh_client = SSHClient(hostname='example.com', username='user', password='password')
ssh_client.connect()
stdout, stderr = ssh_client.execute_command('python3 /script/sstygsc.py')
print("STDOUT:", stdout)
print("STDERR:", stderr)
ssh_client.close()

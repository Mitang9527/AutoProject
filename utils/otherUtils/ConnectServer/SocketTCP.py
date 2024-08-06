import socket

class TCPClient:
    def __init__(self, host, port):
        """
        初始化 TCPClient 类

        :param host: 服务器地址
        :param port: 服务器端口
        """
        self.host = host
        self.port = port
        self.client_socket = None

    def connect(self):
        """
        连接到 TCP 服务器
        """
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.host, self.port))
            print(f"Connected to {self.host}:{self.port}")
        except Exception as e:
            print(f"Failed to connect to {self.host}:{self.port}: {e}")

    def send(self, message):
        """
        发送消息到服务器

        :param message: 要发送的消息
        """
        if self.client_socket is None:
            raise Exception("Connection not established. Call connect() first.")
        self.client_socket.sendall(message.encode())

    def receive(self, buffer_size=1024):
        """
        接收来自服务器的消息

        :param buffer_size: 缓冲区大小
        :return: 接收到的消息
        """
        if self.client_socket is None:
            raise Exception("Connection not established. Call connect() first.")
        return self.client_socket.recv(buffer_size).decode()

    def close(self):
        """
        关闭 TCP 连接
        """
        if self.client_socket:
            self.client_socket.close()
            print(f"Connection to {self.host}:{self.port} closed")

# 使用示例
tcp_client = TCPClient(host='localhost', port=8080)
tcp_client.connect()
tcp_client.send("Hello, Server!")
response = tcp_client.receive()
print("Received:", response)
tcp_client.close()

import requests

class HTTPClient:
    def __init__(self, base_url):
        """
        初始化 HTTPClient 类

        :param base_url: 基础 URL
        """
        self.base_url = base_url

    def get(self, endpoint, params=None):
        """
        发送 GET 请求

        :param endpoint: API 端点
        :param params: 查询参数
        :return: JSON 响应
        """
        try:
            response = requests.get(f"{self.base_url}/{endpoint}", params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None

    def post(self, endpoint, data=None, json=None):
        """
        发送 POST 请求

        :param endpoint: API 端点
        :param data: 表单数据
        :param json: JSON 数据
        :return: JSON 响应
        """
        try:
            response = requests.post(f"{self.base_url}/{endpoint}", data=data, json=json)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None

# 使用示例
# http_client = HTTPClient(base_url='https://jsonplaceholder.typicode.com')
# response = http_client.get('posts')
# print(response)

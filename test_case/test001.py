import pytest


class Test001():
    def test001(self):
        print("测试输出")




if __name__ == '__main__':
    pytest.main((['test001.py', '-s']))
import allure
import pytest

from utils.otherUtils.ConnectServer.ParamikoSSH import clients
import subprocess

@allure.epic("wty自动化测试")
@allure.feature("虎门公园")
class Testhmgy():

    @pytest.fixture(scope="class")
    def ssh_client_and_command(self):

        for client in clients:
            if client.switch:
                client.connect()
                print("开始执行脚本...")

                process = subprocess.Popen(
                    ['python', r'D:\Code\wty_test\script\hmgy_scipt.py'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,  # 行缓冲
                    universal_newlines=True,  # 处理换行符
                    encoding='utf-8' #指定编码utf8
                )

                # 实时读取并打印 stdout 和 stderr
                try:
                    for line in iter(process.stdout.readline, ''):
                        print(f"STDOUT: {line.strip()}")
                    for line in iter(process.stderr.readline, ''):
                        print(f"STDERR: {line.strip()}")
                except Exception as e:
                    print(f"Error: {e}")

                finally:
                    # 确保流和进程被正确关闭
                    process.stdout.close()
                    process.stderr.close()
                    process.wait()

            client.close()



        # mysql_db = MysqlDB()  # 数据库连接实例化
        # yield mysql_db
        # mysql_db.__del__()  # 数据库断开连接

    @allure.story("爬山车")
    def test_psc(self,ssh_client_and_command,):
        assert 1==1


        # #TODO 数据库断言
        # mysql_db = MysqlDB()
        # a = mysql_db.query(sql="select * from `test_obp_configure`.lottery_prize where activity_id = 3")
        # print(a)


if __name__ == '__main__':
    pytest.main(['test_hmgy.py', '-s', '-W', 'ignore:Module already imported:pytest.PytestWarning'])


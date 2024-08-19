import allure

from utils import config
from utils.assertion.assert_control import Assert
import pytest
from utils.otherUtils.ConnectServer.ParamikoSSH import SSHClient, clients
from utils.mysqlUtils.mysqlControl import MysqlDB
import subprocess

@allure.epic("wty自动化测试")
@allure.feature("虎门公园")
class Testhmgy():

    @pytest.fixture(scope="class")
    def ssh_client_and_command(self):



        client = None


        try:


                Client = SSHClient()     # 服务器连接实例化
            # Client.execute_command('python3 /script/hmgy_scipt.py')  # 在用例执行前运行脚本
                for client in clients:
                    if client.switch:
                        Client.connect()  # 确保连接成功

                        print("开始执行脚本...")
                        process = subprocess.Popen(['python', '.\wty_test\script/hmgy_script.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                        # 等待脚本执行结束
                        stdout, stderr = process.communicate()
                        print("执行脚本介结束...")

                        for line in stdout.splitlines():
                            print("hmgy_script.py脚本执行:",line,end="")

                        for line in stderr.splitlines():
                            print("hmgy_script.py脚本执行错误:",line,end="")


                        yield client

        except Exception as error:
            pytest.fail(f"Fixture设置失败: {error}")
            Client.close()

        finally:
            if client:
                client.close()
        # 在脚本结束后关闭服务器连接

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


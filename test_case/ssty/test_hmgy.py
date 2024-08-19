import allure
import clients as clients

import pytest

from utils.otherUtils.ConnectServer.ParamikoSSH import clients
import subprocess

@allure.epic("wty自动化测试")
@allure.feature("虎门公园")
class Testhmgy():

    @pytest.fixture(scope="class")
    def ssh_client_and_command(self):

        if clients:
            print("开始执行脚本...")
            process = subprocess.Popen(['python', './wty_test/script/hmgy_script.py'], stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True)
            # 等待脚本执行结束
            stdout, stderr = process.communicate()
            print("执行脚本结束...")

            for line in stdout.splitlines():
                print("hmgy_script.py脚本执行:", line, end="")

            for line in stderr.splitlines():
                print("hmgy_script.py脚本执行错误:", line, end="")



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


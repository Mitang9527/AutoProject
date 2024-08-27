import allure
import pytest
from script.hmgy_scipt import src_dir,dst_dir,src_dir_dbc,dst_dir_dbc
from utils.assertion.assert_control import Assert

from utils.readFilesUtils.copy_and_modify_files import copy_and_modify_files
from utils.otherUtils.ConnectServer.ParamikoSSH import clients
from utils.timeUtils.time_control import now_time_day, tomorrow_time_day


@allure.epic("wty自动化测试")
@allure.feature("虎门公园")
class Testhmgy():

    @pytest.fixture(scope="class")
    #前置连接服务器
    def ssh_client(self):
        #记录开关打开状态
        connected_clients = []
        for client in clients:
            if client.switch:
                client.connect()
            connected_clients.append(client)

        yield
        for client in connected_clients:
            client.close()

    @allure.story("过山车")
    def test_gsc(self,ssh_client):
        #执行虎门公园过山车脚本
        copy_and_modify_files(src_dir, dst_dir,file_ext = "dat",minute_add = 10)
    @allure.title("收集模块")
    def test_gsc_collect(self):
        #从c_video_collect表中获取数据进行断言
        # TODO 需要做等待,从脚本执行到云端有时间延误
        sql_query = """
        SELECT COUNT(id)
        FROM c_video_collection
        WHERE create_time BETWEEN '{}' AND '{}'
        ORDER BY id DESC;
        """.format(now_time_day,tomorrow_time_day )

        Assert.sql_switch_handle(self,sql_query)
    @allure.title("收集模块")


    @allure.story("大摆锤")
    def test_gsc(self,ssh_client):
        #执行虎门公园大摆锤脚本
        copy_and_modify_files(src_dir_dbc, dst_dir_dbc,file_ext = "dat",minute_add = 10)




if __name__ == '__main__':
    pytest.main(['test_hmgy.py', '-s', '-W', 'ignore:Module already imported:pytest.PytestWarning'])



import allure
import pytest
from script.hmgy_scipt import src_dir,dst_dir,src_dir_hdc,dst_dir_hdc
from utils.readFilesUtils.copy_and_modify_files import copy_and_modify_files
from utils.otherUtils.ConnectServer.ParamikoSSH import clients
from utils.mysqlUtils.mysqlControl import mysql_db
from utils.timeUtils.time_control import now_time_day, tomorrow_time_day

@allure.epic("wty自动化测试")
@allure.feature("虎门公园")
class Testhmgy():

    @pytest.fixture(scope="class")
    #前置连接服务器
    def ssh_client(self):

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

    @allure.title("过山车-云端收集")
    def test_gsc_collect(self):
        #从c_video_collect表中获取数据进行断言
        sql_query = """
        SELECT COUNT(id)
        FROM c_video_collection
        WHERE create_time BETWEEN '{}' AND '{}';
        """.format(now_time_day,tomorrow_time_day )

        expected_result = "待填入的预期结果"
        result = mysql_db.wait_for_result(sql_query, expected_result=expected_result)
        assert result and result[0].get('count') == expected_result #断言

    @allure.title("过山车-云端推理")
    #从c_inference中获取数据进行断言

    @allure.title("过山车-云端识别")


    @allure.title("过山车-云端生成")




    @allure.story("海盗船")
    def test_gsc(self,ssh_client):
        #执行虎门公园大摆锤脚本
        copy_and_modify_files(src_dir_hdc, dst_dir_hdc,file_ext = "dat",minute_add = 10)




if __name__ == '__main__':
    pytest.main(['test_hmgy.py', '-s', '-W', 'ignore:Module already imported:pytest.PytestWarning'])



import allure
import pytest
from script.hmgy_scipt import src_dir,dst_dir
from utils.readFilesUtils.copy_and_modify_files import copy_and_modify_files
from utils.ConnectServer.ParamikoSSH import clients
from utils.mysqlUtils.mysqlControl import mysql_db
from utils.timeUtils.time_control import now_time_day, tomorrow_time_day

@pytest.fixture(scope="class")
def ssh_client():
    connected_clients = []
    for client in clients:
        if client.switch:
            client.connect()
        connected_clients.append(client)

    # 提供客户端给测试类
    yield connected_clients

    # 结束时关闭连接
    for client in connected_clients:
        client.close()


@pytest.mark.usefixtures("ssh_client")

@allure.epic("wty自动化测试")
@allure.feature("虎门公园")
class Test_hmgy():

    @pytest.fixture(autouse=True)
    def setup_class(self, ssh_client):
        self.ssh_client = ssh_client

    @allure.story("过山车")
    @allure.title("过山车执行脚本")
    def test_gsc(self):
        with allure.step("执行虎门公园过山车脚本"):
            for client in self.ssh_client:
                if client.switch:
                    copy_and_modify_files(src_dir,dst_dir,file_ext="dat", minute_add=10)


    @allure.story("过山车")
    @allure.title("云端收集")
    # 从c_video_collect表中获取数据进行断言
    def test_gsc_collect(self):
        sql_query = """
        SELECT COUNT(id)
        FROM sit.c_video_collection
        WHERE create_time BETWEEN '{} 00:00:00' AND '{} 00:00:00';
        """.format(now_time_day,tomorrow_time_day)

        expected_result = {'COUNT(id)': 5}
        result = mysql_db.wait_for_result(sql_query,timeout=6,interval=5,expected_result=expected_result)
        assert result and result[0].get('COUNT(id)') == 5

    @allure.story("过山车")
    @allure.title("过山车-云端启动")
    # 从c_project_record获取数据进行断言
    def test_gsc_record(self):
        sql_query = """
            select count(id)
            from sit.c_project_record where project_name = 'HMGY_roller_coaster' 
            and is_push = 1
            and is_finish = 1 
            and create_time BETWEEN '{} 00:00:00' AND '{} 00:00:00';
            """.format(now_time_day, tomorrow_time_day)

        expected_result = {'COUNT(id)': 2}
        result = mysql_db.wait_for_result(sql_query, timeout=3, interval=5, expected_result=expected_result)
        assert result and result[0].get('COUNT(id)') == 2

    @allure.story("过山车")
    @allure.title("过山车-云端推理")
    # 从c_inference中获取数据进行断言
    def test_gsc_inference(self):
        sql_query = """
        select count(id)
        from sit.c_inference where project = 'HMGY_roller_coaster' 
        and state = 4 
        and create_time BETWEEN '{} 00:00:00' AND '{} 00:00:00';
        """.format(now_time_day,tomorrow_time_day )

        expected_result = {'COUNT(id)': 8}
        result = mysql_db.wait_for_result(sql_query,timeout=2,interval=3,expected_result=expected_result)
        assert result and result[0].get('COUNT(id)') == 8

    @allure.story("过山车")
    @allure.title("过山车-云端识别")
    # 从c_inference中获取数据进行断言
    def test_gsc_recognized(self):
        sql_query = """
        select count(id)
        from sit.c_recognized where project = 'HMGY_roller_coaster' 
        and create_time BETWEEN '{} 00:00:00' AND '{} 00:00:00';
        """.format(now_time_day,tomorrow_time_day )

        expected_result = {'COUNT(id)': 2}
        result = mysql_db.wait_for_result(sql_query,timeout=2,interval=3,expected_result=expected_result)
        assert result and result[0].get('COUNT(id)') == 2

    @allure.story("过山车")
    @allure.title("过山车-生成")
    # 从b_user_resource中获取数据进行断言
    def test_gsc_resource(self):
        allure.description("开启了一条测试故事线生成一条视频")
        sql_query = """
        select count(id)
        from sit.b_user_resource where  status = 1 
        and create_time BETWEEN '{} 00:00:00' AND '{} 00:00:00';
        """.format(now_time_day,tomorrow_time_day )

        expected_result = {'COUNT(id)': 1}
        result = mysql_db.wait_for_result(sql_query,timeout=2,interval=3,expected_result=expected_result)
        assert result and result[0].get('COUNT(id)') == 1


if __name__ == '__main__':
    pytest.main(['test_hmgy.py', '-s', '-W', 'ignore:Module already imported:pytest.PytestWarning'])







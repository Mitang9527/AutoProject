"""
mysql 封装，支持 增、删、改、查
"""
import ast
import datetime
import decimal
import time
from warnings import filterwarnings
import pymysql
from typing import List, Union, Text, Dict



from utils import config
from utils.logUtils.logControl import ERROR, WARNING
from utils.readFilesUtils.regularControl import sql_regular
from utils.readFilesUtils.regularControl import cache_regular
from utils.otherUtils.exceptions import DataAcquisitionFailed, ValueTypeError
from utils.timeUtils.time_control import now_time_day, tomorrow_time_day

# 忽略 Mysql 告警信息
filterwarnings("ignore", category=pymysql.Warning)


class MysqlDB:
    """ mysql 封装 """
    if config.mysql_db.switch:

        def __init__(self):

            try:
                # 建立数据库连接
                self.conn = pymysql.connect(
                    host=config.mysql_db.host,
                    user=config.mysql_db.user,
                    password=config.mysql_db.password,
                    port=config.mysql_db.port
                )
                # 使用 cursor 方法获取操作游标，得到一个可以执行sql语句，并且操作结果为字典返回的游标
                self.cur = self.conn.cursor(cursor=pymysql.cursors.DictCursor)
            except AttributeError as error:
                ERROR.logger.error("数据库连接失败，失败原因 %s", error)

        def __del__(self):
            try:
                # 关闭游标
                self.cur.close()
                # 关闭连接
                self.conn.close()
            except AttributeError as error:
                ERROR.logger.error("数据库连接失败，失败原因 %s", error)

        def query(self, sql, state="all"):
            """
                查询
                :param sql:
                :param state:  all 是默认查询全部
                :return:
                """
            try:
                self.cur.execute(sql)

                if state == "all":
                    # 查询全部
                    data = self.cur.fetchall()
                else:
                    # 查询单条
                    data = self.cur.fetchone()
                return data
            except AttributeError as error_data:
                ERROR.logger.error("数据库连接失败，失败原因 %s", error_data)
                raise

        def wait_for_result(self, sql_query, timeout=60, interval=5, expected_result=None):
            """等待结果，直到超时或匹配预期结果"""
            global result
            start_time = time.time()
            while time.time() - start_time < timeout:
                result = self.query(sql_query)
                if expected_result and result:
                    if [expected_result] == result:
                            return result
                    else:
                        WARNING.logger.warning("查询结果%s不符合预期:%s", expected_result,result)

                time.sleep(interval)

            # 如果超时仍未找到符合预期的结果
            ERROR.logger.error("数据库结果未按预期返回: 预期结果 %s，实际结果 %s", expected_result, result)
            raise RuntimeError("数据库结果未按预期返回")

        def execute(self, sql: Text):
            """
                更新 、 删除、 新增
                :param sql:
                :return:
                """
            try:
                # 使用 execute 操作 sql
                rows = self.cur.execute(sql)
                # 提交事务
                self.conn.commit()
                return rows
            except AttributeError as error:
                ERROR.logger.error("数据库连接失败，失败原因 %s", error)
                # 如果事务异常，则回滚数据
                self.conn.rollback()
                raise

        @classmethod
        def sql_data_handler(cls, query_data, data):
            """
            处理部分类型sql查询出来的数据格式
            @param query_data: 查询出来的sql数据
            @param data: 数据池
            @return:
            """
            # 将sql 返回的所有内容全部放入对象中
            for key, value in query_data.items():
                if isinstance(value, decimal.Decimal):
                    data[key] = float(value)
                elif isinstance(value, datetime.datetime):
                    data[key] = str(value)
                else:
                    data[key] = value
            return data


class SetUpMySQL(MysqlDB):
    """ 处理前置sql """

    def setup_sql_data(self, sql: Union[List, None]) -> Dict:
        """
            处理前置请求sql
            :param sql:
            :return:
            """
        sql = ast.literal_eval(cache_regular(str(sql)))
        try:
            data = {}
            if sql is not None:
                for i in sql:
                    # 判断断言类型为查询类型的时候，
                    if i[0:6].upper() == 'SELECT':
                        sql_date = self.query(sql=i)[0]
                        for key, value in sql_date.items():
                            data[key] = value
                    else:
                        self.execute(sql=i)
            return data
        except IndexError as exc:
            raise DataAcquisitionFailed("sql 数据查询失败，请检查setup_sql语句是否正确") from exc


class AssertExecution(MysqlDB):
    """ 处理断言sql数据 """

    def assert_execution(self, sql: list, resp) -> dict:
        """
         执行 sql, 负责处理 yaml 文件中的断言需要执行多条 sql 的场景，最终会将所有数据以对象形式返回
        :param resp: 接口响应数据
        :param sql: sql
        :return:
        """
        try:
            if isinstance(sql, list):

                data = {}
                _sql_type = ['UPDATE', 'update', 'DELETE', 'delete', 'INSERT', 'insert']
                if any(i in sql for i in _sql_type) is False:
                    for i in sql:
                        # 判断sql中是否有正则，如果有则通过jsonpath提取相关的数据
                        sql = sql_regular(i, resp)
                        if sql is not None:
                            # for 循环逐条处理断言 sql
                            query_data = self.query(sql)[0]
                            data = self.sql_data_handler(query_data, data)
                        else:
                            raise DataAcquisitionFailed(f"该条sql未查询出任何数据, {sql}")
                else:
                    raise DataAcquisitionFailed("断言的 sql 必须是查询的 sql")
            else:
                raise ValueTypeError("sql数据类型不正确，接受的是list")
            return data
        except Exception as error_data:
            ERROR.logger.error("数据库连接失败，失败原因 %s", error_data)
            raise error_data


mysql_db = MysqlDB()

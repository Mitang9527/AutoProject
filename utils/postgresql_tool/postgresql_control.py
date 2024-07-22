
"""
postgresql CRUD 封装
"""
import ast
import datetime
import decimal
from typing import List, Union, Text, Dict

import psycopg2
import psycopg2.extras

from utils import config
from utils.logging_tool.log_control import ERROR
from utils.other_tools.exceptions import DataAcquisitionFailed, ValueTypeError
from utils.read_files_tools.regular_control import cache_regular
from utils.read_files_tools.regular_control import sql_regular


# filterwarnings("ignore", category=psycopg2.Warning)


class PostgresqlDB:
    """Postgresql封装"""
    if config.postgresql_db.switch:
        def __init__(self):
            try:
                self.conn = psycopg2.connect(
                    dbname=config.postgresql_db.dbname,
                    host=config.postgresql_db.host,
                    user=config.postgresql_db.user,
                    password=config.postgresql_db.password,
                    port=config.postgresql_db.port
                )

                self.cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            except AttributeError as error:
                ERROR.logger.error("数据库连接失败，失败原因 %s", error)

        def __del__(self):
            try:
                self.cur.close()
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
                    data = self.cur.fetchall()
                else:
                    data = self.cur.fetchone()
                return data
            except AttributeError as error_data:
                ERROR.logger.error("数据库连接失败，失败原因 %s", error_data)
                raise

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
        def sql_data_handler(cls, query_result_data, data):
            """
            处理部分类型sql查询出来的数据格式
            @param query_result_data: 查询出来的sql数据
            @param data: 数据池
            @return:
            """
            # 将sql 返回的所有内容全部放入对象中
            for key, value in query_result_data.items():
                if isinstance(value, decimal.Decimal):
                    data[key] = float(value)
                elif isinstance(value, datetime.datetime):
                    data[key] = str(value)
                else:
                    data[key] = value
            return data


class SetUpPostgresql(PostgresqlDB):
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


class AssertExecution(PostgresqlDB):
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


if __name__ == '__main__':
    db = PostgresqlDB()
    result = db.query(sql="select * from dept_employee_relation where employee_id = 218")
    print(result)

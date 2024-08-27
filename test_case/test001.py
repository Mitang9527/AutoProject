import time
from utils.mysqlUtils.mysqlControl import mysql_db
from utils.logUtils.logControl import ERROR

# 创建数据库连接
def get_db_connection():
    return mysql_db

def get_db_result(query, params=None):
    try:
        result = mysql_db.query(sql=query)
        return result
    except Exception as e:
        ERROR.logger.error(f"查询数据库时发生错误: {e}")
        return None


def wait_for_result(query, params=None, timeout=60, interval=5, expected_result=None):
    """等待结果，直到超时或匹配预期结果"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        result = get_db_result(query, params)
        if result:
            if result[0].get('result_column') == expected_result:
                return
        time.sleep(interval)
    raise AssertionError("数据库结果未按预期返回")

def execute_script():
    # 这里执行你的脚本或其他操作
    pass

def test_database_response():
    # 执行脚本或其他操作
    execute_script()

    # 等待数据库结果完成并检查结果
    query = "SELECT result_column FROM your_table WHERE your_condition"  # 替换为实际查询
    expected_result = "预期结果"
    wait_for_result(query, expected_result=expected_result)

    # 获取数据库的结果
    result = get_db_result(query)

    # 进行断言
    assert result and result[0].get('result_column') == expected_result

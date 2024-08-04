
import allure
import pytest
from utils.readFilesUtils.get_yaml_data_analysis import GetTestCase
from utils.assertion.assert_control import Assert
from utils.requestsUtils.requestControl import RequestControl
from utils.readFilesUtils.regularControl import regular
from utils.requestsUtils.teardown_control import TearDownHandler


case_id = ['add_dept_01']
TestData = GetTestCase.case_data(case_id)
re_data = regular(str(TestData))


@allure.epic("山水田园")
@allure.feature("自控飞机")
class TestCollectAddtool:

    @allure.story("飞机自动化")
    @pytest.mark.parametrize('in_data', eval(re_data), ids=[i['detail'] for i in TestData])
    def test_ssty(self, in_data, case_skip):
        """
        :param :
        :return:
        """
        res = RequestControl(in_data).http_request()
        TearDownHandler(res).teardown_handle()
        Assert(assert_data=in_data['assert_data'],
               sql_data=res.sql_data,
               request_data=res.body,
               response_data=res.response_data,
               status_code=res.status_code).assert_type_handle()


if __name__ == '__main__':
    pytest.main(['test_ssty.py', '-s', '-W', 'ignore:Module already imported:pytest.PytestWarning'])

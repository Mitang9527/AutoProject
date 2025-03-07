import xmindparser
import xlwt, xlrd
from xlutils.copy import copy
from xlwt import Worksheet
from xmindparser import xmind_to_dict
import datetime
import os
import re
import traceback
from utils.readFilesUtils.get_path import get_project_root

# 当前时间戳
a = datetime.datetime.now().strftime('%Y-%m-%d%H:%M:%S')
timestp = re.sub(r'-|:|\s', '', str(a))

# 根目录
base_dir = os.path.abspath(os.path.dirname(__file__))

# xmindparser配置
xmindparser.config = {
    'showTopicId': False,  # 是否展示主题ID
    'hideEmptyValue': True  # 是否隐藏空值
}


def traversal_xmind(root, rootstring, lisitcontainer, flag):
    try:
        # 判断数据是否是字典类型
        if isinstance(root, dict):
            print('root1:', root)
            # 如果这个字典的key中同时有title和topics，则可认为这个title有下级分支
            if 'title' in root.keys() and 'topics' in root.keys():
                traversal_xmind(root['topics'], str(rootstring), lisitcontainer, True)
            # 如果这个字典的key中有title且没有topics，则可认为这个title是最末端
            if 'title' in root.keys() and 'topics' not in root.keys():
                traversal_xmind(root['title'], str(rootstring), lisitcontainer, True)

        # 判断数据是否是列表类型
        elif isinstance(root, list):
            #
            flag = True
            # 遍历列表
            for sonroot in root:
                # sonroot只可能是dict类型
                # 如果这个字典的key中同时有title和topics，则可认为这个title有下级分支
                if flag:
                    if 'title' in sonroot.keys() and 'topics' in sonroot.keys():
                        traversal_xmind(sonroot['topics'], str(rootstring) + "!" + sonroot['title'], lisitcontainer,
                                        True)
                    # 如果这个字典的key中有title且没有topics，则可认为这个title是最末端
                    elif 'title' in sonroot.keys() and 'topics' not in sonroot.keys():
                        # # 判断蓝色感叹号标识（前置条件）是否存在
                        if 'makers' in sonroot.keys() and 'symbol-info' in sonroot['makers']:
                            case = str(rootstring) + "!" + root[0]['title'] + "!" + root[1]['title'] + "!" + \
                                   root[1]['topics'][0]['title']
                            # 如果有特殊标签，则改变flag状态
                            flag = False
                            traversal_xmind(case, case, lisitcontainer, flag)
                        else:
                            case = str(rootstring) + "!" + sonroot['title']
                            traversal_xmind(case, case, lisitcontainer, True)

        # 判断数据是否是字符串类型
        elif isinstance(root, str):
            # lisitcontainer.append(str(rootstring.replace('\n', '')))  # 此处是去掉一步骤多结果情况直接拼接
            lisitcontainer.append(str(rootstring))  # 此处是一步骤多结果时，多结果合并
            # print('lisitcontainer:', lisitcontainer)
    except:
        tips = 'xmind处理异常，请联系Dora！！！'
        # 输出异常信息
        traceback.print_exc()

# 将xmind中的每条用例提取出来，放入列表中，以逗号分隔
def get_case(root):
    rootstring = root['title']
    lisitcontainer = []
    traversal_xmind(root, rootstring, lisitcontainer, True)
    return lisitcontainer

# 写入第b行的用例数据内容
def write_sheet(Worksheet, b, organization,tomodoule,casename,precondition, casestep, expectresult,is_maoyan):
    '''
    功能解释：去掉用例中的换行符，写入一条用例到Excel中
    @param Worksheet: excel表对象
    @param b: 写入的数据在表中所处的行数
    @param casename: 用例名称
    @param casestep: 用例操作
    @param expectresult: 期望结果
    '''
    # 用例名称
    caseName = re.sub(r'\r\n', '', str(casename))
    # 用例步骤
    caseStep = re.sub(r'\r\n', '', str(casestep))
    # 期望结果
    expectResult = re.sub(r'\r\n', '', str(expectresult))
    Worksheet.write(b, 1, organization)  # 所属系统
    Worksheet.write(b, 2, tomodoule)  # 所属模块
    Worksheet.write(b, 3, casename)  # 用例名称
    Worksheet.write(b, 4, precondition)  # 前置条件
    Worksheet.write(b, 5, casestep)  # 用例步骤
    Worksheet.write(b, 6, expectresult)  # 预期结果
    Worksheet.write(b, 7, is_maoyan)  # 是否冒烟

# 处理xmind数据
def deal_with_list(Worksheet, case_list):
    '''
    功能解释：处理从xmind转换过来的用例list，并写入Excel中
    @param Worksheet: excel表对象
    @param case_list: 通过xmind转换好的用例列表
    '''
    tips = 'excel表格处理成功！！！'

    b = 1  # 记录写了多少行
    for row_case in case_list:
        case = row_case.split("!")  # 用‘!’分隔，存在list中，这是一条用例
        caselength = len(case)
        try:
                organization = case[1]# 所属系统
                tomodoule = case[2]# 所属模块
                casename = case[3]# 用例标题
                precondition = case[4]# 预置条件
                casestep = case[5]  # 用例步骤，（倒数第2个下标是步骤)
                expectresult = case[6]  # 预期结果，（倒数第1个下标是预期结果）
                if 'Y' in row_case:
                    is_maoyan = 'Y'
                else:
                    is_maoyan = 'N'
                # print(expectresult)
                write_sheet(Worksheet, b, organization,tomodoule,casename,precondition, casestep, expectresult,is_maoyan)  # 写入Excel
        except:
            tips = 'excel表格处理异常，请联系Dora！！！'
            print('异常tips:', tips)
            # 输出异常信息
            traceback.print_exc()
        b = b + 1
    return tips

def xmindToexcelfile(uploadPath):
    # 创建一个Workbook对象 编码encoding
    Workbook = xlwt.Workbook(encoding='utf-8', style_compression=0)
    # 添加一个sheet工作表、sheet名命名为Sheet1、cell_overwrite_ok=True允许覆盖写
    Worksheet = Workbook.add_sheet('Sheet1', cell_overwrite_ok=True)
    Worksheet.write(0, 0, '用例编号')
    Worksheet.write(0, 1, '所属系统')
    Worksheet.write(0, 2, '所属模块名称')
    Worksheet.write(0, 3, '用例名称')
    Worksheet.write(0, 4, '预置条件')
    Worksheet.write(0, 5, '用例步骤')
    Worksheet.write(0, 6, '预期结果')
    Worksheet.write(0, 7, '冒烟用例')
    root = xmind_to_dict(uploadPath)[0]['topic']  # 解析成dict数据类型xmindparser.xmind_to_dict(filePath)
    print('root:', root)
    case_list = get_case(root)
    print('case:', case_list)
    tips = deal_with_list(Worksheet, case_list)
    # Excel表保存的文件名字
    project_root = get_project_root()
    folder_path = project_root / 'excelFiles'
    folder_path.mkdir(parents=True, exist_ok=True)

    Name = root["title"] + timestp + ".xls"

    savepath = folder_path / Name
    # savepath = os.path.abspath(os.path.dirname(__file__)) + '\\excelFiles\\'
    Workbook.save(savepath)  # 此处可以填写生成文件的路径
    return tips

xmindToexcelfile(r'E:\测试物料\POCSTARS - Web调度台-xmind\pocstar-运营平台-巡更.xmind')
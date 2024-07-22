
目录结构
├── common                         // 配置
│   ├── conf.yaml                  // 公共配置
│   ├── setting.py                 // 环境路径存放区域
├── data                           // 测试用例数据
├── File                           // 上传文件接口所需的文件存放区域
├── logs                           // 日志层
├── report                         // 测试报告层
├── test_case                      // 测试用例代码
├── utils                          // 工具类
│   └── assertion                
│       └── assert_control.py      // 断言
│       └── assert_type.py         // 断言类型
│   └── cache_process              // 缓存处理模块
│       └── cacheControl.py
│       └── redisControl.py  
│   └── logUtils                   // 日志处理模块
│       └── logControl.py
│       └── logDecoratrol.py       // 日志装饰器
│       └── runTimeDecoratrol.py   // 统计用例执行时长装饰器
│   └── mysqlUtils                 // 数据库模块
│       └── get_sql_data.py       
│       └── mysqlControl.py   
│   └── noticUtils                 // 通知模块
│       └── dingtalkControl.py     // 钉钉通知 
│       └── feishuControl.py       // 飞书通知
│       └── sendmailControl.py     // 邮箱通知
│       └── weChatSendControl.py   // 企业微信通知
│   └── otherUtils                 // 其他工具类
│       └── allureDate             // allure封装
│           └── allure_report_data.py // allure报告数据清洗
│           └── allure_tools.py   // allure 方法封装
│           └── error_case_excel.py   // 收集allure异常用例，生成excel测试报告
│       └── localIpControl.py      // 获取本地IP
│       └── threadControl.py       // 定时器类
│   └── readFilesUtils             // 文件操作
│       └── caseAutomaticControl.py // 自动生成测试代码 
│       └── clean_files.py          // 清理文件
│       └── excelControl.py         // 读写excel
│       └── get_all_files_path.py   // 获取所有文件路径
│       └── get_yaml_data_analysis.py // yaml用例数据清洗
│       └── regularControl.py        // 正则
│       └── yamlControl.py          // yaml文件读写
│   └── recordingUtils             // 代理录制
│       └── mitmproxyContorl.py
│   └── requestsUtils 
│       └── dependentCase.py        // 数据依赖处理
│       └── requestControl.py      // 请求封装
│   └── timeUtils
├── Readme.md                       // help
├── pytest.ini                  
├── run.py                           // 运行入口  


依赖库
allure-pytest==2.9.45
allure-python-commons==2.9.45
atomicwrites==1.4.0
attrs==21.2.0
certifi==2021.10.8
cffi==1.15.0
charset-normalizer==2.0.7
colorama==0.4.4
colorlog==6.6.0
cryptography==36.0.0
DingtalkChatbot==1.5.3
execnet==1.9.0
Faker==9.8.3
idna==3.3
iniconfig==1.1.1
jsonpath==0.82
packaging==21.3
pluggy==1.0.0
py==1.11.0
pycparser==2.21
PyMySQL==1.0.2
pyOpenSSL==21.0.0
pyparsing==3.0.6
pytest==6.2.5
pytest-forked==1.3.0
pytest-xdist==2.4.0
python-dateutil==2.8.2
PyYAML==6.0
requests==2.26.0
six==1.16.0
text-unidecode==1.3
toml==0.10.2
urllib3==1.26.7
xlrd==2.0.1
xlutils==2.0.0
xlwt==1.3.0
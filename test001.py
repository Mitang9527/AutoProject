#多并发接口请求
import json
import time

import grequests

adata = json.dumps({"key":"value"})
header = {"Content-type": "appliaction/json", "Accept":"application/json"}
# url = "https://www.baidu.com/"


def use_grequest(num):
    task = []
    urls = [ "https://www.baidu.com/" for i in (range(num))]
    while urls:
        url = urls.pop(0)
        rs = grequests.request("POST",url = url,data=adata,headers=header)
        task.append(rs)
    resp = grequests.map(task,size=5)
    return resp


def main(num):
    print(u'正在使用grequest模块发起请求...')
    time1 = time.time()
    finall_res = use_grequest(num)
    # print(finall_res)
    time2 = time.time()
    T1 = time2-time1
    print(u'use_grequest发起{}个请求花费了{}秒'.format(num,T1))



if __name__ == '__main__':
    main(1000)
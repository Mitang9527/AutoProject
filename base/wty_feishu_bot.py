#飞书机器人测试
import base64
import hashlib
import hmac
import json
import time


def get_iciba():
    url = 'http://open.iciba.com/dsapi/'
    res  = requests.get(url)
    content = res.json()['content']
    print(content)
    note = res.json()['note']
    print(note)
    return note

# 加签
import requests
import urllib3

timestamp = str(round(time.time()))
print(timestamp)
secret = 'gw5LXZ0acv5HvBazHblE8'
secret_enc = secret.encode('utf-8')
string_to_sign = '{}\n{}'.format(timestamp, secret)
hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
sign = base64.b64encode(hmac_code).decode('utf-8')
print(sign)


def Dingmessage ():
    # 请求的URL，WebHook地址
    webhook = f"https://open.feishu.cn/open-apis/bot/v2/hook/69dc685f-3da3-4d47-9fd0-d018c5278ec5"
    # 构建请求头部
    header = {"Content-Type": "application/json", "Charset": "UTF-8"}

    message_json = json.dumps({

        "content": {
            "text": "<at user_id='all'>所有人</at>"
        },
        "timestamp":timestamp,
        "sign":sign,
        "msg_type": "text",
        "tag": "at"
    })
    info = requests.post(url=webhook, data=message_json, headers=header, verify=False)
    print("hello")# 打印返回的结果
    print(info.text)

urllib3.disable_warnings()
Dingmessage()
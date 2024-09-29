#飞书机器人测试
import base64
import hashlib
import hmac
import json
import time


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
    print(sign)
    print(timestamp)
    rich_text = {
            "msg_type": "interactive",
            "card": {
                "elements": [
                    {
                        "tag": "markdown",
                        "content": "**🤖 测试人员： "
                    },
                    {
                        "tag": "markdown",
                        "content": "**🚀 运行环境： "
                    },
                    {
                        "tag": "markdown",
                        "content": "**💌 成功率： "
                    },
                    {
                        "tag": "markdown",
                        "content": "**🎖️ 用例数： "
                    },
                    {
                        "tag": "markdown",
                        "content": "**⭕ 成功用例： "
                    },
                    {
                        "tag": "markdown",
                        "content": "**❌ 失败用例： "
                    },
                    {
                        "tag": "markdown",
                        "content": "**❗ 异常用例： "
                    },
                    {
                        "tag": "markdown",
                        "content": "**❓ 跳过用例： "
                    },
                    {
                        "tag": "markdown",
                        "content": "📅 时间： "
                    },
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "text": {
                                    "tag": "plain_text",
                                    "content": "报告详情"
                                },
                                "type": "primary",
                                "url": "https://mam-testcase-report.yiye.ai/"
                            }
                        ]
                    }
                ],
                "header": {
                    "template": "header_color",
                    "title": {
                        "content": "header_text",
                        "tag": "plain_text"
                    }
                }
            },
            "timestamp":timestamp,
            "sign" : sign
    }
    print(rich_text)

    message_json_1 = json.dumps(
        {
        "content": {
            "text": "<at user_id='all'>所有人</at>"
        },
        "timestamp":timestamp,
        "sign":sign,
        "msg_type": "text",
        "tag": "at"
    })
    print(message_json_1)
    message_json = json.dumps(rich_text)
    info = requests.post(url=webhook,data=message_json, headers=header, verify=False)
    print(info.text)
    info_1 = requests.post(url=webhook,data=message_json_1, headers=header, verify=False)
    print(info_1.json())

urllib3.disable_warnings()
# Dingmessage()
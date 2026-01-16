# web调度台测试
import json
import requests
from utils.OcRUtils.OcrRecognition import OcrRecognition
from utils.timeUtils.time_control import timestamp
from utils.logUtils.loguruControl import logger

timestp = timestamp()

url = f"https://web-dispatchsg.pocstar.com/dispatchWeb/dispatch/shanli/generateImage?{timestp}"
payload={}
headers = {
   'User-Agent': 'Apifox/1.0.0 (https://apifox.com)'
}
response = requests.request("GET", url, headers=headers, data=payload)
binary_data = response.content
Ocr = OcrRecognition()
Code = Ocr.ocr_recognition(binary_data)
logger.info(Code)

login_url = f"https://web-dispatchsg.pocstar.com/dispatchWeb/dispatch/shanli/userLogin?{timestp}"
payload_1 = json.dumps({
   "userName": "dp1@nx300.sdb",
   "userPassword": "a123456",
   "jcaptchaCode": Code
})
headers_1 = {
   'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
   'Content-Type': 'application/json'
}

response = requests.request("POST", login_url, headers=headers_1, data=payload_1)

logger.info(response.text)


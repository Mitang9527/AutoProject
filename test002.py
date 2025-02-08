from utils.selenuimUtils.selenium_utils import Browser
from utils.OcRUtils.OcrRecognition import OcrRecognition

driver = Browser()
Ocr = OcrRecognition()
driver.open("https://manage.pocstar.com/login.action?locale=zh_CN#reloaded")
driver.element_wait('id', 'username').send_keys('tiantian')
driver.element_wait('id', 'password').send_keys('a123456')
element = driver.element_wait('id', 'jcaptchaImage')
png_data = element.screenshot_as_png
Code = Ocr.ocr_recognition(png_data)
driver.element_wait('id', 'jcaptchaCode').send_keys(Code)
driver.element_wait('id', 'loginsubmit').click()
driver.max_window()

#TODO 正常登录后走识别逻辑会报错,还需做另外方式的断言,结合pytest做重跑用例操作
# if driver.get_element('id=>errorMsg').text == "验证码错误":
#     raise Exception("验证码识别错误，登录失败")
# else:
#     print("登录成功")

driver.element_wait('xpath', '//*[@id="menu-system"]/dt[3]').click()
driver.element_wait('link_text', 'Company List').click()



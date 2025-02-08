#web调度台ui
import time

from utils.selenuimUtils.selenium_utils import Browser
from utils.OcRUtils.OcrRecognition import OcrRecognition

driver = Browser()
Ocr = OcrRecognition()

driver.open("https://web-dispatch-sg.sre.shanlitech.com/#/login")
driver.max_window()
driver.element_wait('class', 'el-input__inner').send_keys('dp1@addad.sdb')
driver.element_wait('css', '[placeholder="Password：abcdef"]').send_keys('a123456')
element = driver.element_wait('class', 'code-img')

time.sleep(2)
png_data = element.screenshot_as_png
Code = Ocr.ocr_recognition(png_data)
driver.element_wait('css', '[placeholder="Verification code"]').send_keys(Code)

#远程麦克风


driver.element_wait('xpath', '//*[@id="app"]/section/section/div[1]/div[3]/div[2]/div[5]/div/img').click()
#长按
# driver.long_click('class=>speak-btn')

# driver.element_wait('link_text', 'Login').click()






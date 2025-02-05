import pytesseract
from PIL import Image
import io
from utils.readFilesUtils.get_path import get_project_root
from utils.timeUtils.time_control import datetime_strftime


class OcrRecognition:
    def __init__(self):
        pass

    def ocr_recognition(self, png_data):
        """
        OCR图像识别技术获取图像验证码
        :param png_data: 通过外部方法获得的PNG截图数据
        :return: 识别结果
        """
        # 将二进制数据转换为图像
        image = Image.open(io.BytesIO(png_data))

        project_root = get_project_root()
        png_folder_path = project_root / 'png'
        png_folder_path.mkdir(parents=True, exist_ok=True)

        pngName = datetime_strftime() + '_png.png'

        file_path = png_folder_path / pngName
        image.save(file_path)

        # 进行 OCR 识别
        result = pytesseract.image_to_string(image)

        return result

import os
import json
from .constants import RESOURCE_PATH

# ==================== 国际化多语言支持 ====================


class I18N:
    def __init__(self):
        self.current_lang = "en"  # 默认中文
        self.translations = {}
        self.locales_dir = RESOURCE_PATH / "locales"
        self.load_language("en")

    def load_language(self, lang_code):
        """加载指定语言的 JSON 文件"""
        file_path = os.path.join(self.locales_dir, f"{lang_code}.json")
        if not os.path.exists(file_path):
            print(f"Warning: Language file {file_path} not found.")
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self.translations = json.load(f)
            self.current_lang = lang_code
            return True
        except Exception as e:
            print(f"Error loading language file: {e}")
            return False

    def get(self, key, default=None):
        """获取翻译文本"""
        return self.translations.get(key, default if default else key)


# 全局实例
i18n = I18N()


def _(key):
    """快捷翻译函数"""
    return i18n.get(key)

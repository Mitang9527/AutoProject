# -*- coding: utf-8 -*-

import logging
import re
import tkinter as tk


# === 自定义Tkinter日志Handler ===

class TkinterLogHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        # 去除ANSI颜色编码
        msg = self.remove_ansi_codes(msg)

        # 更新Tkinter的text widget
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.see(tk.END)
            self.text_widget.configure(state='disabled')

        self.text_widget.after(0, append)

    def remove_ansi_codes(self, text):
        """去除ANSI颜色转义字符"""
        ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
        return ansi_escape.sub('', text)

    def add_color_tags(self, text, level):
        """根据日志级别，为日志添加颜色标签"""
        if level == 'INFO':
            return f'\033[32m{text}\033[0m'  # 绿色
        elif level == 'ERROR':
            return f'\033[31m{text}\033[0m'  # 红色
        elif level == 'DEBUG':
            return f'\033[36m{text}\033[0m'  # 青色
        return text

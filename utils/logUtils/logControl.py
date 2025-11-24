"""
日志封装，可设置不同等级的日志颜色
"""
import logging
import os
from logging import handlers
from typing import Text
import colorlog
from common.setting import ensure_path_sep
from utils.logUtils.tkinter_log_handler import TkinterLogHandler
from utils.timeUtils.time_control import now_time_day

class LogHandler:
    """ 日志打印封装"""
    # 日志级别关系映射
    level_relations = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }

    def __init__(self, filename: Text, level: Text = "info", when: Text = "D",
                 fmt: Text = "%(levelname)-8s %(asctime)s %(name)s:%(filename)s:%(lineno)d %(message)s"):
        self.logger = logging.getLogger(filename)  # 获取logger

        if not self.logger.handlers:

            formatter = self.log_color()  # 用colorlog配置带颜色的日志格式
            format_str = logging.Formatter(fmt)  # 设置普通日志格式

            # 设置日志级别
            self.logger.setLevel(self.level_relations.get(level.lower(), logging.INFO))

            log_folder = os.path.dirname(filename)
            if not os.path.exists(log_folder):
                os.makedirs(log_folder)

            # 设置控制台输出处理器
            screen_output = logging.StreamHandler()
            screen_output.setFormatter(formatter)
            self.logger.addHandler(screen_output)


            time_rotating = handlers.TimedRotatingFileHandler(
                filename=filename, when=when, backupCount=3, encoding='utf-8'
            )
            time_rotating.setFormatter(format_str)  # 文件日志输出的格式
            self.logger.addHandler(time_rotating)

        # 默认的日志路径
        self.log_path = ensure_path_sep('\\logs\\log.log')

    @classmethod
    def log_color(cls):
        """ 设置日志颜色 """
        log_colors_config = {
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red',
        }

        formatter = colorlog.ColoredFormatter(
            '%(log_color)s[%(asctime)s] [%(name)s] [%(levelname)s]: %(message)s',
            log_colors=log_colors_config
        )
        return formatter

    def add_tkinter_handler(self, text_widget):
        """动态添加Tkinter Handler到已有logger"""
        tk_handler = TkinterLogHandler(text_widget)
        tk_handler.setFormatter(self.log_color())  # 颜色格式保持一致
        self.logger.addHandler(tk_handler)
#
# INFO = LogHandler(ensure_path_sep(f"\\logs\\info-{now_time_day()}.log"), level='info')
# ERROR = LogHandler(ensure_path_sep(f"\\logs\\error-{now_time_day()}.log"), level='error')
# WARNING = LogHandler(ensure_path_sep(f'\\logs\\warning-{now_time_day()}.log'), level='warning')
# DEBUG = LogHandler(ensure_path_sep(f'\\logs\\warning-{now_time_day}.log'), level='debug')


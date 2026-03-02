import os
from functools import wraps
from loguru import logger
from datetime import datetime
from common.setting import ensure_path_sep


class LogManager:
    _initialized = False

    def __init__(self, log_dir=None, level="INFO"):
        if LogManager._initialized:
            return

        if log_dir is None:
            log_dir = ensure_path_sep('\\logs')

        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        log_path = os.path.join(log_dir, datetime.now().strftime("%Y-%m-%d") + ".log")
        logger.add(
            log_path,
            rotation="00:00",
            retention="7 days",
            compression="gz",
            level=level.upper(),
            format="{time:YYYY-MM-DD HH:mm:ss}| {level} | {message} |",
            enqueue=True,
            encoding="utf-8",
        )
        logger.level("FATAL", no=60, color="<red>", icon="!!!")
        LogManager._initialized = True

    @staticmethod
    def capture_exceptions(func=None, *, reraise=True, log_message="An exception occurred"):
        """
        支持两种使用方式：

        1) 无参数用法：
           @capture_exceptions
           def f(): ...

        2) 带参数用法：
           @capture_exceptions(reraise=False, log_message="出错")
           def f(): ...
        """

        if func is None:
            def decorator(real_func):
                @wraps(real_func)
                def wrapper(*args, **kwargs):
                    try:
                        return real_func(*args, **kwargs)
                    except Exception:
                        logger.exception(log_message)
                        if reraise:
                            raise
                        return None

                return wrapper

            return decorator

        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception:
                logger.exception(log_message)
                if reraise:
                    raise
                return None

        return wrapper



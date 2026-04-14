import os
import time
import subprocess
import platform
import queue
import threading
import traceback
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from .constants import APKTOOL_JAR
from .utils import load_yml


def run_with_live_output(
    app_instance,
    command: List[str],
    timeout: Optional[float] = None,
    encoding: Optional[str] = None,
) -> int:
    """
    【核心改进】双线程读取 stdout/stderr 字节流，防止死锁，并实时推送到 GUI
    """
    start_time = time.time()

    startupinfo = None
    creationflags = 0
    if platform.system() == "Windows":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        creationflags = subprocess.CREATE_NO_WINDOW

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
            startupinfo=startupinfo,
            creationflags=creationflags,
            encoding=encoding,
        )
    except FileNotFoundError:
        app_instance.append_log(f"[ERROR] Command or file not found: {command[0]}\n")
        return -1
    except Exception as e:
        app_instance.append_log(f"[CRITICAL] Failed to start process: {e}\n")
        return -1

    log_queue = queue.Queue(maxsize=1000)

    def reader_thread(stream, prefix: str = ""):
        try:
            for line in iter(stream.readline, ""):
                if line:
                    log_queue.put((prefix, line.rstrip("\n\r")))
            stream.close()
        except Exception as e:
            app_instance.append_log(f"[ERROR] Error reading subprocess output: {e}\n")
        finally:
            log_queue.put((None, None))

    t_out = threading.Thread(
        target=reader_thread, args=(process.stdout, ""), daemon=True
    )
    t_err = threading.Thread(
        target=reader_thread, args=(process.stderr, "[ERR] "), daemon=True
    )
    t_out.start()
    t_err.start()

    streams_to_read = 2

    while streams_to_read > 0:
        try:
            item = log_queue.get(timeout=0.1)

            if item[0] is None and item[1] is None:
                streams_to_read -= 1
                continue

            prefix, line_content = item
            app_instance.after(0, app_instance.append_log, f"{prefix}{line_content}\n")

        except queue.Empty:
            if process.poll() is not None:
                remaining_timeout = (
                    timeout - (time.time() - start_time) if timeout else None
                )
                if remaining_timeout and remaining_timeout <= 0:
                    break
                continue

            if timeout is not None and (time.time() - start_time) > timeout:
                app_instance.append_log(
                    f"[TIMEOUT] Execution timeout ({timeout}s), terminating...\n"
                )
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                return -1
        except Exception as e:
            app_instance.append_log(f"[ERROR] 处理子进程输出时出错: {e}\n")
            traceback.print_exc()

    t_out.join()
    t_err.join()

    returncode = process.wait()
    app_instance.append_log(
        f"[Result] Command execution completed,  code：{returncode}\n"
    )
    return returncode


def safe_remove(app_instance, file_path: str, retries: int = 3) -> bool:
    for i in range(retries):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                app_instance.append_log(f"[OK] Temporary file has been deleted\n")
                return True
        except PermissionError:
            app_instance.append_log(
                f"[Warn] File is occupied, wait 0.5 seconds and try again... ({i + 1}/{retries})\n"
            )
            time.sleep(0.5)
        except Exception as e:
            app_instance.append_log(f"[Error] Failed to delete file：{e}\n")
            return False
    return False


def get_version_info(yml_path: Path):
    from .utils import load_yml

    data = load_yml(yml_path)
    if data:
        version_info = data.get("versionInfo", {})
        return version_info.get("versionCode"), version_info.get("versionName")
    return None, None

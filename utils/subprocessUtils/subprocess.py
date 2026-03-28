import queue
import subprocess
import threading
import time
import traceback
from sys import platform
from typing import List, Optional

from utils.logUtils.logControl import INFO


def execute_python_script(script_path):
    process = None
    try:
        process = subprocess.Popen(
            ['python3', script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
            encoding='utf-8'
        )

        for line in iter(process.stdout.readline, ''):
            print(f"STDOUT: {line.strip()}")

        for line in iter(process.stderr.readline, ''):
            print(f"STDERR: {line.strip()}")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        if process:
            if process.stdout:
                process.stdout.close()
            if process.stderr:
                process.stderr.close()
            process.wait()

def run_with_live_output(command):
    process = subprocess.Popen(command, creationflags=subprocess.CREATE_NO_WINDOW, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            INFO.logger.info(f" {line.strip()}")
    return process.returncode


def run_cmd(
        self,
        command: List[str],
        timeout: Optional[float] = None,
        encoding: Optional[str] = 'utf-8'
) -> int:
    """
    【核心改进】双线程读取 stdout/stderr 字节流，防止死锁，并实时推送到 GUI
    Args:
        command (List[str]): 要执行的命令列表。
        timeout (Optional[float], optional): 命令执行超时时间（秒）。None表示无限制。
        encoding (Optional[str], optional): 用于解码输出流的编码。默认为 'utf-8'。

    Returns:
        int: 子进程的返回码。如果发生异常或超时，则返回 -1。
    """
    start_time = time.time()
    self.append_log(f"[CMD] {' '.join(command)}\n")

    # 准备跨平台的启动选项
    startupinfo = None
    creationflags = 0
    if platform.system() == "Windows":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        creationflags = subprocess.CREATE_NO_WINDOW

    #  启动子进程
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            # text=False,  # False 是默认值，代表返回 bytes
            # universal_newlines=False,
            bufsize=1,  # 行缓冲
            startupinfo=startupinfo,
            creationflags=creationflags,
        )
    except FileNotFoundError:
        self.append_log(f"[ERROR] 找不到命令或文件: {command[0]}\n")
        return -1
    except Exception as e:
        self.append_log(f"[CRITICAL] 启动进程失败: {e}\n")
        return -1

    #  创建线程安全队列用于接收子进程输出
    log_queue = queue.Queue(maxsize=1000)

    def reader_thread(stream, prefix: str = ""):
        """读取子进程的一个字节流输出，并放入队列"""
        try:
            for line_bytes in iter(stream.readline, b""):
                if line_bytes:
                    decoded_line = None
                    for enc in ['utf-8', 'gbk', 'latin1']:
                        try:
                            decoded_line = line_bytes.decode(enc, errors='replace').rstrip('\n\r')
                            break
                        except UnicodeDecodeError:
                            continue
                        except Exception:
                            continue

                    if decoded_line is None:
                        decoded_line = "<无法解码的输出>"

                    log_queue.put((prefix, decoded_line))
            stream.close()
        except Exception as e:
            self.append_log(f"[ERROR] 读取子进程输出流时出错: {e}\n")
        finally:
            # 发送一个哨兵值，表示该流已读完
            log_queue.put((None, None))

    # 启动两个守护线程，分别读取 stdout 和 stderr
    t_out = threading.Thread(target=reader_thread, args=(process.stdout, ""), daemon=True)
    t_err = threading.Thread(target=reader_thread, args=(process.stderr, "[ERR] "), daemon=True)
    t_out.start()
    t_err.start()

    # 引入计时器
    streams_to_read = 2
    #  主循环：从队列中获取输出并更新GUI
    last_update_time = time.time()
    while streams_to_read > 0:
        try:
            item = log_queue.get(timeout=0.1)

            if item[0] is None and item[1] is None:
                streams_to_read -= 1
                continue

            prefix, line_content = item
            # 使用 after 方法将更新操作调度到主线程执行
            self.after(0, self.append_log, f"{prefix}{line_content}\n")

        except queue.Empty:
            # 检查主进程是否已经结束
            if process.poll() is not None:
                remaining_timeout = timeout - (time.time() - start_time) if timeout else None
                if remaining_timeout and remaining_timeout <= 0:
                    break
                continue

            if timeout is not None and (time.time() - start_time) > timeout:
                self.append_log(f"[TIMEOUT] 命令执行超时 ({timeout}s)，正在终止...\n")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                return -1
        except Exception as e:
            self.append_log(f"[ERROR] 处理子进程输出时出错: {e}\n")
            traceback.print_exc()

    # 6. 等待读取线程完成
    t_out.join()
    t_err.join()

    # 7. 获取最终返回码
    returncode = process.wait()
    total_time = time.time() - start_time
    self.append_log(f"[Result] 命令执行完毕，返回码：{returncode}，耗时 {total_time:.2f}s\n")
    return returncode

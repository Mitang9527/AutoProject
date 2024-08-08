#山水田园过山车脚本  验证推送
from utils.readFilesUtils.copy_and_modify_files import copy_and_modify_files
import time

now_time_day = time.strftime("%Y-%m-%d", time.localtime())

# 定义源目录和目标目录列表
src_dir = [
    "/resource3/ftp/ssty/gsc1/rec/待补充/127.0.0.1/000/",
    "/resource3/ftp/ssty/gsc2/rec/2024-06-28/127.0.0.1/000/",
    "/resource3/ftp/ssty/gsc3/rec/2024-06-28/127.0.0.1/000/",
    "/resource3/ftp/ssty/gsc4/rec/2024-06-28/127.0.0.1/000/",
    "/resource3/ftp/ssty/gsc5/rec/2024-06-28/127.0.0.1/000/"
]
#目标目录列表
dst_dir = [
    f"/resource/ftp/ssty/gsc1/rec/{now_time_day}/127.0.0.1/000/",
    f"/resource/ftp/ssty/gsc2/rec/{now_time_day}/127.0.0.1/000/",
    f"/resource/ftp/ssty/gsc3/rec/{now_time_day}/127.0.0.1/000/",
    f"/resource/ftp/ssty/gsc4/rec/{now_time_day}/127.0.0.1/000/",
    f"/resource/ftp/ssty/gsc5/rec/{now_time_day}/127.0.0.1/000/"
]

file_ext = "dat"  # 只处理.dat文件
minute_add = 10  # 增加的分钟数


copy_and_modify_files(src_dir, dst_dir, file_ext, minute_add)

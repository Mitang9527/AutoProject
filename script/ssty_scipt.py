#山水田园过山车脚本
from utils.readFilesUtils.copy_and_modify_files import copy_and_modify_files
import time

now_time_day = time.strftime("%Y-%m-%d", time.localtime())

# 定义源目录和目标目录列表

#山水田园过山车
src_dir = [
    "/resource3/ftp/ssty/gsc1/rec/2024-07-29/127.0.0.1/000/",
    "/resource3/ftp/ssty/gsc2/rec/2024-07-29/127.0.0.1/000/",
    "/resource3/ftp/ssty/gsc3/rec/2024-07-29/127.0.0.1/000/",
    "/resource3/ftp/ssty/gsc4/rec/2024-07-29/127.0.0.1/000/",
    "/resource3/ftp/ssty/gsc5/rec/2024-07-29/127.0.0.1/000/"
]
#目标目录列表
dst_dir = [
    f"/resource/ftp/ssty/gsc1/rec/{now_time_day}/127.0.0.1/000/",
    f"/resource/ftp/ssty/gsc2/rec/{now_time_day}/127.0.0.1/000/",
    f"/resource/ftp/ssty/gsc3/rec/{now_time_day}/127.0.0.1/000/",
    f"/resource/ftp/ssty/gsc4/rec/{now_time_day}/127.0.0.1/000/",
    f"/resource/ftp/ssty/gsc5/rec/{now_time_day}/127.0.0.1/000/"
]

#山水田园海盗船
src_dir_hdc = [
    "/resource3/ftp/ssty/hdcy1/rec/2024-07-29/127.0.0.1/000/",
    "/resource3/ftp/ssty/hdcy2/rec/2024-07-29/127.0.0.1/000/",
    "/resource3/ftp/ssty/hdcz1/rec/2024-07-29/127.0.0.1/000/",
    "/resource3/ftp/ssty/hdcz2/rec/2024-07-29/127.0.0.1/000/"
]
#目标目录列表
dst_dir_hdc = [
    f"/resource/ftp/ssty/hdcy1/rec/{now_time_day}/127.0.0.1/000/",
    f"/resource/ftp/ssty/hdcy2/rec/{now_time_day}/127.0.0.1/000/",
    f"/resource/ftp/ssty/hdcz1/rec/{now_time_day}/127.0.0.1/000/",
    f"/resource/ftp/ssty/hdcz2/rec/{now_time_day}/127.0.0.1/000/"
]

#山水田园大摆锤
src_dir_dbc = [
    "/resource3/ftp/ssty/dbc2/rec/2024-07-05/127.0.0.1/000/",
    "/resource3/ftp/ssty/dbc3/rec/2024-07-05/127.0.0.1/000/",
    "/resource3/ftp/ssty/dbc4/rec/2024-07-05/127.0.0.1/000/",
    "/resource3/ftp/ssty/dbc5/rec/2024-07-05/127.0.0.1/000/"
]
#目标目录列表
dst_dir_dbc = [
    f"/resource/ftp/ssty/hdcy1/rec/{now_time_day}/127.0.0.1/000/",
    f"/resource/ftp/ssty/hdcy2/rec/{now_time_day}/127.0.0.1/000/",
    f"/resource/ftp/ssty/hdcyz1/rec/{now_time_day}/127.0.0.1/000/",
    f"/resource/ftp/ssty/hdcz2/rec/{now_time_day}/127.0.0.1/000/"
]


file_ext = "dat"  # 只处理.dat文件
minute_add = 10  # 增加的分钟数

#山水田园过山车
copy_and_modify_files(src_dir, dst_dir, file_ext, minute_add)
#山水田园海盗船
# copy_and_modify_files(src_dir_hdc,dst_dir_hdc,file_ext,minute_add)
#山水田园大摆锤
# copy_and_modify_files(src_dir_dbc,dst_dir_dbc,file_ext,minute_add)



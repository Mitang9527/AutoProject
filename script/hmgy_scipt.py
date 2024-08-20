# 山水田园过山车脚本
# 自动增加文件名称且复制，输出日志

from utils.readFilesUtils.copy_and_modify_files import copy_and_modify_files
from utils.timeUtils.time_control import now_time_day

now_time_day = now_time_day()
# 定义源目录和目标目录列表
# 虎门公园过山车脚本
src_dir = [
    "/resource3/ftp/hmgy/gsc1/rec/2024-07-30/127.0.0.1/000/",
    "/resource3/ftp/hmgy/gsc2/rec/2024-07-30/127.0.0.1/000/",
    "/resource3/ftp/hmgy/gsc3/rec/2024-07-30/127.0.0.1/000/",
    "/resource3/ftp/hmgy/gsc4/rec/2024-07-30/127.0.0.1/000/",
    "/resource3/ftp/hmgy/gsc5/rec/2024-07-30/127.0.0.1/000/",
    "/resource3/ftp/hmgy/gsc6/rec/2024-07-30/127.0.0.1/000/"
]
# 目标目录列表
dst_dir = [
    f"/resource/ftp/hmgy/gsc1/rec/{now_time_day}/127.0.0.1/000/",
    f"/resource/ftp/hmgy/gsc2/rec/{now_time_day}/127.0.0.1/000/",
    f"/resource/ftp/hmgy/gsc3/rec/{now_time_day}/127.0.0.1/000/",
    f"/resource/ftp/hmgy/gsc4/rec/{now_time_day}/127.0.0.1/000/",
    f"/resource/ftp/hmgy/gsc5/rec/{now_time_day}/127.0.0.1/000/",
    f"/resource/ftp/hmgy/gsc6/rec/{now_time_day}/127.0.0.1/000/"
]

# 虎门公园大摆锤脚本
src_dir_dbc = [
    "/resource3/ftp/hmgy/dbc1/rec/2024-07-30/127.0.0.1/000/",
    "/resource3/ftp/hmgy/dbc2/rec/2024-07-30/127.0.0.1/000/"

]
# 目标目录列表
dst_dir_dbc = [
    f"/resource/ftp/hmgy/dbc1/rec/{now_time_day}/127.0.0.1/000/",
    f"/resource/ftp/hmgy/dbc2/rec/{now_time_day}/127.0.0.1/000/"
]

# 虎门公园大转盘脚本
src_dir_dzp = [
    "/resource3/ftp/hmgy/dzp1/rec/2024-07-30/127.0.0.1/000/",
    "/resource3/ftp/hmgy/dzp2/rec/2024-07-30/127.0.0.1/000/"

]
# 目标目录列表
dst_dir_dzp = [
    f"/resource/ftp/hmgy/dzp1/rec/{now_time_day}/127.0.0.1/000/",
    f"/resource/ftp/hmgy/dzp2/rec/{now_time_day}/127.0.0.1/000/"
]

# 虎门公园爬山车脚本
src_dir_psc = [
    "/resource3/ftp/hmgy/psc1/rec/2024-07-30/127.0.0.1/000/",
    "/resource3/ftp/hmgy/psc2/rec/2024-07-30/127.0.0.1/000/",
    "/resource3/ftp/hmgy/psc3/rec/2024-07-30/127.0.0.1/000/"

]
# 目标目录列表
dst_dir_psc = [
    f"/resource/ftp/hmgy/psc1/rec/{now_time_day}/127.0.0.1/000/",
    f"/resource/ftp/hmgy/psc2/rec/{now_time_day}/127.0.0.1/000/",
    f"/resource/ftp/hmgy/psc3/rec/{now_time_day}/127.0.0.1/000/"
]

# 虎门公园海盗船左脚本
src_dir_hdcz = [
    "/resource3/ftp/hmgy/hdcz1/rec/2024-07-30/127.0.0.1/000/",
    "/resource3/ftp/hmgy/hdcz2/rec/2024-07-30/127.0.0.1/000/",
    "/resource3/ftp/hmgy/hdcz3/rec/2024-07-30/127.0.0.1/000/"

]
# 目标目录列表
dst_dir_hdcz = [
    f"/resource/ftp/hmgy/hdcz1/rec/{now_time_day}/127.0.0.1/000/",
    f"/resource/ftp/hmgy/hdcz2/rec/{now_time_day}/127.0.0.1/000/",
    f"/resource/ftp/hmgy/hdcz3/rec/{now_time_day}/127.0.0.1/000/"
]

# 虎门公园海盗船右脚本
src_dir_hdcy = [
    "/resource3/ftp/hmgy/hdcy1/rec/2024-07-30/127.0.0.1/000/",
    "/resource3/ftp/hmgy/hdcy2/rec/2024-07-30/127.0.0.1/000/",
    "/resource3/ftp/hmgy/hdcy3/rec/2024-07-30/127.0.0.1/000/"

]
# 目标目录列表
dst_dir_hdcy = [
    f"/resource/ftp/hmgy/hdcy1/rec/{now_time_day}/127.0.0.1/000/",
    f"/resource/ftp/hmgy/hdcy2/rec/{now_time_day}/127.0.0.1/000/",
    f"/resource/ftp/hmgy/hdcy3/rec/{now_time_day}/127.0.0.1/000/"
]

file_ext = "dat"  # 只处理.dat文件
minute_add = 10  # 增加的分钟数

copy_and_modify_files(src_dir, dst_dir, file_ext, minute_add)

# copy_and_modify_files(src_dir_dbc, dst_dir_dbc, file_ext, minute_add)

# copy_and_modify_files(src_dir_dzp, dst_dir_dzp, file_ext, minute_add)

# copy_and_modify_files(src_dir_psc, dst_dir_psc, file_ext, minute_add)

# copy_and_modify_files(src_dir_hdcz, dst_dir_hdcz, file_ext, minute_add)

# copy_and_modify_files(src_dir_hdcy, dst_dir_hdcy, file_ext, minute_add)



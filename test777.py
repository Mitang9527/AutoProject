import time
now_time_day = time.strftime("%Y-%m-%d", time.localtime())
print(now_time_day)

dsc_dir = [
    f"/resource/ftp/ssty/gsc1/rec/{now_time_day}/127.0.0.1/000/",
    "/resource/ftp/ssty/gsc2/rec/2024-06-28/127.0.0.1/000/",
    "/resource/ftp/ssty/gsc3/rec/2024-06-28/127.0.0.1/000/",
    "/resource/ftp/ssty/gsc4/rec/2024-06-28/127.0.0.1/000/",
    "/resource/ftp/ssty/gsc5/rec/2024-06-28/127.0.0.1/000/"
]
print(dsc_dir)
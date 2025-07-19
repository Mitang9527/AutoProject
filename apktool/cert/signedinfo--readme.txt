echo on

SET CURRENT_PATH=%CD%

SET PATH=%PATH%;%CURRENT_PATH%\win

call apktool.bat b --use-aapt2 -o app-unsigned-unaligned.apk app_out
call zipalign.exe -v -p 4 app-unsigned-unaligned.apk app-unsigned.apk
del app-unsigned-unaligned.apk
call apksigner.bat sign --ks cert/shanlitech.keystore --ks-pass pass:Lgsj829517 --out app.apk app-unsigned.apk
del app-unsigned.apk

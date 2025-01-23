@echo off
setlocal enabledelayedexpansion

:: 设置所有Monkey日志存放的目录(根据实际情况修改)
:: set ff="C:\Users\Administrator\Desktop\log\*.log"
set ff="D:\code\AutoProject\logs\*.log"

:: 设置查询关键字
set str=CRASH crash ANR died

:: 设置查询结果存放的目录
set fileName=Result.txt

:: 开始查询
echo 正在统计
echo.
echo %date% %time% > %fileName%
echo. >> %fileName%
echo 分析结果：>> %fileName%
echo ---------------------------------------------- >> %fileName%

:: 依次打开目录下每一个Monkey日志查询关键字并输出个数
(for %%a in (%str%) do (
    set n%%a=0
    set /p= %%a : <nul> con
    for /f "delims=" %%b in ('findstr /I "%%a" %ff%') do (
        set h=%%b
        call :yky %%a
    )
    echo !n%%a! > con
    echo 关键字 %%a 共有 !n%%a! 处
)) >> %fileName%

echo. >> %fileName%

:: 针对崩溃的日志输出其所在文件行数
echo 崩溃日志： >> %fileName%
findstr /I "%str%" %ff% >> %fileName%

:: 自动打开结果文件
start notepad %fileName%

echo.
pause
exit

:yky
set /a n%1+=1
set h=!h:*%1=!
if defined h if not "!h:*%1=!"=="!h!" goto :yky

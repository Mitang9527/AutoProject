@echo off
setlocal enabledelayedexpansion

:: ��������Monkey��־��ŵ�Ŀ¼(����ʵ������޸�)
:: set ff="C:\Users\Administrator\Desktop\log\*.log"
set ff="D:\code\AutoProject\logs\*.log"

:: ���ò�ѯ�ؼ���
set str=CRASH crash ANR died

:: ���ò�ѯ�����ŵ�Ŀ¼
set fileName=Result.txt

:: ��ʼ��ѯ
echo ����ͳ��
echo.
echo %date% %time% > %fileName%
echo. >> %fileName%
echo ���������>> %fileName%
echo ---------------------------------------------- >> %fileName%

:: ���δ�Ŀ¼��ÿһ��Monkey��־��ѯ�ؼ��ֲ��������
(for %%a in (%str%) do (
    set n%%a=0
    set /p= %%a : <nul> con
    for /f "delims=" %%b in ('findstr /I "%%a" %ff%') do (
        set h=%%b
        call :yky %%a
    )
    echo !n%%a! > con
    echo �ؼ��� %%a ���� !n%%a! ��
)) >> %fileName%

echo. >> %fileName%

:: ��Ա�������־����������ļ�����
echo ������־�� >> %fileName%
findstr /I "%str%" %ff% >> %fileName%

:: �Զ��򿪽���ļ�
start notepad %fileName%

echo.
pause
exit

:yky
set /a n%1+=1
set h=!h:*%1=!
if defined h if not "!h:*%1=!"=="!h!" goto :yky

@echo off
copy "%~dp0start.vbs" "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\ai_input.vbs"
echo 已添加开机自启动！
echo 现在立即启动一次...
pythonw.exe "%~dp0ai_input.py"
pause

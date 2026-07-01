@echo off
chcp 65001 >nul
echo ===================================================
echo   正在为 Work Buddy 桌宠配置开机自启和后台静默运行...
echo ===================================================

:: 获取当前目录
set "CURRENT_DIR=%~dp0"
set "VBS_PATH=%CURRENT_DIR%run_hidden.vbs"
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_FOLDER%\WorkBuddy_DeskPet.lnk"

:: 创建快捷方式的 VBS 脚本
set "CREATE_SHORTCUT_VBS=%TEMP%\CreateShortcut.vbs"
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%CREATE_SHORTCUT_VBS%"
echo sLinkFile = "%SHORTCUT_PATH%" >> "%CREATE_SHORTCUT_VBS%"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%CREATE_SHORTCUT_VBS%"
echo oLink.TargetPath = "%VBS_PATH%" >> "%CREATE_SHORTCUT_VBS%"
echo oLink.WorkingDirectory = "%CURRENT_DIR%" >> "%CREATE_SHORTCUT_VBS%"
echo oLink.Description = "Work Buddy Desk Pet Auto Start" >> "%CREATE_SHORTCUT_VBS%"
echo oLink.Save >> "%CREATE_SHORTCUT_VBS%"

:: 运行并生成快捷方式
cscript /nologo "%CREATE_SHORTCUT_VBS%"
del "%CREATE_SHORTCUT_VBS%"

echo.
echo [成功] 已将桌宠加入系统开机启动项！
echo 路径: %SHORTCUT_PATH%
echo.
echo 正在为您立即在后台启动桌宠...
cscript /nologo "%VBS_PATH%"

echo.
echo [完成] 桌宠现已在后台静默运行！
echo 以后每次开机它都会自动在后台蹲守。
echo 当您打开 Work Buddy 时，它会自动出现。
echo.
pause

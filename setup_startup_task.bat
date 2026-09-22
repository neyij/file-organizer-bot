@echo off
set TASK_NAME=FileArrangementDaemon
set SCRIPT_DIR=%~dp0
set VBS_TARGET=%SCRIPT_DIR%start_daemon.vbs

echo Registering scheduled task '%TASK_NAME%' to run automatically at user logon...
schtasks /create /tn "%TASK_NAME%" /tr "wscript.exe \"%VBS_TARGET%\"" /sc onlogon /rl limited /f

if %errorlevel% equ 0 (
    echo.
    echo Task '%TASK_NAME%' registered successfully!
    echo It will start silently in the background whenever you log into Windows.
) else (
    echo.
    echo Failed to create Task Scheduler task. Creating Startup Folder shortcut fallback...
    powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([Environment]::GetFolderPath('Startup') + '\FileArrangementDaemon.lnk'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\"%VBS_TARGET%\"'; $s.WorkingDirectory = '%SCRIPT_DIR%'; $s.Save()"
    echo Startup shortcut added to Windows Startup folder.
)
echo.
pause

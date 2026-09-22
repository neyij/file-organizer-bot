@echo off
echo Stopping File Organizer background processes...
wmic process where "name='pythonw.exe' and CommandLine like '%%organize_files.py%%'" call terminate >nul 2>&1
if %errorlevel% neq 0 (
    powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*organize_files.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
)
echo Done. File Organizer stopped.
pause

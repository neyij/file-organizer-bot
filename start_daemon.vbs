Set WshShell = CreateObject("WScript.Shell")
strCurDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
' Run pythonw.exe completely hidden (window style 0, do not wait)
WshShell.Run "pythonw """ & strCurDir & "\organize_files.py""", 0, False

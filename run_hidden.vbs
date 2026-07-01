Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "python """ & CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\main.py""", 0, False

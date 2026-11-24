' Windowless desktop launcher for lplab Native Desktop GUI
Set WshShell = CreateObject("WScript.Shell")
currentDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = currentDir

Dim fso, exePath, distExePath, pythonwPath, pythonPath
Set fso = CreateObject("Scripting.FileSystemObject")
exePath = currentDir & "\lplab.exe"
distExePath = currentDir & "\dist\lplab.exe"
pythonwPath = currentDir & "\.venv\Scripts\pythonw.exe"
pythonPath = currentDir & "\.venv\Scripts\python.exe"

If fso.FileExists(exePath) Then
    WshShell.Run """" & exePath & """ gui", 0, False
ElseIf fso.FileExists(distExePath) Then
    WshShell.Run """" & distExePath & """ gui", 0, False
ElseIf fso.FileExists(pythonwPath) Then
    WshShell.Run """" & pythonwPath & """ -m lplab.gui", 0, False
ElseIf fso.FileExists(pythonPath) Then
    WshShell.Run """" & pythonPath & """ -m lplab.gui", 0, False
Else
    WshShell.Run "pythonw -m lplab.gui", 0, False
End If

Set fso = Nothing
Set WshShell = Nothing

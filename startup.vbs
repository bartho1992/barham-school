Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

' Repertoire de l'application
strAppDir = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strAppDir

' Attendre que Windows soit entierement charge
WScript.Sleep 15000

' Demarrer le serveur Flask (fenetre invisible)
WshShell.Run "C:\Python314\python.exe """ & strAppDir & "\app.py""", 0, False

' Demarrer le gardien (fenetre invisible)
WshShell.Run "wscript.exe """ & strAppDir & "\gardien.vbs""", 0, False

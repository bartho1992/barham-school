Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

' Se placer dans le dossier de l'application
WshShell.CurrentDirectory = FSO.GetParentFolderName(WScript.ScriptFullName)

' Lancer le serveur sans fenetre (0 = invisible)
WshShell.Run "python app.py", 0, False

' Attendre que le serveur soit pret
WScript.Sleep 4000

' Ouvrir le navigateur
WshShell.Run "http://localhost:5000"

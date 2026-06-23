Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

strAppDir = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strAppDir
strPython = "C:\Python314\python.exe"

' --- Demarrer le serveur ---
Sub StartServer()
    On Error Resume Next
    WshShell.Run """" & strPython & """ """ & strAppDir & "\app.py""", 0, False
    WScript.Sleep 7000
End Sub

' --- Le serveur tourne-t-il ? ---
Function IsPythonRunning()
    On Error Resume Next
    Dim ret
    ret = WshShell.Run("cmd /c tasklist /nh /fi ""IMAGENAME eq python.exe"" 2>nul | find /i ""python"" >nul", 0, True)
    If Err.Number <> 0 Then Err.Clear : IsPythonRunning = False : Exit Function
    IsPythonRunning = (ret = 0)
End Function

' ============================================================
' DEMARRER LE SERVEUR PUIS SURVEILLER EN BOUCLE INFINIE
' ============================================================
Call StartServer()

Do While True
    If Not IsPythonRunning() Then Call StartServer()
    WScript.Sleep 15000
Loop

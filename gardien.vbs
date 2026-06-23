Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

' Repertoire de l'application
strAppDir = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strAppDir

' Chemin complet vers Python
strPython = "C:\Python314\python.exe"

' Fonction pour verifier si python.exe est en cours d'execution
Function IsPythonRunning()
    On Error Resume Next
    Dim intRetVal
    intRetVal = WshShell.Run("cmd /c tasklist /nh /fi ""IMAGENAME eq python.exe"" 2>nul | find /i ""python"" >nul", 0, True)
    If Err.Number <> 0 Then
        Err.Clear
        IsPythonRunning = False
    ElseIf intRetVal = 0 Then
        IsPythonRunning = True
    Else
        IsPythonRunning = False
    End If
End Function

' Fonction pour demarrer le serveur Flask
Sub StartServer()
    On Error Resume Next
    WshShell.Run """" & strPython & """ """ & strAppDir & "\app.py""", 0, False
    WScript.Sleep 6000
End Sub

' ============================================
' Programme principal - Gardien de processus
' ============================================

' Attendre que le serveur principal demarre
WScript.Sleep 8000

' Boucle de surveillance : verifier toutes les 15 secondes
Do While True
    If Not IsPythonRunning() Then
        Call StartServer()
    End If
    WScript.Sleep 15000
Loop

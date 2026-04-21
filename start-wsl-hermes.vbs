Set oShell = CreateObject("WScript.Shell")
oShell.Run "wsl -- bash -c 'systemctl --user start hermes'", 0, False

# Creates Windows shortcuts to launch lplab GUI silently
$WshShell = New-Object -ComObject WScript.Shell

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $scriptDir) { $scriptDir = (Get-Location).Path }

$exePath = Join-Path $scriptDir "lplab.exe"
$distExePath = Join-Path $scriptDir "dist\lplab.exe"
$pythonwPath = Join-Path $scriptDir ".venv\Scripts\pythonw.exe"

if (Test-Path $exePath) {
    $targetPath = $exePath
    $arguments = "gui"
} elseif (Test-Path $distExePath) {
    $targetPath = $distExePath
    $arguments = "gui"
} elseif (Test-Path $pythonwPath) {
    $targetPath = $pythonwPath
    $arguments = "-m lplab.gui"
} else {
    $targetPath = "wscript.exe"
    $arguments = "`"$scriptDir\launch_gui.vbs`""
}
$icon = "$env:SystemRoot\System32\shell32.dll,220"

# 1. Desktop shortcut
$desktopDir = [Environment]::GetFolderPath("Desktop")
$desktopShortcutPath = Join-Path $desktopDir "lplab.lnk"
$shortcut = $WshShell.CreateShortcut($desktopShortcutPath)
$shortcut.TargetPath = $targetPath
$shortcut.Arguments = $arguments
$shortcut.WorkingDirectory = $scriptDir
$shortcut.Description = "lplab - CompTIA Linux+ (XK0-006) Hands-On Lab Engine"
$shortcut.IconLocation = $icon
$shortcut.Save()

# 2. Project root shortcut
$projectShortcutPath = Join-Path $scriptDir "lplab.lnk"
$projectShortcut = $WshShell.CreateShortcut($projectShortcutPath)
$projectShortcut.TargetPath = $targetPath
$projectShortcut.Arguments = $arguments
$projectShortcut.WorkingDirectory = $scriptDir
$projectShortcut.Description = "lplab - CompTIA Linux+ (XK0-006) Hands-On Lab Engine"
$projectShortcut.IconLocation = $icon
$projectShortcut.Save()

# 3. Start Menu Programs shortcut
$programsDir = [Environment]::GetFolderPath("Programs")
$startMenuShortcutPath = Join-Path $programsDir "Linux+ Lab Engine.lnk"
$smShortcut = $WshShell.CreateShortcut($startMenuShortcutPath)
$smShortcut.TargetPath = $targetPath
$smShortcut.Arguments = $arguments
$smShortcut.WorkingDirectory = $scriptDir
$smShortcut.Description = "lplab - CompTIA Linux+ (XK0-006) Hands-On Lab Engine"
$smShortcut.IconLocation = $icon
$smShortcut.Save()

Write-Host "Desktop shortcut created: $desktopShortcutPath"
Write-Host "Project shortcut created: $projectShortcutPath"
Write-Host "Start Menu shortcut created: $startMenuShortcutPath"

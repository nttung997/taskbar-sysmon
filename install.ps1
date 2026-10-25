#Requires -Version 5.1
[CmdletBinding()]
param(
    [switch]$SkipAutostart,
    [switch]$NoStart
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venv = Join-Path $root '.venv'
$python = Join-Path $venv 'Scripts\python.exe'
$pythonw = Join-Path $venv 'Scripts\pythonw.exe'
$entry = Join-Path $root 'run.pyw'

if (-not (Test-Path $python)) {
    Write-Host 'Creating virtual environment...'
    python -m venv $venv
}

Write-Host 'Installing dependencies...'
& $python -m pip install --upgrade pip --quiet
& $python -m pip install -r (Join-Path $root 'requirements.txt') --quiet

if (-not $SkipAutostart) {
    $startup = [Environment]::GetFolderPath('Startup')
    $shortcutPath = Join-Path $startup 'SysMon 3x3.lnk'
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $pythonw
    $shortcut.Arguments = '"' + $entry + '"'
    $shortcut.WorkingDirectory = $root
    $shortcut.WindowStyle = 7
    $shortcut.Description = '3x3 dot-matrix system monitor'
    $shortcut.Save()
    Write-Host "Autostart shortcut created: $shortcutPath"
}

if (-not $NoStart) {
    Start-Process -FilePath $pythonw -ArgumentList ('"' + $entry + '"') -WorkingDirectory $root
    Write-Host 'SysMon started - look for the 3x3 dot icon in the notification area.'
}

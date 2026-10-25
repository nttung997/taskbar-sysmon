#Requires -Version 5.1
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

$shortcutPath = Join-Path ([Environment]::GetFolderPath('Startup')) 'SysMon 3x3.lnk'
if (Test-Path $shortcutPath) {
    Remove-Item $shortcutPath -Force
    Write-Host "Removed autostart shortcut: $shortcutPath"
}

Get-CimInstance Win32_Process -Filter "Name = 'pythonw.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like '*run.pyw*' -and $_.CommandLine -like '*taskbar-sysmon*' } |
    ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        Write-Host "Stopped process $($_.ProcessId)"
    }

Write-Host 'SysMon stopped and autostart removed. The .venv folder was left in place.'

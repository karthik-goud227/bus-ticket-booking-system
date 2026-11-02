$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Python environment missing. Follow the setup steps in README.md first.'
}

$activeAdapters = @(Get-NetAdapter | Where-Object {
    $_.Status -eq 'Up' -and $_.HardwareInterface
} | Select-Object -ExpandProperty ifIndex)

$lanAddresses = @(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
    $activeAdapters -contains $_.InterfaceIndex -and
    $_.AddressState -eq 'Preferred' -and
    $_.IPAddress -notmatch '^(127\.|169\.254\.)'
} | Select-Object -ExpandProperty IPAddress -Unique)

$env:BUSBOOK_LAN_HOST = $lanAddresses -join ','
if (-not $env:DB_PASSWORD) {
    $secure = Read-Host 'BUSBOOKING password' -AsSecureString
    $env:DB_PASSWORD = [System.Net.NetworkCredential]::new('', $secure).Password
}

Write-Host 'Refreshing the next 14 days of recurring trips...'
& $pythonPath manage.py generate_daily_trips --days 14
if ($LASTEXITCODE -ne 0) {
    throw 'Trip generation failed. Run the latest database migrations, then try again.'
}

Write-Host 'Your laptop: http://127.0.0.1:8000/'
if ($lanAddresses.Count -eq 0) {
    Write-Warning 'No active physical network IPv4 address found. Connect to Wi-Fi or a hotspot, then restart this script.'
} else {
    Write-Host 'Teammate links (use the one for the network they joined):'
    foreach ($address in $lanAddresses) {
        Write-Host "  http://${address}:8000/"
    }
}
Write-Host 'Keep this window open. After switching networks, stop with Ctrl+C and run this script again.'
& $pythonPath manage.py runserver 0.0.0.0:8000

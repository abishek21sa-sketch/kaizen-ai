$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$url = "https://archive.ics.uci.edu/static/public/447/condition+monitoring+of+hydraulic+systems.zip"
Invoke-WebRequest -Uri $url -OutFile (Join-Path $root "hydraulic_systems.zip")
Write-Host "EXTERNAL_DATA_REFRESH=PASS"

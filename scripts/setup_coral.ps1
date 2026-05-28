# Register Coral specs with paths for this machine
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

& "$root\.venv\Scripts\python.exe" "$root\scripts\setup_coral.py"

if (-not (Get-Command coral -ErrorAction SilentlyContinue)) {
    Write-Host "Coral CLI not found. Install from Coral hackathon docs, then run:"
    Write-Host "  coral spec apply coral/mock_sources.yaml"
    Write-Host "  coral spec apply coral/live_obs.yaml"
    Write-Host "  coral spec apply coral/cortex_system.yaml"
    exit 0
}

Set-Location $root
coral spec apply coral/mock_sources.yaml
coral spec apply coral/live_obs.yaml
coral spec apply coral/cortex_system.yaml
Write-Host "Coral specs applied. Test: coral sql `"SELECT * FROM mock_obs.sentry_issues LIMIT 1`""

param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

if (Test-Path ".venv") {
    $cfg = Join-Path ".venv" "pyvenv.cfg"
    if (Test-Path $cfg) {
        $content = Get-Content $cfg -Raw
        if ($content -match "Users\\ilfir|Users/ilfir") {
            Write-Host "Ancien environnement detecte. Suppression de .venv..."
            Remove-Item ".venv" -Recurse -Force
        }
    }
}

if (-not (Test-Path ".venv")) {
    Write-Host "Creation de l'environnement virtuel..."
    & $Python -m venv .venv
}

$VenvPython = Join-Path ".venv" "Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r requirements.txt

Write-Host ""
Write-Host "Environnement pret."
Write-Host "Tests rapides:"
Write-Host "  .\.venv\Scripts\python.exe scripts\run_business_tests.py"
Write-Host "Dashboard:"
Write-Host "  .\.venv\Scripts\streamlit.exe run dashboard\app.py"

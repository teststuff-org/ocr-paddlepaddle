$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Get-Command uv -ErrorAction SilentlyContinue) {
    if (-not (Test-Path ".venv")) { uv venv }
    uv pip install -r requirements.txt
    uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
}
else {
    Write-Host "uv introuvable, utilisation de venv + pip (installer uv : https://docs.astral.sh/uv/)"
    if (-not (Test-Path ".venv")) { python -m venv .venv }
    & .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
}

$ErrorActionPreference = 'Stop'

. .\.venv\Scripts\Activate.ps1
git pull origin main
pip install --upgrade -r requirements.txt

Write-Host "Updated to latest version."

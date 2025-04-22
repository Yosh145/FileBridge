$ErrorActionPreference = 'Stop'

python -m venv .venv
. .\.venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install -r requirements.txt

Write-Host "Installation complete. Run '. .\ .venv\Scripts\Activate.ps1; python src\filebridge.py'"

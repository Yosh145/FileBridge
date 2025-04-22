# Stop on any error
$ErrorActionPreference = 'Stop'

# Activate the virtual environment
. .\.venv\Scripts\Activate.ps1

# Pull the latest changes from GitHub
git pull origin main

# Upgrade Python dependencies
pip install --upgrade PyQt5 qdarkstyle google-auth-oauthlib google-api-python-client

Write-Host "Updated to latest version."

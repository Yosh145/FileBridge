#!/usr/bin/env bash
set -e

# Activate the virtual environment
source .venv/bin/activate

# Pull the latest changes from GitHub
git pull origin main

# Upgrade Python dependencies
pip install --upgrade PyQt5 qdarkstyle google-auth-oauthlib google-api-python-client

echo "Updated to latest version."

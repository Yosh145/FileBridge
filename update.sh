#!/usr/bin/env bash
set -e

source .venv/bin/activate
git pull origin main
pip install --upgrade -r requirements.txt

echo "Updated to latest version."

#!/usr/bin/env bash
set -o errexit

python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt

npm --prefix frontend ci
npm --prefix frontend run build

python backend/manage.py collectstatic --no-input

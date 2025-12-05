#!/bin/bash
set -e
export PYTHONPATH=/app:$PYTHONPATH
cd /app
exec gunicorn --bind 0.0.0.0:5001 --timeout 3600 --workers 2 app.main:app


#!/bin/bash
# Render startup script for ResellGenie

# Ensure we're in the project directory
cd /opt/render/project/src || exit 1

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Install gunicorn if not present (safety check)
python -m pip list | grep gunicorn || pip install gunicorn

# Start the application
exec gunicorn web_app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120

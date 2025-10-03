#!/bin/bash
# Force software rendering to avoid potential GPU/driver conflicts
export QT_OPENGL=software
# Set the Python path to include the app's root directory
export PYTHONPATH=/app
# Run the main application
python3 /app/app/main_window.py
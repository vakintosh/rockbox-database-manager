#!/bin/bash
# Launcher script for Rockbox Database Manager GUI on macOS
# This ensures we use framework-enabled Python for wxPython

cd "$(dirname "$0")"

# Use the venv created with Homebrew's framework Python
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment with framework Python..."
    UV_PYTHON=/usr/local/opt/python@3.11/bin/python3.11 uv venv .venv
    uv pip install mutagen wxpython
fi

# Launch the GUI using the framework-enabled Python
echo "Launching Rockbox Database Manager..."
.venv/bin/python gui.pyw


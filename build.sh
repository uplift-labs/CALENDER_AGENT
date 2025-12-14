#!/bin/bash
# Build script for Email Agent - macOS/Linux
# Creates a standalone executable

echo "========================================"
echo "Building Email Agent Executable"
echo "========================================"

# Install PyInstaller if not present
pip install pyinstaller

# Build the executable
pyinstaller --onefile \
    --name EmailAgent \
    --add-data "config.py:." \
    --hidden-import=composio \
    --hidden-import=openai \
    --hidden-import=flask \
    --collect-all composio \
    --collect-all openai \
    main.py

echo "========================================"
echo "Build complete!"
echo "Executable is in: dist/EmailAgent"
echo "========================================"


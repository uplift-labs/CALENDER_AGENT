@echo off
REM Build script for Email Agent - Windows
REM Creates a standalone .exe file

echo ========================================
echo Building Email Agent Executable
echo ========================================

REM Install PyInstaller if not present
pip install pyinstaller

REM Build the executable
pyinstaller --onefile ^
    --name EmailAgent ^
    --add-data "config.py;." ^
    --hidden-import=composio ^
    --hidden-import=openai ^
    --hidden-import=flask ^
    --collect-all composio ^
    --collect-all openai ^
    main.py

echo ========================================
echo Build complete!
echo Executable is in: dist\EmailAgent.exe
echo ========================================

pause


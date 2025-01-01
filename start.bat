@echo off
start "" "https://discord.gg/leafhub"
echo Installing required libraries...
pip install requests aiohttp tls_client colorama

if %errorlevel% neq 0 (
    echo Failed to install required libraries. Please check your Python and pip installation.
    pause
    exit /b
)

echo Starting Username Sniper...
python main.py

if %errorlevel% neq 0 (
    echo An error occurred while running the script. Please check the output for details.
    pause
)
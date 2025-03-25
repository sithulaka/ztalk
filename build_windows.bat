@echo off
echo Building ZTalk for Windows...

REM Check if Python is installed
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Python not found. Please install Python 3.6+ and try again.
    exit /b 1
)

REM Check if virtual environment exists
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to create virtual environment. Make sure venv is available.
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller

REM Build with PyInstaller
echo Building application...
pyinstaller --noconfirm --onedir --windowed ^
    --name ZTalk ^
    --icon=docs/icon.ico ^
    --add-data ".venv\Lib\site-packages\customtkinter;customtkinter\" ^
    main.py

echo Build completed. The executable is located in dist\ZTalk\ZTalk.exe

REM Deactivate virtual environment
call deactivate

echo Build process finished! 
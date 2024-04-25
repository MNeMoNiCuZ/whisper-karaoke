@echo off
if "%~1"=="" (
    start cmd /k "%0" run
    exit /b
)

REM Check if python is installed
python --version > nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Python is not installed. Please install Python and rerun this script.
    goto end
)

REM Creating virtual environment
echo Creating virtual environment...
python -m venv venv

REM Activate the virtual environment
call venv\Scripts\activate

REM Check if pip is available
pip --version > nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo pip is not available. Please ensure pip is installed.
    goto end
)

REM Install requirements from the requirements.txt file
echo Installing packages from requirements.txt...
pip install -r requirements.txt

echo Attempting to create launch.bat to run app.py...
echo @echo off > launch.bat
echo call venv\Scripts\activate >> launch.bat
echo python app.py >> launch.bat
echo echo. >> launch.bat
echo echo Application exited. Press any key to close... >> launch.bat
echo pause >> launch.bat
echo launch.bat created successfully.

:end
echo Setup complete. Virtual environment is ready to use.
pause

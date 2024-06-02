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

REM Add .gitignore to the virtual environment folder
echo Creating .gitignore in the venv folder...
(
echo # Ignore all content in the virtual environment directory
echo *
echo # Except this file
echo !.gitignore
) > venv\.gitignore

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

REM Create launch.bat to run app.py
echo Attempting to create launch.bat to run app.py...
(
echo @echo off
echo call venv\Scripts\activate
echo python app.py
echo echo.
echo echo Application exited. Press any key to close...
echo pause
) > launch.bat
echo launch.bat created successfully.

echo Attempting to create batch_convert.bat to run batch_convert.py...
(
echo @echo off
echo call venv\Scripts\activate
echo python batch_convert.py
echo echo.
echo echo Batch conversion completed. Press any key to close...
echo pause
) > batch_convert.bat
echo batch_convert.bat created successfully.

:end
echo Setup complete. Virtual environment is ready to use.
pause

@echo off
setlocal EnableDelayedExpansion

:: ============================================================================
:: WINDOWS PROJECT LIFECYCLE MANAGER
:: Compatible with Windows 10 and Windows 11 (64-bit)
:: Features:
::   1. Startup script with automated dependency checks & installations:
::      - Python runtime check & winget/choco auto-install
::      - pip package manager bootstrap
::      - Project dependencies installation (requirements.txt / package.json)
::      - Core service engine check (LibreOffice for document processing)
::      - Project startup with port verification and PID tracking
::   2. Stop script with graceful process termination & network port cleanup
::   3. Simple, intuitive text menu with Options 1, 2, and 3
:: ============================================================================

:: ----------------------------------------------------------------------------
:: SECTION 1: CONFIGURATION & ENVIRONMENT VARIABLES
:: Reusable settings that can be customized for any project.
:: ----------------------------------------------------------------------------
set "PROJECT_NAME=Universal Document Generation Engine (UDGE)"
set "HOST=127.0.0.1"
set "PORT=8000"
set "PID_FILE=server.pid"
set "REQUIREMENTS_FILE=requirements.txt"
set "PACKAGE_JSON=package.json"

:: Project Startup Command (e.g., python app.py, npm start, uvicorn ...)
set "STARTUP_CMD=python -m uvicorn udge.web.app:app --host %HOST% --port %PORT%"

:: Dependency Check Flags (1 = enable check & auto-install, 0 = disable)
set "ENABLE_PYTHON_CHECK=1"
set "ENABLE_PIP_CHECK=1"
set "ENABLE_NODE_CHECK=0"
set "ENABLE_LIBREOFFICE_CHECK=1"

:: Set working directory to the folder containing this batch script
set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

:: Support direct non-interactive CLI arguments for automation / CI
if /i "%~1"=="1" goto START_PROJECT
if /i "%~1"=="start" goto START_PROJECT
if /i "%~1"=="2" goto STOP_PROJECT
if /i "%~1"=="stop" goto STOP_PROJECT
if /i "%~1"=="3" goto EXIT_SCRIPT
if /i "%~1"=="exit" goto EXIT_SCRIPT

:: ----------------------------------------------------------------------------
:: SECTION 2: INTERACTIVE TEXT MENU
:: ----------------------------------------------------------------------------
:MENU
cls
echo ============================================================================
echo   !PROJECT_NAME!
echo   Windows Service ^& Process Control Panel
echo ============================================================================
echo.
echo   Option 1: Start Project (with dependency check ^& install)
echo   Option 2: Stop Project
echo   Option 3: Exit
echo.
echo ============================================================================
set /p "CHOICE=Select an option [1-3]: "

if "%CHOICE%"=="1" goto START_PROJECT
if "%CHOICE%"=="2" goto STOP_PROJECT
if "%CHOICE%"=="3" goto EXIT_SCRIPT

echo.
echo [ERROR] Invalid selection "!CHOICE!". Please choose 1, 2, or 3.
ping -n 3 127.0.0.1 >nul
goto MENU


:: ----------------------------------------------------------------------------
:: SECTION 3: START SCRIPT (Check, Auto-Install & Start Project)
:: ----------------------------------------------------------------------------
:START_PROJECT
cls
echo ============================================================================
echo   STARTING PROJECT: !PROJECT_NAME!
echo ============================================================================
echo.

:: ----------------------------------------------------------------------------
:: 3.1 Check & Auto-Install Python Runtime
:: ----------------------------------------------------------------------------
if not "%ENABLE_PYTHON_CHECK%"=="1" goto SKIP_PYTHON_CHECK
echo [CHECK] Verifying Python runtime...
where python >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo [OK] Python is installed: %%v
    goto SKIP_PYTHON_CHECK
)

echo [WARNING] Python was not found in system PATH.
echo [INSTALL] Attempting automatic installation via Windows Package Manager (winget)...
where winget >nul 2>&1
if not errorlevel 1 (
    winget install -e --id Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
    if not errorlevel 1 (
        echo [OK] Python installed successfully.
        goto SKIP_PYTHON_CHECK
    )
)

echo [WARNING] winget installation failed or is unavailable. Checking Chocolatey...
where choco >nul 2>&1
if not errorlevel 1 (
    choco install python3 -y
    if not errorlevel 1 (
        echo [OK] Python installed via Chocolatey.
        goto SKIP_PYTHON_CHECK
    )
)

echo [FATAL] Automatic Python installation could not be completed.
echo [ACTION] Please install Python manually from https://www.python.org/downloads/
pause
goto MENU

:SKIP_PYTHON_CHECK

:: ----------------------------------------------------------------------------
:: 3.2 Check & Bootstrap pip Package Manager
:: ----------------------------------------------------------------------------
if not "%ENABLE_PIP_CHECK%"=="1" goto SKIP_PIP_CHECK
echo.
echo [CHECK] Verifying pip package manager...
python -m pip --version >nul 2>&1
if not errorlevel 1 (
    echo [OK] pip package manager is ready.
    goto SKIP_PIP_CHECK
)

echo [INSTALL] Bootstrapping pip via ensurepip...
python -m ensurepip --default-pip
if errorlevel 1 (
    echo [ERROR] Failed to bootstrap pip. Please ensure Python is configured properly.
    pause
    goto MENU
)
echo [OK] pip bootstrapped successfully.

:SKIP_PIP_CHECK

:: ----------------------------------------------------------------------------
:: 3.3 Check & Auto-Install Node.js / npm (if enabled)
:: ----------------------------------------------------------------------------
if not "%ENABLE_NODE_CHECK%"=="1" goto SKIP_NODE_CHECK
echo.
echo [CHECK] Verifying Node.js and npm...
where node >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=*" %%v in ('node -v 2^>^&1') do echo [OK] Node.js is installed: %%v
    goto SKIP_NODE_CHECK
)

echo [WARNING] Node.js was not found in system PATH.
echo [INSTALL] Attempting automatic installation of Node.js LTS via winget...
where winget >nul 2>&1
if not errorlevel 1 (
    winget install -e --id OpenJS.NodeJS.LTS --silent --accept-package-agreements --accept-source-agreements
    if not errorlevel 1 (
        echo [OK] Node.js LTS installed successfully.
        goto SKIP_NODE_CHECK
    )
)

echo [ERROR] Automatic Node.js installation failed.
echo [ACTION] Please install Node.js manually from https://nodejs.org/
pause
goto MENU

:SKIP_NODE_CHECK

:: ----------------------------------------------------------------------------
:: 3.4 Check & Auto-Install LibreOffice (Required for Document Engine)
:: ----------------------------------------------------------------------------
if not "%ENABLE_LIBREOFFICE_CHECK%"=="1" goto SKIP_LIBREOFFICE_CHECK
echo.
echo [CHECK] Verifying LibreOffice document conversion engine...
set "LO_FOUND=0"
if exist "C:\Program Files\LibreOffice\program\soffice.com" set "LO_FOUND=1"
if exist "C:\Program Files (x86)\LibreOffice\program\soffice.com" set "LO_FOUND=1"
where soffice >nul 2>&1 && set "LO_FOUND=1"

if "!LO_FOUND!"=="1" (
    echo [OK] LibreOffice engine is present and ready.
    goto SKIP_LIBREOFFICE_CHECK
)

echo [WARNING] LibreOffice is not installed in standard locations.
echo [INSTALL] Attempting automatic installation via winget...
where winget >nul 2>&1
if not errorlevel 1 (
    winget install -e --id TheDocumentFoundation.LibreOffice --silent --accept-package-agreements --accept-source-agreements
    echo [INFO] LibreOffice installer dispatched.
) else (
    echo [WARNING] winget not found. Please install LibreOffice from https://www.libreoffice.org/
)

:SKIP_LIBREOFFICE_CHECK

:: ----------------------------------------------------------------------------
:: 3.5 Check & Install Project Dependencies
:: ----------------------------------------------------------------------------
echo.
echo [CHECK] Checking and installing project library dependencies...

if not exist "%REQUIREMENTS_FILE%" goto SKIP_PIP_REQS
echo [INSTALL] Synchronizing Python packages from %REQUIREMENTS_FILE%...
python -m pip install -r "%REQUIREMENTS_FILE%" --quiet
if not errorlevel 1 (
    echo [OK] Python dependencies are up-to-date.
    goto SKIP_PIP_REQS
)

echo [WARNING] Retrying dependency installation with verbose output...
python -m pip install -r "%REQUIREMENTS_FILE%"
if errorlevel 1 (
    echo [ERROR] Encountered issues installing dependencies from %REQUIREMENTS_FILE%.
    pause
    goto MENU
)
echo [OK] Python dependencies installed successfully.

:SKIP_PIP_REQS

if not exist "%PACKAGE_JSON%" goto SKIP_NPM_REQS
if not "%ENABLE_NODE_CHECK%"=="1" goto SKIP_NPM_REQS
echo [INSTALL] Installing Node.js packages via npm...
call npm install
if errorlevel 1 (
    echo [ERROR] npm install encountered errors.
    pause
    goto MENU
)
echo [OK] Node.js packages installed.

:SKIP_NPM_REQS

:: ----------------------------------------------------------------------------
:: 3.6 Start the Project
:: ----------------------------------------------------------------------------
echo.
echo ============================================================================
echo   STARTING APPLICATION SERVICE
echo ============================================================================
echo.

:: Check if the project is already listening on the designated port
netstat -aon | findstr ":%PORT%" | findstr "LISTENING" >nul 2>&1
if errorlevel 1 goto LAUNCH_SERVICE

echo [INFO] !PROJECT_NAME! is ALREADY RUNNING on http://!HOST!:!PORT!
echo [INFO] Opening project interface in default browser...
start http://!HOST!:!PORT!
echo.
if not "%~1"=="" exit /b 0
echo Press any key to return to main menu...
pause >nul
goto MENU

:LAUNCH_SERVICE
echo [START] Executing startup command: %STARTUP_CMD%
echo [INFO] Launching background process and monitoring port !PORT!...

:: Launch process in background via PowerShell and save process ID (PID)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$proc = Start-Process python -ArgumentList '-m uvicorn udge.web.app:app --host %HOST% --port %PORT%' -PassThru -WindowStyle Hidden; [System.IO.File]::WriteAllText('%PID_FILE%', $proc.Id.ToString())"

:: Wait up to 5 seconds for service port binding
ping -n 5 127.0.0.1 >nul

:: Verify that the process is actively listening on the target port
netstat -aon | findstr ":%PORT%" | findstr "LISTENING" >nul 2>&1
if errorlevel 1 goto STARTUP_WARN

echo.
echo ============================================================================
echo [SUCCESS] !PROJECT_NAME! started successfully!
echo [SUCCESS] Web Interface: http://!HOST!:!PORT!
echo ============================================================================
echo.
echo [INFO] Opening browser...
start http://!HOST!:!PORT!
goto AFTER_STARTUP

:STARTUP_WARN
echo.
echo [WARNING] Service process was launched, but port !PORT! is still initializing.
echo [INFO] You can access http://!HOST!:!PORT! shortly.

:AFTER_STARTUP
echo.
echo Project is running in the background. Choose Option 2 from the menu to stop it.
if not "%~1"=="" exit /b 0
echo Press any key to return to main menu...
pause >nul
goto MENU


:: ----------------------------------------------------------------------------
:: SECTION 4: STOP SCRIPT (Graceful Process Termination & Port Cleanup)
:: ----------------------------------------------------------------------------
:STOP_PROJECT
cls
echo ============================================================================
echo   STOPPING PROJECT: !PROJECT_NAME!
echo ============================================================================
echo.

set "STOP_CONFIRMED=0"

:: Step 4.1: Terminate process tree using saved PID
if not exist "%PID_FILE%" goto CHECK_PORT_STOP
set /p SAVED_PID=<"%PID_FILE%"
if not defined SAVED_PID goto DELETE_PID_FILE
echo [STOP] Terminating process PID !SAVED_PID! recorded in %PID_FILE%...
taskkill /F /PID !SAVED_PID! /T >nul 2>&1
set "STOP_CONFIRMED=1"
echo [OK] Process tree for PID !SAVED_PID! terminated.

:DELETE_PID_FILE
del /f /q "%PID_FILE%" >nul 2>&1

:CHECK_PORT_STOP
:: Step 4.2: Ensure any lingering process on the port is stopped
for /f "tokens=5" %%p in ('netstat -aon ^| findstr ":%PORT%" ^| findstr "LISTENING"') do (
    echo [STOP] Found lingering process on port !PORT! with PID %%p. Terminating...
    taskkill /F /PID %%p /T >nul 2>&1
    set "STOP_CONFIRMED=1"
)

:: Step 4.3: Confirmation message
echo.
if "!STOP_CONFIRMED!"=="1" goto STOP_CONFIRMED_MSG
echo [INFO] No running instance of !PROJECT_NAME! was found on port !PORT!.
goto FINISH_STOP

:STOP_CONFIRMED_MSG
echo ============================================================================
echo [CONFIRMATION] !PROJECT_NAME! has been stopped successfully.
echo [CONFIRMATION] Network port !PORT! has been released.
echo ============================================================================

:FINISH_STOP
echo.
if not "%~1"=="" exit /b 0
echo Press any key to return to main menu...
pause >nul
goto MENU


:: ----------------------------------------------------------------------------
:: SECTION 5: EXIT SCRIPT
:: ----------------------------------------------------------------------------
:EXIT_SCRIPT
echo.
echo ============================================================================
echo   Exiting !PROJECT_NAME! Manager. Goodbye!
echo ============================================================================
ping -n 2 127.0.0.1 >nul
exit /b 0

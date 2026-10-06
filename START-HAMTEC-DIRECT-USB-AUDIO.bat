@echo off
setlocal
cd /d "%~dp0"
title HamTec SDR Direct USB - V6 Continuous USB
echo Close SDRsharp, rtl_test, rtl_tcp and other SDR applications first.
if not exist "rtlsdr.dll" if not exist "RTL\x64\rtlsdr.dll" goto missingdll
if exist ".venv\Scripts\python.exe" goto install
py -3 -c "import sys,struct; assert sys.version_info >= (3,10) and struct.calcsize('P')==8" >nul 2>&1
if not errorlevel 1 goto usepy
python -c "import sys,struct; assert sys.version_info >= (3,10) and struct.calcsize('P')==8" >nul 2>&1
if errorlevel 1 goto missingpython
python -m venv .venv
if errorlevel 1 goto failed
goto install
:usepy
py -3 -m venv .venv
if errorlevel 1 goto failed
:install
if exist ".venv\audio-v6-ready" goto run
echo Installing audio receiver dependencies. First run requires internet access.
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo ready>".venv\audio-v6-ready"
:run
".venv\Scripts\python.exe" hamtec_usb_audio.py
goto done
:missingdll
echo Copy ALL official RTL-SDR Blog V4 x64 release DLLs into RTL\x64.
echo Then run INSTALL-RTL-V4-FILES.bat and this launcher again.
goto done
:missingpython
echo Install Python 3.10 or newer, 64-bit, with the Python launcher or PATH option.
goto done
:failed
echo Setup failed. Read the error above.
:done
pause
endlocal

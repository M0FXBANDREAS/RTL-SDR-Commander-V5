@echo off
cd /d "%~dp0"
if exist rtlsdr.dll (echo Bundled RTL V4 DLLs are already in place.&pause&exit /b 0)
if not exist "RTL\x64\rtlsdr.dll" (echo rtlsdr.dll missing. Re-extract the full V5 ZIP.&pause&exit /b 1)
copy /Y "RTL\x64\*.dll" "." >nul
echo RTL-SDR DLLs installed.
pause

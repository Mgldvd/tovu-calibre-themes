@echo off
rem Tovu Calibre Themes launcher for Windows. Double-click it, or run: install-windows.bat
setlocal EnableExtensions
set "TOVU_DIR=%~dp0"

rem Find calibre-debug.exe: an explicit CALIBRE_DEBUG, the PATH, then the default install folders.
if defined CALIBRE_DEBUG if not exist "%CALIBRE_DEBUG%" set "CALIBRE_DEBUG="
if not defined CALIBRE_DEBUG for %%I in (calibre-debug.exe) do if not "%%~$PATH:I"=="" set "CALIBRE_DEBUG=%%~$PATH:I"
if not defined CALIBRE_DEBUG if exist "%ProgramFiles%\Calibre2\calibre-debug.exe" set "CALIBRE_DEBUG=%ProgramFiles%\Calibre2\calibre-debug.exe"
if not defined CALIBRE_DEBUG if exist "%ProgramFiles(x86)%\Calibre2\calibre-debug.exe" set "CALIBRE_DEBUG=%ProgramFiles(x86)%\Calibre2\calibre-debug.exe"
if not defined CALIBRE_DEBUG (
    echo Calibre was not found. Install it from https://calibre-ebook.com/download and run this file again.
    pause
    exit /b 1
)

rem Configure the profile before calibre-debug imports Calibre's constants.
rem cmd splits --config-dir=PATH into two arguments, so both forms land here.
:parse
if "%~1"=="" goto run
if /i "%~1"=="--config-dir" set "CALIBRE_CONFIG_DIRECTORY=%~2"
shift
goto parse

:run
"%CALIBRE_DEBUG%" -e "%TOVU_DIR%installer.py" -- %*
set "TOVU_EXIT=%ERRORLEVEL%"
if not "%TOVU_EXIT%"=="0" pause
exit /b %TOVU_EXIT%

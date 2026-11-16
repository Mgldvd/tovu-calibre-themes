@echo off
rem Restores the icon theme you had before installing Tovu Calibre Themes (Windows).
call "%~dp0install-windows.bat" --uninstall %*
exit /b %ERRORLEVEL%

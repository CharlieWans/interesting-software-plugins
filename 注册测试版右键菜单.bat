@echo off
setlocal
pushd "%~dp0"

title PacMan Delete - Register Current Version
echo.
echo ================================================
echo   PacMan Delete - Register Current Version
echo ================================================
echo.
echo [1/2] Checking the project test environment...
if not exist ".venv\Scripts\python.exe" goto :missing_python

echo [2/2] Registering the desktop context-menu command...
".venv\Scripts\python.exe" "scripts\install_context_menu.py"
if errorlevel 1 (
  echo.
  echo FAILED: The context menu was not registered.
  echo Please take a screenshot of this window and send it to me.
) else (
  echo.
  echo SUCCESS: The current version is now registered.
  echo Right-click a desktop file, choose "Show more options",
  echo then choose "吃豆人删除" to test it.
)
echo.
pause
endlocal
exit /b

:missing_python
echo.
echo FAILED: .venv\Scripts\python.exe was not found.
echo Please take a screenshot of this window and send it to me.
echo.
pause
endlocal

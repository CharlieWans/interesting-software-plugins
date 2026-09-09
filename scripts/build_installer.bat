@echo off
setlocal
chcp 65001 >nul
pushd "%~dp0.."
if errorlevel 1 (
  echo [错误] 无法进入项目目录
  pause
  exit /b 1
)

echo ============================================================
echo  [步骤 1/2] 运行 build.bat 打包绿色版 ...
echo ============================================================
call scripts\build.bat
if errorlevel 1 (
  echo [错误] build.bat 打包失败
  pause
  exit /b 1
)

echo.
echo ============================================================
echo  [步骤 2/2] 用 Inno Setup 编译安装包 ...
echo ============================================================

set "ISCC="
for /f "delims=" %%i in ('where ISCC 2^>nul') do set "ISCC=%%i"
if not defined ISCC (
    if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
    if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
    if exist "%ProgramFiles(x86)%\Inno Setup 5\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 5\ISCC.exe"
    if exist "%ProgramFiles%\Inno Setup 5\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 5\ISCC.exe"
)

if not defined ISCC (
    echo.
    echo [错误] 未找到 Inno Setup 编译器 (ISCC.exe)
    echo 请先安装 Inno Setup 6: https://jrsoftware.org/isinfo.php
    echo 或者手动: 右键 scripts\installer.iss -^> Compile
    pause
    exit /b 1
)

echo 使用 ISCC: %ISCC%
"%ISCC%" /O"scripts\Output" "scripts\installer.iss"
if errorlevel 1 (
  echo [错误] 安装包编译失败
  pause
  exit /b 1
)

echo.
echo ============================================================
echo  全部完成!
echo  安装包: scripts\Output\吃豆人删除安装程序.exe
echo  绿色版: dist\吃豆人删除\
echo ============================================================
pause
endlocal

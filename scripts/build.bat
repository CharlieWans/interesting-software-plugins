@echo off
setlocal
chcp 65001 >nul
pushd "%~dp0.."
if errorlevel 1 (
  echo [错误] 无法进入项目目录, 请确认脚本所在位置
  pause
  exit /b 1
)

echo.
set "PYTHON=.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
  echo [错误] 未找到项目构建环境: %PYTHON%
  echo 请先在项目根目录创建 .venv 并安装 requirements.txt 与 pyinstaller
  pause
  exit /b 1
)

echo [1/4] 使用项目构建环境 ...
"%PYTHON%" -m PyInstaller --version
if errorlevel 1 (
  echo [错误] PyInstaller 不可用
  pause
  exit /b 1
)

echo [2/4] 清理旧打包产物 ...
if exist build rmdir /s /q build
if exist "dist\吃豆人删除" rmdir /s /q "dist\吃豆人删除"
if exist "dist\PacManDelete" rmdir /s /q "dist\PacManDelete"
if exist PacManDelete.spec del /q PacManDelete.spec

echo [3/4] PyInstaller 打包 (onedir) ...
"%PYTHON%" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onedir ^
  --windowed ^
  --name PacManDelete ^
  --icon "assets\icon.ico" ^
  --hidden-import send2trash ^
  --collect-submodules pywinauto ^
  --collect-all comtypes ^
  --distpath dist ^
  --workpath build ^
  "src\dragon_delete.py"
if errorlevel 1 (
  echo [错误] PyInstaller 打包失败, 请把上方错误信息发给我
  pause
  exit /b 1
)

echo [4/4] 复制素材, 重命名应用目录 ...
if not exist "dist\吃豆人删除" mkdir "dist\吃豆人删除"
xcopy /e /i /y "dist\PacManDelete" "dist\吃豆人删除" >nul
rmdir /s /q "dist\PacManDelete"
xcopy /e /i /y assets "dist\吃豆人删除\assets" >nul

echo.
echo ============================================================
echo  打包完成!
echo  应用目录: dist\吃豆人删除\
echo  主程序  : dist\吃豆人删除\PacManDelete.exe
echo ============================================================
pause
endlocal

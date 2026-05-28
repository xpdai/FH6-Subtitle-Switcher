@echo off
REM Build FH6 Subtitle Switcher into a single .exe
chcp 65001 >nul
setlocal
cd /d "%~dp0"

where pyinstaller >nul 2>nul
if errorlevel 1 (
    echo [安裝] pyinstaller 尚未安裝，先安裝它...
    python -m pip install --upgrade pyinstaller
    if errorlevel 1 (
        echo [錯誤] 安裝 pyinstaller 失敗。請先確認 Python 與 pip 都可用。
        pause
        exit /b 1
    )
)

echo.
echo === 開始打包 ===
echo.

pyinstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name "FH6_Subtitle_Switcher" ^
    --icon "icon.ico" ^
    --add-data "icon.ico;." ^
    --version-file "version_info.txt" ^
    fh6_switcher.py

if errorlevel 1 (
    echo.
    echo [錯誤] 打包失敗。
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  完成！輸出檔案：
echo  %~dp0dist\FH6_Subtitle_Switcher.exe
echo ============================================================
echo.
pause

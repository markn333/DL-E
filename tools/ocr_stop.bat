@echo off
REM DL-E OCR 停止: ocr_all.py を実行している python.exe を安全に終了
REM コマンドライン文字列に "ocr_all.py" を含む python.exe のみを対象にする
setlocal

set "TARGET=ocr_all.py"

echo Searching for python processes running %TARGET% ...
for /f "tokens=*" %%P in ('powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -match 'ocr_all\.py' } | ForEach-Object { $_.ProcessId }"') do (
    echo Killing PID %%P
    taskkill /PID %%P /T 1>nul
    if errorlevel 1 (
        echo   force-killing PID %%P
        taskkill /F /PID %%P /T
    )
)

echo Done. Re-run ocr_run.bat to resume from the last completed page.
endlocal

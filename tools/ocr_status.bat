@echo off
REM DL-E OCR 進捗確認
cd /d "%~dp0\.."
python tools\ocr_all.py --stats

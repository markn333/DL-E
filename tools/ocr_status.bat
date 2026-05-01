@echo off
REM DL-G OCR 進捗確認
cd /d "%~dp0\.."
python tools\ocr_all.py --stats

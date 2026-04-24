@echo off
REM DL-E PDF 全ページ OCR バッチ起動
cd /d "%~dp0\.."
python tools\ocr_all.py %*

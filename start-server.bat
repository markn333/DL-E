@echo off
REM DL-E ローカル動作確認用 HTTP サーバ
REM Service Worker を有効にするため、ファイル直接開きではなく HTTP 経由で開く必要あり
cd /d "%~dp0"
echo Starting local server at http://localhost:8001/
echo Press Ctrl+C to stop.
python -m http.server 8001

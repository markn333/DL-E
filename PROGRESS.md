# DL-E 進捗記録

## 現在のステータス

Mothership にインポート完了（雛形コピーのみ・DL-E 化未着手）。

## 実装済み機能（雛形流用）

- [x] PWA 基本構成（index.html / manifest.json / sw.js）
- [x] 出題エンジン（quiz.js: ランダム/苦手/順番モード、カテゴリフィルタ、複数選択対応）
- [x] LocalStorage 永続化（履歴・進捗・誤答統計）
- [x] 5画面構成（home / quiz / result / history / weakness）
- [x] Chart.js 連携（履歴推移グラフ・弱点分析グラフ）
- [x] 中断・再開機能
- [x] 不正解問題のみ再挑戦
- [x] カテゴリ別正解率表示

> ※ 上記はすべて OSSDB プロジェクトからの流用。タイトル等は OSS-DB のままで DL-E 表記ではない。

## 未実装

- [ ] PDF → Markdown 変換
- [ ] Markdown → questions.json 変換
- [ ] DL-E 用問題データの差し替え
- [ ] アプリ内のテキスト/メタデータの DL-E 化（title, manifest, CACHE_NAME, LocalStorage キー）
- [ ] アイコンの差し替え（任意）
- [ ] iOS / Android 実機検証
- [ ] GitHub 公開（リポジトリ作成 + Pages 設定）

## 作業ログ

### 2026-04-24
- 方針確定（PDF を Git 対象外、問題本文は公開リポジトリに含める、PDF→MD は pdf2md ベース）
- `.gitignore` 作成（PDF / tessdata / build 除外）
- PDF 構造調査: 全 408 ページが画像のみのスキャン PDF（テキストレイヤーなし）と判明
  → `pdf2md`（pymupdf4llm）単独では抽出不可、OCR 必須
- Tesseract OCR 5.5.0 導入（winget）+ pytesseract 0.3.13 導入
- `tessdata_best/jpn.traineddata` を `tessdata/` に配置
- 試行 OCR（p100/p50/p30）で精度確認 → 約 95〜98% の認識率、後処理可能と判断
- 全ページ OCR バッチ `tools/ocr_all.py` 実装（CLAUDE.md ルール準拠の 4 機能）
  - 起動: `tools/ocr_run.bat`
  - 停止: `tools/ocr_stop.bat`（コマンドライン文字列で対象 python.exe を限定）
  - 再開: 出力済みページを自動スキップ（`--force` で強制再OCR）
  - 進捗: `tools/ocr_status.bat` / `python tools/ocr_all.py --stats`
- 5ページの試走で平均 3.3 秒/ページ → 全 408 ページで約 22 分の見込み
- 全件 OCR 実行中

### 2026-04-23
- Mothership にインポート
  - 既存 `REQUEST.md` を `imported/REQUEST.md` に退避
  - `REQUEST.md` / `PROJECT.md` / `SPEC.md` / `PLAN.md` / `PROGRESS.md` / `TODO.md` を生成
  - `reports/` / `bugs/` フォルダ作成
  - `CLAUDE.md`（憲章テンプレート）配置
- 既存ファイル群が OSSDB アプリの完全コピーであることを確認
  - `data/questions.json` は OSS-DB Silver 問題のまま
  - `index.html` `<title>` / `manifest.json` / `sw.js` の CACHE_NAME / `storage.js` の KEYS いずれも `ossdb` 名のまま
- PDF（150MB）はプロジェクト直下に配置済み

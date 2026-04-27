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

### 2026-04-27
- 全 409 問の自動 QA チェック (`tools/qa_check.py`) を実装・実行
  - 章別 id 連番 / answer/choices 整合 / 文末・括弧・OCR 残検査
  - 章別 id 連番は全章で抜け・重複なし
  - 要レビュー 166 問（解答ペアリング失敗 103 + その他 OCR 起因）
- OCR 後処理を更に拡充（選へ→選べ、句読点連続、末尾 `|` `__` 除去、固有名詞辞書追加）
- 手動レビュー支援 CSV ツール (`tools/export_review.py` / `import_review.py`)
- **GitHub 公開**:
  - リポジトリ: <https://github.com/markn333/DL-E>
  - 公開 URL: <https://markn333.github.io/DL-E/>

### 2026-04-25
- アプリを DL-E 用にリブランド（title / manifest / CACHE_NAME / LocalStorage キー）
- ローカル動作確認用 `start-server.bat`（port 8001）
- OCR 由来の頭ゴミ・解答ポインタゴミを徹底除去
  - 「[lio3.」「[Ll140.」「[し L| 4.」「[っ P274 |」など各種化けに対応
  - final_clean に loop 適用 + explanation 用ポインタ除去パターン追加

### 2026-04-24
- 方針確定（PDF を Git 対象外、問題本文は公開リポジトリに含める、PDF→MD は pdf2md ベース）
- `.gitignore` 作成（PDF / tessdata / build 除外）
- PDF 構造調査: 全 408 ページが画像のみのスキャン PDF（テキストレイヤーなし）と判明
  → `pdf2md`（pymupdf4llm）単独では抽出不可、OCR 必須
- Tesseract OCR 5.5.0 導入（winget）+ pytesseract 0.3.13 導入
- `tessdata_best/jpn.traineddata` を `tessdata/` に配置
- 試行 OCR（p100/p50/p30）で精度確認 → 約 95〜98% の認識率、後処理可能と判断
- 全ページ OCR バッチ `tools/ocr_all.py` 実装（CLAUDE.md ルール準拠の 4 機能）
  - 起動 / 停止 / 再開 / 進捗確認
- 全 408 ページ OCR 完走（1407 秒 = 23.5 分、3 ページは白紙の章扉裏）
- **書籍構造の解明**: 章ごとに「問題編」と「解答編」が分離。第3章以降の解答ページは「N. <正答>」が明示されている。
- クイズ抽出パーサ `tools/parse_quiz.py` 実装
  - 全 11 章のページ範囲を `CHAPTERS` テーブルで管理
  - 問題分割: 解答ポインタ（ゆ/中/呂/必/→ Pxx）を区切りに使用
  - 解答分割: 番号付き（第3章以降）/ マーカー分割（第1, 2章）の 2 モード
  - 「最も不適切なものを選べ」型は `REVIEW_NEGATIVE` フラグで識別
  - 解答ペアリング失敗は `REVIEW_NO_MATCH` フラグで識別
- 統合スクリプト `tools/merge_quiz.py` 実装
- **全 11 章から 404 問を抽出**
  - 自動抽出 OK: 約 242 問（60%）
  - 要レビュー: 162 問（NEGATIVE 83 + NO_MATCH 103、重複あり）
- `build/review_summary.md` で章ごとの統計を出力
- 初回 git commit（b974f3d）

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

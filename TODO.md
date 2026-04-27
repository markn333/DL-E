# DL-E タスク一覧

最終更新: 2026-04-24

---

## ✅ 確定済み方針（2026-04-24）

- PDF は Git 管理対象外（`.gitignore` 設定済み）
- 問題本文を公開リポジトリに含めて OK
- PDF→Markdown は `projects/pdf2md`（pymupdf4llm）を使用

---

## Phase 1: 出題データ整備 🚧

### 1-1. PDF → テキスト（OCR）
- [x] PDF 構造調査 → 全ページ画像のみ（pymupdf4llm 単独では不可）と判明
- [x] OCR エンジン選定 → Tesseract 5.5.0（jpn best モデル）採用
- [x] Tesseract / pytesseract / jpn.traineddata 環境構築
- [x] 試行 OCR（p100 / p50 / p30）で精度確認 → 約 95〜98%、実用 OK
- [x] OCR バッチ `tools/ocr_all.py` 実装（起動/停止/再開/進捗 4 機能）
- [ ] 全 408 ページ OCR 実行（実行中、約 22 分見込み）
- [ ] 後処理ルール策定（過剰スペース除去、`Al/A!→AI` などの誤認識補正）

### 1-2. テキスト → questions.json
- [x] OCR テキストの構造解析（問題セクション / 解答セクションの判定）
- [x] パーサ実装（章/問題/選択肢/正答/解説 → JSON）
- [x] `multiAnswer` 自動判定
- [x] `category` マッピング（章タイトル）
- [x] 番号付き解答 / マーカー分割の 2 モード対応
- [x] 「不適切型」の識別（REVIEW_NEGATIVE フラグ）
- [x] 解答ペアリング失敗の識別（REVIEW_NO_MATCH フラグ）
- [x] 全 11 章で動作確認 → 404 問抽出
- [ ] **手動レビュー: 162 問** （NEGATIVE 83 + NO_MATCH 103）
  - PDF 書籍を見ながら正答 + 解説を補正
  - `build/questions_review.json` で対象一覧

### 1-2. Markdown → questions.json
- [ ] パーサ実装（章/問題/選択肢/正答/解説 → JSON）
- [ ] `multiAnswer` 自動判定
- [ ] `category` マッピング（章タイトル）
- [ ] バリデーション（id 一意・answer ⊆ choices・空フィールド検出）
- [ ] サンプル数十問で動作確認

### 1-3. 全件変換 & 手動補正
- [ ] 全章変換実施
- [ ] サンプリング目視レビュー
- [ ] 必要に応じ手動補正

---

## Phase 2: アプリの DL-E 化 ✅

- [x] `index.html`: title / h1 / subtitle / theme-color を DL-E 用に変更
- [x] `manifest.json`: name / short_name / description / theme_color
- [x] `sw.js`: `CACHE_NAME` を `dle-quiz-v1` に変更
- [x] `js/storage.js`: `KEYS` を `dle_*` に変更
- [x] `start-server.bat` ローカル動作確認（port 8001）
- [ ] `icons/*.png`: 任意で差し替え（DL-E ロゴ）

---

## Phase 3: 検証 ⬜

- [ ] 中断 / 再開
- [ ] 履歴グラフ
- [ ] 弱点分析
- [ ] カテゴリフィルタ
- [ ] 苦手問題モード
- [ ] iOS Safari でホーム画面追加 → PWA 動作
- [ ] Android Chrome で同上

---

## Phase 4: GitHub 公開 ✅

- [x] `.gitignore` 作成（PDF / tessdata / build 除外）
- [x] GitHub リポジトリ作成 & 初回 push: <https://github.com/markn333/DL-E>
- [x] GitHub Pages 設定: <https://markn333.github.io/DL-E/>
- [ ] 公開 URL から PWA インストール最終確認

---

## Phase 5: 手動レビュー（QA 結果より）

### 自動 QA 検査結果（2026-04-27）
- 全 409 問中 **要レビュー 166 問**（章別 id 連番は OK）
- うち 103 問は解答ペアリング失敗（OCR 取りこぼし）
- レビュー対象 → `build/review.csv` に出力済み

### レビュー手順
1. `python tools/export_review.py` → `build/review.csv` を出力
2. CSV を Excel/VS Code 等で編集（PDF を見ながら正答・解説を補正）
3. `python tools/import_review.py` → `data/questions.json` に反映（バックアップ自動作成）
4. `python tools/qa_check.py` で再検証 → コミット & push

### レビュー優先度
- 高: NO_MATCH（解答が空、103 件）
- 中: 選択肢ラベル欠損（answer ⊆ choices にない、8 件）
- 中: 選択肢長アンバランス（17 件）
- 低: 助詞連続（38 件、大半は元 OCR どおり）

---

## Phase 5（任意）: 拡張アイデア

- [ ] タイマー機能
- [ ] 問題ブックマーク
- [ ] 解説への自分メモ
- [ ] スペースド・リピティション
- [ ] ダークモード

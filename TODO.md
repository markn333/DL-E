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
- [ ] OCR テキストの構造解析（問題セクション / 解答セクションの判定）
- [ ] パーサ実装（章/問題/選択肢/正答/解説 → JSON）
- [ ] `multiAnswer` 自動判定
- [ ] `category` マッピング（章タイトル）
- [ ] バリデーション（id 一意・answer ⊆ choices・空フィールド検出）
- [ ] サンプル数十問で動作確認

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

## Phase 2: アプリの DL-E 化 ⬜

- [ ] `index.html`: title / h1 / subtitle を DL-E 用に変更
- [ ] `manifest.json`: name / short_name / description / theme_color
- [ ] `sw.js`: `CACHE_NAME` を `dle-quiz-v1` に変更
- [ ] `js/storage.js`: `KEYS` を `dle_*` に変更
- [ ] `icons/*.png`: 任意で差し替え
- [ ] ローカル動作確認（`python -m http.server` 等）

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

## Phase 4: GitHub 公開 ⬜

- [ ] `.gitignore` 作成（PDF 除外）
- [ ] 著作権面の最終整理
- [ ] GitHub リポジトリ作成 & 初回 push
- [ ] GitHub Pages 設定
- [ ] 公開 URL から PWA インストール最終確認

---

## Phase 5（任意）: 拡張アイデア

- [ ] タイマー機能
- [ ] 問題ブックマーク
- [ ] 解説への自分メモ
- [ ] スペースド・リピティション
- [ ] ダークモード

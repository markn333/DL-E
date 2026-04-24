# DL-E 実行計画

ステータス: **承認済み**
承認日: 2026-04-24
作成日: 2026-04-23（インポート時）

---

## 確定済みの方針

- PDF は Git 管理対象外（`.gitignore` に `*.pdf` 追加済み）
- 問題本文は公開リポジトリに含めて良い（著作権面は OK）
- PDF→Markdown は **`projects/pdf2md`（pymupdf4llm ベース）** を使用

---

## 既存実装状況

- OSSDB 模擬試験アプリの一式（PWA構成）が雛形としてコピー済み
- DL-E 用の作り込みは未着手
  - タイトル・テーマカラー・キャッシュ名・LocalStorage キー名すべて OSS-DB のまま
  - `data/questions.json` は OSS-DB Silver の問題のまま
- 出題ソース PDF（150MB）はプロジェクト直下に配置済み

---

## Phase 1: 出題データ整備（最重要・所要時間が読みにくい）

### Step 1-1: PDF → Markdown 変換 🚧 着手中
- [x] PDF パーサ選定 → `projects/pdf2md`（pymupdf4llm 0.3.4）を使用
- [ ] 試行変換（冒頭 10 ページ程度）で出力構造を確認
- [ ] PDF 全体を Markdown 化（章/問題/選択肢/正答/解説の構造を保つ）
- [ ] 図表・画像問題の扱いを決定（除外 or 画像化して埋め込み）

### Step 1-2: Markdown → questions.json 変換 ⬜ 未着手
- [ ] MD パーサ実装（章/問題/選択肢/正答/解説 → JSON スキーマへ）
- [ ] `multiAnswer` 判定（複数選択かどうかを問題文から推定）
- [ ] `category` マッピング（章タイトルを category に）
- [ ] バリデーション（id 一意・answer が choices の範囲内・空フィールド検出）
- [ ] サンプル数十問で動作確認

### Step 1-3: 全件変換 & レビュー ⬜ 未着手
- [ ] 全章の変換実施
- [ ] 目視レビュー（ランダムサンプル + 章先頭/末尾）
- [ ] 必要に応じて手動補正

---

## Phase 2: アプリの DL-E 化（軽作業）

- [ ] `index.html` のタイトル/見出し/サブタイトルを DL-E 用に変更
- [ ] `manifest.json` の name/short_name/description/theme_color を変更
- [ ] `sw.js` の `CACHE_NAME` を `dle-quiz-v1` 等に変更
- [ ] `js/storage.js` の `KEYS` を `dle_*` に変更
- [ ] `icons/*.png` を DL-E 用に差し替え（任意・後回し可）
- [ ] 動作確認（ローカルサーバ → スマホ実機 PWA インストール）

---

## Phase 3: 学習機能の検証 & 微調整

- [ ] 中断/再開の動作確認
- [ ] 履歴グラフの表示確認
- [ ] 弱点分析の表示確認
- [ ] カテゴリフィルタの動作確認
- [ ] 苦手問題モードの動作確認
- [ ] iOS Safari / Android Chrome での動作確認

---

## Phase 4: GitHub 公開

- [ ] `.gitignore` 作成（PDF・node_modules 等を除外）
- [ ] 著作権面の整理（問題本文を公開リポジトリに含めて良いか判断）
  - NG なら問題データは別管理（環境変数 / 別 private repo / ローカル取り込み）
- [ ] GitHub リポジトリ作成 & push
- [ ] GitHub Pages 設定 → 公開 URL 確認
- [ ] PWA インストールの最終確認（iOS / Android）

---

## Phase 5（任意）: 機能拡張アイデア

- [ ] タイマー機能（試験本番想定の制限時間）
- [ ] 問題ブックマーク
- [ ] 解説への自分メモ追加
- [ ] スペースド・リピティション（忘却曲線ベースの復習）
- [ ] 章末まとめ・チートシート
- [ ] ダークモード

---

## 次のアクション

**Phase 1-1: pdf2md でお試し変換（冒頭 10 ページ）→ 出力構造を確認 → 全件変換**

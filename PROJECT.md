# DL-G - ディープラーニングG検定 模擬試験アプリ

## プロジェクト情報

| 項目 | 値 |
|------|-----|
| プロジェクト名 | DL-G |
| 種別 | Webアプリケーション（PWA） |
| インポート日 | 2026-04-23 |
| ステータス | インポート済み（雛形のみ・DL-E向け作り込み未着手） |
| 現在フェーズ | Phase 0: 雛形コピー完了 / Phase 1: 問題データ整備（未着手） |

## 概要

書籍『徹底攻略 ディープラーニングG検定ジェネラリスト問題集 第3版』を出題ソースとした、
ディープラーニングG検定ジェネラリスト試験対策の模擬試験 PWA。
OSSDB 模擬試験アプリ（`projects/OSSDB`）の実装を雛形として流用し、DL-G 用に書き換える。

## 技術スタック

- HTML5 / CSS3 / Vanilla JavaScript
- PWA（manifest.json / Service Worker）
- LocalStorage（履歴・進捗・誤答統計）
- Chart.js（履歴・弱点分析グラフ）
- 出題ソース: 書籍 PDF（150MB） → Markdown / questions.json に変換

## ファイル構成

```
projects/DL-G/
├── index.html                  # UI（※現状は OSS-DB Silver のまま、要書き換え）
├── manifest.json               # PWA マニフェスト（※OSS-DB のまま）
├── sw.js                       # Service Worker（※キャッシュ名 ossdb-quiz-v1 のまま）
├── css/
│   └── style.css               # スタイル
├── js/
│   ├── app.js                  # メインロジック・画面遷移
│   ├── quiz.js                 # 出題エンジン
│   ├── storage.js              # LocalStorage ラッパ（※キー名 ossdb_* のまま）
│   ├── chart-helper.js         # Chart.js 連携
│   └── chart.min.js            # Chart.js 本体
├── data/
│   └── questions.json          # 問題データ（※現状は OSS-DB Silver の問題、要差し替え）
├── icons/
│   ├── icon-192.png
│   └── icon-512.png
├── 徹底攻略ディープラーニングG検定ジェネラリスト問題集 第3版 徹底攻略シリーズ.pdf
├── imported/
│   └── REQUEST.md              # 元の依頼文
├── REQUEST.md                  # 整理後の要件
├── PROJECT.md                  # 本ファイル
├── SPEC.md                     # 技術仕様
├── PLAN.md                     # 実行計画（要確認）
├── PROGRESS.md                 # 進捗記録
├── TODO.md                     # タスク一覧
├── CLAUDE.md                   # 開発憲章
├── reports/                    # 各種レポート
└── bugs/                       # バグ記録
```

## 関連ドキュメント

| ドキュメント | 説明 |
|-------------|------|
| imported/REQUEST.md | 当初の依頼（原文） |
| REQUEST.md | 整理した要件 |
| SPEC.md | データ仕様・アプリ構造 |
| PLAN.md | 実行計画（Phase 1〜） |
| PROGRESS.md | 進捗記録 |
| TODO.md | タスク一覧 |
| projects/OSSDB | リファレンス実装（流用元） |

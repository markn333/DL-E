# DL-E 技術仕様

## 1. アプリ全体構成

PWA 構成。すべて静的ファイルで構成され、サーバ不要（GitHub Pages 等にデプロイ可能）。

```
[Browser]
  ├─ index.html
  │   └─ <script> chart.min.js → storage.js → quiz.js → chart-helper.js → app.js
  ├─ Service Worker (sw.js)  ← オフラインキャッシュ
  └─ LocalStorage             ← 履歴・進捗・誤答統計
        ↑
        fetch('data/questions.json')
```

## 2. 画面構成（screen-* div）

| 画面 ID | 用途 |
|---------|------|
| `screen-home` | ホーム（出題条件選択・再開・履歴・弱点分析へのナビ） |
| `screen-quiz` | 試験画面（進捗バー・選択肢・解答ボタン・解説） |
| `screen-result` | 結果画面（スコアリング・カテゴリ別正解率・不正解一覧・再挑戦） |
| `screen-history` | 学習履歴（正解率推移グラフ・統計サマリ・過去結果） |
| `screen-weakness` | 弱点分析（カテゴリ別正解率・よく間違える問題 TOP10） |

## 3. データ仕様（questions.json）

```jsonc
[
  {
    "id": 1,
    "chapter": 1,                 // 章番号
    "category": "一般知識",       // カテゴリ（章タイトル等）
    "question": "...",
    "choices": ["A. ...", "B. ...", ...],   // 接頭辞 "X. " 必須
    "answer": ["B", "D"],         // 正答ラベル配列（複数選択もあり）
    "explanation": "...",
    "multiAnswer": true            // 複数選択かどうか
  }
]
```

- `id` は数値（一意）
- `category` の集合がカテゴリフィルタの選択肢になる
- `multiAnswer === true` の場合、`answer.length` 個まで選択可能

## 4. 出題エンジン仕様（js/quiz.js）

| 関数 | 役割 |
|------|------|
| `loadQuestions()` | `data/questions.json` を fetch & 保持 |
| `getCategories()` | カテゴリ一覧 |
| `generateQuiz(count, categories, mode)` | カテゴリで pool 絞り込み → mode 別に並べる → count 件返す |
| `getQuestionById(id)` | id 検索 |
| `checkAnswer(qId, selected)` | 選択肢配列を sort して厳密一致判定 |

出題モード:
- `random` ... pool をシャッフルして count 件
- `weak` ... `Storage.getWeakQuestionIds()` で誤答率高い問題に絞る
- `sequential` ... 先頭から順番に count 件

## 5. ストレージ仕様（js/storage.js）

LocalStorage キー（※流用元命名のため要リネーム）:

| キー | 内容 |
|------|------|
| `ossdb_history` | 受験結果履歴（最大 100 件） |
| `ossdb_progress` | 中断中試験のスナップショット |
| `ossdb_wrong_stats` | 問題ごとの解答回数・誤答回数 |

→ DL-E 用に `dle_*` 等へ rename 予定（既存ユーザーがいないので破壊的変更可）。

## 6. 画面遷移・操作（js/app.js）

- `App.state` に試験中の状態を保持（questionIds / currentIndex / answers / mode / startedAt）
- 解答ごとに `Storage.recordAnswer()` で誤答統計更新、`Storage.saveProgress()` で中断点保存
- 結果画面では `Storage.addHistory()` で履歴に追加

## 7. PWA / オフライン

- `sw.js` で `index.html` / CSS / JS / questions.json / manifest を install 時にキャッシュ
- fetch ハンドラはキャッシュファースト + ネットワークフォールバック
- ナビゲーションリクエストは `index.html` にフォールバック
- ※キャッシュ名 `ossdb-quiz-v1` は DL-E 用に rename 予定

## 8. 依存ライブラリ

| ライブラリ | バージョン | 用途 |
|-----------|-----------|------|
| Chart.js | min 同梱 | 履歴・弱点分析グラフ |

## 9. 流用元との差分（DL-E 化に必要な変更）

| 対象 | 現状（OSS-DB Silver） | DL-E 化後 |
|------|---------------------|-----------|
| `index.html` `<title>` | OSS-DB Silver 模擬試験 | ディープラーニング G検定 模擬試験 |
| `index.html` h1/subtitle | OSS-DB Silver | DL-E（G検定） |
| `manifest.json` name/short_name/description/theme_color | OSS-DB | DL-E |
| `sw.js` CACHE_NAME | `ossdb-quiz-v1` | `dle-quiz-v1` |
| `storage.js` LocalStorage キー | `ossdb_*` | `dle_*` |
| `data/questions.json` | OSS-DB Silver の問題 | G検定問題（書籍から抽出） |
| `icons/*.png` | 既存 | DL-E 用に差し替え（任意） |

## 10. 出題データ生成パイプライン（要構築）

```
PDF (徹底攻略 G検定問題集 第3版)
   ↓ pdf2md / 手動補正
Markdown（章ごとに問題・選択肢・正答・解説）
   ↓ MD パーサ（要実装、Python or Node）
data/questions.json（上記 §3 のスキーマ）
```

- PDF は約 150MB、画像/図表を含む可能性があるため OCR・整形の手戻りを想定
- 章番号 → `chapter`、章タイトル → `category` にマッピング
- 解説は ChatGPT/Claude による要約・補強も視野

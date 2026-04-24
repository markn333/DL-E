"""build/ch01.json 〜 ch11.json を統合して questions.json を生成。

出力:
  data/questions.json          ... アプリ用（_flags 除去）
  build/questions_review.json  ... レビュー用（_flags 残し、要確認のみ抽出）
  build/review_summary.md      ... レビュー用サマリ
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
DATA = ROOT / "data"


def main() -> None:
    parts = sorted(BUILD.glob("ch*.json"))
    if not parts:
        raise SystemExit("build/ch*.json が見つかりません。先に parse_quiz.py --all を実行してください。")

    all_q: list[dict] = []
    for p in parts:
        all_q.extend(json.loads(p.read_text(encoding="utf-8")))

    # アプリ用（_flags 除去 + answer 空でも残す）
    app_data = []
    for q in all_q:
        clean = {k: v for k, v in q.items() if not k.startswith("_")}
        app_data.append(clean)

    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "questions.json").write_text(
        json.dumps(app_data, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )

    # レビュー用（_flags が空でないものだけ抽出）
    review = [q for q in all_q if q.get("_flags")]
    (BUILD / "questions_review.json").write_text(
        json.dumps(review, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # サマリ
    by_chapter: dict[int, dict[str, int]] = {}
    for q in all_q:
        ch = q["chapter"]
        slot = by_chapter.setdefault(ch, {"total": 0, "REVIEW_NEGATIVE": 0, "REVIEW_NO_ANSWER": 0, "REVIEW_NO_MATCH": 0})
        slot["total"] += 1
        for f in q.get("_flags", []):
            slot[f] = slot.get(f, 0) + 1

    lines = ["# DL-E questions レビューサマリ", ""]
    lines.append("| 章 | 問題数 | NEGATIVE | NO_ANSWER | NO_MATCH |")
    lines.append("|---|---:|---:|---:|---:|")
    tot = {"total": 0, "REVIEW_NEGATIVE": 0, "REVIEW_NO_ANSWER": 0, "REVIEW_NO_MATCH": 0}
    for ch in sorted(by_chapter):
        s = by_chapter[ch]
        lines.append(
            f"| {ch} | {s['total']} | {s.get('REVIEW_NEGATIVE', 0)} | "
            f"{s.get('REVIEW_NO_ANSWER', 0)} | {s.get('REVIEW_NO_MATCH', 0)} |"
        )
        for k in tot:
            tot[k] += s.get(k, 0)
    lines.append(f"| **合計** | **{tot['total']}** | **{tot['REVIEW_NEGATIVE']}** | "
                 f"**{tot['REVIEW_NO_ANSWER']}** | **{tot['REVIEW_NO_MATCH']}** |")
    lines.append("")
    lines.append("## フラグの意味")
    lines.append("- **REVIEW_NEGATIVE**: 「最も不適切なものを選べ」型。自動抽出した正答が誤りの選択肢を指している可能性があり、要確認。")
    lines.append("- **REVIEW_NO_ANSWER**: 解説テキストから正答ラベル（A〜D）を抽出できなかった。要手入力。")
    lines.append("- **REVIEW_NO_MATCH**: 対応する解答チャンクが見つからなかった（解答ページの OCR 取りこぼし）。要手入力。")
    (BUILD / "review_summary.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"wrote data/questions.json          ({len(app_data)} questions)")
    print(f"wrote build/questions_review.json  ({len(review)} entries)")
    print(f"wrote build/review_summary.md")


if __name__ == "__main__":
    main()

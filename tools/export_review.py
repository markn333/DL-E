"""手動レビュー対象（_flags 付き）を CSV にエクスポート。

CSV 編集後は import_review.py で data/questions.json に反映。
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "questions.json"
REVIEW_JSON = ROOT / "build" / "questions_review.json"
OUT_CSV = ROOT / "build" / "review.csv"

COLUMNS = [
    "id", "chapter", "category", "question",
    "choice_A", "choice_B", "choice_C", "choice_D",
    "answer", "multiAnswer", "explanation", "_flags",
]


def split_choice(choices: list[str], label: str) -> str:
    for c in choices:
        if c.startswith(f"{label}."):
            return c[len(label) + 1:].strip()
    return ""


def main() -> None:
    if not REVIEW_JSON.exists():
        raise SystemExit(f"{REVIEW_JSON} が見つかりません。先に merge_quiz.py を実行してください。")

    review = json.loads(REVIEW_JSON.read_text(encoding="utf-8"))
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for q in review:
            w.writerow({
                "id": q["id"],
                "chapter": q["chapter"],
                "category": q["category"],
                "question": q["question"],
                "choice_A": split_choice(q["choices"], "A"),
                "choice_B": split_choice(q["choices"], "B"),
                "choice_C": split_choice(q["choices"], "C"),
                "choice_D": split_choice(q["choices"], "D"),
                "answer": ",".join(q.get("answer", [])),
                "multiAnswer": "true" if q.get("multiAnswer") else "false",
                "explanation": q.get("explanation", ""),
                "_flags": ",".join(q.get("_flags", [])),
            })
    print(f"wrote {OUT_CSV}  ({len(review)} entries)")
    print("Excel/Numbers/VS Code で編集後、tools/import_review.py で取り込み")


if __name__ == "__main__":
    main()

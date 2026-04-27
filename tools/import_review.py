"""編集済み review.csv を data/questions.json に反映。

- バックアップ: data/questions.json.bak.<timestamp>
- 上書き対象は CSV に含まれる id のみ（その他はそのまま）
- answer は「C」または「B,D」形式
- multiAnswer は "true" / "false"
- choice_A〜D が空の列はその選択肢を削除（4 択 → 3 択にも対応）
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "questions.json"
DEFAULT_CSV = ROOT / "build" / "review.csv"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=str, default=str(DEFAULT_CSV), help="入力 CSV (default: build/review.csv)")
    parser.add_argument("--dry-run", action="store_true", help="書き込まず差分のみ表示")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"ERROR: {csv_path} が見つかりません", file=sys.stderr)
        return 2
    if not DATA.exists():
        print(f"ERROR: {DATA} が見つかりません", file=sys.stderr)
        return 2

    data = json.loads(DATA.read_text(encoding="utf-8"))
    by_id = {q["id"]: q for q in data}

    updates: dict[int, dict] = {}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                qid = int(row["id"])
            except (KeyError, ValueError):
                continue
            if qid not in by_id:
                print(f"  skip: id={qid} は data/questions.json に存在しません", file=sys.stderr)
                continue
            choices = []
            for label in ("A", "B", "C", "D"):
                body = row.get(f"choice_{label}", "").strip()
                if body:
                    choices.append(f"{label}. {body}")
            answer = [a.strip().upper() for a in row.get("answer", "").split(",") if a.strip()]
            multi = row.get("multiAnswer", "").strip().lower() == "true"
            updates[qid] = {
                "question": row.get("question", "").strip(),
                "choices": choices,
                "answer": answer,
                "multiAnswer": multi,
                "explanation": row.get("explanation", "").strip(),
            }

    # 差分カウント
    n_changed = 0
    for qid, upd in updates.items():
        cur = by_id[qid]
        for k, v in upd.items():
            if cur.get(k) != v:
                n_changed += 1
                break
    print(f"target rows in CSV : {len(updates)}")
    print(f"actually changed   : {n_changed}")

    if args.dry_run:
        print("(dry-run: 書き込みません)")
        return 0

    # バックアップ
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = DATA.with_suffix(DATA.suffix + f".bak.{ts}")
    shutil.copy(DATA, bak)
    print(f"backup: {bak}")

    # 反映
    for qid, upd in updates.items():
        q = by_id[qid]
        q.update(upd)
        # 解答が埋まったら _flags を整理（手動修正されたら REVIEW_NO_MATCH/NO_ANSWER は外す）
        if "_flags" in q:
            cleared = [f for f in q["_flags"]
                       if f not in {"REVIEW_NO_MATCH", "REVIEW_NO_ANSWER"}
                       or not (upd.get("answer") and upd.get("explanation"))]
            q["_flags"] = cleared

    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {DATA}  (updated {n_changed} questions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

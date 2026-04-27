"""data/questions.json の品質を自動チェック。

実施項目:
  A. 構造整合性
     A1. 各章の id 連番チェック（抜け / 重複）
     A2. answer リストの妥当性（A〜D 範囲、選択肢に存在）
     A3. multiAnswer フラグと answer 数の整合
     A4. 必須フィールドの欠損
  B. テキスト品質（OCR 由来の異常検出）
     B1. 問題文・選択肢・解説の長さ異常
     B2. 文末の不自然さ
     B3. 助詞連続 / OCR ノイズ語
     B4. 選択肢の長さアンバランス
     B5. 開閉記号の不一致

出力:
  build/qa_report.md  （Markdown サマリ）
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "questions.json"
REPORT = ROOT / "build" / "qa_report.md"

# ---------- ヒューリスティクス ----------

# 助詞の不自然な連続（明らかな OCR エラー）
NOISE_PATTERNS = [
    (re.compile(r"をを"), "助詞連続: をを"),
    (re.compile(r"がが"), "助詞連続: がが"),
    (re.compile(r"のの"), "助詞連続: のの"),
    (re.compile(r"にに"), "助詞連続: にに"),
    (re.compile(r"でで"), "助詞連続: でで"),
    (re.compile(r"はは"), "助詞連続: はは"),
    (re.compile(r"ととと"), "OCRノイズ: ととと"),
    (re.compile(r"とと"), "助詞連続: とと"),
    # 既知の OCR ノイズ語（残存チェック）
    (re.compile(r"ぐス"), "OCR残: ぐス"),
    (re.compile(r"でぐ"), "OCR残: でぐ"),
    (re.compile(r"ぐで"), "OCR残: ぐで"),
    (re.compile(r"層い"), "OCR残: 層い→弱い?"),
    (re.compile(r"propblem"), "OCR残: propblem"),
    (re.compile(r"ブゾ"), "OCR残: ブゾーム"),
    (re.compile(r"AM 効果"), "OCR残: AM効果"),
    (re.compile(r"タタ"), "OCR残: タタ"),
    (re.compile(r"AlI"), "OCR残: AlI"),
    (re.compile(r"\bAl\b"), "OCR残: Al(単独)"),
    # 数字+全角句点
    (re.compile(r"\d。\d"), "句読点誤り: 数字。数字"),
    # 連続句点
    (re.compile(r"。。"), "句点連続"),
    (re.compile(r"、、"), "読点連続"),
    # 開閉カッコの不一致（同行）
]

# 文末が日本語として自然なパターン
RE_PROPER_END = re.compile(
    r"(?:[。？！])\s*$"
    r"|(?:[らよえねよ])。\s*$"
    r"|(?:選べ)\s*[。．\.]?\s*$"
    r"|(?:答えよ|示せ|述べよ)\s*[。．\.]?\s*$"
)

# 「最も適切なものを選べ」「2つ選べ」など問題末尾の典型語
RE_QUESTION_TAIL = re.compile(r"(?:選べ|答えよ|示せ|述べよ)")

# 半角ピリオド3つ以上連続（OCR ノイズ）
RE_DOTS = re.compile(r"\.{3,}")


def check_brackets(text: str) -> list[str]:
    """全角括弧・カギ括弧の開閉数を確認。"""
    errs = []
    pairs = [("（", "）"), ("「", "」"), ("【", "】"), ("『", "』")]
    for o, c in pairs:
        if text.count(o) != text.count(c):
            errs.append(f"括弧不一致: {o}={text.count(o)} / {c}={text.count(c)}")
    return errs


def check_question(q: dict) -> list[str]:
    """問題1件のチェック。問題のある観点を string のリストで返す。"""
    issues: list[str] = []
    qid = q["id"]
    qtext = q.get("question", "")
    choices = q.get("choices", [])
    answer = q.get("answer", [])
    multi = q.get("multiAnswer", False)
    explanation = q.get("explanation", "")

    # ---- A. 構造 ----
    if not qtext:
        issues.append("[A4] question 空")
    if not explanation:
        issues.append("[A4] explanation 空")
    if not choices:
        issues.append("[A4] choices 空")
    elif len(choices) < 2:
        issues.append(f"[A4] choices 数={len(choices)} 少ない")

    # answer の妥当性
    if not answer:
        issues.append("[A2] answer 空")
    else:
        for a in answer:
            if a not in {"A", "B", "C", "D"}:
                issues.append(f"[A2] answer に不正値: {a!r}")
        # 選択肢に存在するか
        choice_labels = {c[0] for c in choices if c and c[0] in "ABCD"}
        for a in answer:
            if a not in choice_labels:
                issues.append(f"[A2] answer={a} だが choices に対応ラベルなし")

    # multi 整合
    if multi and len(answer) <= 1:
        issues.append(f"[A3] multiAnswer=true だが answer={answer}")
    if not multi and len(answer) > 1:
        issues.append(f"[A3] multiAnswer=false だが answer={answer}")

    # ---- B. テキスト品質 ----
    # B1: 長さ
    if qtext and len(qtext) < 15:
        issues.append(f"[B1] question 短すぎ ({len(qtext)} chars)")
    if qtext and len(qtext) > 600:
        issues.append(f"[B1] question 長すぎ ({len(qtext)} chars)")
    for c in choices:
        body = re.sub(r"^[A-D]\.\s*", "", c)
        if len(body) < 2:
            issues.append(f"[B1] 選択肢 '{c[:8]}' 本文がほぼ空")
    if explanation and len(explanation) < 30:
        issues.append(f"[B1] explanation 短すぎ ({len(explanation)} chars)")

    # B2: 文末
    if qtext and RE_QUESTION_TAIL.search(qtext) is None:
        if not RE_PROPER_END.search(qtext):
            issues.append(f"[B2] question 末尾不自然: ...{qtext[-15:]!r}")

    # B3: ノイズ語
    blob = qtext + " " + " ".join(choices) + " " + explanation
    for pat, desc in NOISE_PATTERNS:
        if pat.search(blob):
            issues.append(f"[B3] {desc}")

    # B4: 選択肢長さアンバランス（4択時のみ・極端に短いものを検出）
    if len(choices) == 4:
        bodies = [re.sub(r"^[A-D]\.\s*", "", c) for c in choices]
        lens = [len(b) for b in bodies]
        if max(lens) > 0:
            min_len, max_len = min(lens), max(lens)
            if max_len >= 20 and min_len * 4 < max_len:
                short = [f"{l}/{lens[i]}c" for i, l in enumerate("ABCD") if lens[i] < max_len // 4]
                issues.append(f"[B4] 選択肢長アンバランス: 最長={max_len} 最短={min_len} ({','.join(short)})")

    # B5: 括弧不一致
    issues.extend(f"[B5] {e}" for e in check_brackets(qtext))
    issues.extend(f"[B5] choices: {e}" for e in check_brackets(" ".join(choices)))

    return issues


def main():
    if not DATA.exists():
        print(f"ERROR: {DATA} が見つかりません", file=sys.stderr)
        sys.exit(2)

    data = json.loads(DATA.read_text(encoding="utf-8"))

    # ---- 章ごとの id 連番チェック ----
    by_chapter: dict[int, list[int]] = defaultdict(list)
    for q in data:
        by_chapter[q["chapter"]].append(q["id"])

    chapter_issues: list[str] = []
    for ch in sorted(by_chapter):
        ids = sorted(by_chapter[ch])
        nums = [i % 1000 for i in ids]
        # 連続性チェック
        expected = list(range(1, len(nums) + 1))
        if nums != expected:
            missing = sorted(set(expected) - set(nums))
            extra = sorted(set(nums) - set(expected))
            msg = f"ch{ch}: id 連番ズレ"
            if missing:
                msg += f" 抜け={missing[:10]}{'...' if len(missing) > 10 else ''}"
            if extra:
                msg += f" 余り={extra[:10]}"
            chapter_issues.append(msg)
        # 重複チェック
        dup = [n for n in set(nums) if nums.count(n) > 1]
        if dup:
            chapter_issues.append(f"ch{ch}: id 重複={dup}")

    # ---- 各問題のチェック ----
    per_q: dict[int, list[str]] = {}
    issue_counter: dict[str, int] = defaultdict(int)
    for q in data:
        issues = check_question(q)
        if issues:
            per_q[q["id"]] = issues
            for it in issues:
                # 種別キー（先頭の [Xn]）で集計
                m = re.match(r"\[[A-Z]\d\][^:]+", it)
                key = m.group(0) if m else it
                issue_counter[key] += 1

    # ---- レポート生成 ----
    lines: list[str] = []
    lines.append("# DL-E questions.json 品質チェックレポート")
    lines.append("")
    lines.append(f"- 対象: `data/questions.json`")
    lines.append(f"- 総問題数: **{len(data)}**")
    lines.append(f"- 問題のある問題数: **{len(per_q)}**")
    lines.append(f"- 章別問題数: " + " / ".join(f"ch{c}={len(v)}" for c, v in sorted(by_chapter.items())))
    lines.append("")
    lines.append("## 1. 章別 id 連番チェック")
    lines.append("")
    if chapter_issues:
        for c in chapter_issues:
            lines.append(f"- ⚠️ {c}")
    else:
        lines.append("- ✅ 全章で id は 1〜N の連番（抜け・重複なし）")
    lines.append("")
    lines.append("## 2. 観点別 集計")
    lines.append("")
    lines.append("| 観点 | 件数 |")
    lines.append("|---|---:|")
    for key in sorted(issue_counter):
        lines.append(f"| {key} | {issue_counter[key]} |")
    lines.append("")
    lines.append("## 3. 問題ごとの詳細（先頭 50 件）")
    lines.append("")
    sorted_ids = sorted(per_q)
    for qid in sorted_ids[:50]:
        q = next(x for x in data if x["id"] == qid)
        lines.append(f"### id={qid} (ch{q['chapter']})")
        lines.append("")
        lines.append(f"- Q: {q['question'][:120]}")
        lines.append(f"- ans: {q['answer']} multi={q['multiAnswer']}")
        for it in per_q[qid]:
            lines.append(f"- ⚠️ {it}")
        lines.append("")

    if len(sorted_ids) > 50:
        lines.append(f"*（残り {len(sorted_ids) - 50} 件は省略）*")
        lines.append("")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {REPORT}")
    print(f"  total questions: {len(data)}")
    print(f"  questions with issues: {len(per_q)}")
    print(f"  chapter issues: {len(chapter_issues)}")
    print()
    print("=== 観点別件数 ===")
    for key, n in sorted(issue_counter.items(), key=lambda x: -x[1]):
        print(f"  {key:<40} {n:>4}")


if __name__ == "__main__":
    main()

"""DL-E OCR テキストから questions.json を組み立てる試作パーサ。

第1章を対象に、問題ページと解答ページを別々にパースして突合する。
出力結果はレビュー用。本実装前に第1章で十分検証する。

使い方:
    python tools/parse_quiz.py --chapter 1
    python tools/parse_quiz.py --chapter 1 --debug
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES_DIR = ROOT / "build" / "pages"

# (章番号, タイトル, 問題ページ範囲, 解答ページ範囲)  ※範囲は inclusive
CHAPTERS = {
    1: ("人工知能とは", (13, 15), (16, 20)),
    2: ("人工知能をめぐる動向", (23, 29), (30, 41)),
    3: ("機械学習の概要", (43, 59), (60, 84)),
    4: ("ディープラーニングの概要", (85, 96), (97, 116)),
    5: ("ディープラーニングの要素技術", (117, 128), (129, 154)),
    6: ("ディープラーニングの応用例", (155, 178), (179, 208)),
    7: ("AIの社会実装に向けて", (210, 222), (223, 235)),  # 推定
    8: ("AIに必要な数理・統計知識", (236, 247), (248, 254)),  # 推定
    # 第9, 10, 11 章は要再調査
}


# ---------- 文字列正規化 ----------

# 漢字・かな文字（CJK Unified Ideographs + Hiragana + Katakana）クラス
_JP_CHAR = r"[぀-ゟ゠-ヿ一-鿿㐀-䶿]"

# 解答ページへのリンク記号: 「中 P17」「ゆ P19」「呂 P21」「→ P25」「必 P19」「ぷ P25」等
# 安全のため漢字・かな1〜3字 + P + 数字 のパターンを広めにマッチ。
# 戻り値はマーカー（後段で問題分割に使う）に置き換える。
ANSWER_POINTER = "<<ANS>>"

OCR_REPLACEMENTS = [
    # 解答ポインタ → マーカー
    (re.compile(r"[中ゆ呂必→ぷ品時時時かが時器が][ 　]*P\s*\d+"), ANSWER_POINTER),
    # AI 表記の揺れを統一
    (re.compile(r"A[lI!|][_ ]?(?=[ァ-ンー])"), "AI "),  # 「Al ブーム」→「AI ブーム」
    (re.compile(r"\bA[lI!|]\b"), "AI"),
    # 選択肢直後の余計なアンダースコア（「A. _ シンボル」→「A. シンボル」）
    (re.compile(r"^([A-D])\.[ ]+_[ ]+", re.MULTILINE), r"\1. "),
    (re.compile(r"^([A-D])\.[ ]*_+[ ]*", re.MULTILINE), r"\1. "),
    # 「[| 1.」「| 1.」「口 1.」など問題番号の頭の汚れ → 「N.」だけ残す
    (re.compile(r"^[\[\|口](\| )?[ ]*(\d+)\.", re.MULTILINE), r"\2."),
    # 行頭の数字だけのページ番号行を削除
    (re.compile(r"^\d{1,3}\s*$", re.MULTILINE), ""),
]

# 漢字/カナ間の余計なスペース除去
_RE_JP_SPACE = re.compile(rf"({_JP_CHAR})[ 　]+(?={_JP_CHAR})")
# 漢字+英数字 / 英数字+漢字 の間のスペースは温存（読みやすさのため）


def normalize_text(text: str) -> str:
    for pat, repl in OCR_REPLACEMENTS:
        text = pat.sub(repl, text)
    # 漢字・かな間のスペースを潰す（複数回適用で安定化）
    for _ in range(4):
        text = _RE_JP_SPACE.sub(r"\1", text)
    # 連続改行は2つまで
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def collect_pages(start: int, end: int) -> str:
    parts = []
    for i in range(start, end + 1):
        p = PAGES_DIR / f"page_{i:04d}.txt"
        if p.exists() and p.stat().st_size > 0:
            parts.append(p.read_text(encoding="utf-8"))
    return "\n".join(parts)


# ---------- 問題ページのパース ----------

@dataclass
class RawQuestion:
    number: int
    text: str
    choices: dict[str, str] = field(default_factory=dict)
    multi_answer: bool = False
    is_negative: bool = False  # 「最も不適切なもの」型かどうか
    raw: str = ""


_RE_Q_NUM_LEAD = re.compile(r"^\s*(\d{1,3})\s*\.\s*", re.MULTILINE)  # 先頭の N. を抽出
_RE_CHOICE = re.compile(r"^([A-D])\.\s*(.+?)$", re.MULTILINE)
_RE_MULTI_HINT = re.compile(r"([2-5])\s*[つ個]\s*選")
_RE_NEGATIVE = re.compile(r"(不適切|誤って|間違って|当てはまらない)")


def parse_questions(raw_pages: str) -> list[RawQuestion]:
    """ANSWER_POINTER で問題ブロックを区切り、選択肢A〜Dを持つブロックだけ採用する。"""
    text = normalize_text(raw_pages)
    # ANSWER_POINTER で分割（最後のチャンクは余白）
    blocks = text.split(ANSWER_POINTER)
    questions: list[RawQuestion] = []
    auto_n = 0
    for block in blocks:
        body = block.strip()
        if not body:
            continue
        choice_matches = list(_RE_CHOICE.finditer(body))
        if len(choice_matches) < 2:
            continue
        # 番号の検出（無ければ自動採番）
        head = body[: choice_matches[0].start()]
        m = _RE_Q_NUM_LEAD.search(head)
        if m:
            try:
                number = int(m.group(1))
            except ValueError:
                number = -1
            # 妥当性チェック: 1〜80
            if not (1 <= number <= 80):
                auto_n += 1
                number = auto_n
            else:
                # 自動カウンタも進めて整合させる（問題番号が連番になる前提）
                auto_n = number
            # 問題文 = head から番号部分を削った残り
            q_text = head[: m.start()] + head[m.end():]
        else:
            auto_n += 1
            number = auto_n
            q_text = head
        q_text = q_text.strip()
        # 選択肢の抽出（複数行にまたがる本文を全部取る）
        choices: dict[str, str] = {}
        for j, cm in enumerate(choice_matches):
            label = cm.group(1)
            c_start = cm.start()
            c_end = choice_matches[j + 1].start() if j + 1 < len(choice_matches) else len(body)
            raw_choice = body[c_start:c_end]
            # 先頭の「A. 」「A.  _ 」を取り除く
            ctext = re.sub(r"^[A-D]\.\s*_*\s*", "", raw_choice, count=1)
            # 改行を空白に圧縮、末尾の空白除去
            ctext = re.sub(r"\s*\n\s*", " ", ctext).strip()
            choices[label] = ctext
        if len(choices) < 2:
            continue
        multi = bool(_RE_MULTI_HINT.search(q_text))
        negative = bool(_RE_NEGATIVE.search(q_text))
        questions.append(
            RawQuestion(
                number=number,
                text=re.sub(r"\s*\n\s*", " ", q_text),
                choices=choices,
                multi_answer=multi,
                is_negative=negative,
                raw=body,
            )
        )
    return questions


# ---------- 解答ページのパース ----------

@dataclass
class RawAnswer:
    answer_letters: list[str]
    explanation: str
    raw: str = ""


# 「(A)」「( A )」「(A、 B)」「(A, B)」「(A・B)」「(○A)」など
_RE_ANS_INLINE = re.compile(r"[(（]\s*[○]?\s*([A-D])(?:\s*[,、・]\s*([A-D])(?:\s*[,、・]\s*([A-D]))?)?\s*[)）]")
# 解答セクション開始マーカー：「○○問題です。」のような短い行
_RE_SECTION_HEAD = re.compile(r"^.{2,80}?問題で[すし]\s*[。.]?\s*$", re.MULTILINE)


def split_answers(raw_pages: str, expected_count: int) -> list[str]:
    """解答ページを問題数 N 個のチャンクに分割。

    各解答セクションは「〜問題です。」で始まる行を持つことが多いので、
    その行を区切りとして使う。
    """
    text = normalize_text(raw_pages)
    # ヘッダ行「第N章 ... 解答」を除去
    text = re.sub(r"^第\s*\d+\s*[章草].*?解\s*答\s*$", "", text, flags=re.MULTILINE)

    # セクション開始行の位置をすべて取得
    starts = [m.start() for m in _RE_SECTION_HEAD.finditer(text)]
    if not starts:
        return [text]
    # 先頭の余白（章扉等）を捨て、セクション位置で分割
    chunks: list[str] = []
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(text)
        chunks.append(text[s:e].strip())
    return chunks


def parse_answer_chunk(chunk: str) -> RawAnswer:
    # 解説本文中で最初に登場する正答ラベル群を採用
    # ただし「(A) (B) (C) (D)」が選択肢解説でばらけて出る場合があるので、
    # 「最も適切」「正解」「正答」近傍は信頼度高い → 簡易ヒューリスティック
    letters: list[str] = []
    # まず冒頭5行に絞って探す（複数選択の正答が冒頭で示されるケース）
    lead = "\n".join(chunk.splitlines()[:6])
    m = _RE_ANS_INLINE.search(lead)
    if m:
        letters = [g for g in m.groups() if g]
    if not letters:
        # フォールバック：本文全体の最初の正答ラベル
        m2 = _RE_ANS_INLINE.search(chunk)
        if m2:
            letters = [g for g in m2.groups() if g]
    return RawAnswer(answer_letters=letters or [], explanation=chunk, raw=chunk)


# ---------- 突合 ----------

def build(chapter: int, debug: bool = False) -> list[dict]:
    if chapter not in CHAPTERS:
        raise SystemExit(f"chapter {chapter} 未対応")
    title, q_range, a_range = CHAPTERS[chapter]
    q_text = collect_pages(*q_range)
    a_text = collect_pages(*a_range)

    questions = parse_questions(q_text)
    a_chunks = split_answers(a_text, len(questions))
    answers = [parse_answer_chunk(c) for c in a_chunks]

    if debug:
        print(f"[ch{chapter}] questions: {len(questions)}", file=sys.stderr)
        print(f"[ch{chapter}] answer chunks: {len(answers)}", file=sys.stderr)
        for q in questions:
            print(f"  Q{q.number}  multi={q.multi_answer}  choices={list(q.choices)}", file=sys.stderr)
        for i, a in enumerate(answers, 1):
            head = a.explanation.splitlines()[0] if a.explanation else ""
            print(f"  A#{i}  letters={a.answer_letters}  head={head[:50]}", file=sys.stderr)

    out = []
    n = min(len(questions), len(answers))
    base_id = chapter * 1000  # 章 N の問 K → id = N*1000 + K
    for i in range(n):
        q = questions[i]
        a = answers[i]
        # 「不適切なものを選べ」型は正答抽出が難しく、目視確認推奨
        flags = []
        if q.is_negative:
            flags.append("REVIEW_NEGATIVE")
        if not a.answer_letters:
            flags.append("REVIEW_NO_ANSWER")
        out.append(
            {
                "id": base_id + q.number,
                "chapter": chapter,
                "category": title,
                "question": q.text,
                "choices": [f"{k}. {v}" for k, v in sorted(q.choices.items())],
                "answer": a.answer_letters,
                "explanation": a.explanation,
                "multiAnswer": q.multi_answer,
                "_flags": flags,  # レビュー用、最終 questions.json からは削除予定
            }
        )
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chapter", type=int, required=True)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--out", type=str, default=None, help="出力先 (default: build/ch<N>.json)")
    args = parser.parse_args()

    data = build(args.chapter, debug=args.debug)
    out_path = Path(args.out) if args.out else ROOT / "build" / f"ch{args.chapter:02d}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_path}  ({len(data)} questions)")


if __name__ == "__main__":
    main()

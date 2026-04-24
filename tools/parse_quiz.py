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
# OCR テキストから境界を実測。書籍ページ番号と PDF index は基本的に1ページずれる。
CHAPTERS = {
    1:  ("人工知能とは",                       (13, 15),   (16, 22)),
    2:  ("人工知能をめぐる動向",                (23, 29),   (30, 42)),
    3:  ("機械学習の概要",                      (43, 59),   (60, 84)),
    4:  ("ディープラーニングの概要",            (85, 96),   (97, 116)),
    5:  ("ディープラーニングの要素技術",        (117, 128), (129, 146)),
    6:  ("ディープラーニングの応用例",          (147, 166), (167, 202)),
    7:  ("AIの社会実装に向けて",                (203, 208), (209, 218)),
    8:  ("AIに必要な数理・統計知識",            (219, 222), (223, 232)),
    9:  ("AIに関する法律と契約",                (233, 238), (239, 248)),
    10: ("AI倫理・AIガバナンス",                (249, 254), (255, 267)),
    11: ("総仕上げ問題",                        (269, 336), (337, 407)),
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
    number: int | None  # 解答ページに番号が明示されていれば取得
    answer_letters: list[str]
    explanation: str
    raw: str = ""


# 「(A)」「( A )」「(A、 B)」「(A, B)」「(A・B)」「(○A)」など
_RE_ANS_INLINE = re.compile(r"[(（]\s*[○]?\s*([A-D])(?:\s*[,、・]\s*([A-D])(?:\s*[,、・]\s*([A-D]))?)?\s*[)）]")
# 解答セクション開始マーカー：「○○問題です。」のような短い行
_RE_SECTION_HEAD = re.compile(r"^.{2,80}?問題で[すし]\s*[。.]?\s*$", re.MULTILINE)
# 解答ページの番号付き解答ヘッダ：「12. C」「3. D L → P24」「30. B L → P927」「2. 」など
# letter は OCR 抜けで取れない場合あり → 番号だけでも採用、letter は別途本文から推定
_RE_NUMBERED_ANS = re.compile(r"^[\s\[\|]*?(\d{1,3})\.[ \t]+(?:([A-D])(?:[\s,、・・]+([A-D])(?:[\s,、・・]+([A-D]))?)?)?", re.MULTILINE)


def split_answers_by_number(text: str) -> list[tuple[int, list[str], str]]:
    """解答ページに「N. <letter>?」が明示されている場合の分割。

    1〜80 の範囲かつ単調増加する番号のみ採用（OCR ノイズで「200.」みたいな番号を弾く）。
    letter が取れなかったチャンクは本文から `(X)` で推定。
    """
    matches = list(_RE_NUMBERED_ANS.finditer(text))
    # 単調増加チェック：直前の番号より大きいもののみ採用
    # 第11章（総仕上げ）は 200問前後あるので上限は緩めに
    valid: list[re.Match] = []
    last_n = 0
    for m in matches:
        n = int(m.group(1))
        if not (1 <= n <= 250):
            continue
        if n <= last_n:
            continue
        valid.append(m)
        last_n = n

    out: list[tuple[int, list[str], str]] = []
    for i, m in enumerate(valid):
        number = int(m.group(1))
        letters = [g for g in m.groups()[1:] if g]
        body_start = m.end()
        body_end = valid[i + 1].start() if i + 1 < len(valid) else len(text)
        body = text[body_start:body_end].strip()
        # letter 無ければ本文で補完
        if not letters:
            lead = "\n".join(body.splitlines()[:6])
            mm = _RE_ANS_INLINE.search(lead) or _RE_ANS_INLINE.search(body)
            if mm:
                letters = [g for g in mm.groups() if g]
        out.append((number, letters, body))
    return out


def split_answers_by_marker(text: str) -> list[tuple[int | None, list[str], str]]:
    """フォールバック：「〜問題です。」行で分割（第1, 2章用）。"""
    starts = [m.start() for m in _RE_SECTION_HEAD.finditer(text)]
    if not starts:
        return [(None, [], text)]
    out: list[tuple[int | None, list[str], str]] = []
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(text)
        chunk = text[s:e].strip()
        # 冒頭5行で正答ラベル探索
        lead = "\n".join(chunk.splitlines()[:6])
        m = _RE_ANS_INLINE.search(lead) or _RE_ANS_INLINE.search(chunk)
        letters = [g for g in (m.groups() if m else ()) if g]
        out.append((None, letters, chunk))
    return out


def split_answers(raw_pages: str) -> list[tuple[int | None, list[str], str]]:
    text = normalize_text(raw_pages)
    # ヘッダ行「第N章 ... 解答」を除去
    text = re.sub(r"^第\s*\d+\s*[章草].*?解\s*答\s*$", "", text, flags=re.MULTILINE)

    # まず番号付きで分割を試す
    numbered = split_answers_by_number(text)
    # 番号付き解答が3件以上見つかれば採用
    if len(numbered) >= 3:
        return numbered
    # フォールバック
    return split_answers_by_marker(text)


# ---------- 突合 ----------

def build(chapter: int, debug: bool = False) -> list[dict]:
    if chapter not in CHAPTERS:
        raise SystemExit(f"chapter {chapter} 未対応")
    title, q_range, a_range = CHAPTERS[chapter]
    q_text = collect_pages(*q_range)
    a_text = collect_pages(*a_range)

    questions = parse_questions(q_text)
    a_tuples = split_answers(a_text)  # list[(number|None, letters, explanation)]
    answers = [
        RawAnswer(number=n, answer_letters=letters, explanation=expl, raw=expl)
        for (n, letters, expl) in a_tuples
    ]

    # 問題側は出現順に 1, 2, 3, ... と振り直す（OCR 番号は不安定なので無視）
    for i, q in enumerate(questions, 1):
        q.number = i

    # 解答側に番号がある場合は、その番号で問題に紐付ける（番号 = 問題番号）
    matched: list[tuple[RawQuestion, RawAnswer | None]] = []
    if answers and all(a.number is not None for a in answers):
        ans_map = {a.number: a for a in answers}
        for q in questions:
            matched.append((q, ans_map.get(q.number)))
    else:
        # フォールバック：順番マッチ
        for i, q in enumerate(questions):
            matched.append((q, answers[i] if i < len(answers) else None))

    if debug:
        print(f"[ch{chapter}] questions: {len(questions)}, answers: {len(answers)}", file=sys.stderr)
        for q, a in matched[:10]:
            ans = a.answer_letters if a else None
            num = a.number if a else None
            print(f"  Q{q.number}  ans={ans}  ans_num={num}", file=sys.stderr)

    out = []
    base_id = chapter * 1000  # 章 N の問 K → id = N*1000 + K
    for q, a in matched:
        flags = []
        if q.is_negative:
            flags.append("REVIEW_NEGATIVE")
        if a is None:
            flags.append("REVIEW_NO_MATCH")
        elif not a.answer_letters:
            flags.append("REVIEW_NO_ANSWER")
        out.append(
            {
                "id": base_id + q.number,
                "chapter": chapter,
                "category": title,
                "question": q.text,
                "choices": [f"{k}. {v}" for k, v in sorted(q.choices.items())],
                "answer": a.answer_letters if a else [],
                "explanation": a.explanation if a else "",
                "multiAnswer": q.multi_answer,
                "_flags": flags,
            }
        )
    return out


def write_chapter(chapter: int, debug: bool) -> tuple[int, int, int, int]:
    """1章分を build/chNN.json に書き出し、(問題数, NEGATIVE, NO_ANSWER, NO_MATCH) を返す。"""
    data = build(chapter, debug=debug)
    out_path = ROOT / "build" / f"ch{chapter:02d}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    n_neg = sum(1 for q in data if "REVIEW_NEGATIVE" in q.get("_flags", []))
    n_no_ans = sum(1 for q in data if "REVIEW_NO_ANSWER" in q.get("_flags", []))
    n_no_match = sum(1 for q in data if "REVIEW_NO_MATCH" in q.get("_flags", []))
    return len(data), n_neg, n_no_ans, n_no_match


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chapter", type=int, default=None, help="単一章を変換")
    parser.add_argument("--all", action="store_true", help="全章を変換")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--out", type=str, default=None, help="出力先 (chapter 指定時のみ)")
    args = parser.parse_args()

    if not args.chapter and not args.all:
        parser.error("--chapter <N> または --all を指定してください")

    if args.all:
        total_q = total_neg = total_no_ans = total_no_match = 0
        print(f"{'ch':>3} {'title':<30} {'Q':>5} {'NEG':>5} {'NoAns':>6} {'NoMatch':>8}")
        print("-" * 70)
        for ch in sorted(CHAPTERS):
            n, neg, no_ans, no_match = write_chapter(ch, debug=args.debug)
            title = CHAPTERS[ch][0]
            print(f"{ch:>3} {title:<30} {n:>5} {neg:>5} {no_ans:>6} {no_match:>8}")
            total_q += n
            total_neg += neg
            total_no_ans += no_ans
            total_no_match += no_match
        print("-" * 70)
        print(f"{'TOT':>3} {'':<30} {total_q:>5} {total_neg:>5} {total_no_ans:>6} {total_no_match:>8}")
        return

    # 単一章
    data = build(args.chapter, debug=args.debug)
    out_path = Path(args.out) if args.out else ROOT / "build" / f"ch{args.chapter:02d}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_path}  ({len(data)} questions)")


if __name__ == "__main__":
    main()

"""DL-E PDF 全ページ OCR バッチ。

CLAUDE.md の長時間バッチ処理ルールに準拠:
- 起動:  `python tools/ocr_all.py` または `tools/ocr_run.bat`
- 停止:  `tools/ocr_stop.bat`
- 再開:  既出力済みページを自動スキップ（--force で強制再OCR）
- 進捗:  `python tools/ocr_all.py --stats` または `tools/ocr_status.bat`

出力:
  build/pages/page_NNNN.txt          ... 各ページのOCRテキスト
  build/progress.json                ... 進捗メタデータ（最終更新時に書き込み）
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image
import io

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "徹底攻略ディープラーニングG検定ジェネラリスト問題集 第3版 徹底攻略シリーズ.pdf"
TESSDATA = ROOT / "tessdata"
PAGES_DIR = ROOT / "build" / "pages"
PROGRESS_JSON = ROOT / "build" / "progress.json"

os.environ["TESSDATA_PREFIX"] = str(TESSDATA)
import pytesseract  # noqa: E402

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def page_path(idx: int) -> Path:
    return PAGES_DIR / f"page_{idx:04d}.txt"


def render_page(page, dpi: int) -> Image.Image:
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    return Image.open(io.BytesIO(pix.tobytes("png")))


def ocr_page(img: Image.Image) -> str:
    return pytesseract.image_to_string(img, lang="jpn", config="--psm 4")


def write_progress(total: int, done_idx: list[int], started_at: float, last_idx: int) -> None:
    PROGRESS_JSON.parent.mkdir(parents=True, exist_ok=True)
    elapsed = time.time() - started_at
    PROGRESS_JSON.write_text(
        json.dumps(
            {
                "total_pages": total,
                "done_count": len(done_idx),
                "last_processed_index": last_idx,
                "started_at": datetime.fromtimestamp(started_at).isoformat(timespec="seconds"),
                "updated_at": datetime.now().isoformat(timespec="seconds"),
                "elapsed_seconds": round(elapsed, 1),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def cmd_stats(total: int) -> None:
    done = sorted(int(p.stem.split("_")[1]) for p in PAGES_DIR.glob("page_*.txt") if p.stat().st_size > 0)
    pct = len(done) / total * 100 if total else 0
    print(f"PDF total pages : {total}")
    print(f"OCR done pages  : {len(done)}  ({pct:.1f}%)")
    if done:
        print(f"  range done    : {done[0]} ... {done[-1]}")
        missing = sorted(set(range(total)) - set(done))
        if missing:
            head = ", ".join(str(x) for x in missing[:10])
            tail = f", ... ({len(missing)} missing)" if len(missing) > 10 else ""
            print(f"  missing       : {head}{tail}")
        else:
            print("  missing       : (none)")
    if PROGRESS_JSON.exists():
        print()
        print("--- progress.json ---")
        print(PROGRESS_JSON.read_text(encoding="utf-8"))


def cmd_run(start: int, end: int | None, force: bool, dpi: int) -> int:
    if not PDF.exists():
        print(f"ERROR: PDF not found: {PDF}", file=sys.stderr)
        return 2
    PAGES_DIR.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(PDF)
    total = len(doc)
    end = end if end is not None else total
    end = min(end, total)
    if start < 0 or start >= total:
        print(f"ERROR: start out of range (0..{total - 1})", file=sys.stderr)
        return 2

    targets = list(range(start, end))
    skipped = []
    pending = []
    for i in targets:
        if not force and page_path(i).exists() and page_path(i).stat().st_size > 0:
            skipped.append(i)
        else:
            pending.append(i)

    print(f"target pages : {len(targets)} (range {start}..{end - 1})")
    print(f"skipped (done): {len(skipped)}")
    print(f"to process   : {len(pending)}")
    if not pending:
        print("Nothing to do.")
        return 0

    done_idx = list(skipped)
    started = time.time()
    interrupted = False

    def handle_sigint(signum, frame):  # type: ignore[no-untyped-def]
        nonlocal interrupted
        interrupted = True
        print("\n[interrupt] finishing current page then exiting cleanly...", flush=True)

    signal.signal(signal.SIGINT, handle_sigint)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, handle_sigint)  # type: ignore[attr-defined]

    last_idx = -1
    for n, i in enumerate(pending, 1):
        t0 = time.time()
        try:
            img = render_page(doc[i], dpi=dpi)
            text = ocr_page(img)
        except Exception as e:  # noqa: BLE001
            print(f"  p{i:04d}  ERROR: {e}", file=sys.stderr)
            continue

        page_path(i).write_text(text, encoding="utf-8")
        done_idx.append(i)
        last_idx = i

        elapsed = time.time() - started
        per_page = elapsed / n
        eta = timedelta(seconds=int(per_page * (len(pending) - n)))
        dt = time.time() - t0
        print(
            f"  [{n:4d}/{len(pending):4d}] p{i:04d}  {dt:5.2f}s  chars={len(text):5d}  "
            f"eta={eta}  total={len(done_idx)}/{total}",
            flush=True,
        )

        # progress.json を毎ページ更新（再開・進捗表示用）
        write_progress(total, done_idx, started, last_idx)

        if interrupted:
            break

    doc.close()
    print()
    print(f"done: {len(done_idx)}/{total} pages  (this run processed {len(done_idx) - len(skipped)})")
    if interrupted:
        print("(interrupted — re-run to resume)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="OCR all pages of the DL-E PDF.")
    parser.add_argument("--start", type=int, default=0, help="開始ページ (0-indexed, default 0)")
    parser.add_argument("--end", type=int, default=None, help="終了ページ (exclusive, default = 全体)")
    parser.add_argument("--force", action="store_true", help="既存出力を無視して再OCR")
    parser.add_argument("--dpi", type=int, default=300, help="レンダリング DPI (default 300)")
    parser.add_argument("--stats", action="store_true", help="進捗統計のみ表示して終了")
    args = parser.parse_args()

    if args.stats:
        if not PDF.exists():
            print(f"ERROR: PDF not found: {PDF}", file=sys.stderr)
            return 2
        doc = fitz.open(PDF)
        total = len(doc)
        doc.close()
        cmd_stats(total)
        return 0

    return cmd_run(args.start, args.end, args.force, args.dpi)


if __name__ == "__main__":
    sys.exit(main())

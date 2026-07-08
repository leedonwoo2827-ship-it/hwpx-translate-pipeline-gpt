"""챕터 PDF들을 한 권으로 병합. 각 챕터의 표지(1페이지)를 자동 제거 후 이어붙인다.

각 챕터 hwpx 는 회사 양식 표지가 1페이지로 붙어 있으므로(안정적 렌더), 병합 시
--drop-cover(기본)로 1페이지를 떼고 본문만 이어붙여 깨끗한 한 권을 만든다.

    python pipeline/merge_pdf.py [--run <런폴더>]   # <런>/05-hwpx/*.pdf → 06-book
    python pipeline/merge_pdf.py --keep-cover        # 표지도 포함
"""
from __future__ import annotations

import glob
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paths  # noqa: E402
import fitz  # PyMuPDF  # noqa: E402


def merge(run: str | None = None, drop_cover: bool = True, out_path: str | None = None,
          book: str | None = None) -> str:
    run_dir = paths.resolve_run(run, book=book)
    # 챕터 파일은 '시작페이지-...' 명명이라 정렬하면 원문 순서.
    pdfs = sorted(glob.glob(os.path.join(paths.stage(run_dir, paths.HWPX), "*.pdf")))
    if not pdfs:
        raise FileNotFoundError("병합할 PDF 없음 — 먼저 build + hancom pdf 로 각 장 PDF를 만드세요.")
    book = fitz.open()
    for p in pdfs:
        doc = fitz.open(p)
        start = 1 if (drop_cover and doc.page_count > 1) else 0
        book.insert_pdf(doc, from_page=start, to_page=doc.page_count - 1)
        print(f"  + {os.path.basename(p)}  (p{start+1}-{doc.page_count})")
        doc.close()
    if out_path is None:
        out_dir = paths.stage(run_dir, paths.BOOK)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "UNIVERSITIES-AFTER-AI-KO.pdf")
    book.save(out_path)
    book.close()
    print(f"병합 완료: {out_path}")
    return out_path


if __name__ == "__main__":
    run = sys.argv[sys.argv.index("--run") + 1] if "--run" in sys.argv else None
    book = sys.argv[sys.argv.index("--book") + 1] if "--book" in sys.argv else None
    merge(run=run, drop_cover="--keep-cover" not in sys.argv, book=book)

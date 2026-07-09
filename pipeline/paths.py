"""책(book) · 런(run) · 스테이지 단위 출력 구조 경로 해석.

    output/<책명>/<YYMMDDHHMM>-<영문라벨>/
        01-extract/ 02-translate/ 03-refine/ 04-review/ 05-hwpx/ 06-book/

- output/<책명>/ : 한 권(책/문서). 여러 책을 나란히 둘 수 있다.
- <책명>/<런>/ : 각 실행 회차(교지). 이름 정렬 = 시간순.
- output/ 전체는 .gitignore(GitHub 미포함).
- 명령은 --book <책명> / --run <런폴더>(또는 절대경로) 지원. 생략 시:
  book=최신(없으면 기본책), run=그 책의 최신 런.
- extract 는 --run 없으면 새 런 폴더 생성. md 파일부터 시작도 가능(스테이지 독립).
"""
from __future__ import annotations

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(ROOT, "output")

DEFAULT_BOOK = "translations"

EXTRACT = "01-extract"
TRANSLATE = "02-translate"
REFINE = "03-refine"
REVIEW = "04-review"
HWPX = "05-hwpx"
BOOK = "06-book"

# build 소스 우선순위(존재하는 첫 단계의 content.ko.md 사용)
SOURCE_CHAIN = [(REVIEW, "content.reviewed.md"), (REFINE, "content.ko.md"),
                (TRANSLATE, "content.ko.md")]

_RUN_RE = re.compile(r"\d{10}-")


def _is_run(name: str) -> bool:
    return bool(_RUN_RE.match(name))


def books() -> list[str]:
    """런 폴더를 하나 이상 가진 output 하위 디렉터리 = 책 목록(이름 정렬)."""
    if not os.path.isdir(OUTPUT):
        return []
    out = []
    for b in sorted(os.listdir(OUTPUT)):
        bd = os.path.join(OUTPUT, b)
        if os.path.isdir(bd) and any(
                _is_run(r) and os.path.isdir(os.path.join(bd, r)) for r in os.listdir(bd)):
            out.append(b)
    return out


def latest_book() -> str:
    bs = books()
    return bs[-1] if bs else DEFAULT_BOOK


def book_dir(book: str | None = None) -> str:
    return os.path.join(OUTPUT, book or latest_book())


def runs(book: str | None = None) -> list[str]:
    """책 안의 런(교지) 목록(이름=시간 정렬)."""
    bd = book_dir(book)
    if not os.path.isdir(bd):
        return []
    return sorted(r for r in os.listdir(bd)
                  if _is_run(r) and os.path.isdir(os.path.join(bd, r)))


def latest_run(book: str | None = None) -> str | None:
    rs = runs(book)
    return os.path.join(book_dir(book), rs[-1]) if rs else None


def new_run(label: str = "ko", book: str | None = None) -> str:
    import datetime  # 실제 실행 환경 — datetime 사용 가능
    ts = datetime.datetime.now().strftime("%y%m%d%H%M")  # 연월일시분 (예: 2607081530)
    d = os.path.join(book_dir(book), f"{ts}-{label}")
    os.makedirs(d, exist_ok=True)
    return d


def _find_run_across_books(run_name: str) -> str | None:
    """런 이름만 주어졌을 때 모든 책에서 탐색(하위호환·편의)."""
    for b in books():
        c = os.path.join(OUTPUT, b, run_name)
        if os.path.isdir(c):
            return c
    return None


def resolve_run(run: str | None = None, create: bool = False,
                label: str = "ko", book: str | None = None) -> str:
    """런 디렉터리(절대경로) 반환.

    run: 절대경로 → 그대로. 런 이름 → book 안(없으면 다른 책에서 탐색).
    run 생략: book(또는 최신책)의 최신 런. create=True 면 새 런 생성.
    """
    if run:
        if os.path.isabs(run):
            if create:
                os.makedirs(run, exist_ok=True)
            return run
        cand = os.path.join(book_dir(book), run)
        if os.path.isdir(cand):
            return cand
        if book is None:
            found = _find_run_across_books(run)
            if found:
                return found
        if create:
            os.makedirs(cand, exist_ok=True)
        return cand
    if create:
        return new_run(label, book)
    r = latest_run(book)
    if r is None:
        raise SystemExit("런 폴더가 없습니다. 'extract'로 생성하거나 --run <런폴더>[ --book <책명>]을 지정하세요.")
    return r


def stage(run_dir: str, name: str, *sub: str) -> str:
    return os.path.join(run_dir, name, *sub)


def source_md(run_dir: str, chapter_id: str):
    """build 소스: 04-review → 03-refine → 02-translate 중 존재하는 첫 md 경로."""
    for st, fn in SOURCE_CHAIN:
        p = os.path.join(run_dir, st, chapter_id, fn)
        if os.path.exists(p):
            return p, st
    return None, None

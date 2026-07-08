"""Phase 1: PDF → 챕터별 EN 마크다운 + 도표 크롭 PNG.

원문(UNIVERSITIES AFTER AI.pdf)은 페이지마다 풀페이지 JPEG + 텍스트 레이어 구조.
- 텍스트: 블록 단위로 추출해 머리글/쪽번호 제거, 하이픈 결합, 문단 재구성.
- 소제목: Tahoma-Bold(10~13pt) → ## / 챕터 제목: >=14pt → #.
- 도표: 본문 블록 사이 큰 수직 공백을 검출해 고해상 크롭(캡션 "Figure N:" 연결).

사용:
    python pipeline/extract.py                 # 파일럿 전체
    python pipeline/extract.py ch03-trapezoid  # 특정 챕터
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paths  # noqa: E402
import fitz  # PyMuPDF  # noqa: E402

ROOT = os.path.dirname(HERE)
PDF = os.path.join(ROOT, "_asstest", "UNIVERSITIES AFTER AI.pdf")

# 전체 장 맵 (PDF 1-based 페이지 범위, 포함). 페이지 맵은 탐색으로 확보.
# id = "시작(3)-끝(3)-장번호(2)-약칭"  예) 052-059-03-knowledge-trapezoid
_SPECS = [
    (16, 22, "00", "editorial-intro",
     "Editorial Introduction: Designing the AI-Realist University", "Pavel Luksha"),
    (23, 30, "00", "analytical-preface",
     "Analytical preface. Mapping the global discourse, manifestos, and institutional debt", "Vadim Novikov"),
    (32, 40, "01", "labor-economics",
     "Chapter 1. Labor economics, so-so automation, and relational university", "Alexander M. Sidorkin"),
    (41, 51, "02", "after-content",
     "Chapter 2. After AI, the university cannot be organized around content", "Natalia Cebotari"),
    (52, 59, "03", "knowledge-trapezoid",
     "Chapter 3. The knowledge trapezoid: expertise, depthification, and transfer", "Charles Fadel"),
    (60, 76, "04", "symbiotic-aix",
     "Chapter 4. The future of education: symbiotic intelligence and the AI+X paradigm",
     "Shawn Chen, Richard Jiarui Tong, Xiangen Hu, Jack Gao"),
    (77, 89, "05", "epistemic-legitimation",
     "Chapter 5. Epistemic legitimation and hybrid cognitive units", "Timur Schukin"),
    (90, 104, "06", "planetary-doughnut",
     "Chapter 6. The architecture of Planetary Agency and Doughnut Learning",
     "Raphael Costambeys-Kempczynski, François Taddei"),
    (105, 118, "07", "accreditation",
     "Chapter 7. AI meets accreditation: lessons from the U.S. for the future of quality assurance", "Ralph A. Wolff"),
    (119, 128, "00", "bridging-map",
     "Bridging Chapter: Operational Mapping — The AI Ecosystem Map for Universities", "Vadim Novikov"),
    (130, 140, "08", "ai-ready-graduates",
     "Chapter 8. Building AI-ready graduates in a small, fast-shifting economy", "Kakha Shengelia"),
    (141, 148, "09", "learn-with-ai",
     "Chapter 9. The tactical classroom: “Learn with AI, test without AI” in Kyrgyzstan", "Ivan Ninenko"),
    (149, 155, "10", "tolyq-adam",
     "Chapter 10. The “Tolyq Adam” framework: holistic human development in Kazakhstan",
     "Assylbek Kozhakhmetov, Assel Aryn, Aigul Sarenova"),
    (156, 161, "11", "ai-native-bangladesh",
     "Chapter 11. Becoming an entrepreneurial, AI-native university in Bangladesh", "Md. Sabur Khan"),
    (162, 169, "12", "african-governance",
     "Chapter 12. Continental impact and indigenous/African legal governance", "Letlhokwa George Mpedi"),
    (170, 185, "13", "regenerative-mexico",
     "Chapter 13. The university as regenerative ecosystem: a planetary mission experiment in Mexico", "Victoria Haro"),
    (186, 192, "99", "conclusion",
     "Editorial conclusion: Toward an agentic future", "Sholpan Tazabek, Pavel Luksha"),
]

CHAPTERS = {
    f"{s:03d}-{e:03d}-{num}-{slug}": {"title": title, "author": author, "pages": (s, e)}
    for (s, e, num, slug, title, author) in _SPECS
}

# 레이아웃 임계값 (pt, 553x808 페이지 기준)
HEADER_Y = 66      # 이 위쪽 소폰트 = 머리글
FOOTER_Y = 735     # 이 아래쪽 = 쪽번호/꼬리말
FIGURE_MIN_GAP = 85  # 본문 블록 사이 이만큼 이상 빈 세로공간 = 도표
FIG_DPI = 300
CROP_PAD = 6       # 크롭 여백(pt)

_FIG_CAP = re.compile(r"^(Figure|Fig\.?|Table)\s*\d+", re.I)
_PAGENUM = re.compile(r"^\d{1,4}$")


def _is_blank(pix, dark_thresh=0.004) -> bool:
    """크롭 픽스맵이 거의 흰색(도표 아님)인지. 어두운 픽셀 비율이 임계 미만이면 빈 것."""
    from PIL import Image
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("L")
    hist = img.histogram()
    total = pix.width * pix.height
    dark = sum(hist[:210])  # 밝기 210 미만 = 잉크로 간주
    return total == 0 or (dark / total) < dark_thresh


def _span0(block):
    for l in block["lines"]:
        for s in l["spans"]:
            return s
    return None


def _block_text(block) -> str:
    """블록 내 라인을 문단 텍스트로 결합(하이픈/소프트하이픈 처리)."""
    lines = []
    for l in block["lines"]:
        txt = "".join(s["text"] for s in l["spans"])
        lines.append(txt)
    out = ""
    for i, ln in enumerate(lines):
        ln = ln.replace("­", "")  # soft hyphen 제거
        if i == 0:
            out = ln
            continue
        if out.endswith("-"):          # 줄끝 하이픈 → 결합(하이픈 제거)
            out = out[:-1] + ln.lstrip()
        else:
            out = out.rstrip() + " " + ln.lstrip()
    return re.sub(r"\s+", " ", out).strip()


def _classify(block, is_first_page, seen_title):
    """블록 → (kind, text). kind: header/pagenum/title/subhead/caption/body/skip."""
    s = _span0(block)
    if s is None:
        return ("skip", "")
    size = s["size"]
    font = s["font"]
    bold = bool(s["flags"] & (1 << 4)) or "Bold" in font
    y0 = block["bbox"][1]
    text = _block_text(block)
    if not text:
        return ("skip", "")

    # 쪽번호 / 꼬리말
    if y0 >= FOOTER_Y and _PAGENUM.match(text):
        return ("pagenum", text)
    # 머리글(상단 Tahoma 소폰트)
    if y0 < HEADER_Y and "Tahoma" in font and size <= 11 and not (is_first_page and size >= 14):
        return ("header", text)
    # 도표/표 캡션
    if _FIG_CAP.match(text) and size <= 10:
        return ("caption", text)
    # 챕터 제목(첫 페이지 큰 글씨)
    if size >= 14:
        return ("title", text)
    # 소제목(Tahoma-Bold)
    if bold and "Tahoma" in font and size <= 13:
        return ("subhead", text)
    return ("body", text)


def extract_chapter(cid: str, meta: dict, doc, out_root: str) -> None:
    out_dir = os.path.join(out_root, cid)
    fig_dir = os.path.join(out_dir, "figures")
    os.makedirs(fig_dir, exist_ok=True)

    p0, p1 = meta["pages"]
    md_lines = []
    figures = []
    fig_n = 0
    title_emitted = False

    for pno in range(p0 - 1, p1):        # 0-based
        page = doc[pno]
        d = page.get_text("dict")
        # 텍스트 블록만, y 순 정렬
        tblocks = sorted((b for b in d["blocks"] if b["type"] == 0),
                         key=lambda b: b["bbox"][1])
        is_first = (pno == p0 - 1)

        # 본문 흐름을 위한 이전 블록 하단 y (도표 공백 검출)
        prev_bottom = None
        classified = []
        for b in tblocks:
            kind, text = _classify(b, is_first, title_emitted)
            classified.append((kind, text, b["bbox"]))

        for i, (kind, text, bbox) in enumerate(classified):
            x0, y0, x1, y1 = bbox
            # 도표 공백 검출: 콘텐츠 영역 내에서 앞 본문 하단 ~ 현재 블록 상단 사이 큰 공백
            if kind in ("body", "caption", "subhead") and prev_bottom is not None:
                gap = y0 - prev_bottom
                if gap >= FIGURE_MIN_GAP and prev_bottom > HEADER_Y and y0 < FOOTER_Y:
                    clip = fitz.Rect(48, prev_bottom + CROP_PAD, 515, y0 - CROP_PAD)
                    pix = page.get_pixmap(dpi=FIG_DPI, clip=clip)
                    if _is_blank(pix):
                        # 제목-본문 사이 여백 등 빈 크롭은 도표가 아님 → 건너뜀
                        prev_bottom = y1
                        continue
                    fig_n += 1
                    fname = f"fig-{fig_n:02d}.png"
                    pix.save(os.path.join(fig_dir, fname))
                    cap = text if kind == "caption" else ""
                    figures.append({"file": fname, "page": pno + 1, "caption": cap,
                                    "px": [pix.width, pix.height]})
                    md_lines.append(f"\n![{cap or ('Figure ' + str(fig_n))}](figures/{fname})\n")

            if kind in ("header", "pagenum", "skip"):
                pass
            elif kind == "title":
                if not title_emitted:
                    md_lines.append(f"# {text}")
                    if meta.get("author"):
                        md_lines.append(f"\n**{meta['author']}**\n")
                    title_emitted = True
                else:
                    md_lines.append(f"\n## {text}")
            elif kind == "subhead":
                md_lines.append(f"\n## {text}\n")
            elif kind == "caption":
                # 캡션은 위 도표에 붙임(위에서 처리) — 중복 방지: 이미지 없이 온 캡션만 인용으로
                md_lines.append(f"> {text}")
            elif kind == "body":
                # 첫 페이지에서 저자명만 든 본문 블록은 중복이므로 건너뜀
                if is_first and text.strip() == (meta.get("author") or "").strip():
                    prev_bottom = y1
                    continue
                md_lines.append(text + "\n")

            if kind in ("body", "subhead", "caption"):
                prev_bottom = y1

    # 제목 미검출 시 메타 제목 사용
    body = "\n".join(md_lines).strip()
    if not title_emitted:
        body = f"# {meta['title']}\n\n*{meta.get('author','')}*\n\n" + body
    body = re.sub(r"\n{3,}", "\n\n", body) + "\n"

    with open(os.path.join(out_dir, "content.en.md"), "w", encoding="utf-8") as f:
        f.write(body)
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({"id": cid, **meta, "figures": figures}, f, ensure_ascii=False, indent=2)

    print(f"[{cid}] pages {p0}-{p1} | figures={len(figures)} | md={len(body)} chars → {out_dir}")


def main():
    argv = sys.argv[1:]
    run = None
    book = None
    if "--run" in argv:
        i = argv.index("--run"); run = argv[i + 1]; del argv[i:i + 2]
    if "--book" in argv:
        i = argv.index("--book"); book = argv[i + 1]; del argv[i:i + 2]
    # 원본 PDF 확인(없으면 빈 런을 만들지 않고 안내 후 종료)
    if not os.path.exists(PDF):
        print("원본 PDF가 없습니다. 아래 위치에 파일을 넣고 다시 실행하세요:")
        print(f"    {PDF}")
        print("  · 폴더(_asstest)는 저작권·대용량이라 리포에 포함되지 않습니다(직접 준비).")
        print("  · 전체 책(192p)을 넣으면 메뉴 1)이 모든 장을 추출합니다.")
        print("    특정 장만: python run.py extract <chapter-id>  (예: 156-161-11-ai-native-bangladesh)")
        print(f"  · 사용 가능한 chapter-id: {list(CHAPTERS)}")
        raise SystemExit(1)
    # extract 는 기본적으로 새 런 생성(--run 지정 시 해당 런에 추가)
    run_dir = paths.resolve_run(run, create=True, book=book)
    out_root = paths.stage(run_dir, paths.EXTRACT)
    os.makedirs(out_root, exist_ok=True)
    print(f"[run] {os.path.basename(run_dir)}")
    doc = fitz.open(PDF)
    targets = argv or list(CHAPTERS.keys())
    for cid in targets:
        if cid not in CHAPTERS:
            print(f"unknown chapter: {cid}; available: {list(CHAPTERS)}")
            continue
        extract_chapter(cid, CHAPTERS[cid], doc, out_root)


if __name__ == "__main__":
    main()

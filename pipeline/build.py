"""Phase 4: (번역/검토 완료) KO 마크다운 → hwpx (구조·스타일 미러 + 도표 삽입).

문서공방 clone-and-refill(hwpx_gen)로 본문 스타일을 상속하고, 도표 라인
`![캡션](figures/xxx.png)` 은 images.py 로 BinData 삽입 + 캡션(인용) 렌더한다.

사용:
    python pipeline/build.py <chapter-id> [--run <런폴더>]
소스 우선순위: 04-review → 03-refine → 02-translate (존재하는 첫 md).
런이 md 파일부터 시작될 수 있음(01-extract/도표 없어도 무방).
"""
from __future__ import annotations

import io
import os
import re
import sys
import zipfile

# CLI 실행 시에만 콘솔을 UTF-8 로(한글 출력). 서버 등에서 import 될 때는 stdout 을 건드리지 않음.
if __name__ == "__main__":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import paths  # noqa: E402
from hwpx import hwpx_gen, images, mdblocks  # noqa: E402
from lxml import etree  # noqa: E402

HP = f"{{{hwpx_gen.HP}}}"
TEMPLATE = os.path.join(ROOT, "assets", "hwpx_template.hwpx")

_IMG_LINE = re.compile(r"^\s*!\[(?P<cap>.*?)\]\((?P<path>[^)]+)\)\s*$")

# 본문 문단 첫 줄 들여쓰기(원문처럼) — 한 글자 폭(HWPUNIT). 0=없음.
FIRST_LINE_INDENT = 1000


def _set_first_line_indent(blobs, style_map, style_names=("본문",), value=FIRST_LINE_INDENT):
    """header.xml 에서 지정 스타일의 paraPr 첫 줄 들여쓰기(intent)를 설정.
    템플릿을 손대지 않고 빌드 시 적용(재현 가능)."""
    if not value:
        return
    from lxml import etree
    HH = hwpx_gen.HH
    HC = "http://www.hancom.co.kr/hwpml/2011/core"
    target_ids = {style_map[n]["paraPrIDRef"] for n in style_names if n in style_map}
    root = etree.fromstring(blobs["Contents/header.xml"])
    for pp in root.iter(f"{{{HH}}}paraPr"):
        if pp.get("id") in target_ids:
            margin = pp.find(f"{{{HH}}}margin")
            if margin is None:
                continue
            intent = margin.find(f"{{{HC}}}intent")
            if intent is None:
                intent = etree.SubElement(margin, f"{{{HC}}}intent")
            intent.set("value", str(value))
            intent.set("unit", "HWPUNIT")
    blobs["Contents/header.xml"] = etree.tostring(
        root, xml_declaration=True, encoding="UTF-8", standalone=True)


def _segments(md: str):
    """마크다운을 (‘text’, 청크) / (‘figure’, (path, caption)) 세그먼트로 분리."""
    segs = []
    buf = []
    for line in md.replace("\r\n", "\n").split("\n"):
        m = _IMG_LINE.match(line)
        if m:
            if buf:
                segs.append(("text", "\n".join(buf)))
                buf = []
            segs.append(("figure", (m.group("path").strip(), m.group("cap").strip())))
        else:
            buf.append(line)
    if buf:
        segs.append(("text", "\n".join(buf)))
    return segs


def _drop_cover(blobs, members):
    """표지(앞 섹션)를 제거하고 본문 섹션만 남긴다(챕터 파일은 병합용 → 표지 반복 방지).
    본문 섹션을 section0.xml 로 이름 바꾸고 content.hpf(manifest/spine)를 갱신한다.
    members(원본 infolist)에서도 제거된 섹션 항목을 걸러 반환한다."""
    from lxml import etree
    OPF = "http://www.idpf.org/2007/opf/"

    section_names = sorted(n for n in blobs
                           if n.startswith("Contents/section") and n.endswith(".xml"))
    if len(section_names) <= 1:
        return members
    body = section_names[-1]
    covers = section_names[:-1]

    body_xml = blobs[body]
    for n in section_names:
        del blobs[n]
    blobs["Contents/section0.xml"] = body_xml  # 본문을 유일 섹션(0)으로

    # content.hpf: 모든 섹션 item/itemref 제거 후 단일 section0 재등록
    hpf = etree.fromstring(blobs["Contents/content.hpf"])
    manifest = hpf.find(f"{{{OPF}}}manifest")
    spine = hpf.find(f"{{{OPF}}}spine")
    for it in list(manifest.findall(f"{{{OPF}}}item")):
        if it.get("href", "").startswith("Contents/section"):
            manifest.remove(it)
    sec_item = etree.SubElement(manifest, f"{{{OPF}}}item")
    sec_item.set("id", "section0")
    sec_item.set("href", "Contents/section0.xml")
    sec_item.set("media-type", "application/xml")
    if spine is not None:
        for ref in list(spine.findall(f"{{{OPF}}}itemref")):
            if ref.get("idref", "").startswith("section"):
                spine.remove(ref)
        ref = etree.SubElement(spine, f"{{{OPF}}}itemref")
        ref.set("idref", "section0")
        ref.set("linear", "yes")
    blobs["Contents/content.hpf"] = etree.tostring(
        hpf, xml_declaration=True, encoding="UTF-8", standalone=True)

    new_members = [m for m in members
                   if not (m.filename in covers or m.filename == body)]
    return new_members


def build(chapter_id: str, run: str | None = None,
          out_path: str | None = None, include_cover: bool = True,
          book: str | None = None) -> str:
    run_dir = paths.resolve_run(run, book=book)
    md_path, src_stage = paths.source_md(run_dir, chapter_id)
    if md_path is None:
        raise FileNotFoundError(
            f"{chapter_id}: 04-review/03-refine/02-translate 어디에도 content(.ko|.reviewed).md 없음 (run={os.path.basename(run_dir)})")
    md = open(md_path, encoding="utf-8").read()
    # 도표는 런의 01-extract 에 존재하면 참조(md 우선 진입으로 없으면 자동 건너뜀).
    fig_base = paths.stage(run_dir, paths.EXTRACT, chapter_id)

    # 템플릿 로드
    src = zipfile.ZipFile(TEMPLATE)
    members = src.infolist()
    blobs = {m.filename: src.read(m.filename) for m in members}
    src.close()

    style_map = hwpx_gen._style_map(blobs["Contents/header.xml"])
    normal = hwpx_gen._pick(style_map, "본문") or {"styleId": "0", "paraPrIDRef": "0", "charPrIDRef": "0"}
    emph = hwpx_gen._pick(style_map, "강조")
    cap_style = hwpx_gen._pick(style_map, "인용") or normal

    # 스타일은 '양식 정본'(assets/hwpx_template.hwpx)을 그대로 따른다.
    # 첫 줄 들여쓰기 등 서식 보정은 make_template.py 로 템플릿에 구워두었으며,
    # 사용자가 한컴에서 템플릿을 직접 수정하면 그 값이 존중된다(빌드가 덮어쓰지 않음).

    # 챕터 파일은 병합용 → 회사 표지 제거(본문만). include_cover=True 면 표지 유지.
    if not include_cover:
        members = _drop_cover(blobs, members)

    section_names = sorted(n for n in blobs if n.startswith("Contents/section") and n.endswith(".xml"))
    body_name = section_names[-1]
    root = etree.fromstring(blobs[body_name])

    # 기존 본문 단락 제거(secPr 보존)
    paras = [c for c in root if c.tag == f"{HP}p"]
    secpr = next((p for p in paras if p.find(f".//{HP}secPr") is not None),
                 paras[0] if paras else None)
    for p in paras:
        root.remove(p)
    if secpr is not None:
        hwpx_gen._strip_text(secpr)
        root.append(secpr)

    # 세그먼트 순서대로 렌더
    fig_i = 0
    for kind, payload in _segments(md):
        if kind == "text":
            for blk in mdblocks.parse(payload):
                if hwpx_gen._is_divider(blk):
                    continue
                if blk["type"] == "table":
                    tbl_tmpl = hwpx_gen._extract_table_template({body_name: blobs[body_name]}) \
                        or hwpx_gen._extract_table_template(blobs)
                    bf_index = hwpx_gen._borderfill_index(blobs["Contents/header.xml"])
                    if tbl_tmpl is not None:
                        try:
                            root.append(hwpx_gen._make_table(tbl_tmpl, blk, style_map, bf_index))
                            continue
                        except Exception as e:  # noqa: BLE001
                            print(f"[build] 표 렌더 실패, 평탄화: {e}")
                    for b in hwpx_gen._table_to_blocks(blk):
                        st = hwpx_gen._style_for_block(b, style_map, normal)
                        root.append(hwpx_gen._make_para(b, st, emph, normal))
                    continue
                st = hwpx_gen._style_for_block(blk, style_map, normal)
                root.append(hwpx_gen._make_para(blk, st, emph, normal))
        else:  # figure
            rel_path, caption = payload
            img_path = os.path.normpath(os.path.join(fig_base, rel_path))
            if not os.path.exists(img_path):
                print(f"[build] 도표 없음, 건너뜀: {img_path}")
                continue
            fig_i += 1
            item_id = f"fig{fig_i}"
            png = open(img_path, "rb").read()
            images.register_image(blobs, "Contents/content.hpf", png, item_id)
            pw, ph = images.png_size(png)
            root.append(images.make_pic_paragraph(item_id, pw, ph, style=normal))
            if caption:
                capblk = {"type": "quote", "level": 0, "text": caption,
                          "runs": [(caption, False)]}
                root.append(hwpx_gen._make_para(capblk, cap_style, emph, normal))

    blobs[body_name] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)

    if out_path is None:
        out_dir = paths.stage(run_dir, paths.HWPX)  # 05-hwpx, flat
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{chapter_id}.hwpx")
    hwpx_gen._write_hwpx(out_path, members, blobs)

    # 무결성 확인
    with zipfile.ZipFile(out_path) as z:
        assert z.testzip() is None
        for n in z.namelist():
            if n.endswith(".xml") or n.endswith(".hpf"):
                etree.fromstring(z.read(n))
    print(f"[build] {chapter_id} | src={src_stage} | figures={fig_i} → {out_path}")
    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cid = sys.argv[1]
    run = sys.argv[sys.argv.index("--run") + 1] if "--run" in sys.argv else None
    book = sys.argv[sys.argv.index("--book") + 1] if "--book" in sys.argv else None
    build(cid, run=run, book=book)

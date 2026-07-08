"""신규 도표(PNG) 이미지를 HWPX에 삽입 — 문서공방에 없던 net-new 기능.

HWPX 이미지 삽입 3요소:
  1) BinData/imageN.png 를 zip 에 추가
  2) Contents/content.hpf 의 <opf:manifest> 에 <opf:item ... isEmbeded="1"> 등록
  3) 본문 섹션에 <hp:p><hp:run><hp:pic binaryItemIDRef="imageN">…</hp:pic> 삽입

크기 단위: HWPUNIT (1px ≈ 7200/96 = 75). 본문 폭(약 45354)에 맞춰 축소한다.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HC = "http://www.hancom.co.kr/hwpml/2011/core"

HWPUNIT_PER_PX = 75          # 96 DPI 기준
BODY_WIDTH_HWPUNIT = 42000   # A4 본문 폭 안쪽(여백 확보 — 우측 잘림 방지)

_PIC_ID_SEQ = [1200000000]
_INST_SEQ = [40000000]


def _next(seq) -> int:
    seq[0] += 1
    return seq[0]


def register_image(blobs: Dict[str, bytes], content_hpf_name: str,
                   png_bytes: bytes, item_id: str) -> None:
    """BinData 추가 + content.hpf manifest 에 item 등록."""
    from lxml import etree

    blobs[f"BinData/{item_id}.png"] = png_bytes

    hpf = blobs.get(content_hpf_name)
    if hpf is None:
        raise ValueError("content.hpf 없음")
    root = etree.fromstring(hpf)
    OPF = "http://www.idpf.org/2007/opf/"
    manifest = root.find(f"{{{OPF}}}manifest")
    if manifest is None:
        raise ValueError("content.hpf manifest 없음")
    # 중복 방지
    for it in manifest.findall(f"{{{OPF}}}item"):
        if it.get("id") == item_id:
            break
    else:
        item = etree.SubElement(manifest, f"{{{OPF}}}item")
        item.set("id", item_id)
        item.set("href", f"BinData/{item_id}.png")
        item.set("media-type", "image/png")
        item.set("isEmbeded", "1")
    blobs[content_hpf_name] = etree.tostring(
        root, xml_declaration=True, encoding="UTF-8", standalone=True)


def fit_size(px_w: int, px_h: int,
             max_w: int = BODY_WIDTH_HWPUNIT) -> Tuple[int, int]:
    """픽셀 크기 → 본문 폭에 맞춘 HWPUNIT 표시 크기(비율 유지)."""
    w = px_w * HWPUNIT_PER_PX
    h = px_h * HWPUNIT_PER_PX
    if w > max_w:
        h = int(h * max_w / w)
        w = max_w
    return w, h


def make_pic_paragraph(item_id: str, px_w: int, px_h: int,
                       style: Optional[Dict[str, str]] = None,
                       max_w: int = BODY_WIDTH_HWPUNIT):
    """<hp:pic> 를 담은 가운데 정렬 <hp:p> 반환. treatAsChar=1(인라인)."""
    from lxml import etree

    w, h = fit_size(px_w, px_h, max_w)
    pid = str(_next(_PIC_ID_SEQ))
    inst = str(_next(_INST_SEQ))

    p = etree.Element(f"{{{HP}}}p")
    p.set("paraPrIDRef", (style or {}).get("paraPrIDRef", "0"))
    p.set("styleIDRef", (style or {}).get("styleId", "0"))
    run = etree.SubElement(p, f"{{{HP}}}run")
    run.set("charPrIDRef", (style or {}).get("charPrIDRef", "0"))

    pic = etree.SubElement(run, f"{{{HP}}}pic")
    pic.set("id", pid)
    pic.set("zOrder", "0")
    pic.set("numberingType", "PICTURE")
    pic.set("textWrap", "TOP_AND_BOTTOM")
    pic.set("textFlow", "BOTH_SIDES")
    pic.set("lock", "0")
    pic.set("dropcapstyle", "None")
    pic.set("href", "")
    pic.set("groupLevel", "0")
    pic.set("instid", inst)
    pic.set("reverse", "0")

    etree.SubElement(pic, f"{{{HP}}}offset", {"x": "0", "y": "0"})
    etree.SubElement(pic, f"{{{HP}}}orgSz", {"width": str(w), "height": str(h)})
    etree.SubElement(pic, f"{{{HP}}}curSz", {"width": str(w), "height": str(h)})
    etree.SubElement(pic, f"{{{HP}}}flip", {"horizontal": "0", "vertical": "0"})
    etree.SubElement(pic, f"{{{HP}}}rotationInfo",
                     {"angle": "0", "centerX": str(w // 2), "centerY": str(h // 2),
                      "rotateimage": "1"})
    ri = etree.SubElement(pic, f"{{{HP}}}renderingInfo")
    etree.SubElement(ri, f"{{{HC}}}transMatrix",
                     {"e1": "1", "e2": "0", "e3": "0", "e4": "0", "e5": "1", "e6": "0"})
    etree.SubElement(ri, f"{{{HC}}}scaMatrix",
                     {"e1": "1", "e2": "0", "e3": "0", "e4": "0", "e5": "1", "e6": "0"})
    etree.SubElement(ri, f"{{{HC}}}rotMatrix",
                     {"e1": "1", "e2": "0", "e3": "0", "e4": "0", "e5": "1", "e6": "0"})

    rect = etree.SubElement(pic, f"{{{HP}}}imgRect")
    etree.SubElement(rect, f"{{{HC}}}pt0", {"x": "0", "y": "0"})
    etree.SubElement(rect, f"{{{HC}}}pt1", {"x": str(w), "y": "0"})
    etree.SubElement(rect, f"{{{HC}}}pt2", {"x": str(w), "y": str(h)})
    etree.SubElement(rect, f"{{{HC}}}pt3", {"x": "0", "y": str(h)})
    etree.SubElement(pic, f"{{{HP}}}imgClip",
                     {"left": "0", "right": str(w), "top": "0", "bottom": str(h)})
    etree.SubElement(pic, f"{{{HP}}}inMargin",
                     {"left": "0", "right": "0", "top": "0", "bottom": "0"})
    etree.SubElement(pic, f"{{{HC}}}img",
                     {"binaryItemIDRef": item_id, "bright": "0", "contrast": "0",
                      "effect": "REAL_PIC", "alpha": "0"})
    etree.SubElement(pic, f"{{{HP}}}effects")
    etree.SubElement(pic, f"{{{HP}}}sz",
                     {"width": str(w), "widthRelTo": "ABSOLUTE",
                      "height": str(h), "heightRelTo": "ABSOLUTE", "protect": "0"})
    etree.SubElement(pic, f"{{{HP}}}pos",
                     {"treatAsChar": "1", "affectLSpacing": "0", "flowWithText": "1",
                      "allowOverlap": "0", "holdAnchorAndSO": "0", "vertRelTo": "PARA",
                      "horzRelTo": "PARA", "vertAlign": "TOP", "horzAlign": "CENTER",
                      "vertOffset": "0", "horzOffset": "0"})
    etree.SubElement(pic, f"{{{HP}}}outMargin",
                     {"left": "0", "right": "0", "top": "0", "bottom": "0"})
    return p


def png_size(png_bytes: bytes) -> Tuple[int, int]:
    """PNG 픽셀 크기 (PIL 사용)."""
    import io as _io
    from PIL import Image
    with Image.open(_io.BytesIO(png_bytes)) as im:
        return im.width, im.height

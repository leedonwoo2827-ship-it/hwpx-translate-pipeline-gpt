"""양식(템플릿) 생성기: 원본 회사양식(base)에 우리 스타일 보정을 적용해
assets/hwpx_template.hwpx 를 만든다. 이 결과물이 '양식 정본'이며, 사용자가
한컴에서 직접 더 손봐도 된다(그 경우 이 스크립트를 다시 돌릴 필요 없음).

적용 보정:
  - 본문(제목 paraPr) 첫 줄 들여쓰기(intent) = 한 글자 폭
사용:
    python pipeline/make_template.py
"""
from __future__ import annotations

import io
import os
import sys
import zipfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from lxml import etree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
BASE = os.path.join(ASSETS, "hwpx_template.base.hwpx")   # 원본 회사양식(보존)
OUT = os.path.join(ASSETS, "hwpx_template.hwpx")          # 양식 정본

HH = "http://www.hancom.co.kr/hwpml/2011/head"
HC = "http://www.hancom.co.kr/hwpml/2011/core"

# 스타일 보정 파라미터
FIRST_LINE_INDENT = 1000          # 본문 첫 줄 들여쓰기(HWPUNIT, ≈한 글자)
INDENT_STYLES = ("본문",)          # 들여쓰기를 적용할 명명 스타일

# 서체(KoPub World, 한컴 face명). 본문=바탕체(명조), 제목=돋움체(고딕).
BODY_FACE = "KoPubWorld바탕체 Medium"
HEAD_FACE = "KoPubWorld돋움체 Medium"
BODY_STYLES = ("바탕글", "본문", "인용", "동그라미", "마이너스", "코드", "표본문")
HEAD_STYLES = ("제목", "제목 1", "제목 2", "제목 3", "강조", "표제목")
_LANGS = ("hangul", "latin", "hanja", "japanese", "other", "symbol", "user")
_LANG_TAG = {"hangul": "HANGUL", "latin": "LATIN", "hanja": "HANJA", "japanese": "JAPANESE",
             "other": "OTHER", "symbol": "SYMBOL", "user": "USER"}


def _style_paraprefs(root, names):
    ids = set()
    for st in root.iter(f"{{{HH}}}style"):
        if (st.get("name") or "").strip() in names:
            ids.add(st.get("paraPrIDRef"))
    return ids


def _charpr_ids(root, names):
    """명명 스타일 → 그 스타일이 참조하는 charPrIDRef 집합."""
    ids = set()
    for st in root.iter(f"{{{HH}}}style"):
        if (st.get("name") or "").strip() in names:
            ids.add(st.get("charPrIDRef"))
    return ids


def _fontref_pairs(root, charpr_ids):
    """charPr 집합 → 참조하는 (lang, fontIndex) 쌍 집합."""
    pairs = set()
    for cp in root.iter(f"{{{HH}}}charPr"):
        if cp.get("id") in charpr_ids:
            fr = cp.find(f"{{{HH}}}fontRef")
            if fr is None:
                continue
            for lang in _LANGS:
                idx = fr.get(lang)
                if idx is not None:
                    pairs.add((lang, idx))
    return pairs


def _set_faces(root, pairs, face):
    """(lang, fontIndex) 쌍에 해당하는 fontface 항목의 face 를 교체."""
    changed = 0
    fftag = f"{{{HH}}}fontface"
    ftag = f"{{{HH}}}font"
    by_lang = {}
    for ff in root.iter(fftag):
        by_lang.setdefault(ff.get("lang"), []).append(ff)
    for lang, idx in pairs:
        tag = _LANG_TAG.get(lang)
        for ff in by_lang.get(tag, []):
            for fnt in ff.findall(ftag):
                if fnt.get("id") == idx:
                    fnt.set("face", face)
                    # type/isEmbedded 등은 유지. substFont 있으면 동일 face 로.
                    changed += 1
    return changed


def apply_all(header_bytes: bytes) -> bytes:
    root = etree.fromstring(header_bytes)

    # 1) 본문 첫 줄 들여쓰기
    target = _style_paraprefs(root, set(INDENT_STYLES))
    for pp in root.iter(f"{{{HH}}}paraPr"):
        if pp.get("id") in target:
            margin = pp.find(f"{{{HH}}}margin")
            if margin is None:
                continue
            intent = margin.find(f"{{{HC}}}intent")
            if intent is None:
                intent = etree.SubElement(margin, f"{{{HC}}}intent")
            intent.set("value", str(FIRST_LINE_INDENT))
            intent.set("unit", "HWPUNIT")
            print(f"  본문 paraPr id={pp.get('id')} intent → {FIRST_LINE_INDENT}")

    # 2) 서체: 본문류→바탕체, 제목류→돋움체 (body 우선, head는 body와 겹치지 않는 인덱스만)
    body_pairs = _fontref_pairs(root, _charpr_ids(root, set(BODY_STYLES)))
    head_pairs = _fontref_pairs(root, _charpr_ids(root, set(HEAD_STYLES))) - body_pairs
    nb = _set_faces(root, body_pairs, BODY_FACE)
    nh = _set_faces(root, head_pairs, HEAD_FACE)
    print(f"  서체: 본문류 face {nb}건 → {BODY_FACE}")
    print(f"  서체: 제목류 face {nh}건 → {HEAD_FACE}")

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def main():
    if not os.path.exists(BASE):
        # 최초 실행: 현재 정본을 원본으로 백업
        if os.path.exists(OUT):
            import shutil
            shutil.copy(OUT, BASE)
            print(f"원본 회사양식 백업 생성: {BASE}")
        else:
            raise FileNotFoundError("base/정본 템플릿이 모두 없음")

    src = zipfile.ZipFile(BASE)
    members = src.infolist()
    blobs = {m.filename: src.read(m.filename) for m in members}
    src.close()

    blobs["Contents/header.xml"] = apply_all(blobs["Contents/header.xml"])

    order = ["mimetype"] + [m.filename for m in members if m.filename != "mimetype"]
    with zipfile.ZipFile(OUT, "w") as zf:
        for name in order:
            data = blobs[name]
            ct = zipfile.ZIP_STORED if name == "mimetype" else zipfile.ZIP_DEFLATED
            zf.writestr(name, data, compress_type=ct)
    print(f"양식 정본 생성: {OUT}")


if __name__ == "__main__":
    main()

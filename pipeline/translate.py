"""02-translate(완역) · 03-refine(윤문) 자동화 — ChatGPT(codex) 백엔드.

기존에 사람(Claude)이 SKILL.md 계약을 따라 손으로 집필하던 두 LLM 단계를,
OpenAI Codex CLI(`codex`, ChatGPT OAuth 할당량)로 자동화한다. API 키 불필요.

- 시스템 프롬프트 = skills/translate-ko/SKILL.md · skills/refine-ko/SKILL.md 본문(그대로).
- 입력/출력 계약(기존과 동일):
    translate: 01-extract/<장>/content.en.md            → 02-translate/<장>/content.ko.md
    refine   : EN md + 02-translate/<장>/content.ko.md   → 03-refine/<장>/content.ko.md
- 도표 라인 `![캡션](figures/fig-0N.png)` 은 경로/파일명 그대로 유지(build 가 BinData 삽입).
  산출물에서 도표 경로가 누락/변형되면 경고만 출력(빌드 시 자동 건너뜀).

사용(CLI):
    python pipeline/translate.py <chapter-id> [--run <런>] [--refine] [--model <name>]
"""
from __future__ import annotations

import io
import os
import re
import sys

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
from llm import codex_runner  # noqa: E402
from llm.errors import LLMError  # noqa: E402

SKILLS = os.path.join(ROOT, "skills")

# build.py 의 _IMG_LINE 과 동일 — 도표 라인 판별.
_IMG_LINE = re.compile(r"^\s*!\[(?P<cap>.*?)\]\((?P<path>[^)]+)\)\s*$")


def _read_skill(name: str) -> str:
    """skills/<name>/SKILL.md 본문을 시스템 프롬프트로 로드."""
    p = os.path.join(SKILLS, name, "SKILL.md")
    with open(p, encoding="utf-8") as f:
        return f.read()


def _fig_paths(md: str) -> list[str]:
    out = []
    for line in (md or "").replace("\r\n", "\n").split("\n"):
        m = _IMG_LINE.match(line)
        if m:
            out.append(m.group("path").strip())
    return out


def _unwrap_fence(text: str) -> str:
    """codex 가 결과 전체를 ```markdown ... ``` 로 감싼 경우만 벗겨낸다(내부 펜스는 보존)."""
    t = text.strip()
    if t.startswith("```"):
        lines = t.split("\n")
        if len(lines) >= 2 and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1]).strip()
    return text


def _check_figures(cid: str, en_md: str, out_md: str) -> None:
    """EN 도표 경로가 산출물에 보존됐는지 확인, 어긋나면 경고(중단하지 않음)."""
    src, got = set(_fig_paths(en_md)), set(_fig_paths(out_md))
    missing = src - got
    extra = got - src
    if missing:
        print(f"[translate] 경고 {cid}: 도표 링크 누락/변형 {sorted(missing)} "
              f"(build 시 해당 도표 누락됨)")
    if extra:
        print(f"[translate] 경고 {cid}: 원문에 없는 도표 링크 {sorted(extra)}")


def _write(run_dir: str, stage: str, cid: str, text: str) -> str:
    d = paths.stage(run_dir, stage, cid)
    os.makedirs(d, exist_ok=True)
    out = os.path.join(d, "content.ko.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    return out


def translate_chapter(cid: str, run: str | None = None, model: str | None = None,
                      book: str | None = None) -> str:
    """01-extract EN → 02-translate 완역(+내부용 분석). 한국어 md 반환."""
    run_dir = paths.resolve_run(run, book=book)
    en_path = paths.stage(run_dir, paths.EXTRACT, cid, "content.en.md")
    if not os.path.exists(en_path):
        raise FileNotFoundError(f"{cid}: 원문 없음 → {en_path}")
    en_md = open(en_path, encoding="utf-8").read()

    system = _read_skill("translate-ko")
    user = (f"다음 영문 원문을 위 지침대로 한국어로 완역하고, 장 말미에 분석(내부 검토용) "
            f"섹션을 덧붙여라. 마크다운 계약(헤딩/불릿/인용/도표 링크 원형 유지)을 엄격히 지켜라.\n\n"
            f"[원문 content.en.md]\n{en_md}")
    print(f"[translate] {cid} 번역 중… (model={model or codex_runner.get_model() or 'codex 자동'})")
    resp = codex_runner.client.chat(model, [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ])
    ko = _unwrap_fence(resp.text)
    _check_figures(cid, en_md, ko)
    out = _write(run_dir, paths.TRANSLATE, cid, ko)
    print(f"[translate] {cid} → {out} ({len(ko)}자)")
    return ko


def refine_chapter(cid: str, run: str | None = None, model: str | None = None,
                   book: str | None = None) -> str:
    """EN + 02 초벌 → 03-refine 윤문(단일 최선안). 없으면 먼저 번역. 한국어 md 반환."""
    run_dir = paths.resolve_run(run, book=book)
    en_path = paths.stage(run_dir, paths.EXTRACT, cid, "content.en.md")
    en_md = open(en_path, encoding="utf-8").read() if os.path.exists(en_path) else ""

    draft_path = paths.stage(run_dir, paths.TRANSLATE, cid, "content.ko.md")
    if not os.path.exists(draft_path):
        print(f"[refine] {cid}: 초벌(02) 없음 → 먼저 번역")
        draft = translate_chapter(cid, run=run_dir, model=model)
    else:
        draft = open(draft_path, encoding="utf-8").read()

    system = _read_skill("refine-ko")
    user = ("아래 '초벌 번역'을 위 지침대로 자연스러운 한국어로 윤문하라(의미·구조·포맷·도표 링크 보존, "
            "단일 최선의 교정본만 출력). 대조용으로 영문 원문도 함께 제공한다.\n\n"
            f"[영문 원문 content.en.md]\n{en_md}\n\n"
            f"[초벌 번역 02-translate/content.ko.md]\n{draft}")
    print(f"[refine] {cid} 윤문 중… (model={model or codex_runner.get_model() or 'codex 자동'})")
    resp = codex_runner.client.chat(model, [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ])
    ko = _unwrap_fence(resp.text)
    if en_md:
        _check_figures(cid, en_md, ko)
    out = _write(run_dir, paths.REFINE, cid, ko)
    print(f"[refine] {cid} → {out} ({len(ko)}자)")
    return ko


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 1
    cid = argv[0]
    run = argv[argv.index("--run") + 1] if "--run" in argv else None
    book = argv[argv.index("--book") + 1] if "--book" in argv else None
    model = argv[argv.index("--model") + 1] if "--model" in argv else None
    do_refine = "--refine" in argv
    try:
        if do_refine:
            refine_chapter(cid, run=run, model=model, book=book)
        else:
            translate_chapter(cid, run=run, model=model, book=book)
    except LLMError as e:
        print(f"[오류] {type(e).__name__}: {e}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

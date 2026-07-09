"""영한 번역기 — 한국어 변환 파이프라인 CLI (자기완결).

출력 구조: output/<YYMMDDHHMM>-<라벨>/{01-extract 02-translate 03-refine 04-review 05-hwpx 06-book}
대부분 명령은 --run <런폴더> 지원(생략 시 최신 런). 스테이지 독립: md 파일부터 시작 가능.

    python run.py extract [chapter-id ...] [--run <런>]  # PDF → 01-extract (새 런 생성)
    python run.py translate <chapter-id> [--run] [--model]  # 01 EN → 02-translate (ChatGPT/codex)
    python run.py refine <chapter-id> [--run] [--model]     # EN+02 → 03-refine (ChatGPT/codex)
    python run.py viewer [--run <런>]                     # 리뷰 뷰어(연결상태·번역·초벌 vs 교정본 diff)
    python run.py build <chapter-id> [--run <런>]         # 04-review→03-refine→02 중 첫 md → 05-hwpx
    python run.py merge [--run <런>]                       # 05-hwpx/*.pdf → 06-book
    python run.py pdf-batch [--run <런>]                   # 한컴으로 05-hwpx 전체 → PDF
    python run.py pdf <hwpx> [out.pdf]                    # 한컴으로 단일 hwpx→PDF
    python run.py template                                # 회사양식 → 양식 정본(스타일·서체 보정)
    python run.py setup-fonts                             # KoPub World 설치

번역(02)·교정(03)은 OpenAI Codex CLI(`codex`, ChatGPT OAuth 할당량)로 자동화한다(API 키 불필요).
최초 1회 `codex login` 필요. 시스템 프롬프트 = skills/translate-ko·refine-ko/SKILL.md.
뷰어(GUI)에서 장별 [GPT 번역]/[GPT 윤문] 버튼으로도 실행할 수 있다.
"""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PIPE = os.path.join(HERE, "pipeline")
sys.path.insert(0, PIPE)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    rest = sys.argv[2:]
    if cmd == "extract":
        sys.argv = [os.path.join(PIPE, "extract.py")] + rest
        runpy.run_path(os.path.join(PIPE, "extract.py"), run_name="__main__")
    elif cmd == "build":
        sys.argv = [os.path.join(PIPE, "build.py")] + rest
        runpy.run_path(os.path.join(PIPE, "build.py"), run_name="__main__")
    elif cmd in ("translate", "refine"):
        args = rest + (["--refine"] if cmd == "refine" else [])
        sys.argv = [os.path.join(PIPE, "translate.py")] + args
        runpy.run_path(os.path.join(PIPE, "translate.py"), run_name="__main__")
    elif cmd == "template":
        runpy.run_path(os.path.join(PIPE, "make_template.py"), run_name="__main__")
    elif cmd == "pdf":
        sys.argv = [os.path.join(PIPE, "hancom_pdf.py")] + rest
        runpy.run_path(os.path.join(PIPE, "hancom_pdf.py"), run_name="__main__")
    elif cmd == "pdf-batch":
        sys.argv = [os.path.join(PIPE, "hancom_pdf_batch.py")] + rest
        runpy.run_path(os.path.join(PIPE, "hancom_pdf_batch.py"), run_name="__main__")
    elif cmd == "setup-fonts":
        sys.argv = [os.path.join(PIPE, "setup_fonts.py")] + rest
        runpy.run_path(os.path.join(PIPE, "setup_fonts.py"), run_name="__main__")
    elif cmd == "merge":
        sys.argv = [os.path.join(PIPE, "merge_pdf.py")] + rest
        runpy.run_path(os.path.join(PIPE, "merge_pdf.py"), run_name="__main__")
    elif cmd == "viewer":
        runpy.run_path(os.path.join(HERE, "viewer", "server.py"), run_name="__main__")
    else:
        print(f"알 수 없는 명령: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()

"""리뷰 뷰어 — 파이썬 표준 라이브러리만(빌드 스텝/프레임워크 無).

구조: output/<책>/<런=교지>/<스테이지>. 첫 화면에서 책·교지를 고른다.
좌: 영문 원문(01) 또는 임의 교지 / 우: 활성 교지(편집 가능, 저장 시 04-review).
버전(교지) 대비: 1교지 vs N교지 등 임의 두 교지 라인 diff.

    python viewer/server.py [--book <책명>] [--run <런폴더>]   # http://127.0.0.1:8770
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import paths  # noqa: E402
import translate  # noqa: E402  (LLM 자동 번역/윤문)
import extract  # noqa: E402  (PDF → 워크스페이스)
from llm import codex_auth, codex_runner  # noqa: E402
from llm.errors import (  # noqa: E402
    LLMNotInstalled, LLMNotAuthenticated, LLMQuotaExceeded, LLMError,
)

ASSTEST = os.path.join(ROOT, "_asstest")  # 업로드 PDF 저장 위치

PORT = 8770
_ARG_RUN = None
_ARG_BOOK = None


def _book(book=None):
    return book or _ARG_BOOK or paths.latest_book()


def _run_dir(run=None, book=None):
    """활성 런 경로. 워크스페이스(런)가 하나도 없으면 None(뷰어가 빈 화면으로 뜸)."""
    try:
        return paths.resolve_run(run or _ARG_RUN, book=_book(book))
    except SystemExit:
        return None


def _read(path):
    return open(path, encoding="utf-8").read() if os.path.exists(path) else ""


def _chapters(run_dir):
    if not run_dir:
        return []
    out = set()
    for st in (paths.TRANSLATE, paths.REFINE, paths.REVIEW, paths.EXTRACT):
        d = os.path.join(run_dir, st)
        if os.path.isdir(d):
            out.update(c for c in os.listdir(d) if os.path.isdir(os.path.join(d, c)))
    return sorted(out)


def _run_list(book=None):
    """책 안의 런(교지) 목록: 이름(날짜) 오름차순. 1교지, 2교지, … 순서."""
    return paths.runs(_book(book))


def _run_versions(book=None):
    """교지 라벨 부여: [{run, label:'N교지', name}]."""
    return [{"run": r, "label": f"{i + 1}교지", "name": r} for i, r in enumerate(_run_list(book))]


def _repr_md(run_name, cid, book=None):
    """해당 책·런(교지)에서 챕터의 대표 md(04-review→03-refine→02-translate)."""
    rd = os.path.join(paths.book_dir(_book(book)), run_name)
    p, _ = paths.source_md(rd, cid)
    return _read(p) if p else ""


def _chapter_data(run_dir, cid):
    if not run_dir:
        return {"id": cid, "en": "", "latest": "", "src": "-", "active_run": "", "figures": []}
    en = _read(paths.stage(run_dir, paths.EXTRACT, cid, "content.en.md"))
    p, src = paths.source_md(run_dir, cid)
    latest = _read(p) if p else ""
    meta = {}
    mp = paths.stage(run_dir, paths.EXTRACT, cid, "meta.json")
    if os.path.exists(mp):
        meta = json.load(open(mp, encoding="utf-8"))
    return {
        "id": cid, "en": en, "latest": latest, "src": src or "-",
        "active_run": os.path.basename(run_dir),
        "figures": [f["file"] for f in meta.get("figures", [])],
    }


_STAGE_LABEL = {
    paths.REVIEW: "검토본(04)",
    paths.REFINE: "윤문(03)",
    paths.TRANSLATE: "초벌(02)",
}


def _stage_label(run_dir, cid):
    """장의 현재 활성 단계를 사람이 읽는 라벨로. 04→03→02 중 첫 존재, 없으면 원문(01) 여부."""
    _, src = paths.source_md(run_dir, cid)
    if src:
        return _STAGE_LABEL.get(src, src)
    if os.path.exists(paths.stage(run_dir, paths.EXTRACT, cid, "content.en.md")):
        return "원문(01) · 번역 전"
    return "-"


def _index(run_dir, book=None):
    """첫 화면용 장 목록: id/제목/저자/활성단계 + 이 장을 가진 교지(런) 라벨."""
    rows = []
    vers = _run_versions(book)
    for cid in _chapters(run_dir):
        meta = {}
        mp = paths.stage(run_dir, paths.EXTRACT, cid, "meta.json")
        if os.path.exists(mp):
            meta = json.load(open(mp, encoding="utf-8"))
        present = [v["label"] for v in vers if _repr_md(v["run"], cid, book)]
        rows.append({"id": cid, "title": meta.get("title", cid),
                     "author": meta.get("author", ""), "src": _stage_label(run_dir, cid),
                     "proofs": present})
    return rows


def _save_reviewed(run_dir, cid, text):
    """활성 런의 04-review 에 확정본 저장(=그 교지의 대표 md)."""
    d = paths.stage(run_dir, paths.REVIEW, cid)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "content.reviewed.md"), "w", encoding="utf-8") as f:
        f.write(text)
    return os.path.basename(run_dir)


# ── LLM(codex) 연동 ──────────────────────────────────────────────────────────
def _llm_status():
    """연결 상태 + 선택 모델 병합(UI 칩/패널용)."""
    s = codex_auth.status()
    s["selected_model"] = codex_runner.get_model()
    return s


_ERR_KIND = {
    LLMNotInstalled: "not_installed",
    LLMNotAuthenticated: "not_authenticated",
    LLMQuotaExceeded: "quota",
}


def _llm_error_kind(e: Exception) -> str:
    for cls, kind in _ERR_KIND.items():
        if isinstance(e, cls):
            return kind
    return "error"


def _launch_terminal(cmd: list[str]) -> bool:
    """새 OS 터미널에서 명령 실행(브라우저 OAuth 로그인용). 성공하면 True."""
    try:
        sysname = platform.system()
        if sysname == "Windows":
            # start "" cmd /k "<codex> login"  — 새 콘솔 창에서 실행 후 창 유지.
            quoted = " ".join(f'"{c}"' if " " in c else c for c in cmd)
            subprocess.Popen(f'start "codex login" cmd /k {quoted}', shell=True)
            return True
        if sysname == "Darwin":
            script = 'tell application "Terminal" to do script "%s"' % " ".join(cmd)
            subprocess.Popen(["osascript", "-e", script])
            return True
        # Linux: 흔한 터미널 에뮬레이터 순차 시도.
        for term in ("x-terminal-emulator", "gnome-terminal", "konsole", "xterm"):
            try:
                subprocess.Popen([term, "-e", *cmd])
                return True
            except FileNotFoundError:
                continue
        return False
    except Exception:
        return False


def _open_folder(folder: str) -> None:
    """탐색기/파인더로 폴더 열기(빌드 후 결과 확인용). 실패해도 무시."""
    try:
        folder = os.path.abspath(folder)
        sysname = platform.system()
        if sysname == "Windows":
            os.startfile(folder)  # noqa: S606
        elif sysname == "Darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])
    except Exception:
        pass


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass

    def _q(self, p):
        return urllib.parse.parse_qs(p.query)

    def do_GET(self):
        p = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(p.path)
        q = self._q(p)
        run = q.get("run", [None])[0]
        book = q.get("book", [None])[0]
        if path in ("/", "/index.html"):
            return self._send(200, _read(os.path.join(HERE, "index.html")), "text/html; charset=utf-8")
        if path == "/app.js":
            return self._send(200, _read(os.path.join(HERE, "app.js")), "application/javascript; charset=utf-8")
        if path == "/style.css":
            return self._send(200, _read(os.path.join(HERE, "style.css")), "text/css; charset=utf-8")
        if path == "/api/llm/status":
            return self._send(200, _llm_status())
        if path == "/api/llm/models":
            force = q.get("force", ["0"])[0] in ("1", "true")
            return self._send(200, {"models": codex_runner.list_models(force=force),
                                    "selected": codex_runner.get_model()})
        if path == "/api/books":
            return self._send(200, {"books": paths.books(), "active": _book(book)})
        if path == "/api/runs":
            rd = _run_dir(run, book)
            return self._send(200, {"versions": _run_versions(book),
                                    "active": os.path.basename(rd) if rd else "",
                                    "book": _book(book)})
        if path == "/api/chapters":
            return self._send(200, _chapters(_run_dir(run, book)))
        if path == "/api/index":
            return self._send(200, _index(_run_dir(run, book), book))
        if path.startswith("/api/chapter/"):
            return self._send(200, _chapter_data(_run_dir(run, book), path[len("/api/chapter/"):]))
        if path.startswith("/api/runtext/"):
            cid = path[len("/api/runtext/"):]
            rn = q.get("v", [""])[0]  # 교지 런 이름
            return self._send(200, {"run": rn, "text": _repr_md(rn, cid, book)})
        if path.startswith("/figures/"):
            rd = _run_dir(run, book)
            if not rd:
                return self._send(404, {"error": "no workspace"})
            cid, _, fname = path[len("/figures/"):].partition("/")
            fpath = paths.stage(rd, paths.EXTRACT, cid, "figures", fname)
            if os.path.exists(fpath):
                return self._send(200, open(fpath, "rb").read(), "image/png")
            return self._send(404, {"error": "no figure"})
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        p = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(p.path)
        q = self._q(p)
        run = q.get("run", [None])[0]
        book = q.get("book", [None])[0]
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        try:
            data = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            data = {}
        run_dir = _run_dir(run, book)

        # ── PDF 업로드 → 새 워크스페이스(책) 생성 (첫 화면 드롭존) ──
        # 본문(raw)=PDF 바이트, ?title=<책제목>. PDF 전체를 1개 장으로 추출.
        if path == "/api/workspace":
            title = (q.get("title", [""])[0] or "").strip()
            if not title:
                return self._send(200, {"ok": False, "error": "제목을 입력하세요."})
            if not raw:
                return self._send(200, {"ok": False, "error": "PDF 파일이 비어 있습니다."})
            try:
                os.makedirs(ASSTEST, exist_ok=True)
                pdf_path = os.path.join(ASSTEST, extract._slugify(title) + ".pdf")
                with open(pdf_path, "wb") as f:
                    f.write(raw)
                rd, cid = extract.extract_whole(pdf_path, book=title)
                return self._send(200, {"ok": True, "book": title,
                                        "run": os.path.basename(rd), "cid": cid})
            except Exception as e:  # noqa: BLE001
                return self._send(200, {"ok": False, "error": str(e)})

        if path.startswith("/api/save/"):
            cid = path[len("/api/save/"):]
            n = _save_reviewed(run_dir, cid, data.get("ko", ""))
            return self._send(200, {"ok": True, "run": n})

        if path.startswith("/api/build/"):
            # hwpx 만 생성(한글에서 열어 확인용). PDF 는 별도 [PDF 빌드](/api/pdf) 단계로.
            cid = path[len("/api/build/"):]
            _save_reviewed(run_dir, cid, data.get("ko", ""))
            try:
                import build
                out = build.build(cid, run=run_dir)  # include_cover 기본(True): 유효한 hwpx
                return self._send(200, {"ok": True, "hwpx": out})
            except Exception as e:  # noqa: BLE001
                return self._send(200, {"ok": False, "error": str(e)})

        if path.startswith("/api/pdf/"):
            # 이미 빌드된 hwpx → 한컴으로 PDF. 성공 시 폴더 열기.
            cid = path[len("/api/pdf/"):]
            hwpx_path = paths.stage(run_dir, paths.HWPX, f"{cid}.hwpx")
            if not os.path.exists(hwpx_path):
                return self._send(200, {"ok": False, "error": "먼저 [hwpx 빌드]를 하세요."})
            try:
                import hancom_pdf
                pdf = hancom_pdf.to_pdf(hwpx_path)
                _open_folder(os.path.dirname(pdf))
                return self._send(200, {"ok": True, "pdf": pdf})
            except Exception as e:  # noqa: BLE001
                return self._send(200, {"ok": False, "error": str(e)})

        # ── LLM(codex) 관리 ──
        if path == "/api/llm/model":
            codex_runner.set_model(data.get("model", ""))
            return self._send(200, {"ok": True, "selected": codex_runner.get_model()})
        if path == "/api/llm/login":
            ok = _launch_terminal(codex_auth.login_terminal_cmd())
            return self._send(200, {"ok": ok,
                                    "hint": "새 터미널 창에서 codex 로그인(브라우저)이 진행됩니다. "
                                            "완료 후 '새로고침'을 누르세요." if ok else
                                            "터미널을 열 수 없습니다. 수동으로 `codex login` 을 실행하세요."})
        if path == "/api/llm/logout":
            return self._send(200, {"ok": codex_auth.logout()})

        # ── GPT 자동 번역/윤문 (장 단위, 수 분 소요 가능) ──
        if path.startswith("/api/translate/") or path.startswith("/api/refine/"):
            is_refine = path.startswith("/api/refine/")
            cid = path[len("/api/refine/" if is_refine else "/api/translate/"):]
            model = data.get("model") or None
            try:
                fn = translate.refine_chapter if is_refine else translate.translate_chapter
                ko = fn(cid, run=run_dir, model=model)
                stage = paths.REFINE if is_refine else paths.TRANSLATE
                return self._send(200, {"ok": True, "ko": ko, "stage": stage})
            except LLMError as e:
                return self._send(200, {"ok": False, "kind": _llm_error_kind(e), "error": str(e)})
            except Exception as e:  # noqa: BLE001
                return self._send(200, {"ok": False, "kind": "error", "error": str(e)})

        return self._send(404, {"error": "not found"})


def main():
    global _ARG_RUN, _ARG_BOOK
    if "--run" in sys.argv:
        _ARG_RUN = sys.argv[sys.argv.index("--run") + 1]
    if "--book" in sys.argv:
        _ARG_BOOK = sys.argv[sys.argv.index("--book") + 1]
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    try:
        rd = _run_dir()
        where = os.path.basename(rd) if rd else "no workspace yet - drop a PDF on the first page"
        print(f"viewer: http://127.0.0.1:{PORT}  ({where}, Ctrl+C to quit)", flush=True)
    except Exception:
        pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()

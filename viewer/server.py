"""리뷰 뷰어 — 파이썬 표준 라이브러리만(빌드 스텝/프레임워크 無).

구조: output/<책>/<런=교지>/<스테이지>. 첫 화면에서 책·교지를 고른다.
좌: 영문 원문(01) 또는 임의 교지 / 우: 활성 교지(편집 가능, 저장 시 04-review).
버전(교지) 대비: 1교지 vs N교지 등 임의 두 교지 라인 diff.

    python viewer/server.py [--book <책명>] [--run <런폴더>]   # http://127.0.0.1:8770
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import paths  # noqa: E402

PORT = 8770
_ARG_RUN = None
_ARG_BOOK = None


def _book(book=None):
    return book or _ARG_BOOK or paths.latest_book()


def _run_dir(run=None, book=None):
    return paths.resolve_run(run or _ARG_RUN, book=_book(book))


def _read(path):
    return open(path, encoding="utf-8").read() if os.path.exists(path) else ""


def _chapters(run_dir):
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


def _index(run_dir, book=None):
    """첫 화면용 장 목록: id/제목/저자/활성단계 + 이 장을 가진 교지(런) 라벨."""
    rows = []
    vers = _run_versions(book)
    for cid in _chapters(run_dir):
        meta = {}
        mp = paths.stage(run_dir, paths.EXTRACT, cid, "meta.json")
        if os.path.exists(mp):
            meta = json.load(open(mp, encoding="utf-8"))
        _, src = paths.source_md(run_dir, cid)
        present = [v["label"] for v in vers if _repr_md(v["run"], cid, book)]
        rows.append({"id": cid, "title": meta.get("title", cid),
                     "author": meta.get("author", ""), "src": src or "-",
                     "proofs": present})
    return rows


def _save_reviewed(run_dir, cid, text):
    """활성 런의 04-review 에 확정본 저장(=그 교지의 대표 md)."""
    d = paths.stage(run_dir, paths.REVIEW, cid)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "content.reviewed.md"), "w", encoding="utf-8") as f:
        f.write(text)
    return os.path.basename(run_dir)


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
        if path == "/api/books":
            return self._send(200, {"books": paths.books(), "active": _book(book)})
        if path == "/api/runs":
            return self._send(200, {"versions": _run_versions(book),
                                    "active": os.path.basename(_run_dir(run, book)),
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
            cid, _, fname = path[len("/figures/"):].partition("/")
            fpath = paths.stage(_run_dir(run, book), paths.EXTRACT, cid, "figures", fname)
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

        if path.startswith("/api/save/"):
            cid = path[len("/api/save/"):]
            n = _save_reviewed(run_dir, cid, data.get("ko", ""))
            return self._send(200, {"ok": True, "run": n})

        if path.startswith("/api/build/"):
            cid = path[len("/api/build/"):]
            _save_reviewed(run_dir, cid, data.get("ko", ""))
            try:
                import build
                out = build.build(cid, run=run_dir)
                return self._send(200, {"ok": True, "hwpx": out})
            except Exception as e:  # noqa: BLE001
                return self._send(200, {"ok": False, "error": str(e)})

        return self._send(404, {"error": "not found"})


def main():
    global _ARG_RUN, _ARG_BOOK
    if "--run" in sys.argv:
        _ARG_RUN = sys.argv[sys.argv.index("--run") + 1]
    if "--book" in sys.argv:
        _ARG_BOOK = sys.argv[sys.argv.index("--book") + 1]
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"리뷰 뷰어: http://127.0.0.1:{PORT}  "
          f"(책: {_book()}, 런: {os.path.basename(_run_dir())}, Ctrl+C 종료)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()

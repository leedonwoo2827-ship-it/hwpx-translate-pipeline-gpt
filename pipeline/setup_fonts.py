"""KoPub World 서체 설치(초기 셋업). 사용자 폰트 폴더에 설치(관리자/root 불필요).

    python pipeline/setup_fonts.py            # KoPub World TTF 내려받아 설치
    python pipeline/setup_fonts.py --zip <경로>  # 수동 내려받은 zip 사용
    python pipeline/setup_fonts.py --list     # 설치된 KoPub 계열 face 이름만 출력

플랫폼별 사용자 폰트 폴더:
- Windows: %LOCALAPPDATA%\\Microsoft\\Windows\\Fonts (+ HKCU 레지스트리 등록)
- macOS:   ~/Library/Fonts
- Linux:   ~/.local/share/fonts (+ fc-cache 갱신)

폰트 TTF는 리포에 커밋하지 않는다(라이선스상 재배포 가능하나 저장소는 코드만).
"""
from __future__ import annotations

import io
import os
import sys
import zipfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WORLD_TTF_URL = "https://www.kopus.org/wp-content/uploads/2026/04/KOPUBWORLD_TTF_FONTS2026.zip"


def _user_fonts_dir() -> str:
    """플랫폼별 사용자 폰트 설치 경로."""
    if sys.platform.startswith("win"):
        return os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Fonts")
    return os.path.expanduser("~/.local/share/fonts")  # Linux/기타 (freedesktop)


USER_FONTS = _user_fonts_dir()


def _refresh_font_cache():
    """설치 후 OS 폰트 캐시 갱신(즉시 반영 시도)."""
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001D, 0, 0, 0, 1000)  # WM_FONTCHANGE
        except Exception:
            pass
    elif sys.platform == "darwin":
        pass  # macOS 는 ~/Library/Fonts 배치만으로 인식
    else:
        import shutil
        import subprocess
        if shutil.which("fc-cache"):
            try:
                subprocess.run(["fc-cache", "-f", USER_FONTS], check=False)
            except Exception:
                pass


def _family(ttf_bytes: bytes):
    """TTF에서 (family, full) 이름 추출."""
    import io as _io
    from PIL import ImageFont
    f = ImageFont.truetype(_io.BytesIO(ttf_bytes))
    try:
        return f.getname()  # (family, style)
    except Exception:
        return (None, None)


def _register(path: str, full_name: str):
    """HKCU 폰트 레지스트리 등록(Windows 사용자 단위). 다른 OS 는 배치만으로 인식하므로 no-op."""
    if not sys.platform.startswith("win"):
        return
    import winreg
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                         r"Software\Microsoft\Windows NT\CurrentVersion\Fonts",
                         0, winreg.KEY_SET_VALUE)
    winreg.SetValueEx(key, f"{full_name} (TrueType)", 0, winreg.REG_SZ, path)
    winreg.CloseKey(key)


def install(src_zip: str | None = None, url: str = WORLD_TTF_URL):
    os.makedirs(USER_FONTS, exist_ok=True)
    if src_zip:
        data = open(src_zip, "rb").read()
    else:
        import urllib.request
        print(f"다운로드: {url}")
        data = urllib.request.urlopen(url, timeout=120).read()
        print(f"  {len(data)} bytes")
    z = zipfile.ZipFile(io.BytesIO(data))
    families = set()
    n = 0
    for name in z.namelist():
        if not name.lower().endswith(".ttf"):
            continue
        ttf = z.read(name)
        fam, style = _family(ttf)
        base = os.path.basename(name)
        dest = os.path.join(USER_FONTS, base)
        with open(dest, "wb") as f:
            f.write(ttf)
        full = f"{fam} {style}".strip() if fam else os.path.splitext(base)[0]
        try:
            _register(dest, full)
        except Exception as e:  # noqa: BLE001
            print(f"  (레지스트리 등록 경고: {e})")
        if fam:
            families.add(f"{fam}  [{style}]")
        n += 1
    _refresh_font_cache()  # 플랫폼별 폰트 캐시 갱신
    print(f"설치 완료: {n}개 TTF → {USER_FONTS}")
    print("설치된 family 이름:")
    for fam in sorted(families):
        print("  -", fam)
    return sorted(families)


def list_installed():
    fams = set()
    if os.path.isdir(USER_FONTS):
        for f in os.listdir(USER_FONTS):
            if "kopub" in f.lower() and f.lower().endswith(".ttf"):
                fam, style = _family(open(os.path.join(USER_FONTS, f), "rb").read())
                if fam:
                    fams.add(f"{fam}  [{style}]")
    print("KoPub 계열 설치 face:")
    for fam in sorted(fams):
        print("  -", fam)
    return sorted(fams)


if __name__ == "__main__":
    if "--list" in sys.argv:
        list_installed()
    else:
        zp = sys.argv[sys.argv.index("--zip") + 1] if "--zip" in sys.argv else None
        url = sys.argv[sys.argv.index("--url") + 1] if "--url" in sys.argv else WORLD_TTF_URL
        install(zp, url)

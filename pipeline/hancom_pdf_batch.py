"""한컴을 한 번만 실행해 <런>/05-hwpx/*.hwpx 전체를 PDF로 일괄 변환.

    python pipeline/hancom_pdf_batch.py [--run <런폴더>]
"""
import glob
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paths  # noqa: E402


def main():
    if not sys.platform.startswith("win"):
        raise SystemExit(
            "hwpx→PDF 일괄 변환은 한컴오피스 자동화(win32com) 기반이라 Windows 전용입니다.\n"
            "  macOS/Linux: 05-hwpx/*.hwpx 를 한컴/뷰어에서 직접 PDF로 내보낸 뒤\n"
            "  'python run.py merge' 로 06-book 병합하세요.")
    import pythoncom
    import win32com.client as win32

    run = sys.argv[sys.argv.index("--run") + 1] if "--run" in sys.argv else None
    book = sys.argv[sys.argv.index("--book") + 1] if "--book" in sys.argv else None
    hwpx_dir = paths.stage(paths.resolve_run(run, book=book), paths.HWPX)
    hwpxs = sorted(glob.glob(os.path.join(hwpx_dir, "*.hwpx")))
    pythoncom.CoInitialize()
    hwp = win32.Dispatch("HWPFrame.HwpObject")
    try:
        hwp.RegisterModule("FilePathCheckDLL", "AutomationModule")
    except Exception:
        pass
    ok = 0
    for hx in hwpxs:
        pdf = os.path.splitext(hx)[0] + ".pdf"
        try:
            hwp.Open(os.path.abspath(hx), "HWPX", "")
            pset = hwp.HParameterSet.HFileOpenSave
            hwp.HAction.GetDefault("FileSaveAs_S", pset.HSet)
            pset.filename = os.path.abspath(pdf)
            pset.Format = "PDF"
            hwp.HAction.Execute("FileSaveAs_S", pset.HSet)
            hwp.HAction.Run("FileClose")
            print("OK", os.path.basename(pdf), os.path.getsize(pdf) if os.path.exists(pdf) else "MISSING")
            ok += 1
        except Exception as e:  # noqa: BLE001
            print("FAIL", os.path.basename(hx), e)
    try:
        hwp.Quit()
    except Exception:
        pass
    pythoncom.CoUninitialize()
    print(f"done: {ok}/{len(hwpxs)}")


if __name__ == "__main__":
    main()

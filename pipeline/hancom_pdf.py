"""검증 유틸: 한컴 COM으로 hwpx를 열어 PDF로 내보낸다(시각 확인용).

Windows + 한컴오피스 + pywin32 필요. LibreOffice 미설치 환경의 대체 검증 경로.
    python pipeline/hancom_pdf.py <input.hwpx> [output.pdf]
"""
import os
import sys


def to_pdf(hwpx_path: str, pdf_path: str | None = None) -> str:
    if not sys.platform.startswith("win"):
        raise SystemExit("hwpx→PDF(한컴 자동화)는 Windows 전용입니다. 다른 OS 는 한컴/뷰어에서 직접 내보내세요.")
    import pythoncom
    import win32com.client as win32

    hwpx_path = os.path.abspath(hwpx_path)
    if pdf_path is None:
        pdf_path = os.path.splitext(hwpx_path)[0] + ".pdf"
    pdf_path = os.path.abspath(pdf_path)

    pythoncom.CoInitialize()
    try:
        hwp = win32.Dispatch("HWPFrame.HwpObject")
        try:
            hwp.RegisterModule("FilePathCheckDLL", "AutomationModule")
        except Exception:
            pass
        hwp.Open(hwpx_path, "HWPX", "")
        # PDF 저장
        pset = hwp.HParameterSet.HFileOpenSave
        hwp.HAction.GetDefault("FileSaveAs_S", pset.HSet)
        pset.filename = pdf_path
        pset.Format = "PDF"
        ok = hwp.HAction.Execute("FileSaveAs_S", pset.HSet)
        try:
            hwp.Quit()
        except Exception:
            pass
        if not os.path.exists(pdf_path):
            raise RuntimeError(f"PDF 생성 실패 (Execute={ok})")
        return pdf_path
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    out = to_pdf(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print("PDF:", out, os.path.getsize(out), "bytes")

# -*- coding: utf-8 -*-
# Extract text from HWP file (OLE BodyText stream)
#
# 실행 시 참고 (Windows):
#   - PowerShell: 명령 연결 시 "&&" 대신 ";" 사용 (예: cd 프로젝트; py scripts/extract_hwp.py ...)
#   - "python"이 없으면 "py" (Python Launcher) 사용
#   - 한글 메시지 깨짐 시: 터미널에서 chcp 65001 후 실행하거나, 아래 stdout/stderr UTF-8 설정 적용됨
import argparse
import glob
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET


def find_latest_hwp(directory):
    """Find the most recently modified .hwp file in directory."""
    pattern = os.path.join(directory, "*.hwp")
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def normalize_text(text, max_chars=None):
    """공백 정규화 + 선택적 길이 제한.

    순수 함수: 연속 공백을 하나로 축소하고, max_chars가 지정되면 잘라낸다.
    """
    text = re.sub(r"\s+", " ", text).strip()
    if max_chars is not None:
        text = text[:max_chars]
    return text


def extract_with_pyhwpx(hwp_path, max_chars):
    """pyhwpx(아래아한글 오토메이션) 전용 추출.

    - pyhwpx는 win32 COM 기반으로, 실제 한/글 프로그램을 띄워 문서 내용을 가져옵니다.
    - 설치 및 전제 조건:
        uv add pyhwpx pywin32
      + Windows 환경, 그리고 한/글이 설치되어 있어야 합니다.
    - 장점:
      - 최신 HWP/HWPX 포맷에 대해 한/글 자체 엔진을 그대로 활용
      - 서식이 복잡하거나 보호/보안 옵션이 걸린 일부 문서도 더 잘 열릴 가능성
    - 텍스트 + 테이블을 모두 추출.
    - 실패 시 None을 반환.
    """
    try:
        from pyhwpx import Hwp
    except Exception:
        return None

    try:
        hwp = Hwp(visible=False, on_quit=True)
        hwp.open(hwp_path)

        # 1) 본문 텍스트 추출
        try:
            text = hwp.get_text_file()
        except TypeError:
            text = hwp.get_text_file(option="")

        if not isinstance(text, str) or not text.strip():
            return None

        parts = [text]

        # 2) 테이블 추출 (table_to_df)
        try:
            table_count = hwp.get_table_count()
            for i in range(table_count):
                try:
                    df = hwp.table_to_df(i)
                    parts.append(df.to_string())
                except Exception:
                    continue
        except Exception:
            pass

        combined = "\n".join(parts)
        return normalize_text(combined, max_chars)

    except Exception:
        return None


def extract_with_ole(hwp_path, max_chars):
    """OLE 기반 HWP 텍스트 추출.

    PrvText → BodyText/Section0 순으로 시도. 실패 시 None.
    """
    try:
        import olefile
    except ImportError:
        return None

    try:
        ole = olefile.OleFileIO(hwp_path)
    except Exception:
        return None

    try:
        for stream_name in [["PrvText"], ["BodyText", "Section0"]]:
            if not ole.exists(stream_name):
                continue
            raw = ole.openstream(stream_name).read()
            for enc in ("utf-16-le", "utf-16", "utf-8"):
                try:
                    text = raw.decode(enc, errors="replace")
                    if len(text.strip()) > 50:
                        return normalize_text(text, max_chars)
                except Exception:
                    continue
    finally:
        ole.close()

    return None


def extract_with_zip(hwp_path, max_chars):
    """ZIP(HWPX) 기반 텍스트 추출.

    HWPX는 주로 Contents/section*.xml 등에 본문이 있음.
    안전하게 전체 XML에서 텍스트 추출.
    """
    try:
        with zipfile.ZipFile(hwp_path, "r") as zf:
            chunks = []
            for name in zf.namelist():
                if not name.lower().endswith(".xml"):
                    continue
                try:
                    with zf.open(name) as f:
                        tree = ET.parse(f)
                except Exception:
                    continue
                root = tree.getroot()
                for elem in root.iter():
                    if elem.text and elem.text.strip():
                        chunks.append(elem.text.strip())
                    if elem.tail and elem.tail.strip():
                        chunks.append(elem.tail.strip())
            if chunks:
                text = " ".join(chunks)
                return normalize_text(text, max_chars)
    except Exception:
        pass

    return None


def extract_text(hwp_path, max_chars):
    """HWP/HWPX 파일에서 텍스트를 추출한다.

    3-tier 폴백: pyhwpx → OLE → ZIP(HWPX).
    """
    # 1) pyhwpx 우선 시도
    result = extract_with_pyhwpx(hwp_path, max_chars)
    if result:
        return result

    if not os.path.isfile(hwp_path):
        print(f"파일을 찾을 수 없습니다: {hwp_path}", file=sys.stderr)
        sys.exit(1)

    # 2) OLE 기반
    result = extract_with_ole(hwp_path, max_chars)
    if result:
        return result

    # 3) ZIP(HWPX) 기반
    result = extract_with_zip(hwp_path, max_chars)
    if result:
        return result

    print("지원되지 않는 HWP/HWPX 형식이거나 텍스트를 추출할 수 없습니다.", file=sys.stderr)
    return None


def resolve_hwp_path(args):
    """명령행 인자에서 HWP 경로를 해석한다.

    우선순위: --path-file > path 인자 > ~/Downloads 자동 탐색.
    경로를 찾지 못하면 None을 반환.
    """
    if args.path_file:
        path_file = os.path.abspath(args.path_file)
        if not os.path.isfile(path_file):
            return None
        with open(path_file, encoding="utf-8") as f:
            hwp_path = f.read().strip()
        return hwp_path if hwp_path else None

    if args.path and args.path.strip():
        return args.path.strip()

    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    return find_latest_hwp(downloads)


def _ensure_utf8_console():
    """Windows에서 한글 stderr/stdout 깨짐 방지: 터미널이 UTF-8이면 stdout/stderr를 UTF-8로 감쌈."""
    if sys.platform != "win32":
        return
    try:
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    _ensure_utf8_console()
    parser = argparse.ArgumentParser(
        description="HWP 파일에서 텍스트를 추출합니다.",
        epilog="한글 등 비ASCII 문자가 포함된 경로는 셸에서 깨지기 쉬우므로, 해당 경로를 UTF-8 파일에 한 줄로 저장한 뒤 --path-file을 사용하는 것을 권장합니다.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="HWP 파일 경로. 한글 등 비ASCII 경로는 셸 인코딩으로 깨질 수 있으므로 --path-file 사용 권장. 미지정 시에만 ~/Downloads 최신 .hwp 사용.",
    )
    parser.add_argument(
        "--path-file",
        metavar="FILE",
        default=None,
        help="경로가 한 줄만 적힌 UTF-8 텍스트 파일. 지정 시 path 인자 무시. 한글/비ASCII 경로 시 셸 깨짐 방지용으로 권장.",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=50000,
        help="출력 글자 수 제한 (default: 50000)",
    )
    parser.add_argument(
        "--output",
        default=os.path.join(os.path.dirname(__file__), "hwp_extracted.txt"),
        help="출력 파일 경로 (default: scripts/hwp_extracted.txt)",
    )
    args = parser.parse_args()

    hwp_path = resolve_hwp_path(args)

    if hwp_path is None:
        print("HWP 파일 경로를 찾을 수 없습니다.", file=sys.stderr)
        sys.exit(1)

    text = extract_text(hwp_path, args.max_chars)
    if text is None:
        print("텍스트 추출에 실패했습니다.", file=sys.stderr)
        sys.exit(1)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"OK: {args.output} ({len(text)}자)")


if __name__ == "__main__":
    main()

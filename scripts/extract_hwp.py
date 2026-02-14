# -*- coding: utf-8 -*-
# Extract text from HWP file (OLE BodyText stream)
#
# 실행 시 참고 (Windows):
#   - PowerShell: 명령 연결 시 "&&" 대신 ";" 사용 (예: cd 프로젝트; py scripts/extract_hwp.py ...)
#   - "python"이 없으면 "py" (Python Launcher) 사용
import argparse
import glob
import os
import re
import sys


def find_latest_hwp(directory):
    """Find the most recently modified .hwp file in directory."""
    pattern = os.path.join(directory, "*.hwp")
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def extract_text(hwp_path, max_chars):
    """Extract text from HWP file using olefile."""
    try:
        import olefile
    except ImportError:
        print("olefile가 설치되어 있지 않습니다. 설치: uv add olefile", file=sys.stderr)
        sys.exit(1)

    if not os.path.isfile(hwp_path):
        print(f"파일을 찾을 수 없습니다: {hwp_path}", file=sys.stderr)
        sys.exit(1)

    ole = olefile.OleFileIO(hwp_path)
    try:
        for stream_name in [["PrvText"], ["BodyText", "Section0"]]:
            if not ole.exists(stream_name):
                continue
            raw = ole.openstream(stream_name).read()
            for enc in ("utf-16-le", "utf-16", "utf-8"):
                try:
                    text = raw.decode(enc, errors="replace")
                    if len(text.strip()) > 50:
                        text = re.sub(r"\s+", " ", text).strip()
                        return text[:max_chars]
                except Exception:
                    continue
    finally:
        ole.close()

    return None


def main():
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

    # Resolve HWP path: 사용자가 경로를 지정한 경우 해당 경로만 사용(다른 행동 없음)
    hwp_path = None
    if args.path_file:
        path_file = os.path.abspath(args.path_file)
        if not os.path.isfile(path_file):
            print(f"경로 파일을 찾을 수 없습니다: {path_file}", file=sys.stderr)
            sys.exit(1)
        with open(path_file, encoding="utf-8") as f:
            hwp_path = f.read().strip()
        if not hwp_path:
            print("경로 파일이 비어 있습니다.", file=sys.stderr)
            sys.exit(1)
    elif args.path and args.path.strip():
        hwp_path = args.path.strip()

    if hwp_path is None:
        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        hwp_path = find_latest_hwp(downloads)
        if hwp_path is None:
            print(f"~/Downloads에서 HWP 파일을 찾을 수 없습니다.", file=sys.stderr)
            sys.exit(1)
        print(f"자동 선택: {hwp_path}")

    text = extract_text(hwp_path, args.max_chars)
    if text is None:
        print("텍스트 추출에 실패했습니다.", file=sys.stderr)
        sys.exit(1)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"OK: {args.output} ({len(text)}자)")


if __name__ == "__main__":
    main()

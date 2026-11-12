# -*- coding: utf-8 -*-
import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from crawler import fss_replies

_REV_RE = re.compile(r"[A-Za-z0-9._-]+")


class _OmittedRev:
    """--sibling-rev 값 생략. argparse const가 문자열이면 type 검사를 탄다."""


def _sibling_rev_token(value: str) -> str:
    if not _REV_RE.fullmatch(value):
        raise argparse.ArgumentTypeError("rev는 영문, 숫자, 점, 밑줄, 하이픈만 쓸 수 있다")
    return value


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=fss_replies.default_archive())
    parser.add_argument("--dest", type=Path, default=fss_replies.default_raw_dest())
    parser.add_argument(
        "--update-pending",
        action="store_true",
        help="대상이 pending_whale이고 소스가 더 이상 pending_whale이 아닐 때만 덮어쓴다",
    )
    parser.add_argument(
        "--sibling-rev",
        nargs="?",
        const=_OmittedRev(),
        default=None,
        type=_sibling_rev_token,
        help="기존 raw 대신 {board}/{nttId}.{rev}.md와 manifest-{rev}.jsonl을 쓴다. 값을 생략하면 git HEAD",
    )
    args = parser.parse_args(argv)
    if args.update_pending and args.sibling_rev is not None:
        parser.error("--sibling-rev와 --update-pending은 함께 쓸 수 없다")
    return args


def git_head_rev(archive: Path) -> str | None:
    completed = subprocess.run(
        ["git", "-C", str(archive), "rev-parse", "--short=8", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "git rev-parse failed").strip()
        print(detail or "git rev-parse failed", file=sys.stderr)
        return None
    rev = completed.stdout.strip()
    if not _REV_RE.fullmatch(rev):
        print("git rev-parse returned an invalid revision", file=sys.stderr)
        return None
    return rev


def main(argv=None) -> int:
    args = parse_args(argv)
    rev = None
    if args.sibling_rev is not None:
        rev = git_head_rev(args.archive) if isinstance(args.sibling_rev, _OmittedRev) else args.sibling_rev
        if not rev:
            return 1
    copied, updated, skipped = fss_replies.copy_archive_markdown(
        args.archive,
        args.dest,
        update_pending=args.update_pending,
        sibling_rev=rev,
    )
    print(f"copied={copied} updated={updated} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from crawler import fss_replies


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=fss_replies.default_archive())
    parser.add_argument("--dest", type=Path, default=fss_replies.default_raw_dest())
    parser.add_argument(
        "--update-pending",
        action="store_true",
        help="대상이 pending_whale이고 소스가 더 이상 pending_whale이 아닐 때만 덮어쓴다",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    copied, updated, skipped = fss_replies.copy_archive_markdown(
        args.archive,
        args.dest,
        update_pending=args.update_pending,
    )
    print(f"copied={copied} updated={updated} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

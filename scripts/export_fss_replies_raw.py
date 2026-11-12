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
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    copied, skipped = fss_replies.copy_archive_markdown(args.archive, args.dest)
    print(f"copied={copied} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

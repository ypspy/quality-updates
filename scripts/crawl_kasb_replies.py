# -*- coding: utf-8 -*-
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from crawler import kasb_replies


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=kasb_replies.default_archive())
    parser.add_argument("--delay", type=float, default=0.2)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--retry-failed", action="store_true")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    session = kasb_replies.make_session()
    result = kasb_replies.crawl_archive(
        args.archive,
        fetch_list=lambda page: kasb_replies.http_fetch_list(session, page),
        fetch_detail=lambda seq, ctg_cd: kasb_replies.http_fetch_detail(session, seq, ctg_cd),
        fetch_file=lambda file_no, file_seq: kasb_replies.http_fetch_file(session, file_no, file_seq),
        delay=args.delay,
        limit=args.limit,
        retry_failed=args.retry_failed,
    )
    print(f"saved={result['saved']} skipped={result['skipped']} failed={result['failed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

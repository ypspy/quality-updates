# -*- coding: utf-8 -*-
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from crawler import fss_replies


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=fss_replies.default_archive())
    parser.add_argument("--board", choices=["B0000132", "B0000133", "all"], default="all")
    parser.add_argument("--delay", type=float, default=0.3)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument(
        "--refresh-standards",
        action="store_true",
        help="item.md와 manifest의 standards만 오프라인으로 다시 쓴다",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.refresh_standards:
        result = fss_replies.refresh_standards(args.archive)
        print(
            f"updated={result['updated']} unchanged={result['unchanged']} items={result['items']}"
        )
        return 0
    session = fss_replies.make_session()
    result = fss_replies.crawl_archive(
        args.archive,
        boards=fss_replies.selected_boards(args.board),
        fetch_list=lambda board, menu_no, page: fss_replies.http_fetch_list(session, board, menu_no, page),
        fetch_detail=lambda board, ntt_id, menu_no: fss_replies.http_fetch_detail(
            session, board, ntt_id, menu_no
        ),
        fetch_file=lambda menu_no, atch_file_id, file_sn: fss_replies.http_fetch_file(
            session, menu_no, atch_file_id, file_sn
        ),
        delay=args.delay,
        limit=args.limit,
        retry_failed=args.retry_failed,
    )
    print(f"saved={result['saved']} skipped={result['skipped']} failed={result['failed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

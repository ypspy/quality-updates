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
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="failed, partial, empty 항목을 다시 추출한다. partial은 파서 이전 결과일 수 있다",
    )
    parser.add_argument(
        "--extract-local",
        action="store_true",
        help="네트워크 없이 아카이브에 있는 partial 또는 failed .hwp만 다시 읽는다",
    )
    parser.add_argument(
        "--reextract-hwpx",
        action="store_true",
        help="--extract-local과 함께 쓰면 상태가 ok인 .hwpx도 다시 읽는다",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.extract_local:
        result = kasb_replies.extract_local(args.archive, reextract_hwpx=args.reextract_hwpx)
        print(
            "parsed={parsed} failed={failed} partial={partial} skipped={skipped}".format(**result)
        )
        return 0
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

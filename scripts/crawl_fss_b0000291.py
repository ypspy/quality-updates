# -*- coding: utf-8 -*-
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from crawler import fss_b0000291


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="B0000291 view.do 수집. 시드 수집 또는 광역 탐색 중 하나를 실행한다."
    )
    parser.add_argument("--seed", type=Path, help="시드 CSV. 탐색과 함께 주면 제외 목록으로만 쓴다.")
    parser.add_argument("--sweep", action="store_true", help="view.do 구간을 탐색한다.")
    parser.add_argument("--dest", type=Path, default=None)
    parser.add_argument("--delay", type=float, default=fss_b0000291.DEFAULT_DELAY)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--range", dest="range_spec", default=fss_b0000291.DEFAULT_RANGE)
    parser.add_argument("--coarse-from", type=int, default=fss_b0000291.DEFAULT_COARSE_FROM)
    parser.add_argument("--coarse-to", type=int, default=fss_b0000291.DEFAULT_COARSE_TO)
    parser.add_argument("--coarse-stride", type=int, default=fss_b0000291.DEFAULT_COARSE_STRIDE)
    parser.add_argument("--sweep-download", action="store_true")
    args = parser.parse_args(argv)
    if args.seed is None and not args.sweep:
        parser.error("pass --seed or --sweep")
    if args.sweep_download and not args.sweep:
        parser.error("--sweep-download requires --sweep")
    if args.dest is None:
        args.dest = fss_b0000291.default_dest()
    return args


def main(argv=None) -> int:
    args = parse_args(argv)
    session = fss_b0000291.make_session()

    def fetch_html(ntt_id: int) -> str:
        return fss_b0000291.http_fetch_text(session, ntt_id)

    def fetch_file(url: str) -> bytes:
        return fss_b0000291.http_fetch_file(session, url)

    if args.sweep:
        seed = fss_b0000291.load_seed(args.seed) if args.seed else []
        result = fss_b0000291.crawl_sweep(
            args.dest,
            seed=seed,
            fetch_html=fetch_html,
            fetch_file=fetch_file,
            range_spec=args.range_spec,
            coarse_from=args.coarse_from,
            coarse_to=args.coarse_to,
            coarse_stride=args.coarse_stride,
            dry_run=args.dry_run,
            resume=args.resume,
            sweep_download=args.sweep_download,
            delay=args.delay,
        )
        print(f"new={result['new']} empty={result['empty']} failed={result['failed']}")
        return 0

    seed = fss_b0000291.load_seed(args.seed)
    result = fss_b0000291.crawl_seed(
        seed,
        args.dest,
        fetch_html=fetch_html,
        fetch_file=fetch_file,
        dry_run=args.dry_run,
        resume=args.resume,
        delay=args.delay,
    )
    print(
        "posts={posts} attachments={attachments} empty={empty} failed={failed}".format(**result)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

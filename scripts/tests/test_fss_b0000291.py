# -*- coding: utf-8 -*-
import hashlib
import json
import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crawler import fss_b0000291
import crawl_fss_b0000291

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "b0000291"
SEED = FIXTURES / "2022-seed.csv"
SEED_SHA256 = "da566c46dbaa8178731c9c8377767829a870c6414624de3664e156bd3fe29d42"
ROOT = Path(__file__).resolve().parents[2]
VIEW_URL = (
    "https://www.fss.or.kr/fss/bbs/B0000291/view.do"
    "?nttId={ntt_id}&menuNo=200620&cl1Cd=01"
)
FILE_URL = "https://www.fss.or.kr/fss/cmmn/file/fileDown.do?menuNo=200620&atchFileId={atch}&fileSn=1&bbsId="


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("network disabled")

    monkeypatch.setattr(requests.Session, "request", boom)
    monkeypatch.setattr(requests.sessions.Session, "request", boom)


def _html(ntt_id: int) -> str:
    return (FIXTURES / f"view_{ntt_id}.html").read_text(encoding="utf-8")


def _by_id(rows):
    return {row.ntt_id: row for row in rows}


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _tree(root: Path) -> dict[str, bytes]:
    found = {}
    if not root.exists():
        return found
    for path in sorted(root.rglob("*")):
        if path.is_file():
            found[str(path.relative_to(root))] = path.read_bytes()
    return found


class FakeResp:
    def __init__(self, status, content: bytes):
        self.status_code = status
        self.content = content
        self.encoding = "utf-8"
        self.text = content.decode("utf-8", errors="replace")


class FakeSession:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0
        self.urls = []

    def get(self, url, timeout=None):
        self.calls += 1
        self.urls.append(url)
        item = self.outcomes.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def test_seed_csv_bytes_and_counts():
    blob = SEED.read_bytes()
    assert hashlib.sha256(blob).hexdigest() == SEED_SHA256
    assert blob.count(b"\r\n") == 88
    assert b"\n" not in blob.replace(b"\r\n", b"")
    rows = fss_b0000291.load_seed(SEED)
    assert len(rows) == 87
    kinds = {}
    for row in rows:
        kinds[row.kind] = kinds.get(row.kind, 0) + 1
    assert kinds == {"업체별": 85, "연간 종합본": 2}
    by_id = _by_id(rows)
    assert 127970 in by_id and 128616 in by_id
    for hole in (127980, 128600, 128606, 128614):
        assert hole not in by_id
    assert by_id[127983].action_date == "2022-03-15"
    assert by_id[127983].disclose_end == "2025-03-15"
    assert "제437호" in by_id[128040].firm
    assert "제506호" not in by_id[128040].firm
    assert "제506호" in by_id[128040].attach
    assert "제437호" not in by_id[128040].attach
    assert by_id[128004].attach.endswith(".hwp")
    for row in rows:
        assert row.url == VIEW_URL.format(ntt_id=row.ntt_id)


def test_view_url_and_session_verify_browser_ua():
    assert fss_b0000291.view_url(127970) == VIEW_URL.format(ntt_id=127970)
    session = fss_b0000291.make_session()
    assert session.verify is True
    assert session.headers["User-Agent"] == (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    lib = (ROOT / "scripts" / "crawler" / "fss_b0000291.py").read_text(encoding="utf-8")
    cli = (ROOT / "scripts" / "crawl_fss_b0000291.py").read_text(encoding="utf-8")
    assert "--insecure" not in lib and "--insecure" not in cli
    assert "verify=False" not in lib and "verify = False" not in lib
    assert "C:\\backups" not in lib and "C:/backups" not in lib


def test_parse_127970_annual_hwpx():
    post = fss_b0000291.parse_view(_html(127970), 127970, kind="연간 종합본")
    assert post.ntt_id == 127970
    assert post.firm == "2022 품질관리 감리대상 감사반"
    assert post.period == "2021-04-01~2022-03-31"
    assert post.action_date == "2023-03-15"
    assert post.disclose_end == "2026-03-15"
    assert post.kind == "연간 종합본"
    assert len(post.attachments) == 1
    att = post.attachments[0]
    assert att.name == "2022년 품질관리 감리결과 개선권고사항(감사반).hwpx"
    assert "(파일크기" not in att.name
    assert att.ext == ".hwpx"
    assert att.url == FILE_URL.format(atch="7e5db8318bbd4568b70725dff2d76546")
    inferred = fss_b0000291.parse_view(_html(127970), 127970, kind=None)
    assert inferred.kind == "연간 종합본"


def test_parse_127980_empty_page_is_not_a_post():
    assert fss_b0000291.parse_view(_html(127980), 127980) is None


def test_parse_127983_keeps_action_date_2022():
    post = fss_b0000291.parse_view(_html(127983), 127983, kind="업체별")
    assert post.firm == "아람공인회계사감사반(제262호)"
    assert post.action_date == "2022-03-15"
    assert post.disclose_end == "2025-03-15"
    assert post.action_date != "2023-03-15"
    assert post.period == "2021-04-01~2022-03-31"
    assert post.attachments[0].name == "아람공인회계사감사반(제262호) 개선권고사항.hwpx"
    assert post.attachments[0].url == FILE_URL.format(atch="f239d47fef4c4d59aec768e6952d8c72")


def test_parse_128040_does_not_reconcile_numbers():
    post = fss_b0000291.parse_view(_html(128040), 128040, kind="업체별")
    assert post.firm == "서상공인회계사감사반(제437호)"
    assert "제506호" not in post.firm
    assert post.attachments[0].name == "서상공인회계사감사반(제506호) 개선권고사항.hwpx"
    assert "제437호" not in post.attachments[0].name
    assert post.attachments[0].url == FILE_URL.format(atch="51ebd45b5218430db8afb868dead0259")


def test_parse_128004_hwp_extension():
    post = fss_b0000291.parse_view(_html(128004), 128004, kind="업체별")
    assert post.firm == "세아회계법인"
    assert post.kind == "업체별"
    assert post.attachments[0].name == "세아회계법인 개선권고사항.hwp"
    assert post.attachments[0].ext == ".hwp"
    assert post.attachments[0].url == FILE_URL.format(atch="e2b1303fe8fe40bf861c3bab6fe31bdc")
    forced = fss_b0000291.parse_view(_html(128004), 128004, kind="연간 종합본")
    assert forced.kind == "연간 종합본"


def test_period_label_falls_back_to_gamri_and_prefers_gamsa():
    html = """
    <dl class="bd-info">
      <div class="info-wrap"><dt>감사인</dt><dd>예시회계법인</dd></div>
      <div class="info-wrap"><dt>감리대상기간</dt><dd>2019-01-01~2022-12-31</dd></div>
      <div class="info-wrap"><dt>개선권고일</dt><dd>2023-07-03</dd></div>
      <div class="info-wrap"><dt>공시종료일</dt><dd>2026-07-03</dd></div>
    </dl>
    """
    post = fss_b0000291.parse_view(html, 1)
    assert post.period == "2019-01-01~2022-12-31"
    assert post.kind == "업체별"
    both = html.replace(
        "<dt>감리대상기간</dt><dd>2019-01-01~2022-12-31</dd>",
        "<dt>감시대상기간</dt><dd>2021-04-01~2022-03-31</dd>"
        "<dt>감리대상기간</dt><dd>2019-01-01~2022-12-31</dd>",
    )
    assert fss_b0000291.parse_view(both, 1).period == "2021-04-01~2022-03-31"


def test_default_sweep_ids_cover_gap_and_coarse_stride():
    ids = fss_b0000291.sweep_ids("127800-128800", 128800, 136220, 200)
    assert ids[0] == 127800
    assert 128800 in ids
    assert ids.count(128800) == 1
    assert 128041 in ids and 128596 in ids
    assert 127970 in ids and 128616 in ids
    assert 129000 in ids and 136200 in ids
    assert 136220 in ids and ids.count(136220) == 1
    assert 136400 not in ids
    assert 128801 not in ids
    assert len(ids) == 1001 + 38


def test_fetch_retries_5xx_and_unexpected_eof_but_403_is_short():
    sleeps = []
    session = FakeSession([FakeResp(503, b""), FakeResp(502, b""), FakeResp(200, b"ok")])
    body = fss_b0000291.fetch_bytes(
        session,
        "https://www.fss.or.kr/x",
        sleeper=sleeps.append,
        backoff_base=1,
        backoff_cap=30,
        max_attempts=5,
    )
    assert body == b"ok"
    assert sleeps == [1, 2]
    assert session.calls == 3

    sleeps.clear()
    session = FakeSession(
        [requests.exceptions.SSLError("UNEXPECTED_EOF_WHILE_READING"), FakeResp(200, b"page")]
    )
    body = fss_b0000291.fetch_bytes(
        session,
        VIEW_URL.format(ntt_id=127970),
        sleeper=sleeps.append,
        backoff_base=1,
        backoff_cap=30,
        max_attempts=5,
    )
    assert body == b"page"
    assert sleeps == [1]

    sleeps.clear()
    session = FakeSession([requests.exceptions.ConnectTimeout("timed out")] * 3)
    with pytest.raises(fss_b0000291.FetchError) as raised:
        fss_b0000291.fetch_bytes(
            session,
            "https://www.fss.or.kr/x",
            sleeper=sleeps.append,
            backoff_base=1,
            backoff_cap=30,
            max_attempts=3,
        )
    assert raised.value.attempts == 3
    assert raised.value.http_status is None
    assert session.calls == 3

    sleeps.clear()
    session = FakeSession([FakeResp(403, b"no"), FakeResp(403, b"no"), FakeResp(200, b"later")])
    with pytest.raises(fss_b0000291.FetchError) as raised:
        fss_b0000291.fetch_bytes(
            session,
            "https://www.fss.or.kr/x",
            sleeper=sleeps.append,
            forbidden_attempts=2,
            short_retry=0.5,
        )
    assert raised.value.http_status == 403
    assert raised.value.attempts == 2
    assert sleeps == [0.5]
    assert session.calls == 2

    session = FakeSession([FakeResp(404, b"missing"), FakeResp(200, b"unused")])
    with pytest.raises(fss_b0000291.FetchError) as raised:
        fss_b0000291.fetch_bytes(session, "https://www.fss.or.kr/x", sleeper=sleeps.append)
    assert raised.value.http_status == 404
    assert raised.value.attempts == 1
    assert session.calls == 1

    sleeps.clear()
    session = FakeSession(
        [requests.exceptions.ConnectionError("connection reset"), FakeResp(200, b"again")]
    )
    body = fss_b0000291.fetch_bytes(
        session,
        "https://www.fss.or.kr/x",
        sleeper=sleeps.append,
        backoff_base=1,
        backoff_cap=30,
        max_attempts=5,
    )
    assert body == b"again"
    assert sleeps == [1]
    assert session.calls == 2

    sleeps.clear()
    session = FakeSession([requests.exceptions.SSLError("handshake failure")] * 3)
    with pytest.raises(fss_b0000291.FetchError) as raised:
        fss_b0000291.fetch_bytes(
            session,
            "https://www.fss.or.kr/x",
            sleeper=sleeps.append,
            backoff_base=1,
            backoff_cap=30,
            max_attempts=3,
        )
    assert raised.value.attempts == 3
    assert session.calls == 3


def test_http_fetch_text_reads_view_url():
    session = FakeSession([FakeResp(200, "<p>ok</p>".encode("utf-8"))])
    text = fss_b0000291.http_fetch_text(session, 127970)
    assert text == "<p>ok</p>"
    assert session.urls == [VIEW_URL.format(ntt_id=127970)]


def _seed_subset(*ntt_ids: int):
    rows = fss_b0000291.load_seed(SEED)
    wanted = set(ntt_ids)
    return [row for row in rows if row.ntt_id in wanted]


def _html_fetcher(mapping, pages):
    def fetch_html(ntt_id: int) -> str:
        pages.append(ntt_id)
        if ntt_id in mapping:
            value = mapping[ntt_id]
            if isinstance(value, Exception):
                raise value
            return value
        raise AssertionError(f"unexpected html {ntt_id}")

    return fetch_html


def test_dry_run_parses_without_downloading(tmp_path):
    rows = _seed_subset(127970, 127983, 128040, 128004)
    pages = []
    files = []

    def fetch_file(url):
        files.append(url)
        return b"nope"

    summary = fss_b0000291.crawl_seed(
        rows,
        tmp_path / "dest",
        fetch_html=_html_fetcher(
            {
                127970: _html(127970),
                127983: _html(127983),
                128040: _html(128040),
                128004: _html(128004),
            },
            pages,
        ),
        fetch_file=fetch_file,
        dry_run=True,
        delay=0,
    )
    assert files == []
    assert pages == [127970, 127983, 128004, 128040]
    assert summary["posts"] == 4
    assert summary["attachments"] == 4
    assert summary["empty"] == 0
    assert summary["failed"] == 0
    assert _tree(tmp_path) == {}


def test_seed_crawl_is_byte_stable_and_skips_same_hash(tmp_path):
    dest = tmp_path / "dest"
    rows = _seed_subset(127970, 128004)
    payloads = {
        FILE_URL.format(atch="7e5db8318bbd4568b70725dff2d76546"): b"annual-hwpx",
        FILE_URL.format(atch="e2b1303fe8fe40bf861c3bab6fe31bdc"): b"seah-hwp",
    }
    file_calls = []

    def fetch_file(url):
        file_calls.append(url)
        return payloads[url]

    fetch_html = _html_fetcher({127970: _html(127970), 128004: _html(128004)}, [])
    summary = fss_b0000291.crawl_seed(
        rows, dest, fetch_html=fetch_html, fetch_file=fetch_file, delay=0
    )
    assert summary["posts"] == 2
    assert summary["attachments"] == 2
    annual = dest / "127970" / "2022년 품질관리 감리결과 개선권고사항(감사반).hwpx"
    seah = dest / "128004" / "세아회계법인 개선권고사항.hwp"
    assert annual.read_bytes() == b"annual-hwpx"
    assert seah.read_bytes() == b"seah-hwp"
    manifest = _jsonl(dest / "manifest.jsonl")
    assert [row["nttId"] for row in manifest] == [127970, 128004]
    assert manifest[0]["kind"] == "연간 종합본"
    assert manifest[0]["attachments"][0]["ext"] == ".hwpx"
    assert set(manifest[0]["attachments"][0]) == {"name", "url", "ext"}
    assert 127980 not in {row["nttId"] for row in manifest}
    pending = _jsonl(dest / "_pending-conversion.jsonl")
    assert {(row["nttId"], row["ext"], row["path"]) for row in pending} == {
        (127970, ".hwpx", "127970/2022년 품질관리 감리결과 개선권고사항(감사반).hwpx"),
        (128004, ".hwp", "128004/세아회계법인 개선권고사항.hwp"),
    }
    state = json.loads((dest / "_state.json").read_text(encoding="utf-8"))
    assert state["done"] == [127970, 128004]
    stamp = annual.stat().st_mtime_ns
    snapshot = _tree(dest)
    file_calls.clear()
    again = fss_b0000291.crawl_seed(
        rows,
        dest,
        fetch_html=_html_fetcher({127970: _html(127970), 128004: _html(128004)}, []),
        fetch_file=fetch_file,
        delay=0,
    )
    assert again["posts"] == 2
    assert file_calls == list(payloads)
    assert _tree(dest) == snapshot
    assert annual.stat().st_mtime_ns == stamp
    assert not (dest / "_failed.jsonl").exists()


def test_resume_skips_done_and_failure_jsonl_is_idempotent(tmp_path):
    dest = tmp_path / "dest"
    rows = _seed_subset(127970, 128004)
    pages = []

    def fail_html(ntt_id):
        pages.append(("html", ntt_id))
        raise fss_b0000291.FetchError(
            "HTTP 403",
            http_status=403,
            attempts=2,
            url=VIEW_URL.format(ntt_id=ntt_id),
        )

    first = fss_b0000291.crawl_seed(
        rows, dest, fetch_html=fail_html, fetch_file=lambda url: b"", delay=0
    )
    assert first["failed"] == 2
    failed = _jsonl(dest / "_failed.jsonl")
    assert len(failed) == 2
    assert {row["nttId"] for row in failed} == {127970, 128004}
    sample = failed[0]
    assert set(sample) == {
        "ts",
        "nttId",
        "page_url",
        "url",
        "filename",
        "http_status",
        "error",
        "attempts",
    }
    assert sample["http_status"] == 403
    assert sample["attempts"] == 2
    assert sample["filename"] is None
    assert sample["page_url"] == VIEW_URL.format(ntt_id=sample["nttId"])
    assert sample["url"] == sample["page_url"]
    assert sample["ts"].endswith("+00:00") or "+" in sample["ts"] or sample["ts"].endswith("Z")

    def fail_again(ntt_id):
        raise fss_b0000291.FetchError(
            "still forbidden",
            http_status=403,
            attempts=2,
            url=VIEW_URL.format(ntt_id=ntt_id),
        )

    fss_b0000291.crawl_seed(
        rows, dest, fetch_html=fail_again, fetch_file=lambda url: b"", delay=0
    )
    rewritten = _jsonl(dest / "_failed.jsonl")
    assert len(rewritten) == 2
    assert {row["error"] for row in rewritten} == {"still forbidden"}

    saved = {}

    def fetch_html(ntt_id):
        pages.append(("ok", ntt_id))
        return _html(ntt_id)

    def fetch_file(url):
        saved[url] = b"body-" + url.encode("utf-8")
        return saved[url]

    fss_b0000291.crawl_seed(
        rows, dest, fetch_html=fetch_html, fetch_file=fetch_file, delay=0
    )
    assert not (dest / "_failed.jsonl").exists()
    pages.clear()
    saved.clear()
    fss_b0000291.crawl_seed(
        rows,
        dest,
        fetch_html=fetch_html,
        fetch_file=fetch_file,
        resume=True,
        delay=1,
    )
    assert pages == []
    assert saved == {}


def test_attachment_failure_records_file_and_same_hash_keeps_mtime(tmp_path):
    dest = tmp_path / "dest"
    rows = _seed_subset(128004)
    url = FILE_URL.format(atch="e2b1303fe8fe40bf861c3bab6fe31bdc")
    target = dest / "128004" / "세아회계법인 개선권고사항.hwp"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"same-bytes")
    old = target.stat().st_mtime_ns

    def fetch_file(file_url):
        raise fss_b0000291.FetchError(
            "HTTP 503",
            http_status=503,
            attempts=5,
            url=file_url,
        )

    summary = fss_b0000291.crawl_seed(
        rows,
        dest,
        fetch_html=_html_fetcher({128004: _html(128004)}, []),
        fetch_file=fetch_file,
        delay=0,
    )
    assert summary["failed"] == 1
    assert _jsonl(dest / "manifest.jsonl") == []
    failed = _jsonl(dest / "_failed.jsonl")
    assert len(failed) == 1
    assert failed[0]["filename"] == "세아회계법인 개선권고사항.hwp"
    assert failed[0]["url"] == url
    assert failed[0]["page_url"] == VIEW_URL.format(ntt_id=128004)
    assert failed[0]["http_status"] == 503
    assert target.read_bytes() == b"same-bytes"
    assert target.stat().st_mtime_ns == old

    summary = fss_b0000291.crawl_seed(
        rows,
        dest,
        fetch_html=_html_fetcher({128004: _html(128004)}, []),
        fetch_file=lambda file_url: b"same-bytes",
        delay=0,
    )
    assert summary["failed"] == 0
    assert target.read_bytes() == b"same-bytes"
    assert target.stat().st_mtime_ns == old
    assert not (dest / "_failed.jsonl").exists()
    manifest = _jsonl(dest / "manifest.jsonl")
    assert manifest[0]["nttId"] == 128004


def test_sweep_reports_only_new_posts_and_failures(tmp_path):
    dest = tmp_path / "dest"
    seed = _seed_subset(127970)
    downloads = []

    def fetch_html(ntt_id):
        if ntt_id == 127970:
            return _html(127970)
        if ntt_id == 127971:
            return _html(127980)
        if ntt_id == 127972:
            return _html(128004)
        if ntt_id == 128100:
            raise fss_b0000291.FetchError(
                "HTTP 403",
                http_status=403,
                attempts=2,
                url=VIEW_URL.format(ntt_id=ntt_id),
            )
        if ntt_id == 128101:
            raise fss_b0000291.FetchError(
                "TLS UNEXPECTED_EOF_WHILE_READING",
                http_status=None,
                attempts=5,
                url=VIEW_URL.format(ntt_id=ntt_id),
            )
        raise AssertionError(ntt_id)

    summary = fss_b0000291.crawl_sweep(
        dest,
        seed=seed,
        fetch_html=fetch_html,
        fetch_file=lambda url: downloads.append(url) or b"x",
        range_spec="127970-127972",
        coarse_from=128100,
        coarse_to=128101,
        coarse_stride=1,
        delay=0,
    )
    assert downloads == []
    assert summary["new"] == 1
    assert summary["empty"] == 1
    assert summary["failed"] == 2
    rows = _jsonl(dest / "_sweep.jsonl")
    types = {(row["type"], row["nttId"]) for row in rows}
    assert types == {("post", 127972), ("failure", 128100), ("failure", 128101)}
    post = next(row for row in rows if row["type"] == "post")
    assert post["firm"] == "세아회계법인"
    assert post["kind"] == "업체별"
    assert post["attachments"][0]["ext"] == ".hwp"
    failure = next(row for row in rows if row["nttId"] == 128101)
    assert failure["http_status"] is None
    assert "UNEXPECTED_EOF" in failure["error"]
    assert failure["attempts"] == 5
    forbidden = next(row for row in rows if row["nttId"] == 128100)
    assert forbidden["http_status"] == 403
    assert not (dest / "127972").exists()


def test_sweep_download_only_when_asked(tmp_path):
    dest = tmp_path / "dest"
    downloads = []

    def fetch_html(ntt_id):
        assert ntt_id == 128004
        return _html(128004)

    fss_b0000291.crawl_sweep(
        dest,
        seed=[],
        fetch_html=fetch_html,
        fetch_file=lambda url: downloads.append(url) or b"hwp-bytes",
        range_spec="128004-128004",
        coarse_from=128004,
        coarse_to=128004,
        coarse_stride=1,
        sweep_download=True,
        delay=0,
    )
    assert downloads == [FILE_URL.format(atch="e2b1303fe8fe40bf861c3bab6fe31bdc")]
    saved = dest / "128004" / "세아회계법인 개선권고사항.hwp"
    assert saved.read_bytes() == b"hwp-bytes"
    pending = _jsonl(dest / "_pending-conversion.jsonl")
    assert pending[0]["ext"] == ".hwp"


def test_cli_defaults_and_dry_run_does_not_download(tmp_path, monkeypatch, capsys):
    with pytest.raises(SystemExit):
        crawl_fss_b0000291.parse_args([])
    with pytest.raises(SystemExit):
        crawl_fss_b0000291.parse_args(["--seed", "x.csv", "--insecure"])
    args = crawl_fss_b0000291.parse_args(["--sweep"])
    assert args.delay == 1.0
    assert args.range_spec == "127800-128800"
    assert args.coarse_from == 128800
    assert args.coarse_to == 136220
    assert args.coarse_stride == 200
    assert args.sweep_download is False
    assert args.dry_run is False
    assert args.resume is False
    seed_args = crawl_fss_b0000291.parse_args(["--seed", "seed.csv"])
    assert seed_args.delay == 1.0
    assert seed_args.dest == fss_b0000291.default_dest()

    tiny = tmp_path / "tiny.csv"
    tiny.write_text(
        "nttId,action_date,period,firm,kind,attach,disclose_end,url\n"
        "127970,2023-03-15,2021-04-01~2022-03-31,2022 품질관리 감리대상 감사반,연간 종합본,a.hwpx,2026-03-15,"
        + VIEW_URL.format(ntt_id=127970)
        + "\n"
        "127980,2023-03-15,,,업체별,,,"
        + VIEW_URL.format(ntt_id=127980)
        + "\n",
        encoding="utf-8",
    )

    def fetch_html(session, ntt_id):
        return _html(ntt_id)

    def fetch_file(session, url):
        raise AssertionError("download called")

    monkeypatch.setattr(fss_b0000291, "http_fetch_text", fetch_html)
    monkeypatch.setattr(fss_b0000291, "http_fetch_file", fetch_file)
    code = crawl_fss_b0000291.main(
        ["--seed", str(tiny), "--dest", str(tmp_path / "out"), "--dry-run", "--delay", "0"]
    )
    assert code == 0
    captured = capsys.readouterr().out
    assert "posts=1" in captured
    assert "attachments=1" in captured
    assert "empty=1" in captured
    assert "failed=0" in captured
    assert _tree(tmp_path / "out") == {}


def _page(firm: str, filename: str | None = None) -> str:
    attach = ""
    if filename is not None:
        attach = (
            '<a class="btn-attach-download" '
            f'href="/fss/cmmn/file/fileDown.do?fileSn=1">{filename}</a>'
        )
    return (
        "<dl class=\"bd-info\">"
        f"<div><dt>감사인</dt><dd>{firm}</dd></div>"
        "<div><dt>감시대상기간</dt><dd>2021-04-01~2022-03-31</dd></div>"
        "<div><dt>개선권고일</dt><dd>2023-03-15</dd></div>"
        "<div><dt>공시종료일</dt><dd>2026-03-15</dd></div>"
        "</dl>"
        + attach
    )


def _row(ntt_id: int, firm: str = "예시회계법인", attach: str = "예시.hwpx"):
    return fss_b0000291.SeedRow(
        ntt_id=ntt_id,
        action_date="2023-03-15",
        period="2021-04-01~2022-03-31",
        firm=firm,
        kind="업체별",
        attach=attach,
        disclose_end="2026-03-15",
        url=VIEW_URL.format(ntt_id=ntt_id),
    )


def test_sweep_resume_skips_probed_pages_without_downloading(tmp_path):
    dest = tmp_path / "dest"
    seed = _seed_subset(127970)
    calls = []
    downloads = []

    def fetch_html(ntt_id):
        calls.append(ntt_id)
        if ntt_id == 127970:
            return _html(127970)
        if ntt_id == 127971:
            return _html(127980)
        if ntt_id == 127972:
            return _html(128004)
        if ntt_id == 128100:
            raise fss_b0000291.FetchError(
                "HTTP 403",
                http_status=403,
                attempts=2,
                url=VIEW_URL.format(ntt_id=ntt_id),
            )
        raise AssertionError(ntt_id)

    fss_b0000291.crawl_sweep(
        dest,
        seed=seed,
        fetch_html=fetch_html,
        fetch_file=lambda url: downloads.append(url) or b"x",
        range_spec="127970-127972",
        coarse_from=128100,
        coarse_to=128100,
        coarse_stride=1,
        delay=0,
    )
    state = json.loads((dest / "_state.json").read_text(encoding="utf-8"))
    assert state["probed"] == [127970, 127971, 127972]
    assert 128100 not in state["probed"]
    assert state["done"] == []
    kinds = {(row["type"], row["nttId"]) for row in _jsonl(dest / "_sweep.jsonl")}
    assert kinds == {("post", 127972), ("failure", 128100)}
    assert downloads == []
    calls.clear()
    fss_b0000291.crawl_sweep(
        dest,
        seed=seed,
        fetch_html=fetch_html,
        fetch_file=lambda url: downloads.append(url) or b"x",
        range_spec="127970-127972",
        coarse_from=128100,
        coarse_to=128100,
        coarse_stride=1,
        resume=True,
        delay=0,
    )
    assert calls == [128100]
    assert downloads == []


def test_sweep_interrupt_persists_finished_probes(tmp_path):
    dest = tmp_path / "dest"
    calls = []

    def fetch_html(ntt_id):
        calls.append(ntt_id)
        if len(calls) == 3:
            raise RuntimeError("interrupt")
        if ntt_id == 11:
            return _html(127980)
        return _page("새회계법인", "새회계법인 개선권고사항.hwpx")

    with pytest.raises(RuntimeError, match="interrupt"):
        fss_b0000291.crawl_sweep(
            dest,
            seed=[],
            fetch_html=fetch_html,
            fetch_file=lambda url: b"nope",
            range_spec="10-12",
            coarse_from=13,
            coarse_to=12,
            coarse_stride=1,
            delay=0,
        )
    state = json.loads((dest / "_state.json").read_text(encoding="utf-8"))
    assert state["probed"] == [10, 11]
    assert state["done"] == []
    assert [row["nttId"] for row in _jsonl(dest / "_sweep.jsonl")] == [10]
    calls.clear()

    def resume_html(ntt_id):
        calls.append(ntt_id)
        return _page("나머지회계법인", "나머지.hwpx")

    downloads = []
    fss_b0000291.crawl_sweep(
        dest,
        seed=[],
        fetch_html=resume_html,
        fetch_file=lambda url: downloads.append(url) or b"x",
        range_spec="10-12",
        coarse_from=13,
        coarse_to=12,
        coarse_stride=1,
        resume=True,
        delay=0,
    )
    assert calls == [12]
    assert downloads == []
    assert state_probed(dest) == [10, 11, 12]


def state_probed(dest: Path) -> list[int]:
    return json.loads((dest / "_state.json").read_text(encoding="utf-8"))["probed"]


def test_sweep_probe_does_not_finish_seed_collection(tmp_path):
    dest = tmp_path / "dest"
    fss_b0000291.crawl_sweep(
        dest,
        seed=[_row(127970)],
        fetch_html=lambda ntt_id: _html(127970),
        fetch_file=lambda url: (_ for _ in ()).throw(AssertionError("download")),
        range_spec="127970-127970",
        coarse_from=127971,
        coarse_to=127970,
        coarse_stride=1,
        delay=0,
    )
    state = json.loads((dest / "_state.json").read_text(encoding="utf-8"))
    assert state["probed"] == [127970]
    assert state["done"] == []
    pages = []
    files = []
    fss_b0000291.crawl_seed(
        [_row(127970)],
        dest,
        fetch_html=lambda ntt_id: pages.append(ntt_id) or _html(ntt_id),
        fetch_file=lambda url: files.append(url) or b"annual",
        resume=True,
        delay=0,
    )
    assert pages == [127970]
    assert files
    done = json.loads((dest / "_state.json").read_text(encoding="utf-8"))
    assert done["done"] == [127970]
    assert done["probed"] == [127970]


def test_seed_ledger_is_flushed_before_the_next_post(tmp_path):
    dest = tmp_path / "dest"
    rows = _seed_subset(127970, 128004)
    annual = FILE_URL.format(atch="7e5db8318bbd4568b70725dff2d76546")

    def fetch_html(ntt_id):
        if ntt_id == 128004:
            state = json.loads((dest / "_state.json").read_text(encoding="utf-8"))
            assert state["done"] == [127970]
            assert state["probed"] == []
            assert [row["nttId"] for row in _jsonl(dest / "manifest.jsonl")] == [127970]
            raise RuntimeError("stop after first")
        return _html(ntt_id)

    with pytest.raises(RuntimeError, match="stop after first"):
        fss_b0000291.crawl_seed(
            rows,
            dest,
            fetch_html=fetch_html,
            fetch_file=lambda url: b"annual-hwpx",
            delay=0,
        )
    pages = []
    files = []
    fss_b0000291.crawl_seed(
        rows,
        dest,
        fetch_html=lambda ntt_id: pages.append(ntt_id) or _html(ntt_id),
        fetch_file=lambda url: files.append(url) or b"seah-hwp",
        resume=True,
        delay=0,
    )
    assert pages == [128004]
    assert annual not in files
    assert json.loads((dest / "_state.json").read_text(encoding="utf-8"))["done"] == [
        127970,
        128004,
    ]


def test_attachment_names_stay_inside_ntt_directory(tmp_path):
    dest = tmp_path / "dest"
    downloads = []
    names = ["../etc/passwd", "foo/../../x.hwpx", ".", ".."]
    for ntt_id, name in enumerate(names, start=1):
        fss_b0000291.crawl_seed(
            [_row(ntt_id, attach=name)],
            dest,
            fetch_html=lambda ntt, name=name: _page("예시회계법인", name),
            fetch_file=lambda url, name=name: downloads.append(name) or b"body",
            delay=0,
        )
    assert downloads == ["../etc/passwd", "foo/../../x.hwpx"]
    assert (dest / "1" / "passwd").read_bytes() == b"body"
    assert (dest / "2" / "x.hwpx").read_bytes() == b"body"
    assert not (tmp_path / "etc" / "passwd").exists()
    assert not (dest / "3").exists()
    assert not (dest / "4").exists()
    for path in tmp_path.rglob("*"):
        if not path.is_file():
            continue
        relative = path.resolve().relative_to(dest.resolve())
        assert relative.parts[0] in {"1", "2", "_state.json", "_failed.jsonl", "manifest.jsonl", "_pending-conversion.jsonl"}
        if relative.parts[0] in {"1", "2"}:
            assert len(relative.parts) == 2
            assert relative.name not in {".", ".."}
    failed_ids = {row["nttId"] for row in _jsonl(dest / "_failed.jsonl")}
    assert failed_ids == {3, 4}
    assert fss_b0000291._store_attachment(dest, 99, "", b"nope") is False
    assert fss_b0000291._store_attachment(dest, 99, ".", b"nope") is False
    assert fss_b0000291._store_attachment(dest, 99, "..", b"nope") is False
    assert not (dest / "99").exists()


def test_sweep_dry_run_does_not_write_or_download(tmp_path):
    dest = tmp_path / "dest"
    downloads = []
    summary = fss_b0000291.crawl_sweep(
        dest,
        seed=[],
        fetch_html=lambda ntt_id: _page("새회계법인", "새회계법인.hwpx"),
        fetch_file=lambda url: downloads.append(url) or b"x",
        range_spec="5-6",
        coarse_from=8,
        coarse_to=7,
        coarse_stride=1,
        dry_run=True,
        delay=0,
    )
    assert summary == {"new": 2, "empty": 0, "failed": 0}
    assert downloads == []
    assert not dest.exists()


def test_resume_sweep_download_saves_reported_posts_and_retries_failures(tmp_path):
    dest = tmp_path / "dest"
    seed = [_row(1)]
    calls = []
    downloads = []

    def fetch_html(ntt_id):
        calls.append(ntt_id)
        if ntt_id == 1:
            return _html(127970)
        if ntt_id == 2:
            return _html(127980)
        if ntt_id == 3:
            return _page("새회계법인", "새회계법인.hwpx")
        raise fss_b0000291.FetchError(
            "HTTP 403",
            http_status=403,
            attempts=2,
            url=VIEW_URL.format(ntt_id=ntt_id),
        )

    fss_b0000291.crawl_sweep(
        dest,
        seed=seed,
        fetch_html=fetch_html,
        fetch_file=lambda url: downloads.append(url) or b"nope",
        range_spec="1-3",
        coarse_from=4,
        coarse_to=4,
        coarse_stride=1,
        delay=0,
    )
    state = json.loads((dest / "_state.json").read_text(encoding="utf-8"))
    assert state["probed"] == [1, 2, 3]
    assert 4 not in state["probed"]
    assert state["done"] == []
    assert {(row["type"], row["nttId"]) for row in _jsonl(dest / "_sweep.jsonl")} == {
        ("post", 3),
        ("failure", 4),
    }
    assert downloads == []
    calls.clear()

    def retry_html(ntt_id):
        calls.append(ntt_id)
        if ntt_id == 4:
            return _page("복구회계법인", "복구.hwpx")
        raise AssertionError(ntt_id)

    def fetch_file(url):
        downloads.append(url)
        return b"saved-bytes"

    fss_b0000291.crawl_sweep(
        dest,
        seed=seed,
        fetch_html=retry_html,
        fetch_file=fetch_file,
        range_spec="1-3",
        coarse_from=4,
        coarse_to=4,
        coarse_stride=1,
        resume=True,
        sweep_download=True,
        delay=0,
    )
    assert calls == [4]
    assert (dest / "3" / "새회계법인.hwpx").read_bytes() == b"saved-bytes"
    assert (dest / "4" / "복구.hwpx").read_bytes() == b"saved-bytes"
    saved = json.loads((dest / "_state.json").read_text(encoding="utf-8"))
    assert saved["done"] == [3, 4]
    assert {row["nttId"] for row in _jsonl(dest / "manifest.jsonl")} == {3, 4}
    assert [row for row in _jsonl(dest / "_sweep.jsonl") if row["type"] == "failure"] == []
    calls.clear()
    downloads.clear()
    fss_b0000291.crawl_sweep(
        dest,
        seed=seed,
        fetch_html=lambda ntt_id: calls.append(ntt_id),
        fetch_file=lambda url: downloads.append(url) or b"again",
        range_spec="1-3",
        coarse_from=4,
        coarse_to=4,
        coarse_stride=1,
        resume=True,
        sweep_download=True,
        delay=0,
    )
    assert calls == []
    assert downloads == []


def test_failed_probe_is_retried_and_cleared(tmp_path):
    dest = tmp_path / "dest"
    calls = []

    def fail_once(ntt_id):
        calls.append(ntt_id)
        raise fss_b0000291.FetchError(
            "HTTP 403",
            http_status=403,
            attempts=2,
            url=VIEW_URL.format(ntt_id=ntt_id),
        )

    fss_b0000291.crawl_sweep(
        dest,
        seed=[],
        fetch_html=fail_once,
        fetch_file=lambda url: b"",
        range_spec="8-8",
        coarse_from=9,
        coarse_to=8,
        coarse_stride=1,
        delay=0,
    )
    state = json.loads((dest / "_state.json").read_text(encoding="utf-8"))
    assert state["probed"] == []
    assert _jsonl(dest / "_sweep.jsonl")[0]["type"] == "failure"
    calls.clear()

    def recover(ntt_id):
        calls.append(ntt_id)
        return _html(127980)

    fss_b0000291.crawl_sweep(
        dest,
        seed=[],
        fetch_html=recover,
        fetch_file=lambda url: b"",
        range_spec="8-8",
        coarse_from=9,
        coarse_to=8,
        coarse_stride=1,
        resume=True,
        delay=0,
    )
    assert calls == [8]
    rows = _jsonl(dest / "_sweep.jsonl")
    assert rows == []
    assert json.loads((dest / "_state.json").read_text(encoding="utf-8"))["probed"] == [8]


def test_decode_chunk_and_certificate_errors(tmp_path):
    session = FakeSession([FakeResp(200, b"\xff")])
    with pytest.raises(fss_b0000291.FetchError):
        fss_b0000291.http_fetch_text(session, 1)

    dest = tmp_path / "dest"
    calls = []

    def fetch_html(ntt_id):
        calls.append(ntt_id)
        if ntt_id == 1:
            return fss_b0000291.http_fetch_text(FakeSession([FakeResp(200, b"\xff")]), ntt_id)
        return _page("다음회계법인", "다음.hwpx")

    summary = fss_b0000291.crawl_sweep(
        dest,
        seed=[],
        fetch_html=fetch_html,
        fetch_file=lambda url: b"x",
        range_spec="1-2",
        coarse_from=3,
        coarse_to=2,
        coarse_stride=1,
        delay=0,
    )
    assert calls == [1, 2]
    assert summary["failed"] == 1
    assert summary["new"] == 1
    assert 1 not in json.loads((dest / "_state.json").read_text(encoding="utf-8"))["probed"]

    sleeps = []
    session = FakeSession(
        [requests.exceptions.ChunkedEncodingError("broken chunk"), FakeResp(200, b"ok")]
    )
    body = fss_b0000291.fetch_bytes(
        session,
        "https://www.fss.or.kr/x",
        sleeper=sleeps.append,
        backoff_base=1,
        backoff_cap=30,
        max_attempts=5,
    )
    assert body == b"ok"
    assert sleeps == [1]
    assert session.calls == 2

    sleeps.clear()
    session = FakeSession(
        [requests.exceptions.SSLError("CERTIFICATE_VERIFY_FAILED"), FakeResp(200, b"later")]
    )
    with pytest.raises(fss_b0000291.FetchError) as raised:
        fss_b0000291.fetch_bytes(
            session,
            "https://www.fss.or.kr/x",
            sleeper=sleeps.append,
            backoff_base=1,
            backoff_cap=30,
            max_attempts=5,
        )
    assert raised.value.attempts == 1
    assert sleeps == []
    assert session.calls == 1

    sleeps.clear()
    session = FakeSession(
        [requests.exceptions.SSLError("UNEXPECTED_EOF_WHILE_READING"), FakeResp(200, b"page")]
    )
    assert (
        fss_b0000291.fetch_bytes(
            session,
            "https://www.fss.or.kr/x",
            sleeper=sleeps.append,
            backoff_base=1,
            backoff_cap=30,
            max_attempts=5,
        )
        == b"page"
    )
    assert sleeps == [1]


def test_missing_bd_info_is_failure_not_empty_page(tmp_path):
    blocked = "<html><body><p>점검 중</p></body></html>"
    with pytest.raises(fss_b0000291.FetchError):
        fss_b0000291.parse_view(blocked, 50)
    assert fss_b0000291.parse_view(_html(127980), 127980) is None

    dest = tmp_path / "dest"
    calls = []

    def fetch_html(ntt_id):
        calls.append(ntt_id)
        if ntt_id == 50:
            return blocked
        return _page("다른회계법인", "다른.hwpx")

    summary = fss_b0000291.crawl_sweep(
        dest,
        seed=[],
        fetch_html=fetch_html,
        fetch_file=lambda url: b"x",
        range_spec="50-51",
        coarse_from=52,
        coarse_to=51,
        coarse_stride=1,
        delay=0,
    )
    assert summary["failed"] == 1
    assert summary["empty"] == 0
    assert summary["new"] == 1
    state = json.loads((dest / "_state.json").read_text(encoding="utf-8"))
    assert 50 not in state["probed"]
    assert state["probed"] == [51]
    calls.clear()

    def retry(ntt_id):
        calls.append(ntt_id)
        return _html(127980)

    fss_b0000291.crawl_sweep(
        dest,
        seed=[],
        fetch_html=retry,
        fetch_file=lambda url: b"x",
        range_spec="50-51",
        coarse_from=52,
        coarse_to=51,
        coarse_stride=1,
        resume=True,
        delay=0,
    )
    assert calls == [50]


def test_seed_empty_page_is_recorded_and_not_redone(tmp_path):
    dest = tmp_path / "dest"
    calls = []
    summary = fss_b0000291.crawl_seed(
        [_row(127980)],
        dest,
        fetch_html=lambda ntt_id: calls.append(ntt_id) or _html(127980),
        fetch_file=lambda url: b"nope",
        delay=0,
    )
    assert summary["empty"] == 1
    state = json.loads((dest / "_state.json").read_text(encoding="utf-8"))
    assert state["empty"] == [127980]
    assert state["done"] == []
    assert _jsonl(dest / "manifest.jsonl") == []
    calls.clear()
    fss_b0000291.crawl_seed(
        [_row(127980)],
        dest,
        fetch_html=lambda ntt_id: calls.append(ntt_id) or _html(127980),
        fetch_file=lambda url: b"nope",
        resume=True,
        delay=0,
    )
    assert calls == []


def test_duplicate_attachment_names_and_pending_only_after_success(tmp_path):
    dest = tmp_path / "dest"
    html = """
    <dl class="bd-info">
      <div><dt>감사인</dt><dd>둘회계법인</dd></div>
      <div><dt>감시대상기간</dt><dd>2021-04-01~2022-03-31</dd></div>
      <div><dt>개선권고일</dt><dd>2023-03-15</dd></div>
      <div><dt>공시종료일</dt><dd>2026-03-15</dd></div>
    </dl>
    <a class="btn-attach-download" href="/fss/cmmn/file/fileDown.do?fileSn=1">report.hwpx</a>
    <a class="btn-attach-download" href="/fss/cmmn/file/fileDown.do?fileSn=2">report.hwpx</a>
    """

    def fetch_file(url):
        if "fileSn=1" in url:
            return b"FIRST"
        if "fileSn=2" in url:
            return b"SECOND"
        raise AssertionError(url)

    fss_b0000291.crawl_seed(
        [_row(7, attach="report.hwpx")],
        dest,
        fetch_html=lambda ntt_id: html,
        fetch_file=fetch_file,
        delay=0,
    )
    assert (dest / "7" / "report.hwpx").read_bytes() == b"FIRST"
    assert (dest / "7" / "report__2.hwpx").read_bytes() == b"SECOND"

    failed = tmp_path / "failed"
    partial = """
    <dl class="bd-info">
      <div><dt>감사인</dt><dd>둘회계법인</dd></div>
      <div><dt>감시대상기간</dt><dd>2021-04-01~2022-03-31</dd></div>
      <div><dt>개선권고일</dt><dd>2023-03-15</dd></div>
      <div><dt>공시종료일</dt><dd>2026-03-15</dd></div>
    </dl>
    <a class="btn-attach-download" href="/fss/cmmn/file/fileDown.do?fileSn=1">one.hwpx</a>
    <a class="btn-attach-download" href="/fss/cmmn/file/fileDown.do?fileSn=2">two.hwpx</a>
    """

    def fetch_partial(url):
        if "fileSn=1" in url:
            return b"ONE"
        raise fss_b0000291.FetchError("HTTP 503", http_status=503, attempts=5, url=url)

    fss_b0000291.crawl_seed(
        [_row(8)],
        failed,
        fetch_html=lambda ntt_id: partial,
        fetch_file=fetch_partial,
        delay=0,
    )
    assert _jsonl(failed / "manifest.jsonl") == []
    assert _jsonl(failed / "_pending-conversion.jsonl") == []
    assert (failed / "8" / "one.hwpx").read_bytes() == b"ONE"
    assert 8 not in json.loads((failed / "_state.json").read_text(encoding="utf-8"))["done"]


def _forbid(ntt_id):
    raise fss_b0000291.FetchError(
        "HTTP 403",
        http_status=403,
        attempts=2,
        url=VIEW_URL.format(ntt_id=ntt_id),
    )


def test_done_seed_ledger_survives_later_failure(tmp_path):
    dest = tmp_path / "dest"
    row = _row(42, attach="예시.hwpx")
    html = _page("예시회계법인", "예시.hwpx")
    fss_b0000291.crawl_seed(
        [row],
        dest,
        fetch_html=lambda ntt_id: html,
        fetch_file=lambda url: b"original",
        delay=0,
    )
    snapshot = _tree(dest)
    assert json.loads((dest / "_state.json").read_text(encoding="utf-8"))["done"] == [42]
    assert _jsonl(dest / "manifest.jsonl")[0]["nttId"] == 42
    assert _jsonl(dest / "_pending-conversion.jsonl")[0]["nttId"] == 42
    fss_b0000291.crawl_seed(
        [row],
        dest,
        fetch_html=_forbid,
        fetch_file=lambda url: b"should-not",
        delay=0,
    )
    assert _tree(dest) == snapshot
    calls = []
    fss_b0000291.crawl_seed(
        [row],
        dest,
        fetch_html=lambda ntt_id: calls.append(ntt_id) or html,
        fetch_file=lambda url: b"original",
        resume=True,
        delay=0,
    )
    assert calls == []


def test_sweep_failure_does_not_clear_seed_done(tmp_path):
    dest = tmp_path / "dest"
    row = _row(42, attach="예시.hwpx")
    html = _page("예시회계법인", "예시.hwpx")
    fss_b0000291.crawl_seed(
        [row],
        dest,
        fetch_html=lambda ntt_id: html,
        fetch_file=lambda url: b"original",
        delay=0,
    )
    manifest = (dest / "manifest.jsonl").read_bytes()
    body = (dest / "42" / "예시.hwpx").read_bytes()
    calls = []

    def fetch_html(ntt_id):
        calls.append(ntt_id)
        raise fss_b0000291.FetchError(
            "HTTP 403",
            http_status=403,
            attempts=2,
            url=VIEW_URL.format(ntt_id=ntt_id),
        )

    fss_b0000291.crawl_sweep(
        dest,
        seed=[row],
        fetch_html=fetch_html,
        fetch_file=lambda url: b"should-not",
        range_spec="42-42",
        coarse_from=43,
        coarse_to=42,
        coarse_stride=1,
        delay=0,
    )
    assert calls == [42]
    state = json.loads((dest / "_state.json").read_text(encoding="utf-8"))
    assert state["done"] == [42]
    assert (dest / "manifest.jsonl").read_bytes() == manifest
    assert (dest / "42" / "예시.hwpx").read_bytes() == body
    calls.clear()
    fss_b0000291.crawl_sweep(
        dest,
        seed=[row],
        fetch_html=lambda ntt_id: calls.append(ntt_id) or html,
        fetch_file=lambda url: b"should-not",
        range_spec="42-42",
        coarse_from=43,
        coarse_to=42,
        coarse_stride=1,
        resume=True,
        delay=0,
    )
    assert calls == []


def test_same_url_overwrites_changed_bytes_without_extra_suffix(tmp_path):
    dest = tmp_path / "dest"
    row = _row(9, attach="a.hwpx")
    html = _page("예시회계법인", "a.hwpx")
    fss_b0000291.crawl_seed(
        [row],
        dest,
        fetch_html=lambda ntt_id: html,
        fetch_file=lambda url: b"OLD",
        delay=0,
    )
    path = dest / "9" / "a.hwpx"
    stamp = path.stat().st_mtime_ns
    fss_b0000291.crawl_seed(
        [row],
        dest,
        fetch_html=lambda ntt_id: html,
        fetch_file=lambda url: b"OLD",
        delay=0,
    )
    assert path.read_bytes() == b"OLD"
    assert path.stat().st_mtime_ns == stamp
    assert not (dest / "9" / "a__2.hwpx").exists()
    fss_b0000291.crawl_seed(
        [row],
        dest,
        fetch_html=lambda ntt_id: html,
        fetch_file=lambda url: b"NEW",
        delay=0,
    )
    assert path.read_bytes() == b"NEW"
    assert not (dest / "9" / "a__2.hwpx").exists()

    pair = """
    <dl class="bd-info">
      <div><dt>감사인</dt><dd>둘회계법인</dd></div>
      <div><dt>감시대상기간</dt><dd>2021-04-01~2022-03-31</dd></div>
      <div><dt>개선권고일</dt><dd>2023-03-15</dd></div>
      <div><dt>공시종료일</dt><dd>2026-03-15</dd></div>
    </dl>
    <a class="btn-attach-download" href="/fss/cmmn/file/fileDown.do?fileSn=1">report.hwpx</a>
    <a class="btn-attach-download" href="/fss/cmmn/file/fileDown.do?fileSn=2">report.hwpx</a>
    """
    other = tmp_path / "pair"
    bodies = {"fileSn=1": b"FIRST", "fileSn=2": b"SECOND"}

    def fetch_file(url):
        for key, body in bodies.items():
            if key in url:
                return body
        raise AssertionError(url)

    fss_b0000291.crawl_seed(
        [_row(7, attach="report.hwpx")],
        other,
        fetch_html=lambda ntt_id: pair,
        fetch_file=fetch_file,
        delay=0,
    )
    fss_b0000291.crawl_seed(
        [_row(7, attach="report.hwpx")],
        other,
        fetch_html=lambda ntt_id: pair,
        fetch_file=fetch_file,
        delay=0,
    )
    assert (other / "7" / "report.hwpx").read_bytes() == b"FIRST"
    assert (other / "7" / "report__2.hwpx").read_bytes() == b"SECOND"
    assert not (other / "7" / "report__3.hwpx").exists()
    bodies["fileSn=2"] = b"SECOND-NEW"
    fss_b0000291.crawl_seed(
        [_row(7, attach="report.hwpx")],
        other,
        fetch_html=lambda ntt_id: pair,
        fetch_file=fetch_file,
        delay=0,
    )
    assert (other / "7" / "report.hwpx").read_bytes() == b"FIRST"
    assert (other / "7" / "report__2.hwpx").read_bytes() == b"SECOND-NEW"
    assert not (other / "7" / "report__3.hwpx").exists()

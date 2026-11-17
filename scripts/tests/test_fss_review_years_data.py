# -*- coding: utf-8 -*-
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fss_review_cards import (  # noqa: E402
    PAGE,
    YEAR_FILES,
    iter_year_findings,
    load_year,
    materialize_review_markdown,
    render_year_html,
    year_mark,
)

# bytes, sha256
YEAR_FILE = {
    "2019": (46895, "4438ab7f1555c0260e2534cfdb863fbec08349821d9e38554bfe90d8098a79a0"),
    "2020": (68603, "6e426ceea925c53b6d5f360b3f938c5160d13aa1fe59b078c163467f1ca710a8"),
    "2022": (311350, "3a940a00fd7c5ddcae8cc3db2c06e7e5a58a365666a71181bd218656621b714b"),
    "2023": (274221, "4fa7e4e73ffb94fb33571b22e6566159037f47c296e6cc872e3f0ab66afeb891"),
    "2024": (339837, "ff7b6768ab358fdf7f3a99ca7996267e5e40859c2d462ad60908dea5fdec663b"),
}

# block bytes, block sha256, BeautifulSoup div sha256
YEAR_BLOCK = {
    "2019": (
        36956,
        "8e3dfe9745623cac3d9d745046defa4cf7684bce1b5feef84e0c1e465fd74a2c",
        "fb13f1d4d54aaf8126f97bf802feb37ef40b2fee7852694ca22c3215e607d098",
    ),
    "2020": (
        54424,
        "dede15b918ef35eca983ee1285a6de504b05465413910834081f98652d58628f",
        "d2063bb5eec1fa4b5bcc9c96fc0a8fbab315e6335ca580a1bc94813088152a62",
    ),
    "2022": (
        266851,
        "c8b458249a19d9edee8ea9f4a860c1a31fa53b1bcde0e04d6108219a306dcbff",
        "f28b048692eeca4ab3741a60e3c616d2d2ca3b3931567ba4ae7e4332ddde16eb",
    ),
    "2023": (
        231418,
        "3a4e9dadf551d8fe4a3680ffd497944cbb514a14f8c3596b1f917b6934add654",
        "eee534837396dbd9fe3cdb9490e0902dc1ddb6cee867863a751c498b81049886",
    ),
    "2024": (
        282777,
        "2cf4ae49a081700f573a7397a24a17d7df70f840f30b5fa2a786cda0d625204f",
        "d58f37b1fb3a0eb25143e9ff5d116f796d42f8b18073075e2cc2cf32688806dc",
    ),
}

HOOK_YEARS = ("2019", "2020", "2021", "2022", "2023", "2024", "2025")


@pytest.fixture(scope="module")
def materialized_page() -> str:
    return materialize_review_markdown(PAGE.read_text(encoding="utf-8"))


@pytest.mark.parametrize("year", list(YEAR_FILE))
def test_year_data_file_matches_sha_bytes_and_canonical_json(year):
    nbytes, digest = YEAR_FILE[year]
    raw = YEAR_FILES[year].read_bytes()
    assert len(raw) == nbytes
    assert hashlib.sha256(raw).hexdigest() == digest
    text = raw.decode("utf-8")
    assert "\r" not in text
    data = json.loads(text)
    assert text == json.dumps(data, ensure_ascii=False, indent=2) + "\n"


@pytest.mark.parametrize("year", list(YEAR_BLOCK))
def test_render_year_html_matches_block_sha_and_hidden_opener(year):
    nbytes, block_sha, _div_sha = YEAR_BLOCK[year]
    rendered = render_year_html(load_year(year))
    raw = rendered.encode("utf-8")
    assert len(raw) == nbytes
    assert hashlib.sha256(raw).hexdigest() == block_sha
    opening = rendered.split(">", 1)[0]
    assert opening.startswith('<div class="fss-year"')
    assert " hidden" in opening


@pytest.mark.parametrize("year", list(YEAR_BLOCK))
def test_materialized_year_div_matches_beautifulsoup_sha(year, materialized_page):
    _nbytes, _block_sha, div_sha = YEAR_BLOCK[year]
    div = BeautifulSoup(materialized_page, "html.parser").select_one(
        f'div.fss-year[data-year="{year}"]'
    )
    assert div is not None
    assert hashlib.sha256(str(div).encode("utf-8")).hexdigest() == div_sha


def test_source_index_has_one_hook_per_year_and_no_static_year_div():
    source = PAGE.read_text(encoding="utf-8")
    assert '<div class="fss-year"' not in source
    for year in HOOK_YEARS:
        assert source.count(year_mark(year)) == 1


# 손전사에서 마지막 불릿(종결만 있던 줄)이 빠지면 문장이 연결어미로 끊긴다.
# 끝 공백을 버린 뒤 마지막 글자가 구두점이면 통과한다. 원문은 쉼표로 끊기도 한다.
# 그렇지 않으면 마지막 어절이 연결어미 「고」(용언 어간 + 고) 또는 「거나」로
# 끝나면 실패한다. 「미신고」처럼 명사 끝음절이 「고」인 경우는 연결어미가 아니다.
_DANGLING_CONNECTIVE = re.compile(r"(?:하|되|있|않|같|싶|겠|었|았|였)고$|거나$")


def _dangling_connective_token(text: str) -> str | None:
    stripped = text.rstrip()
    if not stripped or unicodedata.category(stripped[-1]).startswith("P"):
        return None
    token = stripped.split()[-1]
    if _DANGLING_CONNECTIVE.search(token):
        return token
    return None


def test_finding_texts_do_not_end_on_a_dangling_connective():
    review_dir = next(iter(YEAR_FILES.values())).parent
    paths = sorted(review_dir.glob("year-*.json"))
    assert paths
    offenders = []
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        for firm_name, finding in iter_year_findings(data):
            token = _dangling_connective_token(finding["text"])
            if token is not None:
                offenders.append(f"{path.name} {firm_name} …{token}")
    assert offenders == []

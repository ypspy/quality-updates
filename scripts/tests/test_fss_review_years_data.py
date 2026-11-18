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
    "2022": (311349, "1ff091e283eb705480a6ed9b8f53a16ebd5107173a400f786628000b2c38bfb4"),
    "2023": (274223, "cff5f578f58a112631417f0306fc74994255aa53865f2bda941c48aeaffd95b6"),
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
        266850,
        "5300cac92bb5c3dec1b40c47f6ecedf552d56b198de4c3f82f06c71c30b0cafc",
        "4c150effed6afb5f2d1c242a0285916d4f486ca436242cc15de6b05e63ea2dd2",
    ),
    "2023": (
        231420,
        "306b7303be8fc06760d5411e15b2a3f5c068d523de293d3399c89a8e456e328d",
        "fd560864f0e1b4c100cdbb686d9cc929bb417340fec69dc9762ce5eec41550c1",
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


# 원문 PDF 띄어쓰기·문장부호 그대로(2026-11-17 사용자 결정 「원문대로 고치는 초안 PR」).
# (연도, 법인, 원문 문구, 손전사 문구) — 2022 원지는 일반회계법인 모음집 p.31 신영 같은 문장,
# 2023 대성삼경은 법인 PDF p.3, 2025 대주는 법인 PDF p.2.
_SOURCE_SPACING = (
    ("2022", "회계법인 원지", "지점에서 보관\u00b7관리하고 있는", "보관\u00b7관리 하고"),
    ("2023", "대성삼경회계법인", "요청하여야 하나 기한을 경과하여 사전심리를 요청한 사례가 있고,", "하나기한을"),
    ("2023", "대성삼경회계법인", "요청한 사례가 있고,", "요청한사례가"),
    ("2025", "대주회계법인", "고용관계 등 발생시 14일 이내에", "발생 시"),
    ("2025", "대주회계법인", "이를 지연 \u2024 미신고한 사례가 발견되었으며,", "지연\u2024미신고한"),
)


def test_three_finding_spacings_follow_the_source_pdf():
    review_dir = next(iter(YEAR_FILES.values())).parent
    for year, firm, source, typed in _SOURCE_SPACING:
        data = json.loads((review_dir / f"year-{year}.json").read_text(encoding="utf-8"))
        texts = [finding["text"] for name, finding in iter_year_findings(data) if name == firm]
        assert sum(source in text for text in texts) == 1, (year, firm, source)
        assert not any(typed in text for text in texts), (year, firm, typed)

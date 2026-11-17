# -*- coding: utf-8 -*-
import hashlib
import json
import sys
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fss_review_cards import (  # noqa: E402
    PAGE,
    YEAR_FILES,
    load_year,
    materialize_review_markdown,
    render_year_html,
    year_mark,
)

# bytes, sha256
YEAR_FILE = {
    "2019": (46895, "4438ab7f1555c0260e2534cfdb863fbec08349821d9e38554bfe90d8098a79a0"),
    "2020": (68603, "6e426ceea925c53b6d5f360b3f938c5160d13aa1fe59b078c163467f1ca710a8"),
    "2022": (311293, "555ab996ef22a1e8a475308d739a7046e5e03589e0f7f49e7166f028a3b77bf6"),
    "2023": (274170, "f421a76990ef09ef92ab0993344427eb3077e7e63aeb482ec636cf07f6574e9e"),
    "2024": (339830, "78192da973a4b77854bd921d4ad3109026c497f6c1867a39b85ace6cf83b895e"),
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
        266794,
        "e6a359c8c209a3a1988705d8318e9f281ecb5fcd746d61d7995603bbc0ab080c",
        "0a4f23296695208d76dd4f53d9813cf8e3a0da4945860cbfd3210d733b106a2f",
    ),
    "2023": (
        231367,
        "e375463292f499e75ea3078cd9e450f38502a8253158a693286005ae1363cd69",
        "a04efa16f933d3aac44bb98434af3bc21160d028790e140c50d77a3f38416baf",
    ),
    "2024": (
        282770,
        "44a238e73063459aa20de353e1d533570c48c936d112ded5e3d94e417c9d96ce",
        "dd252ed36a6f3debb59d9c5c831dfab643bb3dc51a4918b5f4649b0087f87763",
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

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
    "2024": (341456, "a5304a47e67eb0373ee3b8a3ef3df3f8b616720cbd6d0472b7ae9fb982f5640b"),
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
        284396,
        "f289a7037887c499e063aaf7efcf6fef52ccf73c5701b7faeba427d87d833f82",
        "802cd67a04f190eb7873ffe6d90ad92c3fdcd055fa7b029a05ed057547aed539",
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
# 끝 공백을 버린 뒤 끝의 쉼표·쌍반점(반각·전각·「、」, 여러 개·앞 공백 포함)을 떼고 그 앞 어절을 본다
# (「…하고,」「…하고 ,」「…하고，」). 그 밖의 구두점으로 끝나면 통과한다. 마지막 어절이 연결어미로
# 끝나면 걸린다. 어간 쪽은 열린 규칙이 아니라 아래에 적은 음절 목록이다.
# 연결어미: 「고」(수행하고·이루어지고·없고·시키고, 줄인 과거 했고·됐고·왔고·줬고·켰고),
# 「며」(없으며·되었으며·시키며·주며), 「으나」(하였으나·않으나), 「거나」, 「지만」, 「면서」,
# 「하여(서)」, 「되어(서)」.
# 걸지 않는 것: 「미신고」「보고」「참고」(명사 끝음절 「고」), 「확인하였나」「없었나」(의문형),
# 「3월까지만」(「까지」+「만」), 「수행한다면서」(인용형). 「수행하나」「수행하면」은 명사 끝(「중 하나」 등)과
# 구별이 어려워 걸지 않는다.
_DANGLING_CONNECTIVE = re.compile(
    r"(?:하|되|있|없|않|같|싶|겠|었|았|였|했|됐|왔|줬|켰|키|지|이)고$"
    r"|(?:하|되|있|없|않|이|으|었|았|였|키|주)며$"
    r"|으나$"
    r"|거나$|(?<!까)지만$|(?<![다라])면서$|하여서?$|되어서?$"
)
_SOFT_STOPS = frozenset(",;\u3001\uff0c\uff1b")

# 원문 PDF 불릿도 쉼표로 끝나고 다음 불릿·하위 불릿으로 이어지는 문단(손전사 탈락 아님).
# (연도 파일, 법인, 마지막 어절) — 2023 대성삼경 법인 PDF p.3, 2024 안진 법인 PDF p.3,
# 2025 대주 법인 PDF p.2. 예외가 데이터에서 사라지면 이 표도 지운다.
_SOURCE_ENDS_ON_COMMA = frozenset(
    {
        ("year-2023.json", "대성삼경회계법인", "있고,"),
        ("year-2024.json", "안진회계법인", "발견되었고,"),
        ("year-2025.json", "대주회계법인", "발견되었으며,"),
    }
)


def _dangling_connective_token(text: str) -> str | None:
    stripped = text.rstrip()
    body = stripped
    while body and body[-1] in _SOFT_STOPS:
        body = body[:-1].rstrip()
    if not body:
        return None
    if body == stripped and unicodedata.category(stripped[-1]).startswith("P"):
        return None
    word = body.split()[-1]
    if _DANGLING_CONNECTIVE.search(word):
        return word + "".join(stripped[len(body):].split())
    return None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("체계적인 조서관리를 수행하고", "수행하고"),
        ("발행 통제가 수행되고", "수행되고"),
        ("거래내역만 확인하고  ", "확인하고"),
        ("입출고 내역을 기록하거나", "기록하거나"),
        ("상호검토가 실질적으로 이루어지고", "이루어지고"),
        ("확인하는 절차가 없으며", "없으며"),
        ("보관하고 있으며", "있으며"),
        ("절차를 수립하고 있으나", "있으나"),
        ("모니터링을 실시하였지만", "실시하였지만"),
        ("감사조서를 작성하면서", "작성하면서"),
        ("업무를 수행하여", "수행하여"),
        ("조서관리를 수행하고,", "수행하고,"),
        ("사례가 발견되었으며,", "발견되었으며,"),
        ("사전심리를 요청한 사례가 있고;", "있고;"),
        ("교육을 이수시키고", "이수시키고"),
        ("업무를 이관했고", "이관했고"),
        ("절차가 생략됐고", "생략됐고"),
        ("검토를 거치지 않도록 하며", "하며"),
        ("구성원에게 이수시키며", "이수시키며"),
        ("업무를 수행하여서", "수행하여서"),
        ("서명이 누락되어서", "누락되어서"),
        ("관리대장을 작성하였으나", "작성하였으나"),
        ("조서관리를 수행하고 ,", "수행하고,"),
        ("조서관리를 수행하고,,", "수행하고,,"),
        ("조서관리를 수행하고\uff0c", "수행하고\uff0c"),
        ("조서관리를 수행하고\u3001", "수행하고\u3001"),
        ("검토를 확인하였나", None),
        ("관련 절차가 없었나", None),
        ("2024년 3월까지만", None),
        ("전기까지만", None),
        ("수행한다면서", None),
        ("운영이 미흡함", None),
        ("수행하고 있지 아니함", None),
        ("이를 지연 \u2024 미신고", None),
        ("결과를 보고", None),
        ("관련 규정을 참고", None),
        ("미신고,", None),
        ("운영이 미흡함.", None),
        ("수행하고 있음)", None),
        ("", None),
        ("   ", None),
        (",", None),
    ],
)
def test_dangling_connective_token_cases(text, expected):
    assert _dangling_connective_token(text) == expected


def test_finding_texts_do_not_end_on_a_dangling_connective():
    review_dir = next(iter(YEAR_FILES.values())).parent
    paths = sorted(review_dir.glob("year-*.json"))
    assert paths
    offenders = []
    allowed = []
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        for firm_name, finding in iter_year_findings(data):
            token = _dangling_connective_token(finding["text"])
            if token is None:
                continue
            key = (path.name, firm_name, token)
            if key in _SOURCE_ENDS_ON_COMMA:
                allowed.append(key)
            else:
                offenders.append(f"{path.name} {firm_name} …{token}")
    assert offenders == []
    # 예외 하나는 문단 하나만 덮는다(같은 키가 두 번 나오면 실패).
    assert sorted(allowed) == sorted(_SOURCE_ENDS_ON_COMMA)


# 원문 PDF 띄어쓰기·문장부호 그대로(2026-11-17 사용자 결정 「원문대로 고치는 초안 PR」).
# (연도, 법인, 원문 문구, 손전사 문구) — 2022 원지는 법인 PDF p.2와 일반회계법인 모음집 p.10이
# 모두 「보관·관리」 뒤에서 줄을 바꾸므로, 띄어쓰기는 같은 모음집 p.31 신영의 같은 문장을 따른다.
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

"""공개 본문 린트."""

from pathlib import Path

import pytest

from lint_public_body import (
    DEFAULT_MAX_HEADING_REPEATS,
    load_allow_list,
    lint_repo,
    lint_text,
    partition_findings,
)

REPO = Path(__file__).resolve().parents[2]


def rules(text: str, rel: str = "docs/quality-updates/2099/x.md") -> list[str]:
    return [item.rule for item in lint_text(rel, text)]


def test_process_instruction_is_an_error():
    text = "    - 의결서는 로컬에 없다. 보도 링크는 위 URL이다.\n"
    found = lint_text("a.md", text)
    assert {item.rule for item in found} >= {"process_instruction"}
    assert any("의결서는 로컬에 없다" in item.message for item in found)


def test_missing_decision_document_phrase_is_an_error():
    text = "        - (출처) 의결서 공개본은 미입수\n"
    found = lint_text("a.md", text)
    assert {item.rule for item in found} >= {"process_instruction"}
    assert any("의결서 공개본은 미입수" in item.message for item in found)


def test_table_instruction_and_summary_phrases():
    text = (
        "- 지적사항·조치 금액·회사 구분은 보도 첨부·본문을 풀어 표로 적지 않는다.\n"
        "- 요약은 표의 제목 범위만 적는다.\n"
        "- 질의 문답이 없으면 논의·진술 문면은 옮기지 않는다.\n"
    )
    found = lint_text("a.md", text)
    assert any("표로 적지 않는다" in item.message for item in found)
    assert any("요약은 표의" in item.message for item in found)
    assert any("질의 문답이 없으면" in item.message for item in found)
    assert any("논의·진술 문면은" in item.message for item in found)


def test_internal_memos_are_errors():
    text = "##### Mint notes\n열린 질문\n보류함\nMint 분류\nMint r2 확인\n"
    found = lint_text("a.md", text)
    assert all(item.rule == "internal_memo" for item in found)
    assert len(found) >= 5


def test_minutes_page_numbers_are_errors():
    text = (
        "- (의사록) 상정하고 설명함\n"
        "- (의사록) -2-\n"
        "- 10-\n"
    )
    found = lint_text("a.md", text)
    pages = [item for item in found if item.rule == "minutes_page"]
    assert len(pages) == 2


def test_legitimate_minutes_regulation_is_not_a_page_number():
    text = "        - (의사록) 증권선물위원회 의사록 작성사항 상세 규정(제8조)\n"
    assert rules(text) == []


def test_mechanical_sentences_are_errors():
    text = (
        "- 결과는 원안 의결함이다\n"
        "- 결과는 각각 원안 의결함이다\n"
        "- 질의 문답이 의사록에 있다. 문면은 위 조치내역 인용과 같다\n"
    )
    found = lint_text("a.md", text)
    assert {item.rule for item in found} == {"mechanical_sentence"}
    assert len(found) >= 3


def test_descriptive_summary_is_not_process_or_mechanical():
    """2014·2026에 있는 실제 요약·원문 표현은 통과해야 한다."""
    text = (
        "- (의결) 질의 문답 없이 원안 의결함\n"
        "- 위원 질의 문답은 없음\n"
        "- 보도가 표를 싣지 않아 감사인 표를 만들지 않음\n"
        "- 원문에 없는 칸은 미입수이다\n"
        "- 위원 논의는 미공개\n"
        "- 보고자는 그 절차를 대체하지 않는다고 설명함\n"
        "- 기존 이자율지표가 변경되지 않는다고 가정하는 예외규정\n"
    )
    assert rules(text) == []


def test_trailing_dot_host_is_an_error():
    text = "- [예고](https://fsc.go.kr./po040301/view?noticeId=4160)\n"
    found = lint_text("a.md", text)
    assert [item.rule for item in found] == ["trailing_dot_host"]


def test_normal_host_is_ok():
    text = "- [보도](https://fsc.go.kr/no010101/87293?curPage=15)\n"
    assert rules(text) == []


def test_heading_url_repeated_more_than_three_times_fails():
    url = "https://fsc.go.kr/no010101/70196?curPage=1"
    items = "\n".join(
        f"- (12-01-11) [[증선위]같은 보도 {i}]({url})\n\n    !!! note \"조사·감리결과 지적사항 및 조치내역\"\n"
        for i in range(4)
    )
    text = f"#### 제재 의결\n\n{items}\n#### 고시/공고/훈령\n"
    found = lint_text("a.md", text)
    assert any(item.rule == "repeated_heading_url" and "4회" in item.message for item in found)


def test_heading_url_three_times_is_allowed():
    url = "https://fsc.go.kr/no010101/70196"
    items = "\n".join(
        f"- (12-01-11) [같은 보도 {i}]({url})\n" for i in range(3)
    )
    text = f"#### 제재 의결\n\n{items}\n#### 고시/공고/훈령\n"
    assert "repeated_heading_url" not in rules(text)


def test_unpublished_getfile_source_repeats_do_not_fail():
    """2026 미보도 항목은 같은 의결서 getFile을 안건마다 한 번씩 쓴다."""
    src = "https://www.fsc.go.kr/comm/getFile?srvcId=BBSTY1&upperNo=87251&fileTy=ATTACH&fileNo=2"
    boxes = "\n".join(
        f"    !!! info \"안건 분석\"\n\n        - (출처) [의결서]({src}) 의결 제{120+i}호\n"
        for i in range(8)
    )
    text = (
        "#### 제재 의결\n\n"
        "- (26-05-07) [조치](https://fsc.go.kr/no010101/87000)\n\n"
        "- 분기중 미보도 항목\n\n"
        f"{boxes}\n"
        "#### 고시/공고/훈령\n"
    )
    assert rules(text) == []


def test_html_comments_are_ignored():
    text = (
        "<!-- Mint notes 열린 질문 보류함 의결서는 로컬에 없다 -->\n"
        "- (26-07-09) [조치](https://fsc.go.kr/no010101/87293)\n"
    )
    assert rules(text) == []


def test_iso_dates_are_not_page_numbers():
    text = "period:\n  start: 2014-01-01\n  end: 2014-03-31\n- (14-01-22) 항목\n"
    assert "minutes_page" not in rules(text)


def test_allow_list_is_warning_not_error(tmp_path: Path):
    root = tmp_path
    target = root / "docs" / "quality-updates" / "2012"
    target.mkdir(parents=True)
    (target / "2012-01-01_to_2012-03-31.md").write_text(
        "- 의결서는 로컬에 없다.\n", encoding="utf-8"
    )
    other = root / "docs" / "quality-updates" / "2026"
    other.mkdir(parents=True)
    (other / "2026-07-01_to_2026-09-30.md").write_text(
        "- (26-07-09) [조치](https://fsc.go.kr/no010101/87293)\n", encoding="utf-8"
    )
    allow = {"docs/quality-updates/2012/2012-01-01_to_2012-03-31.md"}
    findings = lint_repo(root, allow=allow)
    errors, warnings = partition_findings(findings, allow)
    assert errors == []
    assert any(item.rule == "process_instruction" for item in warnings)
    assert all(item.path.endswith("2012-01-01_to_2012-03-31.md") for item in warnings)


def test_allow_list_loader_ignores_comments(tmp_path: Path):
    path = tmp_path / "allow.txt"
    path.write_text(
        "# 임시 허용 목록. 2단계·3단계에서 지운다.\n"
        "docs/quality-updates/2012/2012-01-01_to_2012-03-31.md\n\n",
        encoding="utf-8",
    )
    assert load_allow_list(path) == {
        "docs/quality-updates/2012/2012-01-01_to_2012-03-31.md"
    }


@pytest.mark.parametrize(
    "rel",
    [
        "docs/quality-updates/2026/2026-07-01_to_2026-09-30.md",
        "docs/quality-updates/2026/2026-04-01_to_2026-06-30.md",
        "docs/quality-updates/2026/2026-01-01_to_2026-03-31.md",
        "docs/quality-updates/2014/2014-01-01_to_2014-03-31.md",
    ],
)
def test_model_years_have_no_hard_errors(rel: str):
    path = REPO / rel
    if not path.is_file():
        pytest.skip(f"missing {rel}")
    # 고시/공고 링크의 trailing-dot은 경고로만 남기고, 그 밖의 오탐은 실패다.
    findings = lint_text(rel, path.read_text(encoding="utf-8"))
    hard = [item for item in findings if item.rule != "trailing_dot_host"]
    assert hard == [], hard


def test_2012_q1_fails_without_allow_list():
    rel = "docs/quality-updates/2012/2012-01-01_to_2012-03-31.md"
    path = REPO / rel
    if not path.is_file():
        pytest.skip("missing 2012 Q1")
    found = lint_text(rel, path.read_text(encoding="utf-8"))
    assert {item.rule for item in found} >= {
        "process_instruction",
        "mechanical_sentence",
        "minutes_page",
        "repeated_heading_url",
    }


def test_default_threshold_is_three():
    assert DEFAULT_MAX_HEADING_REPEATS == 3

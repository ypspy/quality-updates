import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from write_quarterly_record import write_record

QUARTER = """### 금융위원회

#### 보도자료

- (26-07-09) [사업보고서 등에 대한 조사·감리결과 조치](https://fsc.go.kr/no010101/87293)

    <!-- source: pdf|downloads/260708.pdf -->

    !!! note "주요 내용"

        - 과징금 10백만원

- (26-07-09) [같은 제목](https://fsc.go.kr/no010101/2)

- (26-07-10) [같은 제목](https://fsc.go.kr/no010101/3)

- (26-07-11) [건너뜀](https://fsc.go.kr/no010101/4)

    <!-- skip -->

## Appendix

- (26-07-12) [부록 항목](https://fsc.go.kr/no010101/5)
"""


def test_write_record_creates_facts_and_keeps_existing_bytes(tmp_path):
    code, message = write_record(
        QUARTER, "2026-07-01_to_2026-09-30", "사업보고서 등에 대한 조사·감리결과 조치",
        ["과징금 10백만원", "사이트 노트에 없는 문단 번호 3"], None, "create", tmp_path,
    )
    assert code == 0
    assert message.startswith("wrote ")
    path = tmp_path / "data" / "quarterly-processed" / "2026-07-01_to_2026-09-30"
    saved = next(path.glob("26-07-09-*.md"))
    text = saved.read_text(encoding="utf-8")
    assert "https://fsc.go.kr/no010101/87293" in text
    assert "downloads/260708.pdf" in text
    assert "## 확인한 사실" in text
    assert "문단 번호 3" in text
    assert "부록 항목" not in text
    saved.write_text(text + "보존\n", encoding="utf-8")
    code, message = write_record(
        QUARTER, "2026-07-01_to_2026-09-30", "사업보고서 등에 대한 조사·감리결과 조치",
        ["다른 사실"], None, "create", tmp_path,
    )
    assert code == 0
    assert message.startswith("kept ")
    assert saved.read_text(encoding="utf-8").endswith("보존\n")


def test_append_facts_and_minutes_do_not_rewrite_existing_sections(tmp_path):
    write_record(
        QUARTER, "2026-07-01_to_2026-09-30", "사업보고서 등에 대한 조사·감리결과 조치",
        ["과징금 10백만원"], None, "create", tmp_path,
    )
    code, _message = write_record(
        QUARTER, "2026-07-01_to_2026-09-30", "사업보고서 등에 대한 조사·감리결과 조치",
        ["과징금 10백만원", "추가 사실"], None, "append-facts", tmp_path,
    )
    assert code == 0
    saved = next((tmp_path / "data" / "quarterly-processed" / "2026-07-01_to_2026-09-30").glob("*.md"))
    text = saved.read_text(encoding="utf-8")
    assert text.count("과징금 10백만원") == 1
    assert "추가 사실" in text
    code, _message = write_record(
        QUARTER, "2026-07-01_to_2026-09-30", "사업보고서 등에 대한 조사·감리결과 조치",
        ["원안 의결함"], None, "append-minutes", tmp_path,
    )
    assert code == 0
    text = saved.read_text(encoding="utf-8")
    assert "## 위원 논의" in text
    assert "원안 의결함" in text
    assert text.index("## 확인한 사실") < text.index("## 위원 논의")
    code, message = write_record(
        QUARTER, "2026-07-01_to_2026-09-30", "사업보고서 등에 대한 조사·감리결과 조치",
        ["두 번째 논의"], None, "append-minutes", tmp_path,
    )
    assert code == 0
    assert message.startswith("kept ")
    assert saved.read_text(encoding="utf-8").count("## 위원 논의") == 1


def test_skip_duplicate_title_and_empty_facts(tmp_path):
    code, message = write_record(QUARTER, "2026-07-01_to_2026-09-30", "건너뜀", ["사실"], None, "create", tmp_path)
    assert code == 0
    assert message.startswith("skipped")
    assert not (tmp_path / "data").exists()
    code, message = write_record(QUARTER, "2026-07-01_to_2026-09-30", "같은 제목", ["사실"], None, "create", tmp_path)
    assert code == 1
    code, message = write_record(QUARTER, "2026-07-01_to_2026-09-30", "같은 제목", ["사실"], "26-07-10", "create", tmp_path)
    assert code == 0
    assert message.startswith("wrote ")
    code, message = write_record(QUARTER, "2026-07-01_to_2026-09-30", "없는 제목", ["사실"], None, "create", tmp_path)
    assert code == 1
    code, message = write_record(
        QUARTER, "2026-07-01_to_2026-09-30", "사업보고서 등에 대한 조사·감리결과 조치",
        [], None, "create", tmp_path,
    )
    assert code == 1

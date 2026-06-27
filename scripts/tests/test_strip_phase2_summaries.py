from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from strip_phase2_summaries import strip_phase2_from_text

SAMPLE_WITH_ES = """---
title: test
---

## Executive Summary

분기 테마 문장.

#### 기관별 요약

!!! success ""

    === "금융감독원"
        - bullet

---

#### 시사점

!!! success ""

    === "기업"
        - bullet

### 금융감독원

#### 보도자료

- (25-01-01) [제목](https://example.com)
"""

SAMPLE_LEGACY = """---
title: test
---

### 요약

- 기간 : 2022년 …
- 주요 사항

### 금융감독원

#### 보도자료
"""


def test_strip_removes_executive_summary_block():
    out = strip_phase2_from_text(SAMPLE_WITH_ES)
    assert "Executive Summary" not in out
    assert "기관별 요약" not in out
    assert "#### 시사점" not in out
    assert "### 금융감독원" in out
    assert "https://example.com" in out


def test_strip_removes_legacy_summary():
    out = strip_phase2_from_text(SAMPLE_LEGACY)
    assert "### 요약" not in out.split("---")[-1]
    assert "### 금융감독원" in out


def test_strip_idempotent():
    once = strip_phase2_from_text(SAMPLE_WITH_ES)
    twice = strip_phase2_from_text(once)
    assert once == twice


SAMPLE_NO_FM = """### Executive Summary

테마.

#### 기관별 요약

!!! success ""

    === "금융감독원"
        - bullet

### 금융감독원

#### 보도자료
"""


def test_strip_without_front_matter():
    out = strip_phase2_from_text(SAMPLE_NO_FM)
    assert "Executive Summary" not in out
    assert out.startswith("### 금융감독원")

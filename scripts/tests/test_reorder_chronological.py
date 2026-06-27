# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reorder_chronological import process_file


SAMPLE = """\
### 금융감독원

#### 보도자료

- (26-03-31) [newest](https://www.fss.or.kr/fss/bbs/B0000188/view.do?nttId=1)
<!-- no_summary -->

- (26-01-08) [oldest](https://www.fss.or.kr/fss/bbs/B0000188/view.do?nttId=2)

#### 회계감독 동향자료

- (26-03-01) [trend new](https://www.fss.or.kr/fss/bbs/B0000154/view.do?nttId=3)
- (26-01-01) [trend old](https://www.fss.or.kr/fss/bbs/B0000154/view.do?nttId=4)

### 금융위원회

#### 보도자료

- (26-03-31) [fsc new](https://fsc.go.kr/no010101/1)
- (26-01-01) [fsc old](https://fsc.go.kr/no010101/2)

---

## Appendix A. Complete List of Retrieved Items (Unfiltered)

        - (26-03-31) [appendix newest](https://example.com/a-new)
        - (26-01-08) [appendix oldest](https://example.com/a-old)
"""


def test_reorder_per_subsection_preserves_headers(tmp_path):
    md = tmp_path / "sample.md"
    md.write_text(SAMPLE, encoding="utf-8")

    assert process_file(md) is True
    text = md.read_text(encoding="utf-8")

    assert "### 금융감독원" in text
    assert "### 금융위원회" in text
    assert text.index("### 금융감독원") < text.index("#### 보도자료")
    assert text.index("#### 보도자료") < text.index("#### 회계감독 동향자료")
    assert text.index("#### 회계감독 동향자료") < text.index("### 금융위원회")

    body, appendix = text.split("## Appendix A.", 1)
    fss_press = body.split("#### 회계감독 동향자료")[0]
    assert fss_press.index("- (26-01-08)") < fss_press.index("- (26-03-31)")

    trend = body.split("#### 회계감독 동향자료")[1].split("### 금융위원회")[0]
    assert trend.index("- (26-01-01)") < trend.index("- (26-03-01)")

    assert appendix.index("- (26-03-31)") < appendix.index("- (26-01-08)")

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crawler.unified import FSC_MAIN_HEADINGS
from repair_quarterly_structure import SECTIONS


def test_fsc_headings_match_repair_sections():
    repair = dict(SECTIONS)["금융위원회"]
    assert FSC_MAIN_HEADINGS == repair
    assert FSC_MAIN_HEADINGS.index("보도자료") < FSC_MAIN_HEADINGS.index("제재 의결")
    assert FSC_MAIN_HEADINGS.index("제재 의결") < FSC_MAIN_HEADINGS.index("고시/공고/훈령")

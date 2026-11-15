"""빌드 직전에 감리연도 2025 블록을 데이터 파일에서 넣는다.

페이지 소스는 훅만 둔다. 브라우저가 데이터를 따로 받지 않아도 지금과 같은 HTML이 된다.
F004 이행내역은 이 hook 출력에만 붙인다. 연도 블록을 다시 읽어 바이트를 비교하는 검증과 고정 해시를 그대로 두려는 것이다.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fss_f004_followup import inject_f004_followup  # noqa: E402
from fss_review_cards import materialize_review_markdown  # noqa: E402


def on_page_markdown(markdown, page, config, files):
    del config, files
    src = getattr(page.file, "src_uri", None) or getattr(page.file, "src_path", "")
    if str(src).replace("\\", "/") == "fss-review/index.md":
        return inject_f004_followup(materialize_review_markdown(markdown))
    return markdown

"""빌드 직전에 감리연도 2025 블록을 데이터 파일에서 넣는다.

페이지 소스는 훅만 둔다. 브라우저가 데이터를 따로 받지 않아도 지금과 같은 HTML이 된다.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fss_review_cards import materialize_review_markdown  # noqa: E402


def on_page_markdown(markdown, page, config, files):
    del config, files
    src = getattr(page.file, "src_uri", None) or getattr(page.file, "src_path", "")
    if str(src).replace("\\", "/") == "fss-review/index.md":
        return materialize_review_markdown(markdown)
    return markdown

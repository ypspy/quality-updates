"""2024년 제재 의결 순서 소급이 되돌아가지 않게 잠근다.

범위는 2024년 분기 문서 4개뿐이다. 다른 연도 파일은 읽지 않는다.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
YEAR_DIR = REPO / "docs/quality-updates/2024"
FILES = [
    YEAR_DIR / "2024-01-01_to_2024-03-31.md",
    YEAR_DIR / "2024-04-01_to_2024-06-30.md",
    YEAR_DIR / "2024-07-01_to_2024-09-30.md",
    YEAR_DIR / "2024-10-01_to_2024-12-31.md",
]

MEASURE_TITLES = {
    "조사·감리결과 지적사항 및 조치내역",
    "조사·감리결과 최종 과징금 부과",
    "감리결과 지적사항 및 조치내역 (외부감사법 위반)",
}

# hash-check-2024.md와 같은 방식: `|`로 시작하는 줄(들여쓰기 무시)을
# 원문 그대로 `\n`으로 잇고 마지막 개행을 붙인 SHA-256.
TABLE_SHAS = {
    "7c0e156218bde9b1a4b8387e3d38ca017bc4de540f43adf3280655ba6d2bca74",
    "9da1fb0fbd3ad3c638b5824c64f0c1e4cb99049025e381057f5f2afa46a313be",
    "dd42bf1b629edb078046fe85172eebda246d34d12539e9af8a1fa2401e55e811",
    "48076dfaafc0d42245872d7f7dea80229585dfeb07eb74735f5bb22a18e27432",
    "1226caca8e2f7cd8b93f43e2d9045fe6bcc236d51a4bbdf4a41d23f04937b533",
    "7c73d24577736f57e4bb41ad5c38124857a254e464766fb8348de2721f412d17",
    "deb502db592e0cac5971b42f9a630c351c3fba810fb31d1fcb23be924e6159aa",
    "1d6e6b461ad88e34037116b7a7b6e9217e6a731425e2b6c3dfdeea03cbacd4a2",
    "54938457f40edf18f9e7bf40b8d060c8b9f7c728be269f333ae67c11eed0ccc4",
    "b296531effa1e68f86f9747cefe6a3c04f3b9a245d248343e773769f0534b273",
    "c8935393cb351906a6c95c3626136c2503377fd83b2b1017b1aa7057ac315e13",
    "ef647322083bea25c61eba56fe4f809d591df4632bb19a4a2d48edc5d0e0f6ce",
    "52b242a0dbeaab11d80595f5ad73edf490efc252e0c7c034e45385c4d9b61a71",
    "97de327818cf4a0380916174846f53c59787c1ec3d695602ace929d14487d7ff",
    "70a1f6c7e09c9c0be10cee3590ac16c8823f20d4e29f17bf7c7444c82f3e3eb0",
    "52bb948404d4421193481dac691c63d098bf2d4d0a0b63feb07b0f83a7ccfada",
    "6ac7ee84957805bf3a2ceba5f4ad7a1b279a4c014482a8a507365262e5dc4849",
    "42993cce52dda6e4d503cd76a1b248b122e56309744f1e13599f8a7044682b29",
    "f8a7d01fbf3b43b810abf112db8981a6444a0dcc1c0e73af44e2d29e947fc4f0",
    "c92507d174c8137db4de6b6cd5d8aa87c35967ee50a5831823d862cf280cf735",
    "db1444f74392c8a35595ba003e412bb75d83a8ebea4704b527ce6bc443f2110d",
    "54850c84d531a1bd2932c66dcc882f24dbfb9f1c196e7a0163a2fd4d4c0ff4d9",
    "247591abaa9b455034b1eaf1841d9649b5e48f0f53de576a1ed8faa48a474f3a",
    "32ebb77aa1f4bb4434a4e2cd2410ad4399cd9c5201f9f61483483df24475be71",
    "4fdf2d6d88d74aef1078722f92af7acc5824f4da730d7040c70034ede54db368",
    "58620a6b13bd247b894968040b35e55f3791bcf880eed865b5cd080f44afb73d",
}

# results-23.md + r1-response.md의 26곳 배치. 제재 의결 항목 URL id → 출처 경로.
EXPECTED_SOURCE_PATHS = {
    "81975": "downloads/sanctions/2024-증선위-6차/minutes.pdf",
    "81931": "downloads/sanctions/2024-금융위-5차/minutes.pdf",
    "81875": "downloads/sanctions/2024-증선위-5차/minutes.pdf",
    "81816": "downloads/sanctions/2024-증선위-4차/minutes.pdf",
    "81693": "downloads/sanctions/2024-증선위-3차/minutes.pdf",
    "82496": "downloads/sanctions/2024-증선위-12차/minutes.pdf",
    "82374": "downloads/sanctions/2024-금융위-10차/minutes.pdf",
    "82334": "downloads/sanctions/2024-증선위-10차/minutes.pdf",
    "82248": "downloads/sanctions/2024-증선위-9차/minutes.pdf",
    "82136": "downloads/sanctions/2024-금융위-7차/minutes.pdf",
    "82105": "downloads/sanctions/2024-증선위-7차/minutes.pdf",
    "82052": "downloads/sanctions/2024-금융위-6차/minutes.pdf",
    "83067": "downloads/sanctions/2024-증선위-16차/minutes.pdf",
    "83022": "downloads/sanctions/2024-금융위-15차/minutes.pdf",
    "82685": "downloads/sanctions/2024-증선위-14차/minutes.pdf",
    "82651": "downloads/sanctions/2024-금융위-13차/minutes.pdf",
    "82599": "downloads/sanctions/2024-증선위-13차/minutes.pdf",
    "83662": "downloads/sanctions/2024-증선위-22차/minutes.pdf",
    "83585": "downloads/sanctions/2024-금융위-21차/minutes.pdf",
    "83525": "downloads/sanctions/2024-증선위-21차/minutes.pdf",
    "83470": "downloads/sanctions/2024-금융위-20차/minutes.pdf",
    "83438": "downloads/sanctions/2024-증선위-20차/minutes.pdf",
    "83348": "downloads/sanctions/2024-증선위-19차/minutes.pdf",
    "83342": "downloads/sanctions/2024-증선위-19차/minutes.pdf",
    "83244": "downloads/sanctions/2024-증선위-18차/minutes.pdf",
    "83174": "downloads/sanctions/2024-증선위-17차/minutes.pdf",
}
EXTERNAL_AUDIT_ID = "82496"
KAKAO_ID = "83342"
BIDENT_ID = "83348"
URL_ID_RE = re.compile(r"https://(?:www\.)?fsc\.go\.kr/no010101/(\d+)")
SOURCE_RE = re.compile(
    r"<!-- source: pdf\|(downloads/sanctions/2024-[^ \t>]+/minutes\.pdf) -->"
)
ADMONITION_RE = re.compile(r'!!! (note|info) "([^"]+)"')
ITEM_RE = re.compile(r"^- \(")


def table_sha(block: list[str]) -> str:
    rows = [ln for ln in block if ln.lstrip().startswith("|")]
    return hashlib.sha256(("\n".join(rows) + ("\n" if rows else "")).encode("utf-8")).hexdigest()


def url_id(title: str) -> str | None:
    matched = URL_ID_RE.search(title)
    return matched.group(1) if matched else None


def item_source_paths(path: Path, item: dict) -> list[str]:
    """제목과 첫 상자 사이에 있는 의사록 출처 경로."""
    lines = path.read_text(encoding="utf-8").splitlines()
    start = item["title_line"]  # 제목 다음 줄 (1-index)
    end = item["boxes"][0][2] - 1 if item["boxes"] else len(lines)
    block = "\n".join(lines[start:end])
    return SOURCE_RE.findall(block)


def sanction_items(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("#### 제재 의결"))
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if re.match(r"^#{2,4} ", lines[i]) and not lines[i].startswith("#### 제재 의결"):
            end = i
            break
    items: list[dict] = []
    current: dict | None = None
    for i in range(start + 1, end):
        line = lines[i]
        if ITEM_RE.match(line):
            if current is not None:
                items.append(current)
            current = {"title": line, "title_line": i + 1, "boxes": [], "body_by_box": {}}
            continue
        if current is None:
            continue
        admon = ADMONITION_RE.search(line)
        if admon:
            kind, title = admon.group(1), admon.group(2)
            current["boxes"].append((kind, title, i + 1))
            current["body_by_box"][title] = []
            current["_active"] = title
            continue
        if current.get("_active"):
            current["body_by_box"][current["_active"]].append(line)
    if current is not None:
        items.append(current)
    return items


def all_items() -> list[tuple[Path, dict]]:
    out = []
    for path in FILES:
        for item in sanction_items(path):
            out.append((path, item))
    return out


def test_2024_quarter_files_exist():
    assert [path.name for path in FILES] == [
        "2024-01-01_to_2024-03-31.md",
        "2024-04-01_to_2024-06-30.md",
        "2024-07-01_to_2024-09-30.md",
        "2024-10-01_to_2024-12-31.md",
    ]
    for path in FILES:
        assert path.is_file()


def test_2024_sanction_box_order():
    items = all_items()
    assert len(items) == 26
    for path, item in items:
        boxes = item["boxes"]
        assert len(boxes) == 3, (path.name, item["title_line"], boxes)
        assert boxes[0][0] == "note" and boxes[0][1] in MEASURE_TITLES, (
            path.name,
            item["title_line"],
            boxes[0],
        )
        assert boxes[1] == ("info", "안건 분석", boxes[1][2])
        assert boxes[2][0] == "note" and boxes[2][1] == "위원 논의"


def test_2024_table_hashes_match_move_baseline():
    shas = [table_sha(item["body_by_box"][item["boxes"][0][1]]) for _, item in all_items()]
    assert len(shas) == 26
    assert len(set(shas)) == 26
    assert set(shas) == TABLE_SHAS


def test_2024_discussion_is_empty():
    # 출처 주석은 제목과 첫 상자 사이에 있어 위원 논의 본문에는 들어가지 않는다.
    for path, item in all_items():
        body = item["body_by_box"]["위원 논의"]
        text = "\n".join(body).strip()
        assert text == "", (path.name, item["title_line"], text)


def test_2024_minutes_source_paths_locked():
    found: dict[str, str] = {}
    for path, item in all_items():
        ident = url_id(item["title"])
        assert ident is not None, (path.name, item["title_line"], item["title"])
        paths = item_source_paths(path, item)
        expected = EXPECTED_SOURCE_PATHS[ident]
        assert paths == [expected], (path.name, ident, item["title_line"], paths, expected)
        found[ident] = paths[0]
    assert found == EXPECTED_SOURCE_PATHS
    assert len(found) == 26


def test_2024_external_audit_note_title_stays_original():
    matches = [
        item
        for path, item in all_items()
        if url_id(item["title"]) == EXTERNAL_AUDIT_ID
    ]
    assert len(matches) == 1
    assert matches[0]["boxes"][0][1] == "감리결과 지적사항 및 조치내역 (외부감사법 위반)"


def test_2024_kakao_and_bident_stay_separate_in_sanctions():
    q4 = YEAR_DIR / "2024-10-01_to_2024-12-31.md"
    items = sanction_items(q4)
    ids = [url_id(item["title"]) for item in items]
    assert BIDENT_ID in ids
    assert KAKAO_ID in ids
    assert ids.index(BIDENT_ID) != ids.index(KAKAO_ID)
    press = q4.read_text(encoding="utf-8")
    press = press.split("#### 제재 의결")[0]
    assert f"no010101/{KAKAO_ID}" not in press
    assert f"no010101/{BIDENT_ID}" not in press

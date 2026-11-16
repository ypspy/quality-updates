"""의사록을 글 게시일이 아니라 실제 회의(PDF 첫 쪽 회의일)로 분류하는지.

픽스처는 2026-11 금융위·증선위 백필에서 잘못 분류된 실제 사례다. PDF 원본 대신
첫 쪽 텍스트 앞 8줄과 원본 sha256만 담는다(fixtures/sanctions_misfiled/cases.json).
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import attach_sanction_minutes as asm  # noqa: E402

CASES = json.loads(
    (Path(__file__).parent / "fixtures" / "sanctions_misfiled" / "cases.json").read_text(encoding="utf-8")
)["cases"]
BY_ID = {case["id"]: case for case in CASES}
BOARD_PATH = {"금융위": "no020101", "증선위": "no020102"}


def _text(case: dict, name: str) -> str:
    return "\n".join(case["pdfs"][name]["first_page_lines"])


def _post_key(case: dict):
    return asm.decision_key(case["title"], case["posted"])


@pytest.mark.parametrize(
    ("case_id", "name"),
    [(case["id"], name) for case in CASES for name in case["expected"]],
)
def test_every_real_misfiled_minutes_resolves_to_its_meeting(case_id, name):
    case = BY_ID[case_id]
    bundle = asm.is_multi_year_bundle(_post_key(case), case["attachments"])
    key, source, evidence = asm.resolve_minutes_key(_post_key(case), name, _text(case, name), bundle=bundle)
    assert source == "pdf-text"
    assert asm.sanction_folder(key) == case["expected"][name]
    assert evidence[:4] == case["expected"][name][:4]
    if case["current_folder"]:
        assert asm.sanction_folder(_post_key(case)) == case["current_folder"]


def test_bundle_detection_on_real_posts():
    for case_id in ("bundle-2008-5", "cached-27593", "cached-27599"):
        case = BY_ID[case_id]
        assert asm.is_multi_year_bundle(_post_key(case), case["attachments"]), case_id
    for case_id in ("late-december-2016-24", "temporary-2016-1", "written-2009-1", "sfc-2017-1-is-temporary"):
        case = BY_ID[case_id]
        assert not asm.is_multi_year_bundle(_post_key(case), case["attachments"]), case_id


def test_undated_bundle_is_never_filed_under_the_post_date():
    case = BY_ID["bundle-2008-5"]
    key, source, evidence = asm.resolve_minutes_key(
        _post_key(case), "제5차 금융위원회 의사록.pdf", "", bundle=True
    )
    assert key is None
    assert source == "review"
    assert evidence == "undated-multi-year-bundle"


def test_undated_single_post_falls_back_to_the_post():
    case = BY_ID["late-december-2016-24"]
    key, source, _ = asm.resolve_minutes_key(_post_key(case), "제24차 금융위원회 의사록.pdf", "", bundle=False)
    assert key == (2016, "금융위", "정기", 24)
    assert source == "post"


def test_filename_year_is_the_second_fallback():
    post = (2008, "금융위", "정기", 5)
    key, source, _ = asm.resolve_minutes_key(post, "2015-제5차 금융위 의사록(홈).pdf", "", bundle=True)
    assert (key, source) == ((2015, "금융위", "정기", 5), "filename")
    assert asm.minutes_key_from_filename("2010-제1차 임시 금융위 의사록(홈).hwp", (2008, "금융위", "임시", 1)) == (
        2010,
        "금융위",
        "임시",
        1,
    )
    assert asm.minutes_key_from_filename("제1차 임시금융위 의사록(홈).hwp", (2008, "금융위", "임시", 1)) is None


def test_text_date_beats_the_filename_year():
    text = _text(BY_ID["bundle-2008-5"], "제5차 금융위원회 의사록.pdf")
    key, source, _ = asm.resolve_minutes_key((2008, "금융위", "정기", 5), "2015-제5차 의사록.pdf", text, bundle=True)
    assert (key, source) == ((2016, "금융위", "정기", 5), "pdf-text")


def test_parenthetical_line_under_the_title_is_skipped():
    text = "제11차증권선물위원회의사록\n(의결안건 제148호 안건 관련 추가분)\n2018. 6. 7.\n증 권 선 물 위 원 회\n"
    assert asm.meeting_date_from_minutes_text(text) == "2018-06-07"
    identity = asm.minutes_identity_from_text(text)
    assert (identity["committee"], identity["kind"], identity["number"]) == ("증선위", "정기", 11)
    glued = "- 1 -\n제2차증권선물위원회임시회의의사록\n(의결안건제281호(2020년)~제283호(2020년)관련)\n2021. 2. 8.\n"
    identity = asm.minutes_identity_from_text(glued)
    assert (identity["date"], identity["kind"], identity["number"]) == ("2021-02-08", "임시", 2)


def test_missing_pdf_reader_stops_a_real_run(tmp_path, monkeypatch):
    import importlib.util

    real = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, "find_spec", lambda name, *a: None if name == "pypdf" else real(name, *a))
    with pytest.raises(RuntimeError):
        asm.run_backfill(
            lambda url: "<ul></ul>",
            lambda url, dest: None,
            tmp_path / "downloads",
            since=date(2008, 1, 1),
            until=date(2017, 12, 31),
        )


# --- 백필 통합: 목록·글·첨부를 픽스처로 흉내 낸다. 실제 요청은 하지 않는다. ---


def _payload(case: dict, name: str) -> bytes:
    # 같은 원본 PDF에서 온 파일은 같은 바이트가 되도록 원본 sha256을 쓴다.
    return b"%PDF-1.4 fixture " + case["pdfs"][name]["source_sha256"].encode()


class Site:
    def __init__(self, cases: list[dict], *, dated: bool = True):
        self.cases = cases
        self.dated = dated
        self.urls: dict[str, tuple[dict, str]] = {}
        self.downloaded: list[str] = []
        self.texts: dict[bytes, str] = {}
        for case in cases:
            for name in case["pdfs"]:
                self.texts[_payload(case, name)] = _text(case, name) if dated else ""

    def fetch(self, url: str) -> str:
        for board, path in BOARD_PATH.items():
            if f"/{path}?" in url:
                if "curPage=1&" not in url and not url.endswith("curPage=1"):
                    return "<ul></ul>"
                rows = [
                    f'<li><div class="inner"><div class="subject"><a href="/{path}/{case["post_id"]}">'
                    f'{case["title"]}</a></div><div class="day">{case["posted"]}</div></div></li>'
                    for case in self.cases
                    if case["board"] == board
                ]
                return "<ul>" + "".join(rows) + "</ul>"
        for case in self.cases:
            if url.endswith(f"/{BOARD_PATH[case['board']]}/{case['post_id']}"):
                links = []
                for number, name in enumerate(case["attachments"], start=1):
                    href = f"/comm/getFile?srvcId=BBSTY1&upperNo={case['post_id']}&fileTy=ATTACH&fileNo={number}"
                    self.urls[asm.absolute_fsc_url(href)] = (case, name)
                    links.append(f'<a href="{href}">{name}</a>')
                return "\n".join(links)
        raise AssertionError(url)

    def download(self, url: str, dest: Path) -> None:
        self.downloaded.append(url)
        case, name = self.urls[url]
        assert name.lower().endswith(".pdf"), name
        dest.write_bytes(_payload(case, name))

    def read_text(self, path: Path) -> str:
        return self.texts.get(path.read_bytes(), "")


def _run(site: Site, downloads: Path, **extra) -> dict:
    return asm.run_backfill(
        site.fetch,
        site.download,
        downloads,
        since=date(2008, 1, 1),
        until=date(2017, 12, 31),
        read_text=site.read_text,
        **extra,
    )


def _tree(downloads: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(downloads / "sanctions")): path.read_bytes()
        for path in sorted((downloads / "sanctions").rglob("*"))
        if path.is_file() and path.suffix == ".pdf"
    }


def _jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_backfill_files_every_real_case_under_its_real_meeting(tmp_path):
    downloads = tmp_path / "downloads"
    site = Site(CASES)
    # 이미 있는 올바른 폴더: 2017 증선위 임시 1차는 같은 파일을 갖고 있다.
    sfc = BY_ID["sfc-2017-1-is-temporary"]
    existing = downloads / "sanctions" / "2017-증선위-임시-1차" / "minutes.pdf"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(_payload(sfc, sfc["attachments"][0]))

    summary = _run(site, downloads)
    tree = _tree(downloads)
    expected_folders = {folder for case in CASES for folder in case["expected"].values()}
    assert {path.split("/")[0] for path in tree} == expected_folders
    for case in CASES:
        if case["current_folder"]:
            assert not (downloads / "sanctions" / case["current_folder"]).exists(), case["id"]
    # 같은 회의의 같은 파일(28072와 27593의 _홈.pdf, 28986과 기존 임시 1차)은 한 벌만 둔다.
    assert any(line.startswith("duplicate 제1차 임시 금융위 의사록_홈.pdf") for line in summary["report"])
    assert any(line.startswith("duplicate 2017년 제1차 증권선물위원회 의사록.pdf") for line in summary["report"])
    assert summary["reviews"] == 0
    assert not (downloads / "sanctions" / "_review").exists()
    assert not list((downloads / "sanctions").rglob("_staging/*"))

    pending = {row["filename"]: row for row in _jsonl(downloads / "sanctions" / "_pending-conversion.jsonl")}
    # 연도가 붙은 HWP는 버리지 않고 그 해 회의 폴더를 적어 대기에 둔다(받지는 않는다).
    assert pending["2009-제5차 금융위 의사록(홈).hwp"]["meeting_folder"] == "2009-금융위-5차"
    assert pending["2010-제1차 임시 금융위 의사록(홈).hwp"]["meeting_folder"] == "2010-금융위-임시-1차"
    assert pending["2015-제2차 금융위 의사록(홈).hwp"]["key_source"] == "filename"
    # 연도 없는 묶음 HWP는 회의를 모르므로 검토 표시로 남긴다.
    assert pending["제1차 임시금융위 의사록(홈).hwp"]["key_source"] == "review"
    assert pending["제1차 임시금융위 의사록(홈).hwp"]["meeting_folder"] == ""
    # 같은 이름의 PDF가 있는 HWP는 대기에 적지 않는다.
    assert "제1차 임시 금융위 의사록_홈.hwp" not in pending
    assert "제2차 금융위원회 의사록(홈).hwp" not in pending
    assert not any(url for url in site.downloaded if "hwp" in site.urls[url][1])

    state = json.loads((downloads / "sanctions" / "_backfill-state.json").read_text(encoding="utf-8"))
    assert {row["post_id"] for row in state["posts"]} == {case["post_id"] for case in CASES}

    again = _run(site, downloads)
    assert _tree(downloads) == tree
    assert again["reviews"] == 0


def test_undated_bundle_goes_to_the_review_queue(tmp_path):
    downloads = tmp_path / "downloads"
    case = BY_ID["bundle-2008-5"]
    site = Site([case], dated=False)
    summary = _run(site, downloads)
    assert summary["reviews"] == 1
    assert not (downloads / "sanctions" / "2008-금융위-5차").exists()
    rows = _jsonl(downloads / "sanctions" / "_review-queue.jsonl")
    assert len(rows) == 1
    assert rows[0]["reason"] == "undated-multi-year-bundle"
    assert rows[0]["post_id"] == "27605"
    kept = downloads / "sanctions" / rows[0]["path"]
    assert kept.read_bytes() == _payload(case, "제5차 금융위원회 의사록.pdf")
    assert kept.parent.name == "27605"
    state = json.loads((downloads / "sanctions" / "_backfill-state.json").read_text(encoding="utf-8"))
    assert [row["post_id"] for row in state["posts"]] == ["27605"]


def test_undated_single_post_still_uses_the_post(tmp_path):
    downloads = tmp_path / "downloads"
    case = BY_ID["late-december-2016-24"]
    site = Site([case], dated=False)
    summary = _run(site, downloads)
    assert summary["reviews"] == 0
    assert (downloads / "sanctions" / "2016-금융위-24차" / "minutes.pdf").is_file()


def test_different_file_already_in_the_real_folder_goes_to_review(tmp_path):
    downloads = tmp_path / "downloads"
    case = BY_ID["bundle-2008-5"]
    target = downloads / "sanctions" / "2016-금융위-5차" / "minutes.pdf"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"%PDF-1.4 other scan")
    site = Site([case])
    summary = _run(site, downloads)
    assert target.read_bytes() == b"%PDF-1.4 other scan"
    rows = _jsonl(downloads / "sanctions" / "_review-queue.jsonl")
    assert [(row["reason"], row["candidate_folder"]) for row in rows] == [("collision", "2016-금융위-5차")]
    assert rows[0]["evidence"] == "pdf-text:2016-03-15"
    assert summary["reviews"] == 1
    assert not (downloads / "sanctions" / "2008-금융위-5차").exists()


def test_existing_correct_minutes_are_not_downloaded_again(tmp_path):
    downloads = tmp_path / "downloads"
    case = BY_ID["written-2009-1"]
    site = Site([case])
    _run(site, downloads)
    first = list(site.downloaded)
    assert first
    # 묶음이 아닌 글이고 파일명에 연도가 없으면 잠정 폴더는 글 키다. 그 폴더에 다른 회의 파일이 있으면 다시 받는다.
    wrong = downloads / "sanctions" / "2009-금융위-서면-1차" / "minutes.pdf"
    wrong.parent.mkdir(parents=True)
    wrong.write_bytes(_payload(case, case["attachments"][0]))
    site.downloaded.clear()
    _run(site, downloads)
    assert site.downloaded == first
    # 맞는 회의 파일이 잠정 폴더에 있으면 받지 않는다.
    good = BY_ID["temporary-2016-1"]
    folder = downloads / "sanctions" / "2016-금융위-임시-1차"
    folder.mkdir(parents=True)
    (folder / "minutes.pdf").write_bytes(b"%PDF-1.4 undated scan")
    site = Site([good])
    _run(site, downloads)
    assert site.downloaded == []

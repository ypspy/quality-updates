# -*- coding: utf-8 -*-
"""Suggest editor curation markers for quarterly regulatory-update links.

The script reads a quarter markdown file and proposes the same markers
``editor.py`` stores (``<!-- skip -->``, ``<!-- no_summary -->``,
``<!-- source: type|ref -->``). It does not modify content files.

Ground truth for past quarters is reconstructed without git history:

- Appendix A is the unfiltered crawler list.
- A link that remains in the body was kept.
- ``!!! note`` means it was summarized (editor state ``done``).
- ``<!-- no_summary -->`` or a bare kept link means link-only.
- A collected link absent from the body was skipped, then removed by
  ``prepare_deploy.py``.

See ``docs/project/curation-rules.md``.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

from editor.parser import (
    APPENDIX_RE,
    LINK_RE,
    NOTE_RE,
    NO_SUMMARY_RE,
    PDF_RE,
    SECTION_RE,
    SKIP_RE,
    SOURCE_RE,
)

AGENCIES = ("금융감독원", "금융위원회", "한국공인회계사회", "한국회계기준원")
HOLDOUT_NAME = "2026-04-01_to_2026-06-30.md"
PENDING_REF = "pending"

HIGH_PHRASES = (
    "외부감사",
    "내부회계",
    "내부감사",
    "회계법인",
    "회계감사",
    "회계기준",
    "회계부정",
    "회계처리",
    "회계심사",
    "회계투명",
    "회계감독",
    "회계제도",
    "회계이슈",
    "공인회계사",
    "감사인",
    "kifrs",
    "한국채택국제회계기준",
    "중점심사",
    "지적사례",
    "표준감사",
    "xbrl",
    "질의회신",
    "공개초안",
    "주석공시",
    "품질관리감리",
    "수임신고",
    "감사기준",
    "기업회계기준서",
    "비감사용역",
    "감사의견",
    "감사품질",
    "외부감사대상",
    "주기적지정",
    "인증기준",
    "검토기준",
    "감사조서",
    "감사계약",
)

ACCOUNTING_CONTEXT = (
    "공시",
    "감사",
    "기준",
    "법인",
    "부정",
    "처리",
    "심사",
    "감독",
    "투명",
    "이슈",
    "제도",
    "감리",
)

INSURANCE_ACCOUNTING = (
    "ifrs17",
    "kics",
    "보험회계",
    "계리가정",
    "보험부채",
    "일탈회계",
    "책임준비금",
    "계약자지분",
    "듀레이션갭",
)

EXAM_HINTS = (
    "합격",
    "응시",
    "원서",
    "시험장소",
    "출제범위",
    "시행계획",
    "최소선발",
    "시험",
)

ORG_TOKENS = (
    "한국공인회계사회",
    "한국회계기준원",
    "한국회계연구원",
    "금융감독원",
    "금융위원회",
    "공인회계사회",
    "회계기준원",
)

RECRUIT_PHRASES = (
    "모집",
    "입찰",
    "채용",
    "위촉",
    "강의개설",
    "교재구매",
    "교재구입",
    "학술대회",
    "심포지엄",
    "동영상강의",
    "구입신청",
    "선정공고",
    "공개모집",
    "조사위원",
    "간이조사",
    "초빙",
)

HARD_SKIP_PHRASES = (
    "가계대출",
    "주택담보",
    "전세자금",
    "전세대출",
    "부동산",
    "분양",
    "혁신금융",
    "서민금융",
    "불법사금융",
    "중도상환",
    "가계부채",
    "보이스피싱",
    "전자금융업등록",
    "금융투자업신규",
    "등록취소",
    "부수업무",
    "공시송달",
    "임원인사",
    "인사실시",
    "인사보도",
    "연체율",
    "실태조사",
    "불공정거래",
    "공매도",
    "보험사기",
)

_TAG_RE = re.compile(r"^\s*\[([^\]]+)\]")
_PRESS_TAGS = ("보도", "안내")


@dataclass
class Item:
    date: str
    title: str
    url: str
    agency: str | None
    section: str

    @property
    def key(self) -> tuple[str | None, str | None]:
        return (self.agency, url_key(self.url))


@dataclass
class Decision:
    state: str
    rule_id: str
    reason: str
    confidence: float
    source_type: str | None = None
    source_ref: str | None = None

    def marker(self) -> str | None:
        """Marker line written by ``editor.saver.apply_curation`` for this state."""
        if self.state == "skip":
            return "<!-- skip -->"
        if self.state == "no_summary":
            return "<!-- no_summary -->"
        if self.state == "needs_summary" and self.source_type and self.source_ref:
            return f"<!-- source: {self.source_type}|{self.source_ref} -->"
        return None

    def to_public(self) -> dict:
        data = asdict(self)
        data["marker"] = self.marker()
        data["bucket"] = bucket_of(self.state)
        return data


@dataclass
class Labeled:
    item: Item
    actual: str  # skip | no_summary | summarize
    raw_state: str
    source_type: str | None = None
    in_body: bool = False


@dataclass
class Scored:
    item: Item
    actual: str
    predicted: str
    raw_state: str
    rule_id: str
    reason: str
    confidence: float
    actual_source: str | None
    predicted_source: str | None
    marker: str | None


@dataclass
class SplitMetrics:
    name: str
    n: int = 0
    skip_tp: int = 0
    skip_fp: int = 0
    skip_fn: int = 0
    three_correct: int = 0
    confusion: Counter = field(default_factory=Counter)
    source_n: int = 0
    source_correct: int = 0
    source_given_summary_n: int = 0
    source_given_summary_correct: int = 0
    family_n: int = 0
    family_correct: int = 0
    review_n: int = 0

    def add(self, row: Scored) -> None:
        self.n += 1
        if row.predicted == "review":
            self.review_n += 1
        pred_skip = row.predicted == "skip"
        act_skip = row.actual == "skip"
        if pred_skip and act_skip:
            self.skip_tp += 1
        elif pred_skip and not act_skip:
            self.skip_fp += 1
        elif act_skip and not pred_skip:
            self.skip_fn += 1
        if row.predicted == row.actual:
            self.three_correct += 1
        self.confusion[(row.actual, row.predicted)] += 1
        if row.actual_source:
            self.source_n += 1
            hit = (
                row.predicted == "summarize"
                and row.predicted_source == row.actual_source
            )
            if hit:
                self.source_correct += 1
            self.family_n += 1
            if row.predicted == "summarize" and _family(row.predicted_source) == _family(
                row.actual_source
            ):
                self.family_correct += 1
            if row.predicted == "summarize":
                self.source_given_summary_n += 1
                if row.predicted_source == row.actual_source:
                    self.source_given_summary_correct += 1

    def as_dict(self) -> dict:
        prec, rec, f1 = _prf(self.skip_tp, self.skip_fp, self.skip_fn)
        return {
            "name": self.name,
            "n": self.n,
            "skip_precision": prec,
            "skip_recall": rec,
            "skip_f1": f1,
            "skip_tp": self.skip_tp,
            "skip_fp": self.skip_fp,
            "skip_fn": self.skip_fn,
            "three_way_accuracy": (self.three_correct / self.n) if self.n else 0.0,
            "source_type_accuracy": _ratio(self.source_correct, self.source_n),
            "source_type_n": self.source_n,
            "source_type_accuracy_when_summarized": _ratio(
                self.source_given_summary_correct, self.source_given_summary_n
            ),
            "source_type_when_summarized_n": self.source_given_summary_n,
            "source_family_accuracy": _ratio(self.family_correct, self.family_n),
            "review_n": self.review_n,
            "three_way_accuracy_excluding_review": (
                self.three_correct / (self.n - self.review_n) if (self.n - self.review_n) else 0.0
            ),
            "confusion": {
                f"{a}->{p}": n for (a, p), n in sorted(self.confusion.items())
            },
        }


def bucket_of(state: str) -> str:
    if state == "skip":
        return "skip"
    if state in {"no_summary", "bare"}:
        return "no_summary"
    if state in {"needs_summary", "done", "summarize"}:
        return "summarize"
    if state == "review":
        return "review"
    return state


def _family(source_type: str | None) -> str:
    if source_type == "pdf":
        return "pdf"
    if source_type in {"shot", "clip", "web", "url"}:
        return "page"
    return ""


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0
    return prec, rec, f1


def _ratio(num: int, den: int) -> float | None:
    if not den:
        return None
    return num / den


def squash(text: str) -> str:
    lowered = text.lower()
    lowered = lowered.replace("ㆍ", "").replace("·", "").replace("・", "")
    lowered = re.sub(r"\s+", "", lowered)
    lowered = re.sub(r"[^0-9a-z가-힣]", "", lowered)
    return lowered


def norm_section(section: str) -> str:
    text = section.replace("ㆍ", "·").replace("・", "·")
    return re.sub(r"\s+", " ", text).strip()


def url_key(url: str) -> str | None:
    patterns = (
        r"nttId=(\d+)",
        r"bltnNo=(\d+)",
        r"noticeId=(\d+)",
        r"[?&]seq=(\d+)",
        r"/(?:no\d+|po\d+)/(\d+)",
        r"bbsNo=(\d+)",
    )
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return url.split("?")[0].rstrip("/")


def _detect_agency(header: str) -> str | None:
    for name in AGENCIES:
        if name in header:
            return name
    return None


def default_source(item: Item) -> str:
    """Capture channel the editor usually attaches. The file name is not known."""
    section = item.section
    agency = item.agency or ""
    if "주요일정" in section:
        return "clip"
    if "동향" in section:
        return "clip"
    if agency == "한국공인회계사회":
        return "shot"
    if agency == "한국회계기준원" and "보도자료" not in section:
        return "shot"
    return "pdf"


def _decision(
    state: str,
    rule_id: str,
    reason: str,
    confidence: float,
    item: Item | None = None,
    source_type: str | None = None,
) -> Decision:
    if state == "needs_summary":
        chosen = source_type or (default_source(item) if item else "pdf")
        return Decision(
            state=state,
            rule_id=rule_id,
            reason=reason,
            confidence=confidence,
            source_type=chosen,
            source_ref=PENDING_REF,
        )
    return Decision(state=state, rule_id=rule_id, reason=reason, confidence=confidence)


def _parse_date(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%y-%m-%d")
    except ValueError:
        return None


def _dates_close(left: str, right: str, days: int = 21) -> bool:
    a = _parse_date(left)
    b = _parse_date(right)
    if a is None or b is None:
        return False
    return abs((a - b).days) <= days


def strip_orgs(folded: str) -> str:
    """Drop institution names so '한국공인회계사회' does not count as '공인회계사'."""
    for token in ORG_TOKENS:
        folded = folded.replace(squash(token), "")
    return folded


def accounting_hit(title: str) -> str | None:
    folded = strip_orgs(squash(title))
    residue = folded.replace("회계연도", "")
    for phrase in HIGH_PHRASES:
        if phrase in folded:
            return phrase
    for phrase in INSURANCE_ACCOUNTING:
        if phrase in folded:
            return phrase
    if "할인율" in folded and any(token in folded for token in ("보험", "ifrs", "kics", "회계")):
        return "할인율"
    if "가상자산" in folded and any(token in residue for token in ("회계", "주석", "감사", "공시")):
        return "가상자산-회계"
    if "회계" in residue and any(token in residue for token in ACCOUNTING_CONTEXT):
        return "회계+맥락"
    if "재무제표" in folded and any(token in folded for token in ("감사", "회계", "심사", "주석")):
        return "재무제표"
    if "dart" in folded:
        return "dart"
    if "감사보고서" in folded and any(token in folded for token in ("분석", "의견", "정정", "감리")):
        return "감사보고서"
    return None


def _is_exam(folded: str) -> bool:
    folded = strip_orgs(folded)
    if not any(token in folded for token in ("공인회계사", "제1차시험", "제2차시험")):
        return False
    return any(token in folded for token in EXAM_HINTS)


def _is_policy_exception_to_exam(folded: str) -> bool:
    return any(token in folded for token in ("제도개선", "제도를개선", "수습처", "선발수습개선")) or (
        "수습" in folded and any(token in folded for token in ("개선", "지원", "제도"))
    )


def _enforcement(folded: str) -> bool:
    return "감리결과" in folded and any(
        token in folded for token in ("조사", "사업보고서", "감사보고서")
    )


def _enforcement_out_of_scope(folded: str) -> bool:
    return any(
        token in folded
        for token in ("불공정", "가상자산", "보험사기", "보험조사", "공매도", "부동산", "자본시장조사")
    )


def _recruitment(item: Item, folded: str) -> bool:
    if any(phrase in folded for phrase in ("유의사항", "수임신고", "표준감사", "외부감사인선임")):
        return False
    if any(phrase in folded for phrase in RECRUIT_PHRASES):
        return True
    match = _TAG_RE.match(item.title)
    if not match or item.agency != "한국공인회계사회":
        return False
    tag = match.group(1)
    if any(tag.startswith(prefix) for prefix in _PRESS_TAGS):
        return False
    return True


def _hard_skip(folded: str) -> str | None:
    for phrase in HARD_SKIP_PHRASES:
        if phrase in folded:
            return phrase
    if "보험" in folded and not any(phrase in folded for phrase in INSURANCE_ACCOUNTING):
        if "할인율" in folded and any(token in folded for token in ("보험", "ifrs", "회계")):
            return None
        return "보험(비회계)"
    if "가상자산" in folded and not any(token in folded for token in ("회계", "주석", "감사", "공시")):
        return "가상자산(비회계)"
    if folded.startswith("인사") or "인사발령" in folded:
        return "인사"
    return None


def decide_one(item: Item) -> Decision:
    """Classify one link. Duplicate demotion is applied later in ``decide_all``."""
    folded = strip_orgs(squash(item.title))
    raw = squash(item.title)
    section = item.section
    agency = item.agency or ""
    hit = accounting_hit(item.title)

    if _sustainability_excluded(item, folded):
        return _decision(
            "skip",
            "R8-sustainability",
            "SASB·IFRS S2·지속가능성 포럼·지속가능성 일정은 범위 밖이라 스킵",
            0.9,
        )

    if "소유주식" in folded:
        return _decision(
            "skip",
            "R16-ownership-filing",
            "지배주주 등 소유주식 현황 제출은 요약 키워드로 넣지 않고 스킵",
            0.9,
        )

    if "세칙" in section:
        if any(token in folded for token in ("외부감사", "회계감사", "회계등에관한", "공인회계사")):
            return _decision(
                "needs_summary",
                "R12-sechik-accounting",
                "회계·외부감사·공인회계사 관련 시행세칙 개정만 요약",
                0.88,
                item,
            )
        return _decision(
            "skip",
            "R12-sechik-other",
            "회계·외부감사·공인회계사와 무관한 시행세칙은 스킵",
            0.86,
        )

    if "주요일정" in section:
        agenda = any(
            token in folded
            for token in ("회계기준위원회", "kifrs", "공개초안", "기업회계기준서", "기준서")
        )
        if agenda and not ("지속가능" in folded and "회계기준위원회" not in folded and "kifrs" not in folded):
            return _decision(
                "needs_summary",
                "R7-kasb-meeting",
                "회계기준위원회·K-IFRS 안건 일정은 요약. 출처는 일정 페이지 캡처(clip)를 기본값으로 제안",
                0.88,
                item,
                source_type="clip",
            )
        if "지속가능" in folded:
            return _decision(
                "skip",
                "R8-sustainability",
                "지속가능성 일정은 범위 밖이라 스킵",
                0.9,
            )
        return _decision(
            "skip",
            "R8-schedule-other",
            "회계기준 안건이 아닌 주요일정은 스킵 제안(저신뢰)",
            0.5,
        )

    if agency == "한국공인회계사회" and ("감사인증" in section or section.startswith("회계감사")):
        return _decision(
            "needs_summary",
            "R6-kicpa-standards",
            "감사·인증기준 게시판은 원칙적으로 요약",
            0.86,
            item,
            source_type="shot",
        )

    if "입법" in section:
        if hit and hit not in {"dart"}:
            return _decision(
                "needs_summary",
                "R11-legislation-accounting",
                "외부감사·회계·공인회계사 입법예고·규정변경예고는 요약",
                0.88,
                item,
            )
        if "증권선물위원회" in folded and "운영규칙" in folded:
            return _decision(
                "needs_summary",
                "R11-sfc-rules",
                "증선위 운영규칙 개정은 제재 절차와 닿아 요약 제안(저신뢰)",
                0.55,
                item,
            )
        return _decision(
            "skip",
            "R11-legislation-other",
            "회계·외부감사와 무관한 입법예고·규정변경예고는 스킵",
            0.84,
        )

    if "고시" in section or "훈령" in section:
        if "회계의날" in folded or "포상" in folded and "부정" not in folded:
            return _decision(
                "no_summary",
                "R10-award-link",
                "회계의 날·포상 공모는 링크만 유지",
                0.8,
            )
        if _is_exam(folded) and not _is_policy_exception_to_exam(folded):
            return _decision(
                "no_summary",
                "R1-exam-notice",
                "공인회계사 시험 일정·합격·시행계획 공고는 요약하지 않고 링크만 유지",
                0.86,
            )
        substantive = hit in HIGH_PHRASES or hit in INSURANCE_ACCOUNTING
        if substantive and hit not in {"회계처리", "dart"}:
            return _decision(
                "needs_summary",
                "R10-notice-accounting",
                "외부감사·회계 관련 고시·규정 개정은 요약",
                0.78,
                item,
            )
        if any(token in folded for token in ("검토준칙", "회계처리기준", "재무제표")) or (
            "회계" in folded.replace("회계연도", "")
        ):
            return _decision(
                "no_summary",
                "R10-notice-accounting-link",
                "회계 고시·준칙 공고는 링크만 유지. 개정 취지가 제목에 있으면 사람이 요약으로 올릴 수 있음",
                0.58,
            )
        return _decision(
            "skip",
            "R10-notice-other",
            "등록·말소·일반 고시·훈령은 스킵",
            0.9,
        )

    if "동향" in section:
        if "뉴스레터" in folded:
            return _decision(
                "no_summary",
                "R2-newsletter",
                "회계뉴스레터는 요약하지 않고 링크만 유지",
                0.9,
            )
        if hit:
            return _decision(
                "needs_summary",
                "R14-trend-accounting",
                "회계감독 동향 중 제도·설명자료는 요약. 출처 기본값은 clip",
                0.74,
                item,
                source_type="clip",
            )
        return _decision(
            "skip",
            "R16-trend-other",
            "회계 핵심이 아닌 동향자료는 스킵",
            0.7,
        )

    if _enforcement(folded) and not _enforcement_out_of_scope(folded):
        if agency == "금융감독원":
            return _decision(
                "no_summary",
                "R3-enforcement-fss",
                "조사·감리결과 조치는 금융위 쪽에 요약을 두고 금감원은 링크만 유지",
                0.9,
            )
        if agency == "금융위원회":
            return _decision(
                "needs_summary",
                "R4-enforcement-fsc",
                "사업보고서·감사보고서 조사·감리결과 조치는 금융위 본문에서 요약",
                0.92,
                item,
                source_type="pdf",
            )

    if "뉴스레터" in folded:
        return _decision(
            "no_summary",
            "R2-newsletter",
            "뉴스레터는 요약하지 않고 링크만 유지",
            0.88,
        )

    if "회계의날" in folded and agency in {"금융감독원", "금융위원회"}:
        return _decision(
            "no_summary",
            "R15-accounting-day",
            "회계의 날 기념·포상은 금감원·금융위에서 링크만 유지",
            0.8,
        )

    if _is_exam(folded) and not _is_policy_exception_to_exam(folded):
        if agency in {"금융감독원", "금융위원회"}:
            return _decision(
                "no_summary",
                "R1-exam",
                "시험 접수·응시·합격 안내는 요약하지 않고 링크만 유지",
                0.84,
            )
        return _decision(
            "skip",
            "R1-exam-skip",
            "시험·연수 행정 안내는 스킵",
            0.8,
        )

    if agency in {"한국공인회계사회", "한국회계기준원"} and _recruitment(item, folded):
        return _decision(
            "skip",
            "R9-recruitment",
            "모집·입찰·채용·강의·조사위원 신청 안내는 스킵",
            0.9,
        )

    if "회계감사자료" in folded or "온라인발급" in folded:
        return _decision(
            "skip",
            "R16-audit-confirm",
            "금융회사 회계감사자료 온라인 발급 안내는 회원 행정 공지로 보고 스킵",
            0.84,
        )

    if agency in {"한국공인회계사회", "한국회계기준원"} and any(
        token in folded for token in ("세미나", "포럼", "forum", "워크숍", "컨퍼런스")
    ):
        if not any(token in folded for token in ("유의사항", "논의내용", "검토의견")):
            return _decision(
                "skip",
                "R16-event",
                "세미나·포럼·워크숍·컨퍼런스 개최 안내는 스킵. 기준 공개초안·질의회신 본문은 별도",
                0.72,
            )

    if agency in {"한국공인회계사회", "한국회계기준원"} and any(
        token in folded
        for token in (
            "설명회개최",
            "설명회안내",
            "공청회개최",
            "공청회안내",
            "영상공개",
            "교육제공",
            "교육영상",
            "설문조사",
            "점검안내",
        )
    ):
        if not any(token in folded for token in ("논의내용", "검토의견", "의견조회")):
            return _decision(
                "skip",
                "R16-briefing-notice",
                "설명회·교육·설문·점검 안내는 스킵. 같은 주제의 기준 본문·의견조회는 따로 남긴다",
                0.7,
            )

    if agency == "한국회계기준원" and any(
        token in folded for token in ("보도설명", "보도반박", "보도해명")
    ):
        return _decision(
            "needs_summary",
            "R14-kasb-rebuttal",
            "기준원 보도설명·반박·해명은 회계 쟁점 해명으로 보고 요약(저신뢰)",
            0.6,
            item,
        )

    if _unfair_trading_action(folded):
        return _decision(
            "skip",
            "R16-unfair-trading",
            "불공정거래 조치·적발·조사는 스킵. 회계부정 제재 선진화처럼 제도 개편 문서는 예외",
            0.9,
        )

    if _focus_inspection(folded):
        return _decision(
            "review",
            "R18-focus-inspection",
            "중점 점검은 자동 판정하지 않음. 재무제표·비상장 중점 점검분야와 사업보고서 중점 점검사항은 과거에 종종 남았고, 공시 실태·시장·교육·정책금융 중점 점검은 대개 스킵",
            0.35,
        )

    if agency == "한국공인회계사회" and "금융감독원" in raw and (hit or "유의사항" in folded):
        return _decision(
            "needs_summary",
            "R14-kicpa-relay",
            "한공회가 금감원 회계·감사 자료를 재안내한 항목은 요약",
            0.82,
            item,
        )

    if "유의사항" in folded and any(
        token in folded for token in ("재무제표", "감사", "회계", "결산", "외부감사")
    ):
        return _decision(
            "needs_summary",
            "R14-caution",
            "결산·감사 유의사항 안내는 요약",
            0.8,
            item,
        )

    if "표준연수" in folded:
        return _decision(
            "needs_summary",
            "R14-cpe",
            "표준연수기준 개정은 요약 제안(저신뢰)",
            0.6,
            item,
        )

    if "계리감리" in folded:
        return _decision(
            "needs_summary",
            "R14-actuarial-review",
            "계리감리 업무 방향은 보험회계 감독으로 보고 요약",
            0.74,
            item,
        )

    if "ifrs" in folded and any(
        token in folded for token in ("재단", "trustees", "이사회", "이사선임", "자문포럼", "회원국")
    ):
        return _decision(
            "needs_summary",
            "R14-ifrs-foundation",
            "IFRS 재단 인사·회원국 소식은 요약",
            0.7,
            item,
        )

    if "ifrs" in folded and any(token in folded for token in ("의견조회", "사후이행", "pir")):
        return _decision(
            "needs_summary",
            "R14-ifrs-outreach",
            "IFRS 의견조회·사후이행검토는 요약",
            0.74,
            item,
        )

    if hit:
        confidence = 0.8 if hit in HIGH_PHRASES or hit in INSURANCE_ACCOUNTING else 0.64
        return _decision(
            "needs_summary",
            "R14-accounting",
            f"회계·감사 핵심 주제({hit})로 보아 요약",
            confidence,
            item,
        )

    if _is_policy_exception_to_exam(folded) and "공인회계사" in folded:
        return _decision(
            "needs_summary",
            "R14-cpa-policy",
            "공인회계사 수습·선발 제도 개편은 요약",
            0.7,
            item,
        )

    skipped = _hard_skip(folded)
    if skipped:
        return _decision(
            "skip",
            "R16-out-of-scope",
            f"회계·감사 규제 업데이트 범위 밖({skipped})",
            0.86,
        )

    if agency in {"금융감독원", "금융위원회"}:
        return _decision(
            "skip",
            "R17-default-press",
            "회계·감사 핵심어가 없는 보도자료는 스킵",
            0.78,
        )
    if agency == "한국공인회계사회":
        return _decision(
            "skip",
            "R17-default-kicpa",
            "회원 행정·행사 안내는 스킵. 감사 유의사항·수임·기준 개정만 남김",
            0.74,
        )
    return _decision(
        "skip",
        "R17-default-kasb",
        "기준 제·개정·공개초안·질의회신이 아닌 기준원 소식은 스킵(저신뢰)",
        0.58,
    )


def _similar(left: Item, right: Item) -> float:
    """Title similarity. A long title contained in the other counts as the same release."""
    left_key = strip_orgs(squash(left.title))
    right_key = strip_orgs(squash(right.title))
    if min(len(left_key), len(right_key)) >= 20 and (left_key in right_key or right_key in left_key):
        # 0.80 requires a nearby date in apply_fss_demotion (the 0.86 path stays for ratio alone).
        return 0.80
    return SequenceMatcher(None, left_key, right_key).ratio()


def _sustainability_excluded(item: Item, folded: str) -> bool:
    """Owner: SASB, IFRS S2, and sustainability forums/schedules are out of scope."""
    if "회계기준위원회" in folded and "sasb" not in folded and "ifrss2" not in folded:
        return False
    if "sasb" in folded or "ifrss2" in folded:
        return True
    if "주요일정" in item.section and "지속가능" in folded:
        return True
    if "지속가능" in folded and any(token in folded for token in ("포럼", "forum", "세미나")):
        return True
    return False


def _unfair_trading_action(folded: str) -> bool:
    if "불공정" not in folded:
        return False
    if "회계부정" in folded and any(token in folded for token in ("선진화", "tf", "방안")):
        return False
    return any(token in folded for token in ("조치", "적발", "과징금", "고발", "협의회", "점검", "조사"))


def _focus_inspection(folded: str) -> bool:
    """중점 점검, not 중점심사. The owner asked not to auto-decide these."""
    return "중점점검" in folded and "중점심사" not in folded


def apply_fss_demotion(items: list[Item], decisions: list[Decision]) -> list[Decision]:
    """When FSC will summarize a near-duplicate press item, keep FSS as a link only."""
    fsc_kept = [
        item
        for item, decision in zip(items, decisions)
        if item.agency == "금융위원회"
        and "보도자료" in item.section
        and decision.state == "needs_summary"
    ]
    if not fsc_kept:
        return decisions
    adjusted = list(decisions)
    for index, (item, decision) in enumerate(zip(items, decisions)):
        if item.agency != "금융감독원" or "보도자료" not in item.section:
            continue
        if decision.state != "needs_summary":
            continue
        if decision.rule_id == "R3-enforcement-fss":
            continue
        best_ratio = 0.0
        for other in fsc_kept:
            ratio = _similar(item, other)
            close = _dates_close(item.date, other.date)
            if ratio >= 0.86 or (ratio >= 0.70 and close):
                best_ratio = max(best_ratio, ratio)
        if best_ratio:
            adjusted[index] = _decision(
                "no_summary",
                "R13-fss-duplicate",
                f"같은 보도의 금융위 항목을 요약하고 금감원은 링크만 유지(유사도 {best_ratio:.2f})",
                0.84,
            )
    return adjusted


def decide_all(items: list[Item]) -> list[Decision]:
    base = [decide_one(item) for item in items]
    return apply_fss_demotion(items, base)


def _blank(line: str) -> bool:
    return line.strip() == ""


def _state_after(lines: list[str], index: int) -> tuple[str, str | None]:
    cursor = index + 1
    while cursor < len(lines) and _blank(lines[cursor]):
        cursor += 1
    if cursor >= len(lines):
        return "bare", None
    nxt = lines[cursor]
    core = nxt.strip()
    if SKIP_RE.match(core):
        return "skip", None
    if NO_SUMMARY_RE.match(core):
        return "no_summary", None
    source_match = SOURCE_RE.match(nxt)
    if source_match:
        source_type = source_match.group(1).strip()
        if source_type == "url":
            source_type = "web"
        state = "needs_summary"
        look = cursor + 1
        while look < len(lines) and _blank(lines[look]):
            look += 1
        if look < len(lines) and NOTE_RE.match(lines[look]):
            state = "done"
        return state, source_type
    if PDF_RE.match(nxt):
        return "needs_summary", "pdf"
    if NOTE_RE.match(nxt):
        return "done", None
    return "bare", None


def parse_document(text: str) -> tuple[list[Item], list[Item]]:
    """Return ``(body_items, appendix_items)``."""
    lines = text.splitlines()
    split_at = len(lines)
    for index, line in enumerate(lines):
        if APPENDIX_RE.match(line):
            split_at = index
            break
    return _parse_body(lines[:split_at]), _parse_appendix(lines[split_at:])


def _parse_body(lines: list[str]) -> list[Item]:
    items: list[Item] = []
    agency = None
    section = ""
    for index, line in enumerate(lines):
        section_match = SECTION_RE.match(line)
        if section_match:
            header = section_match.group(1).strip()
            detected = _detect_agency(header)
            if detected and line.startswith("###"):
                agency = detected
                section = ""
            elif line.startswith("####"):
                section = norm_section(header)
        link_match = LINK_RE.match(line)
        if not link_match:
            continue
        date, title, url = link_match.groups()
        items.append(
            Item(
                date=date,
                title=title,
                url=url,
                agency=agency,
                section=section,
            )
        )
    return items


def _parse_appendix(lines: list[str]) -> list[Item]:
    items: list[Item] = []
    agency = None
    section = ""
    for line in lines:
        if 'info "' in line:
            detected = _detect_agency(line)
            if detected:
                agency = detected
                section = ""
                continue
        section_match = re.match(r"^\s*\*\*(.+?)\*\*\s*$", line)
        if section_match:
            section = norm_section(section_match.group(1))
            continue
        link_match = LINK_RE.match(line)
        if not link_match:
            continue
        date, title, url = link_match.groups()
        items.append(
            Item(date=date, title=title, url=url, agency=agency, section=section)
        )
    return items


def label_collected(text: str) -> tuple[list[Labeled], list[Item]]:
    """Label appendix items from the curated body.

    The second list is body items that never appear in the appendix
    (hand-added links).
    """
    lines = text.splitlines()
    split_at = len(lines)
    for index, line in enumerate(lines):
        if APPENDIX_RE.match(line):
            split_at = index
            break
    body_lines = lines[:split_at]
    body_items: list[tuple[Item, str, str | None]] = []
    agency = None
    section = ""
    for index, line in enumerate(body_lines):
        section_match = SECTION_RE.match(line)
        if section_match:
            header = section_match.group(1).strip()
            detected = _detect_agency(header)
            if detected and line.startswith("###"):
                agency = detected
                section = ""
            elif line.startswith("####"):
                section = norm_section(header)
        link_match = LINK_RE.match(line)
        if not link_match:
            continue
        date, title, url = link_match.groups()
        state, source_type = _state_after(body_lines, index)
        body_items.append(
            (
                Item(date=date, title=title, url=url, agency=agency, section=section),
                state,
                source_type,
            )
        )

    by_key: dict[tuple[str | None, str | None], list[tuple[Item, str, str | None]]] = defaultdict(list)
    by_title: dict[tuple[str | None, str, str], list[tuple[Item, str, str | None]]] = defaultdict(list)
    for record in body_items:
        item = record[0]
        by_key[item.key].append(record)
        by_title[(item.agency, item.date, squash(item.title)[:80])].append(record)

    appendix = _parse_appendix(lines[split_at:])
    labeled: list[Labeled] = []
    used: set[int] = set()
    for item in appendix:
        match = None
        for record in by_key.get(item.key, []):
            if id(record) not in used:
                match = record
                break
        if match is None:
            title_key = (item.agency, item.date, squash(item.title)[:80])
            for record in by_title.get(title_key, []):
                if id(record) not in used:
                    match = record
                    break
        if match is None:
            labeled.append(Labeled(item=item, actual="skip", raw_state="absent"))
            continue
        used.add(id(match))
        _item, state, source_type = match
        labeled.append(
            Labeled(
                item=item,
                actual=bucket_of(state),
                raw_state=state,
                source_type=source_type,
                in_body=True,
            )
        )
    manual = [record[0] for record in body_items if id(record) not in used]
    return labeled, manual


def score_labeled(labeled: list[Labeled]) -> list[Scored]:
    decisions = decide_all([row.item for row in labeled])
    scored: list[Scored] = []
    for row, decision in zip(labeled, decisions):
        scored.append(
            Scored(
                item=row.item,
                actual=row.actual,
                predicted=bucket_of(decision.state),
                raw_state=row.raw_state,
                rule_id=decision.rule_id,
                reason=decision.reason,
                confidence=decision.confidence,
                actual_source=row.source_type,
                predicted_source=decision.source_type,
                marker=decision.marker(),
            )
        )
    return scored


def quarter_files(root: Path) -> list[Path]:
    files = sorted(root.glob("*/*.md"))
    return [path for path in files if path.name != "index.md" and path.parent.name.isdigit()]


def split_name(path: Path, holdout: str) -> str | None:
    if path.name == holdout:
        return "holdout"
    year = path.parent.name
    if year in {"2023", "2024"}:
        return "2023-2024"
    if year == "2025" or path.name.startswith("2026-01"):
        return "2025-2026Q1"
    if year == "2026":
        return "other-2026"
    return None


def run_backtest(root: Path, holdout: str = HOLDOUT_NAME) -> dict:
    grouped: dict[str, list[Scored]] = defaultdict(list)
    manual_counts: dict[str, int] = {}
    file_counts: dict[str, int] = Counter()
    for path in quarter_files(root):
        group = split_name(path, holdout)
        if group is None:
            continue
        text = path.read_text(encoding="utf-8")
        if "## Appendix" not in text:
            continue
        labeled, manual = label_collected(text)
        if len(labeled) < 30:
            continue
        manual_counts[path.name] = len(manual)
        file_counts[group] += 1
        grouped[group].extend(score_labeled(labeled))

    metrics = {}
    for name, rows in grouped.items():
        bucket = SplitMetrics(name=name)
        for row in rows:
            bucket.add(row)
        metrics[name] = bucket.as_dict()
    return {
        "holdout": holdout,
        "files": dict(file_counts),
        "manual_body_additions": manual_counts,
        "metrics": metrics,
        "rows": grouped,
    }


def _pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def _mismatch_line(row: Scored) -> str:
    source = ""
    if row.actual_source or row.predicted_source:
        source = f" 출처 {row.actual_source or '-'}→{row.predicted_source or '-'}"
    title = row.item.title.replace("|", "/")
    return (
        f"| {row.item.date} | {row.item.agency or ''} | {row.item.section} | "
        f"{row.actual} | {row.predicted} | {row.rule_id} | {row.confidence:.2f} | "
        f"{title}{source} |"
    )


def render_report(payload: dict) -> str:
    holdout_rows: list[Scored] = payload["rows"].get("holdout", [])
    reviews = [row for row in holdout_rows if row.predicted == "review"]
    mismatches = [
        row for row in holdout_rows if row.predicted != "review" and row.actual != row.predicted
    ]
    source_misses = [
        row
        for row in holdout_rows
        if row.predicted != "review"
        and row.actual_source
        and not (
            row.predicted == "summarize" and row.predicted_source == row.actual_source
        )
    ]
    lines = [
        "# 큐레이션 규칙 백테스트",
        "",
        "자동 제안 스크립트 `scripts/auto_curate.py`를 사람이 이미 끝낸 분기와 비교한 결과다. "
        "규칙은 2023–2026 본문과 Appendix에서 읽은 패턴에 소유자 확정을 더한 것이다. "
        "가장 최근의 완전 큐레이션 분기인 "
        f"`{payload['holdout']}` 는 채점용이다. 세칙·지속가능성·금감원 중복·한공회 재안내·불공정거래·소유주식·중점 점검에 대한 소유자 확정을 반영한 뒤의 수치다.",
        "",
        "콘텐츠 파일은 수정하지 않는다. 마커는 편집기 저장 형식과 같고, 제안의 `pending` 은 "
        "실제 PDF·캡처 경로를 아직 모른다는 뜻이다.",
        "",
        "## 데이터 형태",
        "",
        "- 크롤 원본은 각 분기 파일 말미 `## Appendix A` 에 그대로 있다.",
        "- 본문(Appendix 앞)은 사람이 남긴 항목만 있다. `prepare_deploy.py` 가 `<!-- skip -->` 쌍을 지우므로, "
        "배포된 분기에는 스킵 마커가 없고 **Appendix에만 있는 링크 = 스킵**이다.",
        "- 본문에 `!!! note` 가 있으면 요약(편집기 상태 완료). `<!-- no_summary -->` 또는 마커 없는 링크는 링크만 유지.",
        "- `<!-- source: type|ref -->` 는 2025 Q1과 2026년에 남아 있다. 2023–2024와 2025 Q2–Q4 요약문은 출처 마커 없이 노트만 있는 경우가 많다.",
        "- 본문에만 있고 Appendix에 없는 링크는 수기 추가(시행세칙 등)라 채점에서 뺀다.",
        "",
        "## 채점 정의",
        "",
        "- 스킵 정밀도·재현율의 양성 클래스는 **스킵**이다.",
        "- 3분류 정확도는 스킵 / 링크만(`no_summary`) / 요약이 모두 맞을 때의 비율이다.",
        "- 출처 정확도는 실제 출처 유형이 남아 있는 항목만 분모로 한다. 유형(`pdf`·`shot`·`clip`·`web`)이 같고 요약으로 제안했을 때 맞춘 것으로 센다. 파일 경로·clip id 는 맞추지 않는다.",
        "- 출처 계열 정확도는 `pdf`(첨부)와 페이지 캡처(`shot`/`clip`/`web`)만 구분한다.",
        "",
        "## 수치",
        "",
        "| 구간 | 건수 | 스킵 정밀도 | 스킵 재현율 | 스킵 F1 | 3분류 정확도 | 출처 유형 정확도 | 출처 계열 정확도 |",
        "|------|-----:|-----------:|-----------:|--------:|-------------:|-----------------:|-----------------:|",
    ]
    order = ["2023-2024", "2025-2026Q1", "holdout", "other-2026"]
    labels = {
        "2023-2024": "2023–2024 (관행이 성겨 있음)",
        "2025-2026Q1": "2025–2026 Q1 (규칙 관찰 구간)",
        "holdout": "2026 Q2 홀드아웃",
        "other-2026": "기타 2026",
    }
    for key in order:
        metrics = payload["metrics"].get(key)
        if not metrics:
            continue
        lines.append(
            "| {name} | {n} | {sp} | {sr} | {sf} | {tw} | {src} | {fam} |".format(
                name=labels.get(key, key),
                n=metrics["n"],
                sp=_pct(metrics["skip_precision"]),
                sr=_pct(metrics["skip_recall"]),
                sf=_pct(metrics["skip_f1"]),
                tw=_pct(metrics["three_way_accuracy"]),
                src=_pct(metrics["source_type_accuracy"]),
                fam=_pct(metrics["source_family_accuracy"]),
            )
        )

    hold = payload["metrics"].get("holdout", {})
    lines += [
        "",
        "### 홀드아웃 세부",
        "",
        f"- 파일 수: 관찰 구간 {payload['files'].get('2025-2026Q1', 0)}개, "
        f"2023–2024 {payload['files'].get('2023-2024', 0)}개, 홀드아웃 {payload['files'].get('holdout', 0)}개.",
        f"- 스킵 TP/FP/FN: {hold.get('skip_tp', 0)}/{hold.get('skip_fp', 0)}/{hold.get('skip_fn', 0)}.",
        f"- 출처 유형: {hold.get('source_type_n', 0)}건 중 정확도 {_pct(hold.get('source_type_accuracy'))}. "
        f"요약을 맞춘 뒤의 유형 정확도 {_pct(hold.get('source_type_accuracy_when_summarized'))} "
        f"(n={hold.get('source_type_when_summarized_n', 0)}).",
        f"- 보류(중점 점검, 마커 없음): {hold.get('review_n', 0)}건. "
        f"보류를 분모에서 뺀 3분류 정확도 {_pct(hold.get('three_way_accuracy_excluding_review'))}.",
        "",
        "3분류 혼동 (실제 → 제안, 홀드아웃):",
        "",
    ]
    confusion = hold.get("confusion") or {}
    if confusion:
        lines.append("| 실제 → 제안 | 건수 |")
        lines.append("|-------------|-----:|")
        for key, count in confusion.items():
            lines.append(f"| {key} | {count} |")
    else:
        lines.append("혼동 행렬 없음.")

    lines += [
        "",
        "## 홀드아웃 불일치",
        "",
        f"자동 판정이 과거 선별과 다른 항목 {len(mismatches)}건. "
        "`review` 는 중점 점검이라 마커를 내지 않으며 아래 보류 목록으로 뺀다. "
        "정밀도에 닿는 것은 실제로는 남겼는데 스킵으로 제안한 경우이고, "
        "재현율에 닿는 것은 실제 스킵을 남긴 경우다.",
        "",
        "| 날짜 | 기관 | 섹션 | 실제 | 제안 | 규칙 | 신뢰 | 제목 |",
        "|------|------|------|------|------|------|-----:|------|",
    ]
    if mismatches:
        for row in sorted(mismatches, key=lambda r: (r.actual, r.predicted, r.item.agency or "", r.item.date)):
            lines.append(_mismatch_line(row))
    else:
        lines.append("| - | - | - | - | - | - | - | 없음 |")

    lines += [
        "",
        "## 홀드아웃 보류 (중점 점검)",
        "",
        "마커를 쓰지 않는다. 재무제표·비상장 중점 점검분야와 사업보고서 중점 점검사항은 과거에 종종 남았고, "
        "공시 실태·시장·교육·정책금융 중점 점검은 대개 스킵이었다.",
        "",
        "| 날짜 | 기관 | 섹션 | 과거 선별 | 제안 | 규칙 | 신뢰 | 제목 |",
        "|------|------|------|-----------|------|------|-----:|------|",
    ]
    if reviews:
        for row in sorted(reviews, key=lambda r: (r.item.agency or "", r.item.date, r.item.title)):
            lines.append(_mismatch_line(row))
    else:
        lines.append("| - | - | - | - | - | - | - | 없음 |")

    lines += [
        "",
        "## 홀드아웃 출처 유형 불일치",
        "",
        "실제 출처 마커가 있는 항목 가운데 제안 유형이 다른 경우다. `pending` 경로는 비교하지 않는다.",
        "",
        "| 날짜 | 기관 | 섹션 | 실제 | 제안 | 규칙 | 신뢰 | 제목 |",
        "|------|------|------|------|------|------|-----:|------|",
    ]
    if source_misses:
        for row in sorted(source_misses, key=lambda r: (r.item.agency or "", r.item.date, r.item.title)):
            lines.append(_mismatch_line(row))
    else:
        lines.append("| - | - | - | - | - | - | - | 없음 |")

    lines += [
        "",
        "## 읽는 법",
        "",
        "- 2023–2024 3분류 정확도가 더 낮으면, 그 시기에는 회계 항목을 노트 없이 링크만 남긴 경우가 많아서다. "
        "최근 관행(2025 이후)은 같은 주제를 요약한다. 규칙은 최근 관행을 따른다.",
        "- 스킵 정밀도가 높고 3분류가 그보다 낮으면, 빠질 기사를 가리는 것보다 "
        "**남긴 기사를 요약할지 링크만 둘지**가 더 어렵다.",
        "- 규칙 설명과 사람이 볼 경계 사례는 [curation-rules.md](curation-rules.md)에 있다.",
        "",
    ]
    return "\n".join(lines)


def suggest_file(path: Path, scope: str) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    body, appendix = parse_document(text)
    chosen = appendix if scope == "appendix" else body
    # Duplicate detection should see the whole collected set when appendix exists.
    context = appendix or body
    decisions = decide_all(context)
    # Re-decide the chosen scope with the same context when scopes differ.
    if chosen is not context:
        # Map by url key + title so body items pick up appendix decisions.
        index: dict[tuple, Decision] = {}
        for item, decision in zip(context, decisions):
            index.setdefault((item.agency, item.url, squash(item.title)), decision)
        output = []
        for item in chosen:
            decision = index.get((item.agency, item.url, squash(item.title)))
            if decision is None:
                decision = decide_one(item)
            output.append(_public_row(item, decision))
        return output
    return [_public_row(item, decision) for item, decision in zip(chosen, decisions)]


def _public_row(item: Item, decision: Decision) -> dict:
    return {
        "date": item.date,
        "agency": item.agency,
        "section": item.section,
        "title": item.title,
        "url": item.url,
        **decision.to_public(),
    }


def _print_table(rows: list[dict]) -> None:
    counts = Counter(row["bucket"] for row in rows)
    print(
        f"# 제안 {len(rows)}건 | 스킵 {counts.get('skip', 0)} | 링크만 {counts.get('no_summary', 0)} | "
        f"요약 {counts.get('summarize', 0)} | 보류 {counts.get('review', 0)}"
    )
    print("date\tagency\tsection\tstate\tmarker\tconf\trule\treason\ttitle")
    for row in rows:
        title = row["title"].replace("\t", " ")
        reason = row["reason"].replace("\t", " ")
        print(
            f"{row['date']}\t{row['agency']}\t{row['section']}\t{row['state']}\t"
            f"{row['marker'] or ''}\t{row['confidence']:.2f}\t{row['rule_id']}\t{reason}\t{title}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="분기 md에 편집기 큐레이션 마커를 제안합니다. 파일을 수정하지 않습니다."
    )
    parser.add_argument("path", nargs="?", help="분기 markdown 경로")
    parser.add_argument("--backtest", action="store_true", help="과거 분기와 비교해 지표를 계산")
    parser.add_argument("--holdout", default=HOLDOUT_NAME, help="채점에서 빼 둘 파일명")
    parser.add_argument("--report", type=Path, help="백테스트 마크다운을 이 경로에 쓴다")
    parser.add_argument("--json", action="store_true", help="제안 결과를 JSON으로 출력")
    parser.add_argument(
        "--scope",
        choices=("body", "appendix"),
        default="body",
        help="body는 편집기가 보는 본문 링크, appendix는 수집 원본 전체",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "docs" / "quality-updates",
    )
    args = parser.parse_args(argv)

    if args.backtest:
        payload = run_backtest(args.root, args.holdout)
        report = render_report(payload)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(report, encoding="utf-8")
            print(f"[DONE] report → {args.report}", file=sys.stderr)
        if args.json:
            public = {
                "holdout": payload["holdout"],
                "files": payload["files"],
                "manual_body_additions": payload["manual_body_additions"],
                "metrics": payload["metrics"],
            }
            print(json.dumps(public, ensure_ascii=False, indent=2))
        elif not args.report:
            print(report)
        return 0

    if not args.path:
        parser.error("제안할 markdown 경로가 필요합니다. 비교만 하려면 --backtest 를 쓰세요.")
    rows = suggest_file(Path(args.path), args.scope)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        _print_table(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

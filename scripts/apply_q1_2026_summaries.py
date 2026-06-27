from __future__ import annotations

"""DEPRECATED: Phase 2 제거(2026-06-26 spec) 이후 Phase 1 note 일괄 삽입용. 신규 실행 금지."""

import re
from pathlib import Path


TARGET = Path("docs/quality-updates/2026/2026-01-01_to_2026-03-31.md")


def _block(title: str, body_lines: list[str]) -> list[str]:
    marker = '!!! note "{}"'.format(title)
    lines = ["", f"    {marker}", ""]
    lines.extend([f"        {line}" if line else "" for line in body_lines])
    lines.append("")
    return lines


def _type_a_table(rows: list[tuple[str, str, str, str]]) -> list[str]:
    lines = [
        '| 회사명 | 대상자 | 위반내용 | 과징금 부과액 |',
        '| --- | --- | --- | --- |',
    ]
    for r in rows:
        lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} |")
    return lines


def _type_b_table(rows: list[tuple[str, str, str, str]]) -> list[str]:
    lines = [
        '| 회사명 | 구분 | 주요 지적사항 | 주요 조치 |',
        '| --- | --- | --- | --- |',
    ]
    for r in rows:
        lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} |")
    return lines


def summary_block(source_ref: str, title: str) -> tuple[list[str], bool]:
    inaccessible = False
    t = title.strip()

    if source_ref == "pdf|downloads/260327_(보도자료) 2026년도 금융감독원 회계심사, 감리업무 운영계획.pdf":
        return _block(
            "주요 내용",
            [
                "- (개요) 금융감독원이 **2026년도 회계심사·감리업무 운영계획**을 발표하고 회계정보 신뢰성 제고를 위한 감독 기조를 제시함",
                "- (방향) 분식회계 **무관용 원칙** 하에 고위험 기업 집중 모니터링, 부실기업 신속 퇴출, 심사·감리 주기 단축 로드맵을 추진함",
                "- (집행) 상장법인 등 **170사 재무제표 심사·감리**, 회계법인 **10사 감사인 감리**를 실시하고 중대 사건 중심으로 감독 자원을 배분함",
                "- (제도) 내부회계관리제도 감리 확대, 투자자약정·전환사채·공급자금융 공시 등 **중점 회계이슈** 사전 안내 후 신속 점검을 예고함",
                "- (감사품질) 회계법인 위험기반 감리, 경영진 견제기구 설치 의무화, 품질관리평가 공개 추진 등으로 감사품질 책임체계를 강화함",
            ],
        ), inaccessible

    if source_ref == "clip|clip_1782479638_62d30645":
        return _block(
            "주요 내용",
            [
                "- (배경) 불합리한 계리가정이 이익 과대인식과 보험부채 과소평가로 이어질 수 있어 감독당국의 체계적 검증 필요성이 제기됨",
                "- (조직) 금감원이 조직개편을 통해 **계리감리팀**을 신설하고 계리가정 감리 전담체계를 구축함",
                "- (점검) 계리가정·현금흐름 모델링·내부통제 운영의 적정성과 보험업법·감독회계 준수 여부를 중점 확인할 계획임",
                "- (조치) 경미한 사항은 개선권고로 시정 유도하되, 중대 위반은 엄정 제재한다는 방침임",
                "- (일정) 계리가정보고서를 도입하고 상반기 정기감리에 착수하여 보험부채 평가 관행의 신뢰성 제고를 추진함",
            ],
        ), inaccessible

    if source_ref == "pdf|downloads/260225_(보도자료) 25년 외부감사대상 회사 및 감사인 지정 현황.pdf":
        return _block(
            "주요 내용",
            [
                "- (규모) ’25년말 외부감사대상 회사는 **42,891사**로 전년 대비 **773사(1.8%) 증가**함",
                "- (지정) 감사인지정 회사는 **1,971사**로 전년 대비 **112사(6.0%) 증가**했으며, 주기적 지정은 유사하고 직권지정이 증가함",
                "- (상장사) 상장법인 지정회사 수는 **961사**, 지정비율은 **34.9%**로 전년 대비 소폭 하락함",
                "- (사유) 직권지정 사유는 상장예정법인, 감사인 미선임, 재무기준 미달, 관리종목 순으로 분포함",
                "- (운영) 지정방식 합리화와 이해관계자 소통을 통해 제도 준수 지원 및 회계투명성 제고를 병행할 계획임",
            ],
        ), inaccessible

    if source_ref == "clip|clip_1782479745_53797b8e":
        return _block(
            "주요 내용",
            [
                "- (개편) 금융위가 불공정거래·회계부정 내부제보 활성화를 위해 신고포상금 제도 전면 개편을 예고함",
                "- (상한) 주가조작·회계부정 신고 포상금의 **지급상한을 폐지**하고, 환수 부당이득·과징금의 **최대 30%** 지급 구조를 제시함",
                "- (범위) 경찰청 등 타 행정기관 신고 건도 연계해 포상금을 지급하는 **범부처 연계 지급체계**를 추진함",
                "- (절차) 자본시장법·외감법 시행령 및 하위규정 개정안을 입법예고·규정변경예고(2.26~4.7)함",
                "- (일정) 법제처 심사·차관회의·국무회의 절차를 거쳐 이르면 2분기 시행을 목표로 함",
            ],
        ), inaccessible

    if source_ref == "pdf|downloads/260213_(보도자료) 2025년 사업보고서에 대해서 내부회계관리와 자기주식에 대한 충분한 정보제공 여부를 확인할 예정입니다..pdf":
        return _block(
            "주요 내용",
            [
                "- (예고) 금감원이 2025년 사업보고서 제출 전 **중점점검사항 17개(재무 13, 비재무 4)**를 사전 공지함",
                "- (재무) 내부회계관리제도 운영보고서·효과성 평가결과·감사의견, 감사보수·시간, 핵심감사사항 등 공시 충실도를 점검함",
                "- (비재무) 자기주식 처리계획·이행현황, 중대재해 발생사실, 제재현황 등 최근 제도개정 반영 항목을 중점 확인함",
                "- (일정) ’26년 5월 점검 후 6월 중 미흡사항 자진정정 안내, 중대·반복 부실기재는 심사대상 선정 및 제재 검토 예정임",
                "- (유의) 공시담당 임원·실무자가 기업공시서식 작성기준의 신규 항목을 사전 점검해 누락을 최소화할 필요가 있음",
            ],
        ), inaccessible

    if source_ref in {
        "pdf|downloads/260204_(보도자료) 우리 기업의 회계투명성을 개선하여 자본시장 질서를 확립해 나가겠습니다.pdf",
        "pdf|downloads/260204(보도자료) 우리 기업의 회계투명성을 개선하여 자본시장 질서를 확립해 나가겠습니다.pdf",
    }:
        return _block(
            "주요 내용",
            [
                "- (개요) 증선위가 **회계·감사 품질 제고방안**을 발표하고 회계부정 제재 실효성, 감사품질 경쟁, 지배구조 개선을 종합 추진함",
                "- (퇴출) 고의 회계부정 지시자(실질 지시자 포함)의 상장사 임원 취업 제한 등 **시장퇴출 장치**를 강화함",
                "- (감독) 감사시간 과소투입 등 부실감사 징후에 대한 심사·감리 연계와 제재수단 다양화를 통해 감사품질 책임을 확대함",
                "- (지정) 지배구조 취약 비상장사에 대한 직권지정 확대, 품질우수 중견법인 인센티브 도입으로 지정시장 경쟁구조를 개편함",
                "- (거버넌스) 대형 회계법인에 외부전문가 중심의 감사품질 감독기구 설치·공시를 의무화하고 ’26년 중 제도화 추진 예정임",
            ],
        ), inaccessible

    if source_ref == "pdf|downloads/260120_(보도자료) 보험상품의 엄밀한 계리가정 수립과 관리,감독 체계를 구축하여 공정하고 객관적인 보험부채 평가 관행을 확립하겠습니다..pdf":
        return _block(
            "주요 내용",
            [
                "- (배경) IFRS17·K-ICS 도입 이후 계리가정 편차로 보험부채 과소평가 우려가 제기되어 **계리감독 선진화 방안**을 마련함",
                "- (원칙) 계리가정 수립의 핵심원칙으로 중립성·보수성·비교가능성을 제시하고, 내부통제·시장규율 강화 원칙을 병행함",
                "- (손해율) 신규담보 보수적 가정, 비실손 갱신가정 현실화, 최종손해율 적용 합리화, 산출단위 세분화 기준을 도입함",
                "- (사업비) 물가상승률 반영 원칙과 공통비의 전 보험계약기간 인식 원칙을 제시해 비용가정 왜곡을 축소함",
                "- (이행) 계리가정보고서 도입 및 공시 강화와 함께 가이드라인을 ’26년 2분기 결산부터 적용하고 감독규정 개정을 추진함",
            ],
        ), inaccessible

    if source_ref == "pdf|downloads/260113_(보도자료) 보험회사가 충분한 기본자본을 보유하도록 하여 든든한 보험회사로 성장할 수 있는 여건을 조성합니다.pdf":
        return _block(
            "주요 내용",
            [
                "- (도입) 보험사 자본구조의 질 개선을 위해 **기본자본 K-ICS 비율**을 건전성 기준으로 도입함",
                "- (기준) 기본자본비율 기준을 **50%**로 설정하고, 미달 시 경영개선권고·요구 등 적기시정조치를 적용함",
                "- (상환) 기본자본증권 조기상환 시 기본자본비율 **80% 유지**(차환 등 예외 시 50% 이상) 요건을 신설함",
                "- (경과) ’27년 시행, ’35년말까지 9년 경과조치를 두고 최저이행기준을 분기별 부과해 연착륙을 유도함",
                "- (보완) 해약환급금준비금 관련 기본자본 인정구조를 조정해 지급여력 양호 보험사의 역인센티브를 완화함",
            ],
        ), inaccessible

    if source_ref == "pdf|downloads/260107_(보도자료) 2026년 「외부감사제도 전국 순회설명회」 개최.pdf":
        return _block(
            "주요 내용",
            [
                "- (목적) 감사인 선임기한·절차 위반으로 인한 지정 사례 예방을 위해 **외부감사제도 전국 순회설명회**를 개최함",
                "- (일정) 서울·광주·대구·울산·부산 5개 도시에서 1.26~1.30 기간 중 순차 진행함",
                "- (내용) 외부감사 대상·면제 판단, 감사인 선임·지정 제도, 주요 FAQ 및 위반사례를 실무 중심으로 안내함",
                "- (지원) 지방소재 기업·감사인의 접근성을 높이고 현장 질의·상담을 병행하는 방식으로 운영함",
                "- (후속) 설명회 자료를 금감원 홈페이지에 게시해 미참석자도 참고할 수 있도록 제공할 계획임",
            ],
        ), inaccessible

    if source_ref == "pdf|downloads/260325(보도참고) 감사보고서에 대한 조사·감리결과 조치.pdf" and "IR 담당" not in t:
        body = [
            "- (개요) 제6차 증권선물위원회(3.25.)에서 감사절차 위반 감사인에 대한 조치를 의결함",
            "- (주요) 한국공인회계사회 위탁감리위원회 의결 결과를 원안 접수하고 손해배상공동기금 추가적립 등을 확정함",
            "",
            *_type_b_table(
                [
                    ("OOOOOO㈜", "비상장법인", "감사인이 수익인식기준 타당성 검토 등 핵심 감사절차를 생략 또는 현저히 미흡 수행", "정안회계법인 손해배상공동기금 추가적립 10%, 공인회계사 1인 직무연수 2시간"),
                ]
            ),
        ]
        return _block("조사·감리결과 지적사항 및 조치내역", body), inaccessible

    if source_ref == "pdf|downloads/260325(보도참고) 감사보고서에 대한 조사·감리결과 조치.pdf" and "IR 담당" in t:
        return _block(
            "주요 내용",
            [
                "- (개요) 같은 날짜 증선위 의결 건으로, 상장사 **IR 담당 임원 불공정거래 혐의** 적발·조치 사실을 별도 공지함",
                "- (구분) 본 링크는 자본시장 불공정거래 집행 성격의 공지이며 회계감리 조치와 별도 맥락에서 안내된 사안임",
                "- (시사점) IR 공시·소통 과정의 내부통제 및 미공개중요정보 관리체계 점검 필요성이 강조됨",
            ],
        ), inaccessible

    if source_ref == "shot|downloads/fsc.go.kr-preview (3).png":
        return _block(
            "주요 내용",
            [
                "- (재선임) 한국이 IFRS재단 **지속가능성기준자문포럼(SSAF)** 2기(’26~’28) 회원국으로 재선임됨",
                "- (의의) 국내 지속가능성 공시제도 설계 과정의 실무 쟁점과 이해관계자 의견을 국제 기준 논의에 반영할 채널을 확보함",
                "- (운영) 금융위·KSSB가 공동 대표로 정기회의에 참여해 국제기준 정합성과 국내 이행가능성의 균형을 추진할 계획임",
            ],
        ), inaccessible

    if source_ref == "clip|clip_1782482557_b32ec367":
        body = [
            "- (개요) 제5차 금융위원회(3.18.)에서 ㈜볼빅·㈜이킴 관련 최종 과징금 부과를 의결함",
            "",
            *_type_a_table(
                [
                    ("㈜볼빅", "회사", "회계처리기준 위반 재무제표 작성·공시", "17.7억원"),
                    ("", "前대표이사 등 2인", "회계처리기준 위반 관련 회사관계자 책임", "2.9억원"),
                    ("", "안진회계법인", "외부감사 과정 감사절차 소홀", "1.7억원"),
                    ("㈜이킴", "회사", "회계처리기준 위반 재무제표 작성·공시", "5,020만원"),
                    ("", "前대표이사 등 3인", "회계처리기준 위반 관련 회사관계자 책임", "1,500만원"),
                ]
            ),
        ]
        return _block("조사·감리결과 최종 과징금 부과", body), inaccessible

    if source_ref == "pdf|downloads/260311(보도참고) 사업보고서 등에 대한 조사·감리결과 조치.pdf":
        body = [
            "- (개요) 제5차 증권선물위원회(3.11.)에서 이화전기공업㈜ 회계처리기준 위반에 대한 조치를 의결함",
            "",
            *_type_b_table(
                [
                    ("이화전기공업㈜", "비상장법인", "금융자산 담보제공 사실 주석 미기재(’21·’22년 52,000백만원), 내부회계관리제도 중요 취약사항 발생", "과징금(금융위 최종결정 예정), 감사인지정 2년, 前담당임원 해임권고 상당, 개선권고"),
                ]
            ),
        ]
        return _block("조사·감리결과 지적사항 및 조치내역", body), inaccessible

    if source_ref == "clip|clip_1782482690_79cdaf1b":
        return _block(
            "주요 내용",
            [
                "- (개요) 제5차 증권선물위원회(3.11.)에서 **합동대응단 1호 사건** 관련 개인 11명·법인 4개사에 대한 검찰 고발을 의결함",
                "- (혐의) 저유동성 종목 대상 시세조종, 가장·통정매매, 허수주문, 시종가 관여 등 복합 주문전략으로 시장가격을 왜곡한 혐의임",
                "- (추가) 소액주주운동을 빌미로 경영진 압박 후 자기주식 신탁계좌 주문을 활용해 주가를 관리·유인한 정황이 제시됨",
                "- (의미) 회계·공시 영역과 연계된 자본시장 질서 위반에 대해 조사·제재 공조를 강화하는 집행 기조를 재확인한 조치임",
            ],
        ), inaccessible

    if source_ref == "pdf|downloads/260225(보도참고) 사업보고서 등에 대한 조사·감리결과 조치.pdf":
        body = [
            "- (개요) 제4차 증권선물위원회(2.25.)에서 ㈜국보와 감사인 신우회계법인 관련 회계위반·부실감사 조치를 의결함",
            "",
            *_type_b_table(
                [
                    ("㈜국보", "비상장법인", "종속회사 대여금 대손상각비 과대계상, 전환사채·BW 관련 선급비용 과대계상, 소액공모 공시서류 거짓기재", "과징금(금융위 최종결정 예정), 감사인지정 2년, 과태료 3,600만원, 시정요구"),
                    ("㈜국보 감사인(신우회계법인)", "외부감사인", "종속회사 대여금 및 전환사채 관련 감사절차 소홀로 위반사항 반영 실패", "신우회계법인 손해배상공동기금 20% 추가적립·당해회사 감사제한 2년, 담당 공인회계사 제재"),
                ]
            ),
        ]
        return _block("조사·감리결과 지적사항 및 조치내역", body), inaccessible

    if source_ref == "clip|clip_1782482845_a3f9fe3d":
        return _block(
            "주요 내용",
            [
                "- (개편) 주가조작·회계부정 신고포상금의 **지급상한(불공정거래 30억원, 회계부정 10억원) 폐지** 방침을 재확인함",
                "- (산식) 적발·환수된 부당이득·과징금에 연동해 최대 30% 범위에서 포상금을 산정하는 구조를 제시함",
                "- (연계) 금융위·금감원 외 기관 접수 건도 포상금 지급이 가능하도록 기관 간 협업체계를 강화함",
                "- (절차) 자본시장법·외감법 시행령 및 하위규정 개정안 입법예고를 통해 제도개편 법적 기반을 마련 중임",
            ],
        ), inaccessible

    if source_ref == "pdf|downloads/260128(보도참고) 사업보고서 등에 대한 조사·감리결과 조치.pdf":
        body = [
            "- (개요) 제2차 금융위원회(1.28.)에서 ㈜스포츠서울 회사관계자에 대한 최종 과징금 부과를 의결함",
            "",
            *_type_a_table(
                [
                    ("㈜스포츠서울", "前업무집행지시자", "횡령 관련 자기자본 과대계상 등 회계처리기준 위반", "3.4억원"),
                    ("", "前대표이사", "횡령 관련 회계처리기준 위반 책임", "3.0억원"),
                    ("", "前부사장", "횡령 관련 회계처리기준 위반 책임", "3.4억원"),
                    ("", "前담당임원", "횡령 관련 회계처리기준 위반 책임", "3.4억원"),
                ]
            ),
        ]
        return _block("조사·감리결과 최종 과징금 부과", body), inaccessible

    if source_ref == "pdf|downloads/260121(보도참고) 사업보고서 등에 대한 조사·감리결과 조치.pdf":
        body = [
            "- (개요) 제2차 증권선물위원회(1.21.)에서 ㈜볼빅 회계위반과 감사인 부실감사에 대한 조치를 의결함",
            "",
            *_type_b_table(
                [
                    ("㈜볼빅", "코넥스 상장법인", "재고자산 과대계상(’17~’21년), 외부감사 방해", "과징금(금융위 최종결정 예정), 감사인지정 3년, 해임권고 상당, 검찰고발"),
                    ("㈜볼빅 감사인(안진회계법인)", "외부감사인", "재고자산 관련 감사절차 소홀", "과징금(금융위 최종결정 예정), 손해배상공동기금 50% 추가적립, 당해회사 및 지정회사 감사업무 제한"),
                ]
            ),
        ]
        return _block("조사·감리결과 지적사항 및 조치내역", body), inaccessible

    if source_ref in {
        "shot|downloads/fsc.go.kr-preview (2).png",
        "shot|downloads/fsc.go.kr-preview (1).png",
    }:
        # Duplicate policy items captured from FSC web preview; summarize consistently.
        if "기본자본" in t:
            return _block(
                "주요 내용",
                [
                    "- (기준) 보험회사 기본자본 K-ICS 비율을 50% 기준으로 설정하고 미달 시 적기시정조치를 적용하는 제도 도입을 예고함",
                    "- (상환) 기본자본증권 조기상환 시 기본자본비율 80% 유지 요건(차환 예외 포함)을 제시해 자본질 관리 유인을 강화함",
                    "- (일정) ’27년 시행, ’35년말까지 경과조치를 두어 보험사별 분기 목표를 통해 단계적 이행을 유도함",
                ],
            ), inaccessible
        return _block(
            "주요 내용",
            [
                "- (방향) 보험업권 계리감독 선진화 방안으로 손해율·사업비 가정의 보수성·비교가능성·내부통제 강화를 추진함",
                "- (핵심) 신규담보 손해율 가정, 비실손 갱신가정, 공통비 인식기준 등 보험부채 과소평가 우려 영역의 가이드라인을 제시함",
                "- (이행) 계리가정보고서 도입 및 감독규정 개정을 통해 ’26년 2분기 결산·시행 일정에 맞춘 집행을 예고함",
            ],
        ), inaccessible

    if source_ref == "pdf|downloads/260107(보도참고) 감사보고서 등에 대한 조사·감리결과 조치.hwp":
        body = [
            "- (개요) 제1차 증권선물위원회(**1.7.**)에서 ㈜이킴·㈜세코닉스 감사인 등에 대한 조사·감리 조치를 의결함",
            "",
            *_type_b_table(
                [
                    ("㈜이킴", "비상장법인", "회계처리기준 위반 재무제표 작성·공시", "감사인지정 2년 등 조치 의결, 과징금은 금융위 최종결정 예정"),
                    ("㈜세코닉스 감사인(다산회계법인)", "외부감사인", "감사절차 소홀(’19년 관련 사항)", "손해배상공동기금 추가적립 20%, 당해회사 감사업무 제한 등"),
                ]
            ),
        ]
        return _block("조사·감리결과 지적사항 및 조치내역", body), inaccessible

    if source_ref == "pdf|downloads/금융위원회 공고 제2026-189호(외감법시행령 및 포상규정 개정안 입법예고 중 정정).pdf":
        return _block(
            "주요 내용",
            [
                "- (정정) 외감법 시행령·회계부정 포상규정 개정안 공고(제2026-168호)의 **포상금 지급시기 조문** 정정 내용을 공표함",
                "- (변경) 포상금 지급요건 충족시점 정의를 구체화하고, 과징금 부과결정 시 **1/10 선지급(상한 1억원)** 구조를 명시함",
                "- (의미) 신고포상금 지급절차의 예측가능성과 집행 명확성을 높이기 위한 후속 정비 성격임",
            ],
        ), inaccessible

    if source_ref == "shot|downloads/fsc.go.kr-preview.png":
        return _block(
            "주요 내용",
            [
                "- (예고) 외감법 시행령·회계부정 포상규정 개정안을 입법예고·규정변경예고(2.26~4.7)함",
                "- (핵심) 포상금 상한 폐지, 과징금 연동 산정(최대 30%), 타기관 접수 신고 연계 지급 등 신고 유인 강화안을 포함함",
                "- (의견) 이해관계자 의견제출 기한을 **2026.4.7.**로 제시함",
            ],
        ), inaccessible

    if source_ref == "pdf|downloads/1. 금융위원회 공고 제2026-164호_금융위원회 운영규칙 및 증권선물위원회 운영규칙 일부개정고시안.pdf":
        return _block(
            "주요 내용",
            [
                "- (개정) 금융위·증선위 운영규칙의 단순·반복 행정절차 일부를 위원장 권한으로 위임하는 규정변경안을 예고함",
                "- (회계) 회계감사기준·품질관리기준 제개정 사전승인, 공인회계사 등록취소·직무정지 건의 등 회계감독 절차 위임사항을 명시함",
                "- (절차) 회계 관련 위탁업무규정 제개정 승인 등 증선위원장 위임사항을 포함하고, 의견제출 기한을 **2026.2.24.**로 제시함",
            ],
        ), inaccessible

    if source_ref == "shot|downloads/www.kicpa.or.kr-preview (5).png":
        return _block(
            "주요 내용",
            [
                "- (안내) 2025년 12월말 법인 기준 **법인세 세무조정업무 수임신고** 제출을 공지함",
                "- (기한) 제출기한은 **2026.4.30.**이며 KICPA 통합플랫폼을 통한 전자제출 방식만 허용함",
                "- (유의) 기한 내 제출 시 직무회비 감면, 지연 제출 시 구간별 가산금 부과 규정을 재안내함",
            ],
        ), inaccessible

    if source_ref == "shot|downloads/www.kicpa.or.kr-preview (4).png":
        return _block(
            "주요 내용",
            [
                "- (안내) 외부감사업무 수임신고 제출 절차와 2026년 변경 템플릿(표준감사시간 추가)을 안내함",
                "- (기한) 12월 결산법인 기준 제출기한을 **2026.3.16.**로 공지하고 DART 감사계약체결보고서 업로드 방식 등을 제시함",
                "- (유의) 지연신고 가산금 부과 및 법인계정 제출 원칙 등 실무 유의사항을 강조함",
            ],
        ), inaccessible

    if source_ref == "shot|downloads/www.kicpa.or.kr-preview (3).png":
        return _block(
            "주요 내용",
            [
                "- (협조) 한국거래소 요청에 따라 상장법인 외부감사 시 감사인이 확인해야 할 협조사항을 안내함",
                "- (핵심) 감사의견 비적정 통보, 손상차손 표시, 리픽싱조건부 금융상품 관련 확인서 협조 등 거래소 연계 실무사항을 포함함",
                "- (참고) 감사업무 수행 시 관련 공문 및 담당자 연락체계를 활용하도록 부속자료를 제공함",
            ],
        ), inaccessible

    if source_ref == "pdf|downloads/공문(감사인증기준본부-19).pdf":
        inaccessible = True
        lines = [
            "",
            "<!-- 원문 접근 불가 -->",
            "",
            '    !!! note "주요 내용"',
            "",
            "        - (확인) 첨부 공문 PDF가 비어 있어 원문 텍스트 확인이 불가능함",
            "        - (처리) 본 항목은 추가 원문 확보 전까지 `<!-- 원문 접근 불가 -->` 기준으로 관리하는 것이 필요함",
            "",
        ]
        return lines, inaccessible

    if source_ref == "shot|downloads/www.kicpa.or.kr-preview (6).png":
        return _block(
            "주요 내용",
            [
                "- (안내) 2025년 재무제표 작성 관련 회계투명성 제고 유의사항과 심사·감리 업무 개요를 종합 공지함",
                "- (범위) 비상장법인 심사·감리 체계, 2025년 중점 점검분야(매출채권 대손충당금·연결재무제표·이연법인세·국외매출) 등을 재안내함",
                "- (실무) 재무제표 작성 단계에서 분기별 유의사항 공지를 통합 반영하도록 감사인·작성자 점검을 요구함",
            ],
        ), inaccessible

    if source_ref == "shot|downloads/www.kicpa.or.kr-preview (2).png":
        return _block(
            "주요 내용",
            [
                "- (안내) 2025년 4분기 재무제표 회계투명성·감사품질 제고 유의사항을 공문 형태로 배포함",
                "- (구성) 4분기 안내와 함께 1~3분기 유의사항 재안내 자료를 병행 제공해 연간 점검 연속성을 강조함",
                "- (실무) 감사업무 수행 시 누적 유의사항 반영 여부를 최종 결산단계에서 재확인하도록 요청함",
            ],
        ), inaccessible

    if source_ref == "pdf|downloads/(붙임)네트워크 회계법인에 대한 비감사용역 계약체결 현황 공시 서식 관련 FAQ.pdf":
        return _block(
            "주요 내용",
            [
                "- (목적) 사업보고서 내 **네트워크 회계법인 비감사용역 계약 공시** 실무 적용을 위한 FAQ를 배포함",
                "- (정의) 국제윤리기준과 정합화된 네트워크 회계법인 정의(브랜드·전략·품질정책·자원공유 등)를 제시함",
                "- (범위) 국내·해외 네트워크 법인 계약은 공시대상이나, 종속기업 계약은 원칙적으로 제외(지점·사무소는 포함) 기준을 명확화함",
                "- (경과) ’26년 첫 적용 시 전기·전전기 연계기재 및 윤리기준 경과규정 적용방식까지 예시로 안내함",
            ],
        ), inaccessible

    if source_ref == "shot|downloads/www.kasb.or.kr-preview.png":
        return _block(
            "주요 내용",
            [
                "- (조회) IASB 공개초안 **위험경감회계(Risk Mitigation Accounting)**에 대한 국내 검토의견 제출을 요청함",
                "- (기한) 국내 의견수렴 기한을 **2026.6.12.**, IASB 직접 제출 기한을 **2026.7.31.**로 안내함",
                "- (지원) 기준원 검토보고서와 원문 자료를 제공하고, 영문 제출 관련 담당자 지원채널을 병행 안내함",
            ],
        ), inaccessible

    if source_ref == "shot|downloads/www.kasb.or.kr-preview (1).png":
        return _block(
            "주요 내용",
            [
                "- (조회) IASB 공개초안 **관계기업·공동기업 투자 공정가치선택권 개정**에 대한 의견수렴을 공지함",
                "- (기한) 기준원 제출 기한 **2026.3.26.**, IFRS재단 직접 제출 기한 **2026.4.20.**를 제시함",
                "- (자료) 국내 검토보고서와 공개초안 원문을 함께 배포해 이해관계자 검토를 지원함",
            ],
        ), inaccessible

    if source_ref == "pdf|downloads/제1118호정착지원TF_논의내용(킥오프미팅).pdf":
        return _block(
            "주요 내용",
            [
                "- (안건) K-IFRS 1118 적용 시 연결실체 관점에서 금융자산 투자수익의 영업·투자 범주 분류 기준을 논의함",
                "- (쟁점) 연결실체 전체 투자수익을 영업범주로 볼지, 주된 사업활동 해당 투자만 영업범주로 구분할지가 핵심 쟁점이었음",
                "- (논의) 다수 위원이 **투자활동 세분화 접근(대안2)**을 지지하며 자산군 특성·취득목적 기반 판단 필요성을 제시함",
                "- (시사) 기준서 문단(B37, B40 등) 해석과 실무 적용 부담, 공시의무 연계까지 고려한 보수적 적용이 요구됨",
            ],
        ), inaccessible

    if source_ref == "shot|downloads/www.kasb.or.kr-preview (2).png":
        return _block(
            "주요 내용",
            [
                "- (조회) 기업회계기준서 제1021호 **환율변동효과 개정 공개초안**에 대한 검토의견 제출을 요청함",
                "- (기한) 의견제출 기한을 **2026.3.23.**으로 안내하고 홈페이지 접수 절차를 제시함",
                "- (절차) 접수 의견은 원칙적으로 공개될 수 있음을 명시해 의견서 작성 시 공개 가능성 검토를 요구함",
            ],
        ), inaccessible

    if source_ref == "shot|downloads/www.kasb.or.kr-preview (3).png":
        return _block(
            "주요 내용",
            [
                "- (접수) K-IFRS 제1118호 정착지원 TF 논의이슈 제출을 공지하고 서식 기반 접수 절차를 안내함",
                "- (선정) 실무 영향도·해석 다양성·이해관계자 파급성이 큰 이슈를 TF 안건으로 우선 상정하는 기준을 제시함",
                "- (운영) 안건 선정 시 제출자의 회의 참여를 권장하고, 접수 이슈는 원칙적으로 공개될 수 있음을 명시함",
            ],
        ), inaccessible

    if source_ref == "shot|downloads/www.kasb.or.kr-preview (4).png":
        return _block(
            "주요 내용",
            [
                "- (공개) 한국회계기준원이 ’26년 3월 질의회신 요약 및 IFRS 해석위원회 논의결과 요약을 공개함",
                "- (범위) 정규 질의회신 1건과 IFRS IC 논의결과 1건을 공개해 기준 적용 일관성과 실무 해석 접근성을 지원함",
                "- (원칙) 질의회신 제도개선 방향에 따라 유효성·공개대상 기준을 적용해 공개자료를 관리함",
            ],
        ), inaccessible

    if source_ref == "clip|clip_1782503807_dd981a52":
        return _block(
            "주요 내용",
            [
                "□ 의결 안건",
                "",
                "- 해당사항 없음",
                "",
                "□ 보고 안건",
                "",
                "- 제1호 2025년 제13회 회계기준위원회 회의록(보고후공개)",
                "- 제2호 한국회계기준원 2026년도 사업계획",
                "- 제3호 연구과제 착수보고",
                "- 제4호 IFRS 20 ‘규제자산과 규제부채’ 제정 현황 및 국내 대응 계획",
                "- 제5호 IASB 및 IFRS 동향보고",
            ],
        ), inaccessible

    if source_ref == "clip|clip_1782503864_ce64e467":
        return _block(
            "주요 내용",
            [
                "□ 의결 안건",
                "",
                "- 제1호 기업회계기준서 제1021호 ‘환율변동효과’ 개정 공개초안(초인플레이션 표시통화로의 환산)",
                "",
                "□ 보고 안건",
                "",
                "- 제1호 2026년 제1회 회계기준위원회 회의록(보고후공개)",
                "- 제2호 K-IFRS 제1118호 등 개정 공개초안 쟁점 보고",
                "- 제3호 IASB 공개초안 ‘위험경감회계’ 개요 및 국내 의견조회 계획",
                "- 제4호 회계기준원 정규절차 질의회신 보고(대외비)",
                "- 제5호 IASB 및 IFRS 동향보고",
            ],
        ), inaccessible

    if source_ref == "clip|clip_1782503842_b6d057da":
        return _block(
            "주요 내용",
            [
                "□ 의결 안건",
                "",
                "- 해당사항 없음",
                "",
                "□ 보고 안건",
                "",
                "- 제1호 2026년 제2회 회계기준위원회 회의록(보고후공개)",
                "- 제2호 K-IFRS 제1119호 제정 경과와 계획 보고",
                "- 제3호 IASB 공개초안 ‘위험경감회계’ 예비적 견해 보고",
                "- 제4호 2025년 질의회신 업무처리 현황(대외비)",
                "- 제5호 IASB 및 IFRS 동향보고",
            ],
        ), inaccessible

    # Fallback for unexpected markers: keep concise, no fabrication.
    inaccessible = True
    return _block(
        "주요 내용",
        [
            "- (확인) 본 항목의 원문 근거를 자동 매핑하지 못해 상세 요약 생성을 보류함",
            "- (처리) 추가 원문 확인 후 보완이 필요하며 현재는 `<!-- 원문 접근 불가 -->` 기준으로 관리함",
        ],
    ), inaccessible


def replace_frontmatter(text: str) -> str:
    parts = text.split("---", 2)
    if len(parts) < 3:
        return text
    head = parts[1].splitlines()
    out = []
    in_agencies = False
    for line in head:
        if line.startswith("title:"):
            out.append("title: 2026 Q1 회계·감사 규제 동향")
            continue
        if line.startswith("description:"):
            out.append("description: 2026년 1분기 금융감독원·금융위원회·한국공인회계사회·한국회계기준원 주요 규제 동향")
            continue
        if line.startswith("category:"):
            out.append("category: regulatory-updates")
            continue
        if line.startswith("agencies:"):
            out.append("agencies:")
            out.append("  - 금융감독원")
            out.append("  - 금융위원회")
            out.append("  - 한국공인회계사회")
            out.append("  - 한국회계기준원")
            in_agencies = True
            continue
        if in_agencies and re.match(r"^\s*-\s", line):
            continue
        if in_agencies and not re.match(r"^\s", line):
            in_agencies = False
        if not in_agencies:
            out.append(line)
    return "---\n" + "\n".join(out).strip("\n") + "\n---" + parts[2]


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    text = replace_frontmatter(text)
    lines = text.splitlines()

    appendix_idx = None
    for i, line in enumerate(lines):
        if line.startswith("## Appendix A."):
            appendix_idx = i
            break

    new_lines: list[str] = []
    inserted = 0
    inaccessible_titles: list[str] = []
    source_count = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        if appendix_idx is not None and i >= appendix_idx:
            i += 1
            continue
        m = re.match(r"<!-- source: (.+) -->", line.strip())
        if not m:
            i += 1
            continue

        source_count += 1
        source_ref = m.group(1)
        window = lines[i + 1 : i + 7]
        has_note = any(re.match(r"^\s*(!!!|\?\?\?) note", w) for w in window)
        if has_note:
            i += 1
            continue

        prev_link = ""
        j = i - 1
        while j >= 0:
            if lines[j].strip():
                prev_link = lines[j].strip()
                break
            j -= 1
        mt = re.search(r"\[(.*?)\]\(", prev_link)
        title = mt.group(1).strip() if mt else ""
        block, is_inaccessible = summary_block(source_ref, title)
        new_lines.extend(block)
        inserted += 1
        if is_inaccessible:
            inaccessible_titles.append(title or source_ref)
        i += 1

    out_text = "\n".join(new_lines) + "\n"
    TARGET.write_text(out_text, encoding="utf-8")

    print(f"Updated file: {TARGET}")
    print(f"Source markers scanned: {source_count}")
    print(f"Summary blocks inserted: {inserted}")
    if inaccessible_titles:
        print("Source-unavailable or review-needed items:")
        for t in inaccessible_titles:
            print(f"- {t}")
    else:
        print("No source-unavailable items")


if __name__ == "__main__":
    main()

# Mr. Mint — 품질관리감리(fr2022) 작업 정리

## 결과
- 페이지: docs/fss-review/fr2022.md, "## 나. 2022년 품질관리감리 개선권고사항 (일반회계법인·감사반) 및 감사인별 조치일" 섹션
- PR: https://github.com/ypspy/quality-updates/pull/38 (squash 머지, 51702872)
- 배포: https://quality-updates.onrender.com/fss-review/fr2022/

## 날짜 기준
- 발표일이 아니라 조치일(개선권고일)을 사용
- 상장사 등 등록 법인 17곳: DART F004(회계법인 사업보고서)에서 조치일 확인
- 나머지 일반회계법인과 감사반: FSS 게시판 B0000291에서 확인
  - 2022년분 게시글은 nttId 127970~128040 범위
  - 목록에는 안 보이지만 아래 주소로 직접 열 수 있음
  - https://www.fss.or.kr/fss/bbs/B0000291/view.do?nttId=<ID>&menuNo=200620&cl1Cd=01
- 2022년 86건 모두 조치일 있음. 처음에 날짜가 비어 있던 47건은 게시판에서 2023-03-15로 확인
- 모음집 조치일
  - 2023년 모음집: 2024-03-18
  - 2024년 모음집: 2025-03-19
  - 2025년 모음집: 2026-03-20

## 파일
- data/date_recovery.csv: 2022년 86건의 조치일과 근거 URL
- data/compilations_dates.csv: B0000291 종합본(2023·2024·2025)과 B0000188 등록법인 별첨(2019~2025) 날짜·출처
- data/map_2022.csv: m01~m86 코드와 원본 파일명 대응표. `pdf_file`은 현재 저장소 경로
- data/_map_others.csv: n001~n255 대응표. `pdf_file`은 현재 저장소 경로 (2026-11-11에 `pdf/others/`에서 옮김)
- data/map_all_dedup.csv: Drive 두 폴더 602개 중 SHA256 기준 중복을 뺀 341개. n001~n341 코드와 원본 경로
- data/todo_others.csv: 2022년분이 아닌 나머지 255개 (변환 대상 목록. 변환 자체는 완료됨)
- pdf/firms/<권고일 연도>/: 업체별 PDF 333개 (2023=87, 2024=80, 2025=88, 2026=78). 파일명 규칙 `회사명_기간_권고일.pdf` (기간을 모를 때는 `기간미상`)
- pdf/compilations/board-B0000291/: 일반회계법인·감사반 연간 종합본 8개 (2022년 2개 + 2023~2025년 각 2개)
- pdf/compilations/press-B0000188/: 등록법인 보도자료 별첨. 공식 PDF가 있는 2019~2020·2021·2022년분 3개
- scripts/: Whale 실행 스크립트

## HWP→PDF 방법
- Whale 뷰어 툴바의 인쇄 아이콘 → PDF로 저장 → GTK 저장 대화상자
- LibreOffice는 쓰지 않음. 레이아웃이 깨짐

## 특이사항
- 서상감사반: 게시글 제목은 제437호인데 첨부파일은 제506호. 첨부파일 기준(제506호)으로 반영
- 2023년 회계법인 게시판 날짜 2023-08-24는 오기로 보임

## 등록 법인 모음집 (B0000188 별첨)
- 금감원 보도자료 게시판(B0000188) 별첨이다. 보도자료 본문 hwp/pdf는 이 폴더에 두지 않는다.
- pdf/compilations/press-B0000188/2019_2020년 품질관리 감리결과 개선권고사항 (2022.1.25).pdf: 등록 법인 16곳. 게시판 목록일 2022-01-24(nttId 54518), 파일명·기존 기록은 조간 관행으로 2022-01-25. 2026-11-11에 공식 별첨 PDF로 교체함 (996,830 bytes, sha256 `4cd30d92dfba1fd738d4ace467c2d276dd164d0ba406a300d41ee30d047ce601`). 이전 Drive/변환 사본은 732,950 bytes, sha256 `d282abc876eb3f59fdc173b4f47a21e6905b44a0ec346038e3c2ff0f0b0c324e`
- pdf/compilations/press-B0000188/2021년 품질관리 감리결과 개선권고사항 (2022.4.28).pdf: 등록 법인 13곳(그중 11곳은 처음 공개). 게시판 목록일 2022-04-27(nttId 55519), 파일명·기존 기록은 조간 관행으로 2022-04-28. 공식 별첨 PDF로 교체함 (1,009,264 bytes, sha256 `a1cdd597a161dd17d23b151c66c36546c1a7ea9a12065b69e53b574bea9917a1`). 이전 사본은 760,927 bytes, sha256 `964929622857eb7ef44f4128508293aa1d623be4fc8231ce1910ea2efc10ae07`
- pdf/compilations/press-B0000188/230703 (별첨) 2022년 품질관리 감리 개선권고사항.pdf: nttId 128593, 목록일 2023-07-03. 공식 별첨 PDF (947,034 bytes, sha256 `afe2a7989e70b10e63bd6e8464abc3ff05677b00302b0fd539e29a51a81fd687`)
- 2023년분(nttId 137349, 2024-07-25), 2024년분(nttId 194469, 2025-06-01), 2025년분(nttId 218133, 2026-06-01) 별첨은 게시판에 공식 PDF가 없다(hwp 또는 hwpx만). 변환본을 origin/main에 넣지 않았고, 노트북 미추적 변환본도 가져오지 않았다. 메타데이터만 `data/compilations_dates.csv`에 있다.
- FSS 게시판 B0000291에서 업체별 게시글은 2022년 감리분(nttId 127970~)부터 있음. 127969~100000번을 50번 간격으로 확인했지만 그 이전 게시글은 없었음

## undated_dates.csv (2026-10-31 추가)
- 위치: data/undated_dates.csv — 파일명에 '기간미상_권고일미상'이 있는 86개 파일(n256-n341, 기존 m01-m86 PDF와 동일)에 대해 PDF 본문(pdftotext)에서 감리대상기간/권고일을 추출한 결과.
- 결과: 감리기간 확인 2건, 날짜 확인 2건(n256/n257 종합본: '2022년 감리 실시', 2023-05-30 공시/발간일, medium). 나머지 84건은 본문에 감리대상기간·권고일 기재 없음(공란). 4건은 표본점검 사업연도 언급 또는 사실기재 날짜만 있어 low 근거만 기록.
- 방법: map.csv 파일명 매칭 → mint/out/mXX.pdf → pdftotext -layout → 정규식 검색. 추정값은 기입하지 않음. 참고: 권고일은 본문이 아닌 FSS 게시판(fss-review/date_recovery.csv action_date)에서 확인 가능.

### undated_dates.csv 갱신 (2026-10-31)
- recommendation_date: 86건 전부 FSS 게시판 목록 action_date(fss-review/date_recovery.csv)로 채움, date_source='FSS 목록 action_date'. 누락 0건.
- PDF 본문 날짜는 pdf_text_date 열에 별도 보존(n256/n257: 2023-05-30 발간일 vs FSS 목록 2023-03-15 — 불일치 2건).
- 분포: 2023-03-15 69건, 07-03 6, 06-28 3, 04-25 3, 07-04 2, 04-19/04-27/07-06 각 1.
- suggested_filename: 기간 미확인은 '기간미상_YYYY-MM-DD', n256/n257만 '2022_2023-03-15'. 실제 파일명은 변경하지 않음.

### PDF 파일명 변경 (2026-10-31)
- pdf\2022 의 m01-m86.pdf 86개를 undated_dates.csv 의 suggested_filename(.pdf)으로 변경. pdf\others 에는 해당 파일 없음(변경 0). 충돌 0건.
- 로그: data\rename_log.csv (old_path,new_path). map_2022.csv 에 pdf_file 열 추가(file_name 은 원본명 유지), 변경 전 사본 map_2022.pre_rename.csv.
- 원본 연구폴더(20_학업연구)는 변경하지 않음.

### pdf\others 파일명 변경 (2026-10-31)
- pdf\others 의 n001-n255.pdf 255개를 원본 파일명(_map_others.csv 의 path 파일명, 확장자 .pdf)으로 변경. 충돌 0건, '·'/금지문자 0건, 최대 경로 132자.
- 로그: data\rename_log_others.csv. _map_others.csv 에 pdf_file 열 추가, 변경 전 사본 _map_others.pre_rename.csv.

### PDF 폴더 재정리 (2026-11-11)
- 이전 `pdf/2022/`, `pdf/others/`, `pdf/compilations/` 구분은 작업 순서(2022년분 날짜 복구)에 따른 것이었고, 자료 성격 분류가 아니었다.
- `git mv`로 옮겼다. 삭제는 하지 않았고, 위 두 등록법인 모음집만 공식 FSS PDF로 내용을 교체했다.
- 일반·감사반 종합본 8개는 `pdf/compilations/board-B0000291/`로 옮겼다 (예전 `pdf/2022/`의 2022년 종합본 2개, `pdf/others/`의 2023~2025년 종합본 6개).
- 업체별 333개는 파일명 끝의 권고일 연도별로 `pdf/firms/2023/`~`pdf/firms/2026/`에 두었다.
- `data/rename_log.csv`와 `data/rename_log_others.csv`는 2026-10-31 당시 경로(`pdf/2022`, `pdf/others`)를 기록한 로그이므로 그대로 두었다.
- `_map_others.csv`와 `_map_others.pre_rename.csv`는 `data/`로 옮겼다.

> Cursor용 프로젝트 맥락: [CONTEXT.md](CONTEXT.md) (목적·원본 위치·처리 과정·파일 안내·주의사항·작업 원칙)

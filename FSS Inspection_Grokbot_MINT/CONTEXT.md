# CONTEXT — FSS Inspection_Grokbot_MINT

Cursor(AI 코드 에디터)가 프로젝트 맥락으로 읽도록 만든 문서입니다. 작업 이력은 README.md에 있습니다.

## 1. 목적
- 금융감독원(FSS) 품질관리감리 개선권고사항을 모아서 정리합니다.
- 용도 1: 감사인 등록제 연구(2026-01 시작)
- 용도 2: quality-updates 사이트의 품질관리감리 페이지
  - 사이트: https://quality-updates.onrender.com/fss-review/fr2022/
  - 저장소: https://github.com/ypspy/quality-updates (MkDocs)
  - 담당 범위: `docs/fss-review/fr2022.md` (fss-review/fr2022)
  - PR #38: squash 머지 완료 (51702872)

## 2. 원본 위치 (읽기 전용, 절대 수정·이동·이름변경 금지)
- `G:\내 드라이브\20_학업연구\22_학위후_연구활동_2022-\(26-01) 감사인 등록제 연구\감사인 감리 개선권고사항 입수 (26.07)\downloads` (341개, hwpx/hwp)
- `G:\내 드라이브\20_학업연구\22_학위후_연구활동_2022-\(26-01) 감사인 등록제 연구\금융감독원 개선권고사항 (25.12)` (261개)
- 두 폴더를 합치면 602개(341+261)입니다. SHA256 중복을 빼면 341개가 남고, 대표 경로는 모두 downloads 폴더를 가리킵니다.

## 3. 처리 과정
1. 중복 제거: 602개를 SHA256 기준으로 줄여 341개로 만들고, n001~n341 코드를 붙였습니다(`data/map_all_dedup.csv`).
2. HWP→PDF 변환
   - Whale 뷰어 툴바의 인쇄 → PDF로 저장 방식을 썼습니다.
   - LibreOffice는 레이아웃이 깨지므로 쓰지 않습니다.
   - 2022년분 86개는 m01~m86, 나머지 255개는 n001~n255 코드로 변환했습니다.
3. 날짜 복구(`data/date_recovery.csv`)
   - 사용하는 날짜는 발표일이 아니라 조치일(개선권고일)입니다.
   - 등록 법인 17곳: DART F004(회계법인 사업보고서)에서 확인했습니다.
   - 나머지 법인과 감사반: FSS 게시판 B0000291에서 확인했습니다.
4. 기간미상 86건(파일명 `기간미상_권고일미상`, n256~n341 = m01~m86)
   - PDF 본문(pdftotext)에는 감리대상기간과 권고일이 거의 없습니다.
   - 그래서 recommendation_date는 86건 모두 FSS 목록의 action_date로 채웠습니다(`data/undated_dates.csv`).
5. 파일명 변경(2026-10-31, 이 폴더 안에서만)
   - 당시 `pdf/2022` 86개를 suggested_filename으로 바꿨습니다.
   - 당시 `pdf/others` 255개를 원본 파일명(.pdf)으로 바꿨습니다.
   - 충돌은 0건이고, 로그를 남겼습니다.
6. 폴더 재정리(2026-11-11, `git mv`)
   - 업체별 PDF는 권고일 연도별 `pdf/firms/<연도>/`로 옮겼습니다 (333개).
   - 일반회계법인·감사반 연간 종합본 8개는 `pdf/compilations/board-B0000291/`로 옮겼습니다.
   - 등록법인 보도자료 별첨은 `pdf/compilations/press-B0000188/`로 옮겼습니다.
   - 2019~2020년·2021년 모음집은 금감원 공식 별첨 PDF로 교체했고, 2022년 공식 별첨 PDF를 추가했습니다.
   - 파일을 삭제하지는 않았습니다(교체된 두 사본의 내용만 공식본으로 바뀜).

## 4. 폴더/파일 안내
| 경로 | 행 수 | 열 | 내용 |
|---|---|---|---|
| `README.md` | - | - | 작업 이력 |
| `data/map_all_dedup.csv` | 341 | code, sha256, path | 중복 제거 후 전체 목록(n001~n341), 원본 경로 |
| `data/map_2022.csv` | 86 | code, file_name, drive_id, pdf_file | m01~m86 → 원본명, Drive ID, 변경 후 PDF 경로 |
| `data/map_2022.pre_rename.csv` | 86 | code, file_name, drive_id | 파일명 변경 전 백업 |
| `data/todo_others.csv` | 255 | code, sha256, path | 2022년분 외 변환 대상 목록 |
| `data/_map_others.csv` | 255 | code, sha256, path, pdf_file | n001~n255와 현재 PDF 경로 (2026-11-11에 `pdf/others/`에서 옮김) |
| `data/_map_others.pre_rename.csv` | 255 | code, sha256, path | 파일명 변경 전 백업 |
| `data/date_recovery.csv` | 86 | file_name, drive_id, firm, review_year, inferred_disclosure_date_or_range, method, confidence, evidence, action_date, action_date_basis | 2022년분 조치일과 근거 URL |
| `data/compilations_dates.csv` | 12 | file_name, drive_id, release_date, action_date, confidence, evidence | B0000291 2023~2025 종합본 6행 + B0000188 등록법인 별첨 6행 |
| `data/undated_dates.csv` | 86 | code, original_filename, firm_name, review_period, recommendation_date, date_source, pdf_text_date, evidence_snippet, confidence, suggested_filename | 기간미상 파일의 기간·권고일 |
| `data/rename_log.csv` | 86 | old_path, new_path | 2026-10-31 `pdf/2022` 파일명 변경 로그(당시 경로를 유지) |
| `data/rename_log_others.csv` | 255 | old_path, new_path | 2026-10-31 `pdf/others` 파일명 변경 로그(당시 경로를 유지) |
| `pdf/firms/<권고일 연도>/` | 333 PDF | - | 업체별 파일. 2023=87, 2024=80, 2025=88, 2026=78. 파일명 `회사명_기간_권고일` |
| `pdf/compilations/board-B0000291/` | 8 PDF | - | 일반회계법인·감사반 연간 종합본(2022~2025) |
| `pdf/compilations/press-B0000188/` | 6 PDF | - | 등록법인 보도자료 별첨: 공식 PDF 3(2019~2020·2021·2022년분) + 공식 hwp·hwpx의 Whale 변환본 3(2023~2025년분) |
| `scripts/` | 3 | - | Whale 실행 스크립트(mine.sh, mine2.sh, next.sh) |

## 5. 핵심 사실
- 2019~2021년 감리분은 등록 법인 모음집 형태로만 있습니다. 파일은 `pdf/compilations/press-B0000188/`에 있습니다.
  - 2019·2020년 모음집: 16곳, 게시판 목록일 2022-01-24(조간 관행 2022-01-25). 공식 FSS 별첨 PDF sha256 `4cd30d92dfba1fd738d4ace467c2d276dd164d0ba406a300d41ee30d047ce601`
  - 2021년 모음집: 13곳(그중 11곳은 처음 공개), 게시판 목록일 2022-04-27(조간 관행 2022-04-28). 공식 FSS 별첨 PDF sha256 `a1cdd597a161dd17d23b151c66c36546c1a7ea9a12065b69e53b574bea9917a1`
  - 2022년 등록법인 별첨(nttId 128593, 2023-07-03)도 같은 폴더에 공식 PDF로 있습니다. sha256 `afe2a7989e70b10e63bd6e8464abc3ff05677b00302b0fd539e29a51a81fd687`
  - 2023~2025년 등록법인 별첨(nttId 137349, 194469, 218133)은 게시판에 공식 PDF가 없어 파일을 추가하지 않았습니다.
- 업체별 게시글은 2022년 감리분부터 있습니다(nttId 127970~128040).
- FSS 게시판 B0000291의 특이점
  - 2022년분 게시글은 목록에 보이지 않습니다.
  - 그래도 `https://www.fss.or.kr/fss/bbs/B0000291/view.do?nttId=<ID>&menuNo=200620&cl1Cd=01`로 직접 열 수 있습니다.
  - nttId 127969 아래를 확인했지만 이전 게시글은 없었습니다.
  - 2023년 회계법인 게시판 날짜 2023-08-24는 오기로 보입니다.
  - 서상감사반은 게시글 제목이 제437호인데 첨부파일은 제506호입니다. 첨부파일 기준으로 반영했습니다.
- 모음집 조치일: 2023년 모음집 2024-03-18, 2024년 모음집 2025-03-19, 2025년 모음집 2026-03-20 (B0000291 일반·감사반 종합본)

## 6. 주의사항
- date_source
  - undated_dates.csv의 recommendation_date는 86건 모두 `FSS 목록 action_date`입니다. PDF 본문에서 나온 값이 아닙니다.
  - PDF 본문 날짜는 pdf_text_date 열에 따로 있습니다.
- n256/n257 불일치: 2022년 감사반·일반회계법인 종합본입니다.
  - 본문 날짜 2023-05-30은 발간일입니다.
  - FSS 목록 날짜는 2023-03-15입니다.
- `기간미상`: 원본 파일명과 본문 어디에도 감리대상기간이 없어서 붙인 표시입니다. 날짜가 확인된 경우에도 기간은 추정하지 않았습니다.
- 파일명에 `2021`이 있는 파일: 그 연도는 감리대상기간의 시작을 뜻합니다. 감리 실시연도나 공개연도가 아닙니다.
- 파일명 규칙: `<법인명>_<기간시작>~<기간끝>_<권고일>`. 파일명에 `·`와 Windows 금지문자는 `_`로 바꿨습니다.

## 7. 작업 원칙
- 저장소 작업은 브랜치를 만들어 PR로 올립니다. 승인 없이 머지하지 않습니다.
- PR 전에 통과해야 하는 검사: `python validate_content.py --strict`, `mkdocs build --strict`, markdownlint
- 원본 연구폴더(20_학업연구)는 읽기만 합니다. 파일명을 바꾸거나 삭제할 때는 로그를 남기고 백업을 만듭니다.

## 8. 담당
- Mr. Mint (Grok Bot): 품질관리감리(fss-review/fr2022) 담당, 이 폴더 작성
- Mr. Cabbage: 저장소, HWP 변환
- Mr. Rice: Drive 자료 관리(FSS 다운로드분)
- Mr. Zucchini: DART F004 출처

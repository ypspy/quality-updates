# SUMMARIZE 경제성 진단 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `quality-updates-writer` SUMMARIZE의 고정·가변·재작업 비용을 분해하고, gold 수준(C)을 유지하는 슬림 후보 백로그만 `2026-07-23-summarize-economics-design.md` §9에 채운다 (스킬 변경 없음).

**Architecture:** 정적 바이트/토큰 추정으로 분해표 초안 → 2016 Q1 큐에서 3~5링크 선정 → 현행 SUMMARIZE 규칙으로 짧은 실측 로그 → 판정·백로그. 결과는 스펙 파일 §9에만 기입한다.

**Tech Stack:** PowerShell/Python 파일 크기 측정, Read/`extract_pdf.py`, Markdown 스펙, Cursor 세션 관측(대시보드 수치 선택)

**Spec:** `docs/superpowers/specs/2026-07-23-summarize-economics-design.md`

## Global Constraints

- 진단만: SKILL.md / gold / `docs/quality-updates/` **의도적 슬림 패치 금지**
- 품질 하한 **C** (어조·상세도 포함 gold 수준); 절감보다 품질 우선
- 표본 정본: `docs/quality-updates/2016/2016-01-01_to_2016-03-31.md`
- 실측은 **현행 SUMMARIZE**; 2016 본문 대량 note 커밋 금지(사용자 지시 없으면 본문 미반영 또는 실측 후 revert)
- 로컬 LLM·BOILERPLATE·SKIP_REMOVAL 제외
- 커밋은 사용자 요청 시에만

---

## File map

| File | Action | Responsibility |
|------|--------|----------------|
| `docs/superpowers/specs/2026-07-23-summarize-economics-design.md` | Modify §9 | 분해표·실측·백로그·판정 |
| `docs/superpowers/plans/2026-07-23-summarize-economics.md` | Create (본 파일) | 실행 체크리스트 |
| `docs/superpowers/README.md` | Modify | Plans 인덱스 한 줄 |
| `.claude/skills/quality-updates-writer/SKILL.md` | Read-only | 고정비·의무 읽기 근거 |
| `docs/quality-updates/2016/2016-01-01_to_2016-03-31.md` | Read-only (기본) | 큐·실측 풀 |
| `scripts/extract_pdf.py` | Run as needed | 원문 가변비 실측 |

---

### Task 1: 정적 규모 맵 (바이트·토큰)

**Files:**
- Read: `.claude/skills/quality-updates-writer/SKILL.md`
- Read: `docs/quality-updates/2023/2023-04-01_to_2023-06-30.md`
- Read: `docs/quality-updates/2025/2025-10-01_to_2025-12-31.md`
- Read: `docs/quality-updates/2016/2016-01-01_to_2016-03-31.md`
- Modify: `docs/superpowers/specs/2026-07-23-summarize-economics-design.md` (§9.1에 측정 원숫자 메모 가능; 본 태스크는 표 초안 행까지)

**Interfaces:**
- Produces: `StaticSizes` — 각 경로의 `bytes`, `tok_div4 = bytes/4`, `tok_div3 = bytes/3` (정수 반올림)

- [ ] **Step 1: 크기 측정 실행**

Repo 루트에서:

```powershell
$paths = @(
  '.claude/skills/quality-updates-writer/SKILL.md',
  '.claude/skills/quality-updates-writer/boilerplate.md',
  'docs/quality-updates/2023/2023-04-01_to_2023-06-30.md',
  'docs/quality-updates/2025/2025-10-01_to_2025-12-31.md',
  'docs/quality-updates/2016/2016-01-01_to_2016-03-31.md'
)
foreach ($p in $paths) {
  $b = (Get-Item $p).Length
  '{0}`t{1}`t{2}`t{3}' -f $p, $b, [int]($b/4), [int]($b/3)
}
```

Expected: 5행 출력; 2016 파일 ~270000 bytes 근처.

- [ ] **Step 2: 2016 큐 카운트 재확인**

```powershell
$t = Get-Content 'docs/quality-updates/2016/2016-01-01_to_2016-03-31.md' -Raw
'note={0} source={1} skip={2} no_summary={3}' -f @(
  ([regex]::Matches($t,'!!! note')).Count,
  ([regex]::Matches($t,'<!-- source:')).Count,
  ([regex]::Matches($t,'<!-- skip -->')).Count,
  ([regex]::Matches($t,'<!-- no_summary -->')).Count
)
@('pdf','shot','web','clip') | ForEach-Object {
  $n = ([regex]::Matches($t, "<!-- source:\s*$_\|")).Count
  "source_$_=$n"
}
```

Expected: `note=0`, `source≈46`, `source_pdf≈23`, `source_shot≈23`.

- [ ] **Step 3: 스펙 §4.1 항목을 §9.1 표에 행으로 옮기고 StaticSizes로 토큰 열 채우기**

최소 행 (버킷|항목|토큰|gold 기여|슬림 가설|C 위험|우선순위 — 우선순위는 Task 4에서 확정 가능, 여기선 토큰·기여·가설·위험 초안):

| 버킷 | 항목 | 채우는 법 |
|------|------|-----------|
| 고정 | SKILL.md | Step 1 값 |
| 고정 | gold 2023 전문 | Step 1 값 |
| 고정 | gold 2025 전문 | Step 1 값 |
| 고정 | Announce/TaskCreate | 정성: “작음”; 토큰 `~0.5k–2k` |
| 고정 | REFERENCE 재독 | 스킬 내 REFERENCE 구간 바이트 추정 또는 “SKILL 내 포함으로 이중계산 주의” 주석 |
| 가변 | 2016 분기 md 전체 | Step 1 값; 슬림 가설 “링크±80줄 윈도우” |
| 가변 | PDF 추출 텍스트 | Task 2에서 샘플 3건 평균 후 갱신 가능; 임시 `미측정` |
| 가변 | shot 원문 | Task 2; 임시 `미측정` |
| 가변 | note 초안·삽입 | 정성 `~1k–4k`/링크 |
| 재작업 | OCR/HITL | 정성; 실측 후 갱신 |

- [ ] **Step 4: 검증**

스펙 §9.1에 빈 필수 행이 없고, gold 2행 토큰 합이 SKILL보다 **한 자릿수 이상 큼**이 명시되어 있는지 확인.

- [ ] **Step 5: Commit (사용자 요청 시에만)**

```bash
git add docs/superpowers/specs/2026-07-23-summarize-economics-design.md
git commit -m "$(cat <<'EOF'
docs: draft SUMMARIZE economics static cost table

EOF
)"
```

---

### Task 2: 2016 Q1 실측 링크 3~5건 선정 + 원문 크기

**Files:**
- Read: `docs/quality-updates/2016/2016-01-01_to_2016-03-31.md`
- Run: `scripts/extract_pdf.py` (pdf 샘플)
- Modify: 스펙 §9.2 링크 열 채움 (관측 열은 Task 3)

**Interfaces:**
- Consumes: Task 1 `StaticSizes`, 스펙 §3 선정 규칙
- Produces: `SampleLinks[]` — 각 `{id, date, title_short, source_type, source_path, extract_bytes?}`

- [ ] **Step 1: source 목록 추출**

```powershell
Select-String -Path 'docs/quality-updates/2016/2016-01-01_to_2016-03-31.md' -Pattern '^\- \(16-' |
  Select-Object -First 5
# Better: pairs of link + following source
python -c "
import re, pathlib
p = pathlib.Path('docs/quality-updates/2016/2016-01-01_to_2016-03-31.md')
text = p.read_text(encoding='utf-8')
blocks = re.findall(
    r'^- \((16-\d{2}-\d{2})\) \[([^\]]+)\]\([^\)]+\)\n<!-- source: (pdf|shot|web|clip)\|([^\s>]+) -->',
    text, re.M)
for i,b in enumerate(blocks,1):
    print(f'{i}\t{b[0]}\t{b[2]}\t{b[1][:60]}\t{b[3]}')
print('TOTAL', len(blocks))
"
```

Expected: TOTAL ≈ 46.

- [ ] **Step 2: 선정 (스펙 §3 규칙)**

반드시 포함:

1. **짧은 pdf** 1건 — 예: 설명회·사전예고 등 짧은 제목 (파일 크기 작은 쪽)
2. **긴 pdf** 1건 — 예: `160201_...감사전 재무제표...` 또는 `160121_...외부감사대상...` 또는 감리/지정 현황
3. **shot** 1건 — `<!-- source: shot|... -->` 중 하나
4. (선택) **제재/조치 pdf** 1건 — 금융위 조사·감리결과 등 Type A/B 후보
5. (선택) 추가 짧은 pdf 1건 → 총 3~5

선정 결과를 스펙 §9.2 `#` 1..N 행의 링크·source 열에 기입.

- [ ] **Step 3: pdf 샘플 추출 바이트 측정**

각 선정 pdf에 대해 (경로는 Step 2의 `source_path`; `downloads/` 기준):

```powershell
# 예: 경로를 scripts/pdf_path.txt에 UTF-8로 저장 후
Set-Content -Path scripts/pdf_path.txt -Value 'downloads/<선정파일>.pdf' -Encoding utf8
python scripts/extract_pdf.py
(Get-Item scripts/pdf_extracted.txt).Length
```

Expected: `pdf_extracted.txt` 생성; 길이를 SampleLinks.extract_bytes에 기록하고 §9.1 PDF 가변 행 갱신.

`shot`은 이미지이므로 OCR 텍스트가 없으면 “이미지 로드+설명 의존; 텍스트 토큰 미측정 / 비전·클립 경로”로 §9.2 비고에 명시.

- [ ] **Step 4: 검증**

§9.2에 최소 3행이 채워지고, pdf+shot 타입이 모두 포함되는지 확인.

- [ ] **Step 5: Commit (사용자 요청 시에만)** — Task 1과 동일 파일, 메시지 `docs: select 2016-Q1 SUMMARIZE economics sample links`

---

### Task 3: 현행 SUMMARIZE 짧은 실측 (관측 로그)

**Files:**
- Read: `.claude/skills/quality-updates-writer/SKILL.md` (SUMMARIZE Phase 0–1만)
- Read: gold 2파일 — **스킬이 요구하는 대로** 실측 세션에서 읽을지 여부를 관측 기록 (전체 vs 발췌는 변경하지 말고, “실제로 무엇을 읽었는지”만 기록)
- Modify: 스펙 §9.2 관측 열
- Optional scratch: `docs/superpowers/specs/_summarize-economics-live-notes.md` (gitignore 대상 아님 — 쓰지 않거나 실측 후 삭제; **2016 md에 note를 쓰지 않는 것을 기본**)

**Interfaces:**
- Consumes: `SampleLinks[]`
- Produces: 링크당 관측 문자열 (고정비 재발생 여부, 원문 토큰 체감, 실패/재시도)

- [ ] **Step 1: 실측 세션 프로토콜 고지**

에이전트는 사용자/서브에이전트에게 한 줄 고지:

> `품질 진단 실측: quality-updates-writer SUMMARIZE, 표본 N/M, 본문 미반영(기본)`

- [ ] **Step 2: 링크마다 Phase 0 → 초안까지 (본문 삽입 생략 기본)**

각 SampleLink:

1. source 경로로 원문 확보 (`extract_pdf.py` 또는 shot 경로 확인)
2. SKILL REFERENCE B 기준으로 note 초안을 **채팅/스크래치에만** 작성 (2016 파일 Edit 금지, 사용자 지시 시만 예외)
3. §9.2에 기록:
   - 이번 링크 처리 전후로 **gold 전문을 다시 읽었는지**
   - 분기 md를 **전체 vs 해당 링크 근처만** 읽었는지
   - 원문 대략 토큰(`extract_bytes/4`)
   - 막힌 지점(표·OCR·길이)

- [ ] **Step 3: Cursor 사용량 (있으면)**

Cursor Usage/대시보드에서 세션 토큰이 보이면 §9.2 비고에 숫자 기입. 없으면 `상대: 고정(gold)≫가변(원문)≫note` 같은 순위만.

- [ ] **Step 4: 검증**

§9.2 관측 열이 3행 이상 비어 있지 않음. 2016 파일에 새 `!!! note`가 **생기지 않았거나**, 생겼다면 사용자 승인 없이 커밋하지 말고 `git checkout --`로 되돌릴지 사용자에게 확인.

```powershell
$t = Get-Content 'docs/quality-updates/2016/2016-01-01_to_2016-03-31.md' -Raw
([regex]::Matches($t,'!!! note')).Count
```

Expected (기본): `0` (실측 전후 동일).

- [ ] **Step 5: Commit (사용자 요청 시에만)**

---

### Task 4: 백로그·판정·스펙 마감

**Files:**
- Modify: `docs/superpowers/specs/2026-07-23-summarize-economics-design.md` (§9.1 우선순위 확정, §9.3, §9.4)
- Modify: `docs/superpowers/README.md` (Plans 행 — 아직 없으면 추가)

**Interfaces:**
- Consumes: §9.1·§9.2 채움 결과
- Produces: §9.3 백로그 ≥1행(또는 “슬림 후보 없음” 명시), §9.4 세 줄 판정

- [ ] **Step 1: §9.1 우선순위 점수 기입**

규칙: 절감 큼·C 위험 낮음 → 상위. gold 전문 의무는 절감 잠재력 최대여도 **C 위험 고**면 판정은 유지 또는 “발췌 실험은 별도 승인 실험”으로 보류.

- [ ] **Step 2: §9.3 백로그**

각 후보 행 예 템플릿:

| 순위 | 후보 | 추정 절감 | 완화책 | 판정 |
|------|------|-----------|--------|------|
| 1 | gold 전문→대표 note 8~12개 발췌 파일 | 세션당 ~80–100k tok 급 | 발췌 세트가 gold 어조 커버하는지 HITL 체크리스트 | 슬림 후보 또는 보류 |
| 2 | 분기 md 전체→링크 윈도우 | 2016 기준 ~60k+ tok/세션 | 삽입 전후 컨텍스트 80줄 | 슬림 후보 |
| 3 | REFERENCE를 SKILL에서 분리·조건부 로드 | 중 | Type A/B일 때만 D 로드 | 슬림 후보/보류 |

실측과 모순되면 행을 수정한다. **허위 절감 금지.**

- [ ] **Step 3: §9.4 판정 요약**

- 유지: (항목 나열)
- 슬림 후보(승인 대기): …
- 보류: …

- [ ] **Step 4: README Plans 인덱스**

`docs/superpowers/README.md`의 Plans 표에 추가:

```markdown
| 2026-07-23 | [summarize-economics.md](plans/2026-07-23-summarize-economics.md) | SUMMARIZE 비용 분해·슬림 후보 진단 |
```

- [ ] **Step 5: 완료 검증**

- [ ] 스펙 §9.1–9.4 빈 핵심 셀 없음 (토큰 `미측정`은 가변 PDF/shot에 한해 허용하되 이유 명시)
- [ ] SKILL.md diff 없음 (`git diff -- .claude/skills/quality-updates-writer`)
- [ ] 상태 줄을 `진단 결과 기입 완료 — 슬림 구현은 별도 승인`으로 갱신

- [ ] **Step 6: Commit (사용자 요청 시에만)**

```bash
git add docs/superpowers/specs/2026-07-23-summarize-economics-design.md docs/superpowers/plans/2026-07-23-summarize-economics.md docs/superpowers/README.md
git commit -m "$(cat <<'EOF'
docs: complete SUMMARIZE economics diagnosis tables

EOF
)"
```

---

## Plan self-review

| Spec 요구 | Task |
|-----------|------|
| 목적·진단 only·C 품질 | Global + Task 4 |
| 2016 Q1 표본 | Task 2–3 |
| 고정/가변/재작업 분해표 | Task 1, 4 |
| 정적+짧은 실측 | Task 1, 3 |
| 백로그·판정 | Task 4 |
| 스킬 미변경 | Global + Task 4 Step 5 |

Placeholder scan: 없음. 커밋 스텝은 모두 “사용자 요청 시에만”.

# Agent 가이드 (Quality Updates)

Cursor·Claude 등 **AI 에이전트**가 이 저장소에서 작업할 때의 진입점입니다.  
사람용 온보딩은 [README.md](README.md), 분기 운영은 [docs/project/quarterly-operations-guide.md](docs/project/quarterly-operations-guide.md)를 본다.

---

## 1. 작업 유형별 라우팅

| 하고 싶은 일 | 먼저 읽을 것 | 워크플로 |
|--------------|--------------|----------|
| **분기 보도자료 요약** | [.claude/skills/quality-updates-writer/SKILL.md](.claude/skills/quality-updates-writer/SKILL.md) | SUMMARIZE / SKIP_REMOVAL |
| **감사 규제 렌즈 (Planning/Execution/Reporting)** | [.claude/skills/audit-regulatory-lens/SKILL.md](.claude/skills/audit-regulatory-lens/SKILL.md) | ADVISORY; writer와 **동시 사용 금지** |
| **MCP 코퍼스 export·서버** | [docs/superpowers/specs/2026-06-27-mcp-corpus-design.md](docs/superpowers/specs/2026-06-27-mcp-corpus-design.md) | `export_corpus.py` → stdio/HTTP MCP |
| **분기 파이프라인 전체** | [docs/project/quarterly-operations-guide.md](docs/project/quarterly-operations-guide.md) | crawl → editor → skill → prepare_deploy |
| **큐레이션·편집기** | [docs/project/editor-curation-workflow.md](docs/project/editor-curation-workflow.md) | HITL 주도; Agent는 마커 임의 변경 금지 |
| **프로젝트 점검·보완 기획** | 이 파일 + `/brainstorming` | 평가 → 2~3안 → **spec 승인** → plan → 구현 |
| **승인된 기능 구현** | `docs/superpowers/specs/YYYY-MM-DD-*-design.md` | [plan](docs/superpowers/plans/) + Subagent-Driven |
| **PR·CI·린트** | [CONTRIBUTING.md](CONTRIBUTING.md) | pytest, validate `--strict`, mkdocs `--strict` |
| **문서 지도** | [docs/project/README.md](docs/project/README.md) | — |

---

## 2. 프로젝트 보완 기획 — 프롬프트 템플릿

복사 후 `[...]`만 채워서 사용한다. **대규모 변경은 spec 승인 전 구현하지 않는다.**

### A. 프로젝트 점검 + 보완 기획

```markdown
프로젝트를 점검해줘. /brainstorming

범위: [크롤러 / CI / 문서 / 편집기 / 콘텐츠 / 전체]
목표: [한 문장, 예: 단일 repo 파이프라인 완성]
제외: [명시, 예: 분기 콘텐츠 백필]
참고: README, docs/project/README.md, docs/superpowers/specs/ 최신 항목
산출:
  - 현황 평가 (강점·부채)
  - 2~3안 비교 + 추천
  - 승인 후 spec → docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md
```

### B. 승인된 스펙 기반 구현

```markdown
@docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md 를 기준으로
구현 계획을 작성하고 Subagent-Driven으로 실행해줘.

제약:
- spec 범위 외 파일 변경 금지
- 완료 조건: cd scripts && python -m pytest tests/ -q
- python scripts/validate_content.py --strict
- mkdocs build --strict
```

### C. 문서·IA 정리

```markdown
문서 중복과 진입점을 점검하고 IA 정리안을 /brainstorming 해줘.

원칙: SSOT(단일 정본), AGENTS.md 허브, MkDocs exclude
참고: docs/superpowers/specs/2026-06-25-doc-organization-design.md
구현 전 spec 승인 필요.
```

### D. 분기 운영 (요약 아님)

```markdown
@docs/project/quarterly-operations-guide.md 기준으로 [YYYY QN] 분기 운영을 진행해줘.

Agent 담당: crawl.py 실행, prepare_deploy, validate/build
HITL 담당: editor 큐레이션, 요약 검증, nav/index, push 승인
```

---

## 3. 제약 (반드시 준수)

- **분기 요약 포맷**: `quality-updates-writer` 스킬 없이 링크별 note 블록 형식을 임의로 바꾸지 않는다.
- **HITL 큐레이션**: `<!-- skip -->`, `<!-- source: … -->`를 사용자 지시 없이 대량 변경하지 않는다.
- **기획 → 구현**: `/brainstorming`으로 spec이 승인되기 전 코드·대규모 리팩터를 시작하지 않는다.
- **커밋**: 사용자가 요청할 때만. `quality-updates-writer`는 RIGID 스킬이다.
- **Gold standard** (요약 시): `docs/quality-updates/2023/2023-04-01_to_2023-06-30.md`, `docs/quality-updates/2025/2025-10-01_to_2025-12-31.md`
- **감사 규제 렌즈**: `audit-regulatory-lens` 스킬은 코퍼스 **읽기 전용** — `docs/quality-updates/` 및 파이프라인 `.md` **수정 금지**

---

## 4. 설계 이력

| 경로 | 용도 |
|------|------|
| [docs/superpowers/specs/](docs/superpowers/specs/) | 승인된 설계 스펙 |
| [docs/superpowers/plans/](docs/superpowers/plans/) | 구현 계획 (체크리스트) |
| [docs/superpowers/README.md](docs/superpowers/README.md) | 색인 |

새 spec 파일명: `YYYY-MM-DD-<topic>-design.md`

---

## 5. 검증 명령 (구현·PR 후)

```bash
cd scripts && python -m pytest tests/ -q
python scripts/validate_content.py --strict
mkdocs build --strict
```

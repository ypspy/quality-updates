# HWP 추출 스크립트 수정 요청용 인스트럭션

Claude에게 HWP 추출 Python 코드 수정을 요청할 때, 아래 내용을 복사해서 맥락과 함께 전달하세요.

---

## 1. 프로젝트 맥락

- **목적**: 회계·감사 규제 동향 요약(quality-updates)을 위해 **아래아한글(.hwp)** 문서에서 텍스트를 추출
- **출력**: 추출 텍스트를 `scripts/hwp_extracted.txt`에 저장 → 에이전트가 읽어 MkDocs용 요약 생성
- **대상 파일**: `C:\Users\yoont\Downloads` 내 보도자료 등 한글 HWP (예: `251201_(보도자료)생명보험사일탈회계처리관련질의회신결과안내F.hwp`)

---

## 2. HWP 파일 구조 (기술적 배경)

- HWP는 **OLE 복합문서** 형식
- `olefile` 패키지로 스트림 읽기
- **PrvText**: 미리보기용 평문, UTF-16-LE 주로 사용, **가독성 좋음** (추출 우선 사용)
- **BodyText/Section0**: 본문 스트림, HWP 포맷 태그 포함 → PrvText 없을 때 fallback
- 디코딩 순서: `utf-16-le` → `utf-16` → `utf-8`

---

## 3. 현재 스크립트 구성

| 파일 | 용도 |
|------|------|
| `scripts/extract_hwp.py` | HWP 텍스트 추출. `path`(positional) 또는 기본값(~/Downloads 최신 .hwp), `--path-file`, `--max-chars`, `--output` CLI 지원 |
| `scripts/run_extract_hwp.bat` | Windows 전용 실행 래퍼. `py` 우선, 없으면 `python`으로 `extract_hwp.py` 실행 (PATH/Launcher 이슈 회피) |

**실행 예시 (PowerShell, 한글 경로 시)**  
프로젝트 루트에서 경로를 `scripts/hwp_path.txt`에 한 줄로 저장한 뒤:

```powershell
Set-Location "프로젝트경로"; py scripts/extract_hwp.py --path-file scripts/hwp_path.txt --output scripts/hwp_extracted.txt
```

또는 `scripts\run_extract_hwp.bat --path-file scripts/hwp_path.txt`

---

## 4. 요구사항 (AGENT_INSTRUCTION 기준)

- 추출 결과는 반드시 **파일로 저장** (`scripts/hwp_extracted.txt`) — 콘솔 인코딩 이슈 회피
- PrvText 우선, 없으면 BodyText/Section0 사용
- 디코딩: `utf-16-le` → `utf-16` → `utf-8`
- 스크립트 실행 시 **한글 경로** 포함된 Windows 경로에서도 동작해야 함

---

## 5. 알려진 이슈 및 실행 환경

### 5.1 실행 시 자주 발생하는 에러 (Windows)

1. **PowerShell에서 `&&` 오류**
   - 원인: PowerShell은 Bash와 달리 `&&`로 명령을 연결하지 않음.
   - 해결: `&&` 대신 **세미콜론 `;`** 사용.
   - 예: `cd 프로젝트경로; py scripts/extract_hwp.py --path-file scripts/hwp_path.txt`

2. **`python` 미인식 (exit code 9009)**
   - 원인: Windows에서 `python`이 PATH에 없거나, Python Launcher만 설치된 경우.
   - 해결: **`py`** (Python Launcher for Windows) 사용. 또는 프로젝트 루트에서 `scripts\run_extract_hwp.bat` 실행.
   - 예: `py scripts/extract_hwp.py --path-file scripts/hwp_path.txt`

### 5.2 기타 이슈

3. **한글 경로 인코딩**: PowerShell에서 `python -c "..."`로 경로 전달 시 한글이 깨질 수 있음. `# -*- coding: utf-8 -*-`와 **`--path-file`** 사용으로 회피 (경로를 UTF-8 텍스트 파일에 한 줄로 저장 후 `--path-file`로 전달).
4. **PrvText 단축**: PrvText는 미리보기용이라 본문보다 짧을 수 있음 (예: 1~2천자 수준). 본문 전체가 필요하면 BodyText 파싱 검토.
5. **BodyText 파싱**: BodyText는 HWP 포맷 태그가 섞여 있어 추가 파싱 필요 (필요 시 `hwp5` 등 전용 라이브러리 검토).

---

## 6. 수정 시 참고 사항

- 경로: `path`(positional) 또는 기본값(~/Downloads 최신 .hwp) — **구현 완료**
- 출력 글자 수: `--max-chars` CLI 옵션 — **구현 완료**
- `olefile` 미설치 시 `uv add olefile` 또는 `pip install olefile` 안내 메시지 출력
- 추출 실패 시 명확한 에러 메시지와 함께 exit code 1 반환

---

## 7. Claude에게 줄 수정 요청 예시

```
위 HWP 추출 인스트럭션을 참고하여:

1. extract_hwp.py에 --output 옵션을 추가해 출력 경로를 지정할 수 있게 해줘
2. PrvText 없을 때 BodyText fallback 동작을 검증해줘
```

---

# -*- coding: utf-8 -*-
"""F004 부착 데이터를 연도별 파일로 옮긴다 (PR-A, 한 번만 실행).

입력: data/fss-review/f004-attach/2025.json (git mv 직후, 옛 f004-item-attach.json과 같은 바이트: sha256 241b0edc…e682, 246423 B)
이미 이전한 파일에 다시 돌리면 입력 sha가 달라 멈춘다(기록용 스크립트).
출력: data/fss-review/f004-attach/{2025.json, aliases.json, manifest.json}
화면에 쓰는 필드(f004_rows, attachments, firm_reasons)는 손대지 않는다.
"""
import hashlib, json, sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
SRC = ROOT / "data/fss-review/f004-attach/2025.json"
SRC_SHA = "241b0edcd6eae831ef38a8d5a742be3f1bb09672cc1560fd93a54ddccc80e682"
OUT = ROOT / "data/fss-review/f004-attach"


def dump(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, indent=1).encode("utf-8")


raw = SRC.read_bytes()
assert hashlib.sha256(raw).hexdigest() == SRC_SHA and len(raw) == 246423, "입력 sha 불일치"
old = json.loads(raw.decode("utf-8"))

rules = list(old["rules"])
assert rules[1].startswith("자동 부착은 높음과 중간만. 사람 확인 31개는")
rules[1] = "자동 부착은 높음과 중간만. 사람 확인 문단은 자동으로 붙이지 않고 규칙 11(review20.csv 판정)대로만 붙임 (사용자 결정 2026-11-15 #1, v2)."
assert rules[12].startswith("법인 사유 줄은 그 법인의 2025 블록 첫 fss-original 패널")
rules[12] = "법인 사유 줄은 그 법인의 2025 블록 모든 fss-original 패널 끝에 같은 문장 전체로 한 줄씩 (사용자 결정 2026-11-15 9:14 AM CT, PR #122 1안. v2 #1의 '첫 패널에만'을 대체)."

display = dict(old["display"])
display["reason_line"] = "firm_reasons[].text, disclosure가 있으면 뒤에 · 접수번호 링크. 그 법인의 2025 블록 모든 fss-original 패널 끝에 한 줄씩"

counts = dict(old["counts"])
assert counts["firm_reason_panels"] == 41
counts["firm_reason_panels"] = 136  # 사유 줄이 붙는 패널 수(PR #122 뒤). 법인 수는 firm_reason_lines(41)

source = {
    "year_json": "data/fss-review/year-2025.json",
    "year_json_sha256": old["source"]["year_2025_json_sha256"],
    "year_json_commit": "ad479b819ea66822af5194e42d41cae33d005569",
    "year_json_note": "동성 재분류 PR #121 뒤 year-2025.json",
    "f004_followup_v4_sha256": old["source"]["f004_followup_v4_sha256"],
    "item_attach_v1_sha256": old["source"]["item_attach_v1_sha256"],
    "proposal": old["source"]["proposal"],
    "migrated_from": {"file": "data/fss-review/f004-item-attach.json", "sha256": SRC_SHA, "bytes": 246423},
}

new = {"schema": "f004-attach-year/1", "year": "2025"}
for key, value in old.items():
    if key == "source":
        new[key] = source
    elif key == "rules":
        new[key] = rules
    elif key == "display":
        new[key] = display
    elif key == "counts":
        new[key] = counts
    elif key == "serialization":
        new[key] = value
    else:
        new[key] = value
assert new["f004_rows"] == old["f004_rows"] and new["attachments"] == old["attachments"]
assert new["firm_reasons"] == old["firm_reasons"]

aliases = {
    "schema": "f004-attach-aliases/1",
    "note": "F004(DART) 법인 이름을 그 감리연도 화면의 법인 이름(fss-original data-names)으로 바꾸는 표. 기준은 민트, 결정은 윤석님. 이름이 같으면 행이 필요 없음",
    "fields": {
        "canonical": "그 연도 화면 이름(data-names 그대로)",
        "corp_code": "DART 고유번호 8자리, 모르면 null",
        "aliases": "F004·보도자료 등에 나오는 다른 이름 목록",
        "years": "이 대응이 맞는 감리연도 목록(2019–2025, 오름차순)",
        "source": "근거(공시 접수번호, 파일, 보도자료)",
        "decided_by": "민트 기준 문서 또는 윤석님 결정 번호(예: D10)",
    },
    "entries": [],
}

OUT.mkdir(parents=True, exist_ok=True)
files = {}
for name, obj in (("2025.json", new), ("aliases.json", aliases)):
    data = dump(obj)
    (OUT / name).write_bytes(data)
    files[name] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
manifest = {
    "schema": "f004-attach-manifest/1",
    "years": {"2025": dict(file="2025.json", **files["2025.json"])},
    "aliases": dict(file="aliases.json", **files["aliases.json"]),
}
(OUT / "manifest.json").write_bytes(dump(manifest))
for name in ("2025.json", "aliases.json", "manifest.json"):
    data = (OUT / name).read_bytes()
    print(name, len(data), hashlib.sha256(data).hexdigest())

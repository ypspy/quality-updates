import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
from datetime import datetime

# =====================================================
# 공통 설정
# =====================================================
START_DATE = "2024-01-01"
END_DATE   = "2024-03-31"
start_dt = datetime.strptime(START_DATE, "%Y-%m-%d")

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "ko-KR,ko;q=0.9",
})

# =====================================================
# 1. 보도자료
# =====================================================
def fetch_press_release(max_page=50):
    BASE_URL = "https://www.fss.or.kr/fss/bbs/B0000188/list.do"
    results = []

    print("\n[START] 보도자료 수집", flush=True)

    for page in range(1, max_page + 1):
        print(f"[보도자료] pageIndex={page}", flush=True)

        res = session.get(
            BASE_URL,
            params={
                "menuNo": "200218",
                "pageIndex": page,
                "sdate": START_DATE,
                "edate": END_DATE,
                "searchCnd": "1",
                "searchWrd": "",
            },
            timeout=10,
        )

        soup = BeautifulSoup(res.text, "html.parser")
        rows = soup.select("div.bd-list table tbody tr")
        print(f"  └ rows: {len(rows)}", flush=True)

        if not rows:
            break

        for row in rows:
            a = row.select_one("td.title a")
            tds = row.find_all("td")
            if not a or len(tds) < 4:
                continue

            try:
                dt = datetime.strptime(tds[3].get_text(strip=True), "%Y-%m-%d")
            except:
                continue

            if dt < start_dt:
                print("  └ 시작일 이전 도달 → 종료", flush=True)
                return results

            results.append({
                "date": dt.strftime("%y-%m-%d"),
                "title": a.get_text(strip=True),
                "link": urljoin(BASE_URL, a["href"]),
            })

    return results


# =====================================================
# 2. 회계감독 동향자료
# =====================================================
def fetch_accounting_trend(max_page=50):
    BASE_URL = "https://www.fss.or.kr/fss/bbs/B0000154/list.do"
    results = []

    print("\n[START] 회계감독 동향자료 수집", flush=True)

    for page in range(1, max_page + 1):
        print(f"[회계감독] pageIndex={page}", flush=True)

        res = session.get(
            BASE_URL,
            params={
                "menuNo": "200467",
                "pageIndex": page,
                "sdate": START_DATE,
                "edate": END_DATE,
                "searchCnd": "1",
                "searchWrd": "",
            },
            timeout=10,
        )

        soup = BeautifulSoup(res.text, "html.parser")
        rows = soup.select("table tbody tr")
        print(f"  └ rows: {len(rows)}", flush=True)

        if not rows:
            break

        for row in rows:
            a = row.select_one("td.title a")
            tds = row.find_all("td")
            if not a or len(tds) < 4:
                continue

            try:
                dt = datetime.strptime(tds[3].get_text(strip=True), "%Y-%m-%d")
            except:
                continue

            if dt < start_dt:
                print("  └ 시작일 이전 도달 → 종료", flush=True)
                return results

            results.append({
                "date": dt.strftime("%y-%m-%d"),
                "title": a.get_text(strip=True),
                "link": urljoin(BASE_URL, a["href"]),
            })

    return results


# =====================================================
# 3. 세칙 재개정 (캡션 기반 테이블 고정)
# =====================================================
def fetch_rules_revision(max_page=50):
    BASE_URL = "https://www.fss.or.kr/fss/job/lrgRegItnPrvntc/list.do"
    results = []
    seen_ids = set()

    print("\n[START] 세칙 재개정 수집 (최종 확정)", flush=True)

    for page in range(1, max_page + 1):
        print(f"[세칙] pageIndex={page}", flush=True)

        res = session.get(
            BASE_URL,
            params={
                "menuNo": "200489",
                "pageIndex": page,
                "sdate": START_DATE,
                "edate": END_DATE,
                "searchCnd": "1",
                "searchWrd": "",
            },
            timeout=10,
        )

        soup = BeautifulSoup(res.text, "html.parser")

        # 1️⃣ caption 기준으로 테이블 후보 선택
        table = None
        for t in soup.find_all("table"):
            cap = t.find("caption")
            if cap and "세칙" in cap.get_text():
                table = t
                break

        if not table:
            print("  └ 세칙 테이블 없음 → 종료", flush=True)
            break

        rows = table.select("tbody tr")
        print(f"  └ rows(raw): {len(rows)}", flush=True)

        valid_rows = []

        # 2️⃣ 진짜 데이터 row만 필터링
        for row in rows:
            a = row.select_one("td.title a")
            if not a:
                continue
            if "lrgSlno=" not in a.get("href", ""):
                continue
            valid_rows.append(row)

        print(f"  └ valid_rows: {len(valid_rows)}", flush=True)

        # 🔴 핵심 종료 조건
        if not valid_rows:
            print("  └ 유효한 세칙 데이터 없음 → 종료", flush=True)
            break

        # 3️⃣ 수집
        for row in valid_rows:
            a = row.select_one("td.title a")
            tds = row.find_all("td")

            qs = parse_qs(urlparse(a["href"]).query)
            lrg_id = qs.get("lrgSlno", [None])[0]

            if lrg_id in seen_ids:
                print("  └ 이미 수집한 게시물 재등장 → 종료", flush=True)
                return results

            seen_ids.add(lrg_id)

            try:
                dt = datetime.strptime(tds[2].get_text(strip=True), "%Y-%m-%d")
            except:
                continue

            if dt < start_dt:
                print("  └ 시작일 이전 도달 → 종료", flush=True)
                return results

            results.append({
                "date": dt.strftime("%y-%m-%d"),
                "title": a.get_text(strip=True),
                "link": urljoin(BASE_URL, a["href"]),
            })

    return results


# =====================================================
# 전체 취합
# =====================================================
def collect_all():
    print("\n==============================")
    print("FSS 게시판 전체 수집 시작")
    print("==============================", flush=True)

    all_data = []
    all_data.extend(fetch_press_release())
    all_data.extend(fetch_accounting_trend())
    all_data.extend(fetch_rules_revision())

    print("\n==============================")
    print(f"전체 수집 완료: 총 {len(all_data)}건")
    print("==============================", flush=True)

    return all_data


# =====================================================
# 실행부 (최종 출력 포맷)
# =====================================================
if __name__ == "__main__":
    data = collect_all()

    print("\n===== FINAL RESULT =====", flush=True)
    for d in data:
        print(
            f"({d['date']}) [{d['title']}] ({d['link']})",
            flush=True,
        )

    print("\n### SCRIPT END ###", flush=True)

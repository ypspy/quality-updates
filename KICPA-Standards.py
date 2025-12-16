import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

BASE = "https://www.kicpa.or.kr"
LIST_URL = f"{BASE}/kicpa/sumBoard/list.face"

# 하드코딩된 params 값
PARAMS_VALUE = (
    "acc0101/acc0102/acc0103/acc0301/acc0501/acc0502/"
    "acc0601/acc0602/acc0701/acc0702/acc0801/acc0802/"
    "acc1001/acc1002/acc1201/acc1202/acc1203/acc1401/"
    "acc1402/acc1403/acc1404/acc1405/acc1406/acc1407/acc1408"
)


# -------------------------------------------------------------
#  특정 페이지 요청
# -------------------------------------------------------------
def fetch_page(page: int):
    data = {
        "params": PARAMS_VALUE,
        "page": str(page),
    }
    resp = requests.post(LIST_URL, data=data)
    resp.raise_for_status()
    return resp.text


# -------------------------------------------------------------
#  목록 HTML 파싱
# -------------------------------------------------------------
def parse_list(html):
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("table.table_st02 tbody tr")
    items = []

    for tr in rows:
        title_tag = tr.select_one("td.subject a.subject_tit")
        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)

        # onclick="javascript:fn_detail('acc0102','11765342006138');"
        onclick = title_tag.get("onclick", "")
        try:
            parts = onclick.replace("javascript:fn_detail(", "").replace(");", "")
            parts = parts.replace("'", "").split(",")
            board_id = parts[0].strip()
            bltn_no = parts[1].strip()
        except:
            continue

        # 상세 페이지 URL 생성
        link = (
            f"{BASE}/kicpa/sumBoard/detail.face?"
            f"boardId={board_id}&bltnNo={bltn_no}&params={PARAMS_VALUE}"
        )

        # 날짜
        date_tag = tr.select_one("td.day")
        if not date_tag:
            continue
        try:
            date = datetime.strptime(date_tag.get_text(strip=True), "%Y.%m.%d")
        except:
            continue

        items.append({"title": title, "date": date, "link": link})

    return items


# -------------------------------------------------------------
#  최신 페이지 번호 파악
# -------------------------------------------------------------
def get_total_pages():
    html = fetch_page(1)
    soup = BeautifulSoup(html, "html.parser")
    page_tag = soup.select_one(".page strong")
    if not page_tag:
        return 1

    current_page = int(page_tag.get_text(strip=True))

    # "1/16 페이지" 구조 → total pages 얻기
    full_text = page_tag.parent.get_text()
    # 예: "1/16 페이지"
    try:
        total = int(full_text.split("/")[1].split()[0])
    except:
        total = current_page
    return total


# -------------------------------------------------------------
#  페이지 탐색 방식(B): 필요한 페이지 범위만 찾기
# -------------------------------------------------------------
def find_page_range(start_date, end_date):
    total_pages = get_total_pages()
    print(f"[INFO] Total pages = {total_pages}")

    start_page = None
    end_page = None

    for page in range(1, total_pages + 1):
        print(f"[INFO] Checking page {page}/{total_pages}...")
        html = fetch_page(page)
        items = parse_list(html)
        if not items:
            continue

        # 이 페이지의 날짜 범위
        page_dates = [item["date"] for item in items]
        newest = max(page_dates)
        oldest = min(page_dates)

        # 종료 범위 결정(end_page)
        if end_page is None and newest <= end_date:
            end_page = page

        # 시작 범위 결정(start_page)
        if start_page is None and oldest < start_date:
            start_page = page - 1 if page > 1 else 1

        if start_page and end_page:
            break

        time.sleep(0.2)

    if start_page is None:
        start_page = 1
    if end_page is None:
        end_page = total_pages

    print(f"[INFO] start_page = {start_page}, end_page = {end_page}")
    return start_page, end_page


# -------------------------------------------------------------
#  실제 크롤링
# -------------------------------------------------------------
def crawl_sumboard(start_date, end_date):
    start_page, end_page = find_page_range(start_date, end_date)

    print(f"\n[INFO] Crawling pages {start_page} → {end_page}\n")

    collected = []

    for page in range(start_page, end_page + 1):
        print(f"[INFO] Fetching page {page}/{end_page}")
        html = fetch_page(page)
        items = parse_list(html)

        for item in items:
            if start_date <= item["date"] <= end_date:
                collected.append(item)

        time.sleep(0.2)

    # 날짜 최신순 정렬
    collected.sort(key=lambda x: x["date"], reverse=True)
    return collected


# -------------------------------------------------------------
#  실행 예시
# -------------------------------------------------------------
if __name__ == "__main__":
    start = datetime(2023, 9, 30)
    end = datetime(2023, 12, 31)

    print("[INFO] Starting crawl_sumboard...\n")
    results = crawl_sumboard(start, end)

    print("\n====== FINAL OUTPUT ======\n")
    for r in results:
        d = r["date"].strftime("%y-%m-%d")
        print(f"- ({d}) [[{r['title']}]]({r['link']})")

    print(f"\n총 수집: {len(results)}건")

import requests
from bs4 import BeautifulSoup
from datetime import datetime

BASE = "https://www.kicpa.or.kr"


def fetch_page(board_id, page):
    url = f"{BASE}/board/list.brd"
    params = {"boardId": board_id, "cmpBrdId": board_id, "page": page}
    r = requests.get(url, params=params)
    r.raise_for_status()
    return r.text


def parse_table(board_id, html):
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("table.table_st02 tbody tr")

    items = []
    for tr in rows:
        title_tag = tr.select_one("td.subject a.subject_tit")
        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        onclick = title_tag.get("onclick", "")

        try:
            bltnNo = onclick.split("'")[3]
        except:
            continue

        # ========== 방법 A 링크 ==========
        link = (
            f"{BASE}/board/read.brd"
            f"?boardId={board_id}"
            f"&cmpBrdId={board_id}"
            f"&bltnNo={bltnNo}"
        )
        # =================================

        date_tag = tr.select_one("td.day")
        if not date_tag:
            continue

        date = datetime.strptime(date_tag.get_text(strip=True), "%Y.%m.%d")

        items.append({"title": title, "link": link, "date": date})

    return items


def get_total_pages(board_id):
    html = fetch_page(board_id, 1)
    soup = BeautifulSoup(html, "html.parser")
    text = soup.select_one("p.page").get_text()  # "1/438 페이지"
    total = int(text.split("/")[1].split()[0])
    return total


# --------------------------------------------------------------------
#                     START PAGE (>= start_date)
# --------------------------------------------------------------------
def find_start_page(board_id, start_date, total_pages):
    print("[INFO] Finding start_page...")
    low, high = 1, total_pages
    candidate = total_pages

    while low <= high:
        mid = (low + high) // 2
        html = fetch_page(board_id, mid)
        items = parse_table(board_id, html)
        if not items:
            break

        last_date = items[-1]["date"]  # 가장 오래된 날짜

        if last_date > start_date:
            low = mid + 1
        else:
            candidate = mid
            high = mid - 1

    print(f"[INFO] start_page = {candidate}")
    return candidate


# --------------------------------------------------------------------
#                     END PAGE (<= end_date)
# --------------------------------------------------------------------
def find_end_page(board_id, end_date, total_pages):
    print("[INFO] Finding end_page...")
    low, high = 1, total_pages
    candidate = 1

    while low <= high:
        mid = (low + high) // 2
        html = fetch_page(board_id, mid)
        items = parse_table(board_id, html)
        if not items:
            break

        first_date = items[0]["date"]  # 가장 최신 날짜

        if first_date > end_date:
            low = mid + 1
        else:
            candidate = mid
            high = mid - 1

    print(f"[INFO] end_page = {candidate}")
    return candidate


# --------------------------------------------------------------------
#                     MAIN CRAWLER
# --------------------------------------------------------------------
def crawl_period(board_id, start_date, end_date):
    total_pages = get_total_pages(board_id)

    start_page = find_start_page(board_id, start_date, total_pages)
    end_page = find_end_page(board_id, end_date, total_pages)

    # 보정: start_page ≤ end_page 보장
    if start_page > end_page:
        start_page, end_page = end_page, start_page

    print(f"[INFO] Crawling pages {start_page} → {end_page}...")

    collected = []

    for page in range(start_page, end_page + 1):
        print(f"[INFO] Fetching page {page}...")
        html = fetch_page(board_id, page)
        items = parse_table(board_id, html)

        for item in items:
            if start_date <= item["date"] <= end_date:
                collected.append(item)

    return collected


# =====================
# 실행
# =====================
if __name__ == "__main__":
    board_id = "noti"  # ← 다른 게시판이면 여기만 바꾸면 됨

    start = datetime(2023, 10, 1)
    end = datetime(2023, 12, 31)

    results = crawl_period(board_id, start, end)

    print("\n====== FINAL OUTPUT ======\n")
    for r in results:
        # 날짜 YY-MM-DD
        date_fmt = r["date"].strftime("%y-%m-%d")

        # 출력 형식: - (YY-MM-DD) [[제목]](URL)
        print(f"- ({date_fmt}) [[{r['title']}]]({r['link']})")

    print(f"\n총 수집: {len(results)}건")

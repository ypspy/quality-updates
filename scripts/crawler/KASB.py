import requests
from bs4 import BeautifulSoup
from datetime import datetime

BOARDS = {
    "공지사항": {
        "list": "https://www.kasb.or.kr/front/board/comm010List.do",
        "view": "https://www.kasb.or.kr/front/board/comm010View.do",
        "title_idx": 2,
        "date_idx": 4,
    },
    "보도자료": {
        "list": "https://www.kasb.or.kr/front/board/comm020List.do",
        "view": "https://www.kasb.or.kr/front/board/comm020View.do",
        "title_idx": 1,
        "date_idx": 3,
    },
}

SCHEDULE = {
    "list": "https://www.kasb.or.kr/front/board/calListA.do",
    "view": "https://www.kasb.or.kr/front/board/calView.do",
}

SESSION_HEADERS = {
    "User-Agent": "Mozilla/5.0",
}

def fetch_page(session, url, page, start, end):
    data = {
        "siteCd": "002000000000000",
        "searchfield": "ALL",
        "searchword": "",
        "s_date_start": start,
        "s_date_end": end,
        "page": page,
    }
    res = session.post(url, data=data)
    res.raise_for_status()
    return res.text


def parse_page(html, cfg):
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("table tbody tr")
    results = []

    for r in rows:
        cols = r.find_all("td")
        if len(cols) <= cfg["date_idx"]:
            continue

        title_tag = cols[cfg["title_idx"]].find("a")
        if not title_tag:
            continue

        onclick = title_tag.get("onclick", "")
        if "fn_Detail" not in onclick:
            continue

        seq = onclick.split("'")[1]
        title = title_tag.get_text(strip=True)

        raw_date = cols[cfg["date_idx"]].get_text(strip=True)
        d = datetime.strptime(raw_date, "%Y-%m-%d").strftime("%y-%m-%d")

        url = f"{cfg['view']}?seq={seq}"
        results.append((d, title, url))

    return results


def crawl_board(name, cfg, start, end):
    session = requests.Session()
    session.headers.update(SESSION_HEADERS)
    session.get(cfg["list"])  # 세션 초기화

    page = 1
    items = []

    print(f"\n=== [{name}] 크롤링 시작 ===")

    while True:
        html = fetch_page(session, cfg["list"], page, start, end)
        parsed = parse_page(html, cfg)

        if not parsed:
            break

        items.extend(parsed)
        page += 1

    print(f"=== [{name}] 완료: {len(items)}건 ===")
    return items


def parse_schedule_page(html):
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for row in soup.select("table tbody tr"):
        cols = row.find_all("td")
        if len(cols) != 5:
            continue

        title_tag = cols[3].find("a")
        if not title_tag:
            continue

        onclick = title_tag.get("onclick", "")
        if "fn_Detail" not in onclick:
            continue

        title = title_tag.get_text(strip=True)
        if not title:
            continue

        raw_date = cols[0].get_text(strip=True)
        try:
            d = datetime.strptime(raw_date, "%Y-%m-%d").strftime("%y-%m-%d")
        except ValueError:
            continue

        seq = onclick.split("'")[1]
        url = f"{SCHEDULE['view']}?seq={seq}"
        results.append((d, title, url))

    return results


def crawl_schedule(start, end):
    session = requests.Session()
    session.headers.update(SESSION_HEADERS)
    session.get(SCHEDULE["list"])

    page = 1
    items = []

    print("\n=== [주요일정] 크롤링 시작 ===")

    while True:
        html = fetch_page(session, SCHEDULE["list"], page, start, end)
        parsed = parse_schedule_page(html)

        if not parsed:
            break

        items.extend(parsed)
        page += 1

    items.sort(key=lambda t: datetime.strptime(t[0], "%y-%m-%d"))
    print(f"=== [주요일정] 완료: {len(items)}건 ===")
    return items


if __name__ == "__main__":
    START = "2023-09-30"
    END = "2023-12-31"

    all_results = {}

    for name, cfg in BOARDS.items():
        all_results[name] = crawl_board(name, cfg, START, END)

    print("\n====== 최종 결과 ======")
    for name, items in all_results.items():
        print(f"\n### {name} ({len(items)}건) ###")
        for d, title, url in items:
            print(f"- ({d}) [{title}]({url})")

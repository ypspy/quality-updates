import requests
from bs4 import BeautifulSoup
from datetime import datetime

LIST_URL = "https://www.kasb.or.kr/front/board/comm010List.do"
VIEW_URL = "https://www.kasb.or.kr/front/board/comm010View.do"

def fetch_page(page, start=None, end=None):
    data = {
        "siteCd": "002000000000000",
        "page": page,
        "searchfield": "ALL",
        "searchword": "",
        "categoryList": "",
        "s_date_start": start or "",
        "s_date_end": end or "",
    }
    res = requests.post(LIST_URL, data=data)
    res.raise_for_status()
    return res.text


def parse_page(html):
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("table tbody tr")

    results = []

    for r in rows:
        cols = r.find_all("td")
        if len(cols) < 5:
            continue

        # 제목은 cols[2]
        title_tag = cols[2].find("a")
        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)

        # seq는 onclick에서 추출
        onclick = title_tag.get("onclick", "")
        # e.g. "javascript:fn_Detail('2075');"
        if "fn_Detail" not in onclick:
            continue

        seq = (
            onclick.replace("javascript:fn_Detail('", "")
                   .replace("');", "")
                   .strip()
        )

        # 날짜는 cols[4]
        raw_date = cols[4].get_text(strip=True)
        date_obj = datetime.strptime(raw_date, "%Y-%m-%d")
        date_short = date_obj.strftime("%y-%m-%d")

        # URL
        url = f"{VIEW_URL}?seq={seq}"

        results.append((date_short, title, url))

    return results


def crawl(start_date=None, end_date=None):
    page = 1
    items = []

    print("=== 크롤링 시작 ===")

    while True:
        print(f"page={page}")
        html = fetch_page(page, start=start_date, end=end_date)
        parsed = parse_page(html)

        if not parsed:
            print("더 이상 없음 → 종료")
            break

        items.extend(parsed)
        page += 1

    print(f"=== 완료: 총 {len(items)}건 ===")
    return items


if __name__ == "__main__":
    data = crawl("2023-09-30", "2023-12-31")

    for d, title, url in data:
        print(f"- ({d}) [{title}]({url})")

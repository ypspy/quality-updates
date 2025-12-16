import requests
from bs4 import BeautifulSoup

# 세 게시판 URL
BASE_URLS = {
    "보도자료": "https://fsc.go.kr/no010101",
    "소관규정": "https://fsc.go.kr/po040200",
    "입법예고": "https://fsc.go.kr/po040301",
}

START_DATE = "2023-09-30"
END_DATE = "2023-12-31"

def fetch_page(url, page):
    params = {
        "curPage": page,
        "srchBeginDt": START_DATE,
        "srchEndDt": END_DATE,
        "srchCtgry": "",
        "srchKey": "",
        "srchText": "",
    }
    res = requests.get(url, params=params)
    res.raise_for_status()
    return res.text

def parse_page(html):
    soup = BeautifulSoup(html, "html.parser")
    results = []

    items = soup.select("li > div.inner")  # 각 항목 블록

    for item in items:
        subject_tag = item.select_one(".subject a")
        date_tag = item.select_one(".day")

        if subject_tag is None or date_tag is None:
            continue

        title = subject_tag.text.strip()
        href = "https://fsc.go.kr" + subject_tag["href"]

        date_full = date_tag.text.strip()  # YYYY-MM-DD
        yy = date_full[2:4]
        mm = date_full[5:7]
        dd = date_full[8:10]
        date_fmt = f"{yy}-{mm}-{dd}"

        md_line = f"- ({date_fmt}) [{title}]({href})"
        results.append(md_line)

    return results

def crawl_board(name, base_url):
    print(f"\n===== 크롤링 시작: {name} =====")
    
    page = 1
    all_items = []

    while True:
        html = fetch_page(base_url, page)
        items = parse_page(html)

        if not items:
            break

        print(f"{name} Page {page}: {len(items)} items")
        all_items.extend(items)
        page += 1

    return all_items

if __name__ == "__main__":
    merged_output = []

    for name, url in BASE_URLS.items():
        items = crawl_board(name, url)

        # 섹션 제목 추가
        merged_output.append(f"\n## {name}\n")
        merged_output.extend(items)

        print(f"→ {name}: {len(items)}건 수집 완료")

    # 취합 Markdown 파일 저장
    output_file = "fsc_all_20230930_20231231.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(merged_output))

    print(f"\n=== 전체 취합 파일 저장 완료: {output_file} ===")

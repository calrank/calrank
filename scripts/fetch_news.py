"""
calrank 종목별 뉴스 자동 수집 (다중 소스, 상호 독립).

법적으로 안전한 방식만 사용합니다: Google 뉴스 RSS처럼 "개인적·비영리
목적"으로 이용이 제한된 피드는 쓰지 않고, 각 종목 공식 협회가 스스로 공개 운영하는
뉴스 게시판만 개별적으로 수집합니다.

현재 소스:
  - emarathon.or.kr : 마라톤 (런코리아 운영, e-마라톤 "마라톤 관련뉴스")
  - cycling.or.kr   : 자전거 (대한사이클연맹 "사이클뉴스")
  - triathlon.or.kr : 철인3종 (대한철인뎄3종협회 "뉴스")

trail(대한산악연맹), hyrox는 아직 안정적인 공식 뉴스 소스를 찾지 못해
제외되어 있습니다.

사용 예시:
  python scripts/fetch_news.py --out news.json
"""

import json
import re
import argparse
from datetime import datetime

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}

SPORT_LABEL = {
    "marathon": "마라톤", "cycling": "자전거", "triathlon": "철인3종",
}


def guess_year_for_md(month: int, day: int) -> int:
    """MM.DD 형식(연도 없음)에서 연도를 추정합니다. 미래 날짜로 너무 멀면
    작년, 과거로 너무 멀면 내년으로 보정합니다."""
    today = datetime.now()
    candidate = datetime(today.year, month, day)
    diff_days = (today - candidate).days
    if diff_days < -30:
        return today.year - 1
    if diff_days > 300:
        return today.year + 1
    return today.year


def slugify_id(sport: str, title: str, date: str) -> str:
    base = re.sub(r"[^0-9A-Za-z가-힣]+", "-", title).strip("-").lower()
    return f"{sport}-{base[:60]}-{date}"


EMARATHON_URL = "https://emarathon.or.kr/bbs/board.php?bo_table=emara02_03"
EMARATHON_BASE = "https://emarathon.or.kr/bbs/"


def fetch_marathon_news() -> list[dict]:
    resp = requests.get(EMARATHON_URL, timeout=15, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    events = []
    for tr in soup.select("table.list-pc tr"):
        tds = tr.find_all("td")
        if len(tds) < 4:
            continue

        link_el = tr.select_one("td.list-subject a")
        if not link_el:
            continue
        title = link_el.get_text(strip=True)
        if not title:
            continue

        date_text = tds[-2].get_text(strip=True) if len(tds) >= 2 else ""
        m = re.match(r"(\d{1,2})\.(\d{1,2})", date_text)
        if not m:
            continue
        month, day = int(m.group(1)), int(m.group(2))
        year = guess_year_for_md(month, day)
        date_iso = f"{year:04d}-{month:02d}-{day:02d}"

        href = link_el.get("href", "")
        article_url = EMARATHON_BASE + href if href.startswith("board.php") else href

        events.append({
            "id": slugify_id("marathon", title, date_iso),
            "sport": "marathon",
            "sportLabel": SPORT_LABEL["marathon"],
            "title": title,
            "date": date_iso,
            "excerpt": None,
            "sourceUrl": article_url or EMARATHON_URL,
            "sourceName": "e-마라톤",
        })

    return events


CYCLING_URL = "https://cycling.or.kr/news/news/"


def fetch_cycling_news() -> list[dict]:
    resp = requests.get(CYCLING_URL, timeout=15, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    events = []
    for item in soup.select("div.newsList"):
        link_el = item.select_one("h2 a")
        if not link_el:
            continue
        title = link_el.get_text(strip=True)

        date_el = item.select_one("p span.bold")
        date_text = date_el.get_text(strip=True) if date_el else ""
        m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", date_text)
        if not m:
            continue
        date_iso = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

        p_el = item.select_one("p")
        excerpt = None
        if p_el:
            full_text = p_el.get_text(" ", strip=True)
            excerpt = full_text.replace(date_text, "", 1).lstrip("| ").strip()[:150] or None

        href = link_el.get("href", "")
        article_url = CYCLING_URL + href if href and not href.startswith("http") else href

        events.append({
            "id": slugify_id("cycling", title, date_iso),
            "sport": "cycling",
            "sportLabel": SPORT_LABEL["cycling"],
            "title": title,
            "date": date_iso,
            "excerpt": excerpt,
            "sourceUrl": article_url or CYCLING_URL,
            "sourceName": "대한사이클연맹",
        })

    return events


TRIATHLON_NEWS_URL = "https://triathlon.or.kr/community/news/"


def fetch_triathlon_news() -> list[dict]:
    resp = requests.get(TRIATHLON_NEWS_URL, timeout=15, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    events = []
    for li in soup.select("div.news_list li"):
        link_el = li.find("a")
        if not link_el:
            continue

        title_el = li.select_one("strong")
        title = title_el.get_text(strip=True) if title_el else None
        if not title:
            continue

        date_el = li.select_one("span")
        date_text = date_el.get_text(strip=True) if date_el else ""
        m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", date_text)
        if not m:
            continue
        date_iso = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

        excerpt_el = li.select_one("p")
        excerpt = excerpt_el.get_text(strip=True)[:150] if excerpt_el else None

        href = link_el.get("href", "")
        article_url = TRIATHLON_NEWS_URL + href if href and not href.startswith("http") else href

        events.append({
            "id": slugify_id("triathlon", title, date_iso),
            "sport": "triathlon",
            "sportLabel": SPORT_LABEL["triathlon"],
            "title": title,
            "date": date_iso,
            "excerpt": excerpt,
            "sourceUrl": article_url or TRIATHLON_NEWS_URL,
            "sourceName": "대한철인뎄3종협회",
        })

    return events


SOURCES = [
    ("emarathon.or.kr", fetch_marathon_news),
    ("cycling.or.kr", fetch_cycling_news),
    ("triathlon.or.kr", fetch_triathlon_news),
]


def merge_and_dedupe(existing: list[dict], new_items: list[dict]) -> list[dict]:
    by_id = {it["id"]: it for it in existing}
    for it in new_items:
        by_id[it["id"]] = it
    merged = sorted(by_id.values(), key=lambda e: e["date"], reverse=True)
    return merged[:300]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="news.json")
    args = parser.parse_args()

    try:
        with open(args.out, encoding="utf-8") as f:
            existing = json.load(f)
    except FileNotFoundError:
        existing = []

    all_new = []
    for source_name, fetch_fn in SOURCES:
        try:
            new_items = fetch_fn()
            print(f"[{source_name}] {len(new_items)}개 수집 성공")
            all_new.extend(new_items)
        except Exception as e:
            print(f"[{source_name}] 수집 실패, 건너뜀: {e}")

    merged = merge_and_dedupe(existing, all_new)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"[{datetime.now().isoformat()}] {len(merged)}개 뉴스 저장 완료 ({args.out})")


if __name__ == "__main__":
    main()

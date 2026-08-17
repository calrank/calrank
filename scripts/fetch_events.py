"""
calrank 대회 일정 자동 수집.

roadrun.co.kr(마라톤온라인의 실제 데이터가 로딩되는 도메인)의 공개 대회일정 페이지를 수집합니다.
2026.08 기준 실제 페이지 구조를 직접 확인해서 작성했습니다 (표 11번째, 4셀 구조).

중요 — 반드시 지킬 것:
  - 여기서 다루는 건 "대회 일정 정보"(대회명/날짜/장소/종목/거리/주최측 연락처)만입니다.
    참가자 개인 기록(이름, 기록시간 등)은 이 스크립트로 수집하지 않습니다.
  - 새 소스를 추가하기 전에 해당 사이트의 이용약관 / robots.txt를 반드시 먼저 확인하세요.
    명시적으로 크롤링을 금지하는 사이트는 절대 대상에 포함하지 마세요.
    (예: smartchip.co.kr은 개인 기록 페이지에 크롤링 금지 문구가 있음을 이미 확인함 — 대상에서 제외)
  - 주의: 이 코드는 실제 페이지 DOM 구조를 브라우저로 직접 확인해 작성했지만,
    샌드박스 환경 네트워크 제약으로 이 환경에서는 직접 실행 테스트를 하지 못했습니다.
    GitHub Actions에서 첫 실행 시 결과를 반드시 사람이 한 번 검수하세요.

사용 예시:
  python scripts/fetch_events.py --out events.json
"""

import json
import re
import argparse
from datetime import datetime

import requests
from bs4 import BeautifulSoup

ROADRUN_URL = "http://www.roadrun.co.kr/schedule/list.php"

TRAIL_KEYWORDS = ["트레일", "UTMB", "산악", "임도", "알프스"]
CYCLING_KEYWORDS = ["그란폰도", "메디오폰도", "자전거", "사이클"]


def guess_sport(name: str) -> tuple[str, str]:
    """대회명에 포함된 키워드로 종목을 추정합니다. roadrun.co.kr은 러닝계열 대회 위주입니다."""
    if any(k in name for k in TRAIL_KEYWORDS):
        return "trail", "트레일"
    if any(k in name for k in CYCLING_KEYWORDS):
        return "cycling", "자전거"
    return "marathon", "마라톤"


def guess_year(month: int, day: int) -> int:
    """
    페이지에 연도가 표기되지 않으므로 연도를 추정합니다.

    roadrun.co.kr 목록은 최근 지난 대회도 며칠간 계속 보여주는 것으로 확인되어,
    단순히 "오늘보다 과거면 무조건 내년"으로 처리하면 방금 끝난 대회가 내년으로 잘못 분류됩니다.
    그래서 90일의 유예기간을 두고, 그보다 오래 과거인 경우에만 내년으로 판단합니다.
    """
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    candidate = datetime(today.year, month, day)
    grace_period_days = 90
    if (today - candidate).days > grace_period_days:
        return today.year + 1
    return today.year


def parse_date_cell(text: str) -> str | None:
    """'8/1\n(토)' 형태에서 ISO 날짜 문자열을 뽑습니다."""
    m = re.search(r"(\d{1,2})/(\d{1,2})", text)
    if not m:
        return None
    month, day = int(m.group(1)), int(m.group(2))
    year = guess_year(month, day)
    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_name_cell(text: str) -> tuple[str, list[str]]:
    """'2026 인사이더런 S\n10km' 형태에서 (이름, 거리목록)을 분리합니다."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return "", []
    name = lines[0]
    distances = []
    for l in lines[1:]:
        distances.extend([d.strip() for d in l.split(",") if d.strip()])
    return name, distances or ["거리 미확인"]


def slugify(name: str, date: str) -> str:
    base = re.sub(r"[^0-9A-Za-z가-힣]+", "-", name).strip("-").lower()
    return f"{base}-{date}"


def fetch_roadrun() -> list[dict]:
    resp = requests.get(ROADRUN_URL, timeout=15)
    resp.encoding = resp.apparent_encoding
    soup = BeautifulSoup(resp.text, "html.parser")

    tables = soup.find_all("table")
    # 대회 목록 표는 각 행이 4칸(날짜/대회명/장소/주최)인 표 중 행 수가 가장 많은 표.
    target = max(tables, key=lambda t: len(t.find_all("tr")))

    events = []
    for row in target.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) != 4:
            continue  # 구분선(<hr>) 행 등은 건너뜀

        date_text = cells[0].get_text("\n", strip=True)
        name_text = cells[1].get_text("\n", strip=True)
        location = cells[2].get_text(" ", strip=True)

        date_iso = parse_date_cell(date_text)
        name, distances = parse_name_cell(name_text)

        if not date_iso or not name:
            continue

        sport, sport_label = guess_sport(name)

        events.append({
            "id": slugify(name, date_iso),
            "sport": sport,
            "sportLabel": sport_label,
            "name": name,
            "date": date_iso,
            "time": "미확인",
            "location": location,
            "distances": distances,
            "regDeadline": None,
            "saves": 0,
            "savesTrend7d": 0,
            "sourceUrl": ROADRUN_URL,
        })

    return events


def merge_and_dedupe(existing: list[dict], new_events: list[dict]) -> list[dict]:
    """id 기준으로 합치고 중복을 제거합니다. 기존 찜 수 등은 보존합니다."""
    by_id = {ev["id"]: ev for ev in existing}
    for ev in new_events:
        prev = by_id.get(ev["id"], {})
        merged = {**ev}
        # 사용자 데이터(찜 수)는 새로 긁어온 값(항상 0)으로 덮어쓰지 않고 보존
        merged["saves"] = prev.get("saves", ev["saves"])
        merged["savesTrend7d"] = prev.get("savesTrend7d", ev["savesTrend7d"])
        by_id[ev["id"]] = merged
    return sorted(by_id.values(), key=lambda e: e["date"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="events.json")
    args = parser.parse_args()

    try:
        with open(args.out, encoding="utf-8") as f:
            existing = json.load(f)
    except FileNotFoundError:
        existing = []

    new_events = fetch_roadrun()
    merged = merge_and_dedupe(existing, new_events)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"[{datetime.now().isoformat()}] {len(merged)}개 대회 저장 완료 ({args.out})")


if __name__ == "__main__":
    main()

"""
calrank 대회 일정 자동 수집 (다중 소스, 상호 독립).

소스가 하나 죽어도 나머지 소스는 계속 작동하도록, 소스별로 실패를 격리합니다.
같은 사람이 만든 하나의 사이트에만 의존하지 않기 위한 설계입니다.

현재 소스:
  - roadrun.co.kr  : 마라톤/트레일 (표 스크래핑)
  - cyclo.kr       : 자전거 (공개 JSON API, /api/meetup/schedule)

중요 — 반드시 지킬 것:
  - "대회 일정 정보"(대회명/날짜/장소/종목/거리/주최자)만 다룹니다.
    참가자 개인 기록(이름, 기록시간 등)은 이 스크립트로 수집하지 않습니다.
  - 새 소스를 추가하기 전에 이용약관 / robots.txt를 반드시 먼저 확인하세요.
    명시적으로 크롤링을 금지하는 사이트는 절대 대상에 포함하지 마세요.
    (예: smartchip.co.kr은 개인 기록 페이지에 크롤링 금지 문구가 있어 제외됨)
  - 주의: 실제 페이지 구조를 브라우저로 직접 확인해 작성했지만, 샌드박스 환경
    네트워크 제약으로 이 환경에서 직접 실행 테스트는 못 했습니다.
    GitHub Actions 첫 실행 후 결과를 사람이 한 번 검수하세요.

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
ROADRUN_DETAIL_BASE = "http://www.roadrun.co.kr/schedule/"
CYCLO_API_URL = "https://cyclo.kr/api/meetup/schedule"
CYCLO_FALLBACK_URL = "https://cyclo.kr/schedule"

TRAIL_KEYWORDS = ["트레일", "UTMB", "산악", "임도", "알프스"]
CYCLING_KEYWORDS = ["그란폰도", "메디오폰도", "자전거", "사이클"]

REGIONS = [
    "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
    "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
]


def guess_sport(name: str) -> tuple[str, str]:
    """대회명에 포함된 키워드로 종목을 추정합니다."""
    if any(k in name for k in TRAIL_KEYWORDS):
        return "trail", "트레일"
    if any(k in name for k in CYCLING_KEYWORDS):
        return "cycling", "자전거"
    return "marathon", "마라톤"


def guess_region(location: str) -> str:
    """장소 문자열에서 시도 단위 지역을 추정합니다. 못 찾으면 '전국'."""
    for r in REGIONS:
        if r in location:
            return r
    return "전국"


def guess_year(month: int, day: int) -> int:
    """
    페이지에 연도가 표기되지 않으므로 연도를 추정합니다.
    최근 지난 대회도 며칠간 계속 보여주는 사이트가 있어, 90일 유예기간을 둡니다.
    """
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    candidate = datetime(today.year, month, day)
    grace_period_days = 90
    if (today - candidate).days > grace_period_days:
        return today.year + 1
    return today.year


def slugify(name: str, date: str, prefix: str) -> str:
    base = re.sub(r"[^0-9A-Za-z가-힣]+", "-", name).strip("-").lower()
    return f"{prefix}-{base}-{date}"


def blank_event(**kwargs) -> dict:
    """모든 이벤트가 동일한 필드 스키마를 갖도록 하는 헬퍼."""
    base = {
        "id": None,
        "sport": "marathon",
        "sportLabel": "마라톤",
        "name": "",
        "date": None,
        "time": "미확인",
        "location": "",
        "region": "전국",
        "distances": ["거리 미확인"],
        "organizer": None,
        "organizerPhone": None,
        "regDeadline": None,
        "saves": 0,
        "savesTrend7d": 0,
        "sourceUrl": None,
        "applyUrl": None,
    }
    base.update(kwargs)
    return base


# ---- 소스 1: roadrun.co.kr (마라톤/트레일) ----

def parse_date_cell(text: str) -> str | None:
    m = re.search(r"(\d{1,2})/(\d{1,2})", text)
    if not m:
        return None
    month, day = int(m.group(1)), int(m.group(2))
    year = guess_year(month, day)
    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_name_cell(text: str) -> tuple[str, list[str]]:
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return "", []
    name = lines[0]
    distances = []
    for l in lines[1:]:
        distances.extend([d.strip() for d in l.split(",") if d.strip()])
    return name, distances or ["거리 미확인"]


def parse_organizer_cell(cell) -> tuple[str | None, str | None]:
    """조직명과 전화번호를 분리합니다. 예: '러너블\n☎02-2031-1935\n...'"""
    text = cell.get_text("\n", strip=True)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return None, None
    name = None
    phone = None
    for l in lines:
        if l.startswith("☎"):
            phone = l.replace("☎", "").strip()
        elif name is None:
            name = l
    return name, phone


def parse_detail_url(cell) -> str | None:
    a = cell.find("a")
    if not a:
        return None
    href = a.get("href", "")
    m = re.search(r"view\.php\?no=\d+", href)
    if not m:
        return None
    return ROADRUN_DETAIL_BASE + m.group(0)


def fetch_roadrun() -> list[dict]:
    resp = requests.get(ROADRUN_URL, timeout=15)
    resp.encoding = resp.apparent_encoding
    soup = BeautifulSoup(resp.text, "html.parser")

    tables = soup.find_all("table")
    target = max(tables, key=lambda t: len(t.find_all("tr")))

    events = []
    for row in target.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) != 4:
            continue

        date_text = cells[0].get_text("\n", strip=True)
        name_text = cells[1].get_text("\n", strip=True)
        location = cells[2].get_text(" ", strip=True)

        date_iso = parse_date_cell(date_text)
        name, distances = parse_name_cell(name_text)
        if not date_iso or not name:
            continue

        sport, sport_label = guess_sport(name)
        organizer, phone = parse_organizer_cell(cells[3])
        detail_url = parse_detail_url(cells[1])

        events.append(blank_event(
            id=slugify(name, date_iso, "rr"),
            sport=sport,
            sportLabel=sport_label,
            name=name,
            date=date_iso,
            location=location,
            region=guess_region(location),
            distances=distances,
            organizer=organizer,
            organizerPhone=phone,
            sourceUrl=ROADRUN_URL,
            applyUrl=detail_url or ROADRUN_URL,
        ))

    return events


# ---- 소스 2: cyclo.kr (자전거) ----

def fetch_cyclo() -> list[dict]:
    resp = requests.get(CYCLO_API_URL, timeout=15)
    resp.raise_for_status()
    groups = resp.json()

    events = []
    for group in groups:
        for m in group.get("meetups", []):
            name = m.get("name", "").strip()
            dest_date = m.get("dest_date")
            if not name or not dest_date:
                continue

            date_iso = dest_date.split(" ")[0]
            time_str = dest_date.split(" ")[1][:5] if " " in dest_date else "미확인"
            location = (m.get("address") or {}).get("name", "장소 미확인")
            organizer = m.get("organizer")

            events.append(blank_event(
                id=slugify(name, date_iso, "cy"),
                sport="cycling",
                sportLabel="자전거",
                name=name,
                date=date_iso,
                time=time_str,
                location=location,
                region=guess_region(location),
                distances=["거리 미확인"],
                organizer=organizer,
                sourceUrl=CYCLO_FALLBACK_URL,
                applyUrl=CYCLO_FALLBACK_URL,
            ))

    return events


# ---- 병합 ----

SOURCES = [
    ("roadrun.co.kr", fetch_roadrun),
    ("cyclo.kr", fetch_cyclo),
]


def merge_and_dedupe(existing: list[dict], new_events: list[dict]) -> list[dict]:
    """id 기준으로 합치고 중복을 제거합니다. 사용자 데이터(찜)는 보존합니다."""
    by_id = {ev["id"]: ev for ev in existing}
    for ev in new_events:
        prev = by_id.get(ev["id"], {})
        merged = {**ev}
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

    all_new = []
    for source_name, fetch_fn in SOURCES:
        try:
            new_events = fetch_fn()
            print(f"[{source_name}] {len(new_events)}개 수집 성공")
            all_new.extend(new_events)
        except Exception as e:
            print(f"[{source_name}] 수집 실패, 건너뜀: {e}")

    merged = merge_and_dedupe(existing, all_new)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"[{datetime.now().isoformat()}] {len(merged)}개 대회 저장 완료 ({args.out})")


if __name__ == "__main__":
    main()

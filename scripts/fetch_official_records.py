"""
calrank 공식 대회 결과 자동 수집.

대회 주최측이 스스로 공개하는 "수상자 명단/역대기록" 페이지를 수집합니다.
이 데이터는 이미 대회 측이 실명으로 공개한 것이므로 마스킹하지 않고,
프론트엔드에서 "공식" 배지를 붙여 사용자 자체 입력 기록과 구분합니다.

Supabase 쓰기 권한: official_records 테이블은 공개 쓰기를 막아뒀기 때문에
SUPABASE_SERVICE_ROLE_KEY(관리자 키, GitHub Secrets에 등록)가 필요합니다.

사용 예시:
  SUPABASE_SERVICE_ROLE_KEY=xxx python scripts/fetch_official_records.py
"""

import os
import re
import requests
from bs4 import BeautifulSoup

SUPABASE_URL = "https://mlbzsqeoqlyvnyzeegeu.supabase.co"
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}


def time_to_seconds(text: str) -> int | None:
    """'1:16.25' 또는 '35:02' 같은 표기를 초 단위로 변환합니다."""
    text = text.strip()
    m = re.match(r"^(\d+):(\d{1,2})[.:](\d{2})$", text)
    if m:
        h, mi, s = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return h * 3600 + mi * 60 + s
    m = re.match(r"^(\d{1,2}):(\d{2})$", text)
    if m:
        mi, s = int(m.group(1)), int(m.group(2))
        return mi * 60 + s
    return None


def guess_marathon_distance(course_text: str) -> str | None:
    if "하프" in course_text or "21" in course_text:
        return "half"
    if "10km" in course_text or "10K" in course_text.upper():
        return "10km"
    if "5km" in course_text or "5K" in course_text.upper():
        return "5km"
    if "풀" in course_text or "42" in course_text:
        return "full"
    return None


# ---- 소스 1: 제주MBC국제평화마라톤 수상자 명단 ----

JEJU_MBC_URL = "https://marathon.jejumbc.com/02_record/record_02.php"
JEJU_MBC_RACE_NAME = "제주MBC국제평화마라톤"


def fetch_jeju_mbc(race_year: int) -> list[dict]:
    resp = requests.get(JEJU_MBC_URL, timeout=15, headers=HEADERS)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding
    soup = BeautifulSoup(resp.text, "html.parser")

    table = soup.select_one("table.win-table")
    if not table:
        return []

    records = []
    current_course = None
    for tr in table.select("tbody tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        # rowspan으로 인해 '분류'/'코스' 열이 매 행마다 있지 않으므로 이전 값을 이어씀
        if len(cells) == 6:
            _, course, rank, name, record, region = cells
            current_course = course
        elif len(cells) == 5:
            course, rank, name, record, region = cells
            current_course = course
        elif len(cells) == 4:
            rank, name, record, region = cells
            course = current_course
        else:
            continue

        distance = guess_marathon_distance(course or "")
        seconds = time_to_seconds(record)
        if not distance or not seconds or not name:
            continue

        records.append({
            "sport": "marathon",
            "distance_category": distance,
            "race_name": JEJU_MBC_RACE_NAME,
            "race_year": race_year,
            "athlete_name": name,
            "finish_time_seconds": seconds,
            "region": region or None,
            "source_name": JEJU_MBC_RACE_NAME,
            "source_url": JEJU_MBC_URL,
        })

    return records


SOURCES = [
    ("jejumbc.com", lambda: fetch_jeju_mbc(race_year=2026)),
]


def upsert_records(records: list[dict]) -> int:
    if not SERVICE_KEY:
        print("SUPABASE_SERVICE_ROLE_KEY가 없어 저장을 건너뜁니다 (조회만 테스트).")
        return 0

    headers = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/official_records",
        headers=headers, json=records, timeout=30,
    )
    resp.raise_for_status()
    return len(records)


def main():
    all_records = []
    for source_name, fetch_fn in SOURCES:
        try:
            records = fetch_fn()
            print(f"[{source_name}] {len(records)}건 수집 성공")
            all_records.extend(records)
        except Exception as e:
            print(f"[{source_name}] 수집 실패, 건너뜀: {e}")

    if not all_records:
        print("수집된 기록이 없습니다.")
        return

    saved = upsert_records(all_records)
    print(f"총 {len(all_records)}건 수집, {saved}건 저장 완료")


if __name__ == "__main__":
    main()

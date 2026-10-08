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


# ---- 소스 2: JTBC 서울마라톤 역대 기록 ----
#
# https://marathon.jtbc.com/51 에 1999년부터의 역대 수상자가 한 페이지에 있다.
# robots.txt 는 로그인·관리자 경로만 막고 나머지는 Allow 다(2026-10-08 확인).
#
# 엘리트부가 아니라 "마스터즈"만 가져온다. 엘리트는 실업팀·국가대표 선수라
# 동호인 기록과 같은 표에 섞으면 랭킹이 왜곡된다. calrank 는 동호인 서비스다.
#
# 표 구조:
#   [0] 마스터즈 남/녀            <- 구분 제목이 표 안 첫 행에 있다
#   [1] 순위 | 남자 | 여자
#   [2] 성명 | 기록 | 성명 | 기록
#   [3] 1 | 홍길동 | 2:24:02 | 김아무 | 2:47:36     <- 5칸
JTBC_URL = "https://marathon.jtbc.com/51"
JTBC_RACE_NAME = "JTBC서울마라톤"
_YEAR_RE = re.compile(r"^(\d{4})\s*제\s*\d+\s*회")


def fetch_jtbc_seoul() -> list[dict]:
    resp = requests.get(JTBC_URL, timeout=20, headers=HEADERS)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding
    soup = BeautifulSoup(resp.text, "html.parser")

    records: list[dict] = []
    year: int | None = None

    # 연도 제목과 표가 형제로 흩어져 있어, 문서 순서대로 훑으며 현재 연도를 기억한다.
    for node in soup.find_all(True):
        if node.name == "table":
            rows = [
                [c.get_text(strip=True) for c in tr.find_all(["td", "th"])]
                for tr in node.find_all("tr")
            ]
            if not rows or "마스터즈" not in " ".join(rows[0]):
                continue
            if year is None:
                continue
            for cells in rows[1:]:
                # 데이터 행만: 순위 | 남자이름 | 남자기록 | 여자이름 | 여자기록
                if len(cells) != 5 or not cells[0].isdigit():
                    continue
                for name, record in ((cells[1], cells[2]), (cells[3], cells[4])):
                    seconds = time_to_seconds(record)
                    if not name or not seconds:
                        continue
                    records.append({
                        "sport": "marathon",
                        "distance_category": "full",   # JTBC 서울마라톤은 풀코스
                        "race_name": JTBC_RACE_NAME,
                        "race_year": year,
                        "athlete_name": name,
                        "finish_time_seconds": seconds,
                        "region": "서울",
                        "source_name": "JTBC서울마라톤 역대기록",
                        "source_url": JTBC_URL,
                    })
            continue

        # 표가 아니면 연도 제목인지 본다. 자식이 많은 컨테이너는 건너뛴다.
        if len(node.find_all(True, recursive=False)) > 2:
            continue
        m = _YEAR_RE.match(node.get_text(strip=True))
        if m:
            year = int(m.group(1))

    return records


SOURCES = [
    ("jejumbc.com", lambda: fetch_jeju_mbc(race_year=2026)),
    ("marathon.jtbc.com", fetch_jtbc_seoul),
]


def _auth_headers() -> dict:
    return {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json",
    }


def fetch_existing_keys() -> set:
    """이미 저장된 기록의 식별 키를 읽어 온다.

    official_records 에는 유니크 제약이 없어서, 매주 같은 수상자 명단을 다시
    POST 하면 같은 행이 계속 쌓인다. 테이블에 제약을 거는 쪽이 더 깔끔하지만
    기존 데이터를 건드리지 않고 고칠 수 있는 범위에서 여기서 걸러 낸다.
    """
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/official_records"
        "?select=race_name,race_year,distance_category,athlete_name,finish_time_seconds",
        headers=_auth_headers(), timeout=30,
    )
    resp.raise_for_status()
    return {
        (r.get("race_name"), r.get("race_year"), r.get("distance_category"),
         r.get("athlete_name"), r.get("finish_time_seconds"))
        for r in resp.json()
    }


def record_key(r: dict):
    return (r["race_name"], r["race_year"], r["distance_category"],
            r["athlete_name"], r["finish_time_seconds"])


def upsert_records(records: list[dict]) -> int:
    if not SERVICE_KEY:
        print("SUPABASE_SERVICE_ROLE_KEY가 없어 저장을 건너뜁니다 (수집만 확인).")
        return 0

    existing = fetch_existing_keys()
    fresh = [r for r in records if record_key(r) not in existing]
    print(f"기존 {len(existing)}건 / 새 기록 {len(fresh)}건")
    if not fresh:
        return 0

    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/official_records",
        headers={**_auth_headers(), "Prefer": "return=minimal"},
        json=fresh, timeout=30,
    )
    if resp.status_code >= 400:
        # 그동안 이 단계에서 조용히 죽어 왔다. 응답 본문을 남겨 원인을 보이게 한다.
        raise RuntimeError(
            f"저장 실패 HTTP {resp.status_code}: {resp.text[:400]}"
        )
    return len(fresh)


DRY_RUN = os.environ.get("DRY_RUN") == "1"


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

    if DRY_RUN:
        # 새 소스를 처음 붙일 때는 저장 전에 무엇이 들어갈지 눈으로 본다.
        from collections import Counter
        by_src = Counter(r["race_name"] for r in all_records)
        print(f"[DRY_RUN] 저장하지 않습니다. 수집 {len(all_records)}건")
        for k, v in by_src.items():
            print(f"[DRY_RUN]   {k}: {v}건")
        for r in all_records[:6]:
            print(f"[DRY_RUN]   예시 {r['race_year']} {r['distance_category']} "
                  f"{r['athlete_name']} {r['finish_time_seconds']}초")
        return

    try:
        saved = upsert_records(all_records)
    except Exception as e:
        # 수집은 됐는데 저장만 실패한 경우를 구분해서 보여 준다.
        print(f"수집 {len(all_records)}건 성공했으나 저장 단계에서 실패: {e}")
        raise
    print(f"총 {len(all_records)}건 수집, {saved}건 저장 완료")


if __name__ == "__main__":
    main()

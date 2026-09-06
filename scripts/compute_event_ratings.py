"""
calrank 대회 등급(자체 평가 점수) 자동 산정 스크립트

유저가 남기는 참가 후기(별점)와는 별개로, calrank가 보유한 실제 데이터
(주최기관, 코스 구성, 대회 역사, 찜 수 등)만으로 대회 자체의 신뢰도·규모를
20개 항목으로 채점한다. 지어낸 참가인원 등 없는 데이터는 절대 쓰지 않고,
events.json에 실제로 존재하는 필드만 근거로 삼는다.

결과는 event_ratings.json에 저장되며, 모든 대회(이벤트) 페이지/카드에서
공통으로 참조한다. events.json이 매일 갱신될 때마다 다시 계산되어
항상 최신 상태를 유지한다.

사용 예시:
  python scripts/compute_event_ratings.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PRESS_KEYWORDS = ["일보", "신문", "MBC", "KBS", "SBS", "YTN", "JTBC", "방송"]
GOV_KEYWORDS = ["시청", "도청", "군청", "구청", "시체육회", "도체육회", "시육상연맹"]
ASSOC_KEYWORDS = ["연맹", "협회", "체육회"]
BRAND_KEYWORDS = ["삼성", "카카오", "현대", "LG", "SK", "코오롱", "나이키", "아디다스", "뉴발란스"]
CASUAL_KEYWORDS = ["챌린지", "펀런", "fun run", "FUN RUN"]
METRO_REGIONS = {"서울", "경기", "인천", "부산", "대구", "광주", "대전", "울산"}


def load_json(path, default):
    p = ROOT / path
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(path, data):
    p = ROOT / path
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def series_key(name):
    s = re.sub(r"\d{4}\s*", "", name or "")
    s = re.sub(r"제\s*\d+\s*회", "", s)
    s = re.sub(r"\s+", "", s)
    return s.lower()


def has_any(text, keywords):
    text = text or ""
    return any(k in text for k in keywords)


def edition_number(name):
    m = re.search(r"제\s*(\d+)\s*회", name or "")
    return int(m.group(1)) if m else None


# 20개 평가항목. 각 항목은 (라벨, 달성 여부/조건 함수, 배점) 형태로 정의한다.
# 배점은 실제 대회 규모·신뢰도에 미치는 영향력을 감안해 차등 부여했다.
def build_criteria(ev, has_prior_edition):
    name = ev.get("name") or ""
    organizer = ev.get("organizer") or ""
    combined = f"{name} {organizer}"
    distances = ev.get("distances") or []
    dist_text = " ".join(distances)
    saves = ev.get("saves") or 0
    region = ev.get("region") or ""
    ed = edition_number(name)

    items = []

    def add(label, achieved, weight):
        items.append({"label": label, "achieved": bool(achieved), "weight": weight})

    add("풀코스(42.195km) 운영", "풀코스" in dist_text or "42.195" in dist_text or "42km" in dist_text, 8)
    add("하프코스(21km) 운영", "하프" in dist_text or "21" in dist_text, 5)
    add("코스 3종 이상 다양성", len(distances) >= 3, 4)
    add("국제 대회 표방", "국제" in combined, 7)
    add("언론사 주최·후원", has_any(combined, PRESS_KEYWORDS), 10)
    add("지자체 주최", has_any(combined, GOV_KEYWORDS), 6)
    add("육상연맹·협회 주최", has_any(combined, ASSOC_KEYWORDS), 5)
    add("대회 역사 20회 이상", ed is not None and ed >= 20, 10)
    add("대회 역사 10~19회", ed is not None and 10 <= ed < 20, 7)
    add("대회 역사 5~9회", ed is not None and 5 <= ed < 10, 4)
    add("연속 개최 이력 확인", has_prior_edition, 5)
    add("calrank 찜(관심) 10개 이상", saves >= 10, 8)
    add("calrank 찜(관심) 3~9개", 3 <= saves < 10, 4)
    add("수도권·광역시 개최", region in METRO_REGIONS, 5)
    add("온라인 신청 채널 운영", bool(ev.get("applyUrl")), 4)
    add("대회 정보 완전성(장소·주최·거리)", bool(ev.get("location") and ev.get("organizer") and distances), 3)
    add("주최측 연락처 공개", bool(ev.get("organizerPhone")), 3)
    add("울트라/100km 이상 코스 보유", "울트라" in dist_text or "100km" in dist_text.replace(" ", ""), 3)
    add("대기업·브랜드 후원 표기", has_any(combined, BRAND_KEYWORDS), 4)
    add("소규모 캐주얼 대회 특성", has_any(combined, CASUAL_KEYWORDS) and ed is None, -3)

    return items


def compute_stars(items):
    positive_max = sum(i["weight"] for i in items if i["weight"] > 0)
    # 역사 3단계(20회+/10~19/5~9)는 상호배타적이라 최고 구간만 만점 처리되므로,
    # 이론상 달성 가능한 최댓값에서 하위 두 단계의 배점을 빼서 과소평가를 막는다.
    positive_max -= 7 + 4  # "10~19회", "5~9회" 항목은 실제로는 동시 달성 불가능
    achieved = sum(i["weight"] for i in items if i["achieved"])
    ratio = max(0.0, min(1.0, achieved / positive_max)) if positive_max > 0 else 0
    stars = 1 + ratio * 4
    stars = round(stars * 2) / 2  # 0.5 단위로 반올림
    return round(stars, 1), achieved, positive_max


def main():
    events = load_json("events.json", [])
    keys_seen = {}
    for e in events:
        k = series_key(e.get("name"))
        if not k:
            continue
        keys_seen.setdefault(k, []).append(e.get("id"))

    ratings = {}
    for e in events:
        eid = e.get("id")
        if not eid:
            continue
        k = series_key(e.get("name"))
        has_prior = k in keys_seen and len(keys_seen[k]) >= 2
        items = build_criteria(e, has_prior)
        stars, achieved, positive_max = compute_stars(items)
        ratings[eid] = {
            "stars": stars,
            "score": achieved,
            "maxScore": positive_max,
            "criteria": items,
        }

    save_json("event_ratings.json", ratings)
    print(f"Computed ratings for {len(ratings)} events.")


if __name__ == "__main__":
    main()

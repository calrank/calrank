"""
calrank 대회 규모·인지도 지수 자동 산정 스크립트

유저가 남기는 참가 후기(별점)와는 완전히 별개의 지표다. 이건 "품질 평가"가
아니라 "공개된 정보만으로 추정한 대회의 규모·인지도" 지수이며, 반드시
그렇게만 취급한다. 실제 운영 품질·안전·참가자 만족도를 보장하지 않으므로
화면에 노출할 때는 항상 면책 문구를 함께 표시해야 한다.

지어낸 참가인원 등 없는 데이터는 절대 쓰지 않고, events.json에 실제로
존재하는 필드만 근거로 삼는다. 특정 대회를 "질 낮다"고 낙인찍을 수 있는
감점 항목은 포함하지 않는다 — 점수를 덜 받는 것과 나쁘다고 표시하는 것은
다르다.

결과는 event_ratings.json에 저장되며, 모든 대회 페이지/카드에서 공통으로
참조한다. events.json이 매일 갱신될 때마다 다시 계산되어 최신 상태를 유지한다.

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
METRO_REGIONS = {"서울", "경기", "인천", "부산", "대구", "광주", "대전", "울산"}

DISCLAIMER = "이 지수는 공개된 정보만으로 추정한 참고 지표이며, 실제 대회 운영·안전·참가자 만족도를 보장하지 않습니다."


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


# 19개 평가항목 — 전부 "가점만" 주는 방식이다. 특정 대회를 깎아내리는 감점
# 항목은 의도적으로 두지 않았다(오인·명예훼손 소지를 없애기 위함).
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
    add("국제 대회 표방", "국제" in combined, 8)
    # 언론사 주최는 회차 표기가 없어도 그 자체로 대형 대회일 가능성이 매우 높아
    # 가중치를 가장 높게 둔다(춘천마라톤, 동아마라톤 등 실제 사례 반영).
    add("언론사 주최·후원", has_any(combined, PRESS_KEYWORDS), 20)
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

    return items


TIER_THRESHOLDS = [
    (80, "플래티넘"),
    (60, "골드"),
    (40, "실버"),
    (20, "브론즈"),
    (0, "일반"),
]


def tier_for(pct):
    for threshold, label in TIER_THRESHOLDS:
        if pct >= threshold:
            return label
    return "일반"


def compute_index(items):
    positive_max = sum(i["weight"] for i in items)
    # 역사 3단계(20회+/10~19/5~9)는 상호배타적이라 실제로는 최고 구간만 달성
    # 가능하므로, 이론상 최댓값에서 하위 두 단계 배점을 빼 과소평가를 막는다.
    positive_max -= 7 + 4
    achieved = sum(i["weight"] for i in items if i["achieved"])
    pct = round(max(0.0, min(100.0, achieved / positive_max * 100))) if positive_max > 0 else 0
    return pct, tier_for(pct), achieved, positive_max


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
        pct, tier, achieved, positive_max = compute_index(items)
        ratings[eid] = {
            "indexScore": pct,
            "tier": tier,
            "score": achieved,
            "maxScore": positive_max,
            "criteria": items,
            "disclaimer": DISCLAIMER,
        }

    save_json("event_ratings.json", ratings)
    print(f"Computed scale index for {len(ratings)} events.")


if __name__ == "__main__":
    main()

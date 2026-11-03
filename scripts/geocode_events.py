"""
calrank 좌표 보강(지오코딩) 스크립트

events.json에서 위경도(lat/lng)가 없는 대회 중 location(주소) 필드가 있는
것들을 골라, 무료 지오코딩 서비스인 OpenStreetMap Nominatim으로 좌표를 채운다.
날씨 미리보기(Open-Meteo)가 좌표 있는 대회에서만 동작하므로, 좌표를 채울수록
더 많은 대회에서 날씨 미리보기가 노출된다.

Nominatim 사용 정책상 초당 1회 요청 제한을 지킨다. 한 번 실행에 최대
MAX_PER_RUN개만 처리해 GitHub Actions 러너 시간을 아끼고, 실패/성공 이력은
캐시 파일에 남겨 같은 주소를 반복해서 재시도하지 않는다.

사용 예시:
  python scripts/geocode_events.py
"""
import json
import re
import sys
import time
from pathlib import Path
from urllib import request, error, parse

ROOT = Path(__file__).resolve().parent.parent
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "calrank-geocoder/1.0 (https://calrank.vercel.app; contact via site)"
MAX_PER_RUN = 60
SLEEP_SECONDS = 1.1  # Nominatim 사용정책: 초당 1회 이하



SIDO_LONG = ["서울특별시","부산광역시","대구광역시","인천광역시","광주광역시","대전광역시",
             "울산광역시","세종특별자치시","경기도","강원특별자치도","강원도","충청북도",
             "충청남도","전북특별자치도","전라북도","전라남도","경상북도","경상남도",
             "제주특별자치도","제주도"]
SHORT = {"서울":"서울특별시","부산":"부산광역시","대구":"대구광역시","인천":"인천광역시",
         "광주":"광주광역시","대전":"대전광역시","울산":"울산광역시","세종":"세종특별자치시",
         "경기":"경기도","강원":"강원특별자치도","충북":"충청북도","충남":"충청남도",
         "전북":"전북특별자치도","전남":"전라남도","경북":"경상북도","경남":"경상남도",
         "제주":"제주특별자치도"}
# 시·군·구만. 도 이름은 여기서 잡지 않는다 (전북특별자치도가 먼저 걸리던 버그)
# 시도 이름 자체는 제외한다 ('대구광역시'가 '대구광역'+'시' 로 걸리던 버그)
UNIT = re.compile(r'([가-힣]{2,5}(?:시|군|구))(?![가-힣])')
IS_SIDO = re.compile(r'(특별시|광역시|특별자치시|특별자치도|도)$')
NOT_PLACE = re.compile(r'(경기장|체육관|공원|학교|센터|광장|회관|시장|복지|문화|체육|운동장)')
SKIP_REGION = {"전국", "온라인"}


def region_query(ev):
    """(질의 문자열, 시도를 location 에서 직접 읽었는가) 를 돌려준다."""
    """기온 평년값을 붙일 수 있을 만큼의 행정구역 문자열. 없으면 None.

    장소명 전체로는 지오코더가 자주 실패한다('고성군 당항포 엑스포 공원').
    기온은 60km 안의 관측소에서 가져오므로 시·군 수준이면 충분하다.
    region 필드가 틀린 경우가 있어(강원 + 경남 당항포) location 쪽을 먼저 믿는다.
    """
    region = (ev.get("region") or "").strip()
    if region in SKIP_REGION:
        return None
    loc = re.sub(r'\([^)]*\)', ' ', str(ev.get("location") or ""))
    if not loc.strip():
        return SHORT.get(region) or (region if region in SIDO_LONG else None)

    sido = None
    for s in SIDO_LONG:
        if s in loc:
            sido = s
            break
    if not sido:
        m = re.match(r'\s*(서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)(?![가-힣])', loc)
        if m:
            sido = SHORT[m.group(1)]

    units = [u for u in UNIT.findall(loc)
             if not NOT_PLACE.search(u) and not IS_SIDO.search(u) and u not in SIDO_LONG]
    unit = units[0] if units else None

    if not sido:
        sido = SHORT.get(region) or (region if region in SIDO_LONG else None)
    if unit and sido:
        return "%s %s" % (sido, unit)
    return unit or sido


def load_json(path, default):
    p = ROOT / path
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(path, data):
    p = ROOT / path
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def geocode(address):
    query = parse.urlencode({"q": address, "format": "json", "limit": 1, "countrycodes": "kr"})
    url = f"{NOMINATIM_URL}?{query}"
    req = request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (error.URLError, error.HTTPError, TimeoutError) as e:
        print(f"  geocode error for '{address}': {e}", file=sys.stderr)
        return None
    if not data:
        return None
    return float(data[0]["lat"]), float(data[0]["lon"])


def main():
    events = load_json("events.json", [])
    cache = load_json("scripts/geocode_cache.json", {})

    targets = [
        e for e in events
        if (not e.get("lat") or not e.get("lng")) and (e.get("location") or e.get("region"))
    ]
    print("좌표 없는 대회 %d개" % len(targets))

    processed = updated = approx = 0
    for e in targets:
        if processed >= MAX_PER_RUN:
            break

        # 1차: 주소 그대로. 장소명까지 맞으면 가장 정확하다.
        address = (e.get("location") or "").strip()
        result, is_exact = None, True
        if address:
            if address in cache:
                result = cache[address]
            else:
                result = geocode(address)
                cache[address] = result
                processed += 1
                time.sleep(SLEEP_SECONDS)

        # 2차: 행정구역만. 지오코더는 '고성군 당항포 엑스포 공원' 같은
        # 서술형 장소명을 자주 못 찾는다. 기온 평년값은 60km 안의 관측소에서
        # 가져오므로 시·군 수준이면 충분하다. 다만 정확한 좌표가 아니므로
        # 표시해 두고, 페이지에서 '대회장에서 N km' 라고 말하지 않게 한다.
        if not result:
            q = region_query(e)
            if q and processed < MAX_PER_RUN:
                key = "region:" + q
                if key in cache:
                    result = cache[key]
                else:
                    result = geocode(q)
                    cache[key] = result
                    processed += 1
                    time.sleep(SLEEP_SECONDS)
                if result:
                    is_exact = False

        if result:
            e["lat"], e["lng"] = result
            if is_exact:
                e.pop("geoApprox", None)
            else:
                e["geoApprox"] = True
                approx += 1
            updated += 1

    save_json("events.json", events)
    save_json("scripts/geocode_cache.json", cache)
    print("이번 실행 조회 %d건 · 좌표 채운 대회 %d개 (그중 행정구역 기준 %d개)"
          % (processed, updated, approx))


if __name__ == "__main__":
    main()

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
import sys
import time
from pathlib import Path
from urllib import request, error, parse

ROOT = Path(__file__).resolve().parent.parent
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "calrank-geocoder/1.0 (https://calrank.vercel.app; contact via site)"
MAX_PER_RUN = 60
SLEEP_SECONDS = 1.1  # Nominatim 사용정책: 초당 1회 이하


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
        if (not e.get("lat") or not e.get("lng")) and e.get("location")
    ]
    print(f"Total events without coordinates but with location: {len(targets)}")

    processed = 0
    updated = 0
    for e in targets:
        if processed >= MAX_PER_RUN:
            break
        address = e["location"]
        if address in cache:
            result = cache[address]
        else:
            result = geocode(address)
            cache[address] = result
            processed += 1
            time.sleep(SLEEP_SECONDS)

        if result:
            e["lat"], e["lng"] = result
            updated += 1

    save_json("events.json", events)
    save_json("scripts/geocode_cache.json", cache)
    print(f"Processed {processed} new lookups this run, updated {updated} events with coordinates.")


if __name__ == "__main__":
    main()

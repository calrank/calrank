"""OpenStreetMap 에서 우리 코스 주변의 시설 지점(화장실·식수대·샘·쉼터·전망)을 받아 data/course_pois.json 을 만든다.

- Actions 전용(샌드박스는 Overpass 에 닿지 않는다). 매달 한 번, 코스마다 경로 상자(+150m)로 한 번씩 묻는다.
- 지점은 코스 경로 80m 안에 있는 것만 담는다(poi_lib.snap). 기준일은 OSM 의 마지막 편집일이다.
- 자료에 없는 것은 '자료에 없음'이지 '실제로 없음'이 아니다. 현장 확인은 하지 않는다.
- 라이선스: © OpenStreetMap contributors, ODbL 1.0 (https://www.openstreetmap.org/copyright). 산출 파일에 적는다.

  python scripts/fetch_osm_pois.py                 # Overpass 를 불러 만든다
  python scripts/fetch_osm_pois.py --rows r.json   # 받아 둔 지점 목록으로 만든다(시험용)
"""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poi_lib as L  # noqa: E402
import build_poi_layer as B  # noqa: E402
import probe_poi as P  # noqa: E402

MIRRORS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
UA = "calrank-poi/1.0 (https://calrank.kr; 시설 지점 월 1회 수집)"
MARGIN = 0.0015  # 약 150m
SLEEP = 2.0
B.KIND.setdefault("DRINK", "식수대")


def code_of(tags):
    a, n, t = tags.get("amenity"), tags.get("natural"), tags.get("tourism")
    if a == "toilets":
        return "TOILET"
    if a == "drinking_water":
        return "DRINK"
    if n == "spring":
        return "SPRING"
    if a == "shelter" and tags.get("shelter_type") != "public_transport":
        return "SHELTER"
    if t in ("alpine_hut", "wilderness_hut"):
        return "SHELTER"
    if t == "viewpoint":
        return "VIEW"
    return None


def query(bbox):
    s, w, n, e = bbox
    box = f"({s:.5f},{w:.5f},{n:.5f},{e:.5f})"
    q = ("[out:json][timeout:90];(" +
         "".join(f'nwr["{k}"="{v}"]{box};' for k, v in [("amenity", "toilets"), ("amenity", "drinking_water"),
                 ("natural", "spring"), ("amenity", "shelter"), ("tourism", "viewpoint"),
                 ("tourism", "alpine_hut"), ("tourism", "wilderness_hut")]) + ");out center meta;")
    data = urllib.parse.urlencode({"data": q}).encode()
    last = None
    for attempt in range(6):
        url = MIRRORS[attempt % len(MIRRORS)]
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode()).get("elements", []), None
        except Exception as ex:  # noqa: BLE001
            last = str(ex)
            time.sleep(5 * (attempt + 1))
    return None, last


def rows_for(routes):
    rows, seen, failed = [], set(), []
    for i, (rid, pts) in enumerate(routes.items(), 1):
        lats, lons = [p[0] for p in pts], [p[1] for p in pts]
        els, err = query((min(lats) - MARGIN, min(lons) - MARGIN, max(lats) + MARGIN, max(lons) + MARGIN))
        if els is None:
            failed.append(rid)
            print(f"[{i}/{len(routes)}] {rid} 실패: {err}")
            continue
        for el in els:
            key = (el.get("type"), el.get("id"))
            if key in seen:
                continue
            seen.add(key)
            c = code_of(el.get("tags") or {})
            lat = el.get("lat") or (el.get("center") or {}).get("lat")
            lon = el.get("lon") or (el.get("center") or {}).get("lon")
            if not c or lat is None or lon is None:
                continue
            t = el.get("tags") or {}
            rows.append({"code": c, "lat": lat, "lot": lon, "placeNm": t.get("name:ko") or t.get("name") or "",
                         "crtrDt": str(el.get("timestamp") or "")[:10]})
        if i % 20 == 0:
            print(f"[{i}/{len(routes)}] 누적 지점 {len(rows)}")
        time.sleep(SLEEP)
    return rows, failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows")
    ap.add_argument("--out", default=B.OUT)
    a = ap.parse_args()
    routes = P.load_routes()
    failed = []
    if a.rows:
        rows = json.load(open(a.rows, encoding="utf-8"))
    else:
        rows, failed = rows_for(routes)
    if not rows:
        print("지점을 하나도 받지 못했다. 파일을 쓰지 않는다.")
        return 1
    if failed and len(failed) > len(routes) * 0.2:
        print(f"실패한 코스가 {len(failed)}곳으로 많다. 파일을 쓰지 않는다.")
        return 1
    out, skipped = B.build(rows, routes)
    for rid in failed:  # 못 받은 코스는 '없음'이 아니라 '받지 못함'으로 남긴다
        out[rid]["failed"] = True
    day = (datetime.now(timezone.utc) + timedelta(hours=9)).strftime("%Y-%m-%d")
    doc = {"built": day, "source": "OpenStreetMap contributors (ODbL 1.0)", "license": "https://www.openstreetmap.org/copyright",
           "note": "기준일은 OSM 마지막 편집일입니다. 현장 확인은 하지 않았고, 자료에 없는 지점은 실제로 없다는 뜻이 아닙니다.",
           "near_m": L.NEAR_M, "routes": out}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    withp = sum(1 for v in out.values() if v["pois"])
    kinds = {}
    for v in out.values():
        for p in v["pois"]:
            kinds[p[1]] = kinds.get(p[1], 0) + 1
    print(f"코스 {len(out)}곳 중 지점이 잡힌 코스 {withp}곳 · 실패 {len(failed)}곳 · 종류별 {kinds} → {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

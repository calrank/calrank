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
UA = "calrank-poi/1.0 (https://calrank.kr; monthly trail facility fetch)"
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
    for attempt in range(3):
        url = MIRRORS[attempt % len(MIRRORS)]
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode()).get("elements", []), None
        except Exception as ex:  # noqa: BLE001
            last = str(ex)
            time.sleep(4 * (attempt + 1))
    return None, last


BUDGET_S = 75 * 60  # 이 시간이 지나면 거기까지만 쓰고 나머지는 '받지 못함'으로 남긴다


def rows_for(routes):
    """예산 안에서 받을 수 있는 코스까지만 받는다. (rows, 받은 코스 id 목록, 실패 id 목록, 남은 코스 수)"""
    rows, seen, failed, done, t0 = [], set(), [], [], time.time()
    pending = 0
    for i, (rid, pts) in enumerate(routes.items(), 1):
        if time.time() - t0 > BUDGET_S:
            pending += 1
            continue
        lats, lons = [p[0] for p in pts], [p[1] for p in pts]
        els, err = query((min(lats) - MARGIN, min(lons) - MARGIN, max(lats) + MARGIN, max(lons) + MARGIN))
        if els is None:
            failed.append(rid)
            print(f"[{i}/{len(routes)}] {rid} 실패: {err}", flush=True)
            continue
        done.append(rid)
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
        print(f"[{i}/{len(routes)}] {rid} 지점 {len(els)} · 누적 {len(rows)} · {int(time.time() - t0)}초", flush=True)
        time.sleep(SLEEP)
    return rows, done, failed, pending


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows")
    ap.add_argument("--out", default=B.OUT)
    a = ap.parse_args()
    routes = P.load_routes()
    prior = {}
    if os.path.exists(a.out) and not a.rows:  # 이어받기: 이미 받은 코스는 건너뛴다(실패 표시된 코스만 다시)
        try:
            prior = {k: v for k, v in json.load(open(a.out, encoding="utf-8")).get("routes", {}).items() if not v.get("failed")}
        except Exception:  # noqa: BLE001
            prior = {}
    todo = {k: v for k, v in routes.items() if k not in prior}
    print(f"이미 받은 코스 {len(prior)}곳, 이번에 받을 코스 {len(todo)}곳", flush=True)
    failed, pending = [], 0
    if a.rows:
        rows = json.load(open(a.rows, encoding="utf-8"))
        done = list(routes)
    else:
        rows, done, failed, pending = rows_for(todo)
    if not done and not prior:
        print("받은 코스가 하나도 없다. 파일을 쓰지 않는다.")
        return 1
    out, skipped = B.build(rows, {k: routes[k] for k in done})
    out.update(prior)
    for rid in failed:  # 못 받은 코스는 '없음'이 아니라 '받지 못함'으로 남긴다
        out[rid] = {"lengthM": 0, "pois": [], "failed": True}
    day = (datetime.now(timezone.utc) + timedelta(hours=9)).strftime("%Y-%m-%d")
    doc = {"built": day, "source": "OpenStreetMap contributors (ODbL 1.0)", "license": "https://www.openstreetmap.org/copyright",
           "note": "기준일은 OSM 마지막 편집일입니다. 현장 확인은 하지 않았고, 자료에 없는 지점은 실제로 없다는 뜻이 아닙니다.",
           "near_m": L.NEAR_M, "total_routes": len(routes), "routes": out}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    withp = sum(1 for v in out.values() if v["pois"])
    kinds = {}
    for v in out.values():
        for p in v["pois"]:
            kinds[p[1]] = kinds.get(p[1], 0) + 1
    print(f"받은 코스 {len(out)}곳 중 지점이 잡힌 코스 {withp}곳 · 이번 실패 {len(failed)}곳 · 아직 못 받은 코스 {pending}곳 · 종류별 {kinds} → {a.out}")
    if pending:
        print("예산이 끝나 일부만 받았다. 워크플로를 한 번 더 돌리면 이어서 받는다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

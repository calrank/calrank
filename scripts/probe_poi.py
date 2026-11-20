"""
한국등산트레킹지원센터 POI 서비스와 OpenStreetMap 에 화장실·약수터(샘터)·쉼터 같은 시설 지점이
얼마나 있는지 한 번 센다. 로그에만 남고 저장소에는 아무것도 쓰지 않는다.

확인하려는 것:
  1) 공공데이터포털 서비스 키가 이 API 들에 활용신청이 되어 있는가 (안 됐으면 오류 코드가 로그에 나온다)
  2) 장소유형코드별 지점 수, 좌표·기준일 상태, 숲길 몇 곳에 걸쳐 있는가
  3) 우리 코스 경로(두루누비 149곳 + 산림청 숲길 69곳) 80m 안에 시설 지점이 코스 몇 곳에 걸쳐 몇 개 잡히는가
  4) OSM 에서 같은 종류가 대표 산악 지역(북한산·설악산·지리산·한라산)에 몇 개 찍혀 있는가
키는 로그에 나가지 않게 가린다.
"""
import collections
import glob
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

KEY = urllib.parse.unquote(os.environ.get("DATA_GO_KR_KEY", "").strip())
UA = "calrank-probe/1.0 (https://calrank.kr)"
BASE = "https://apis.data.go.kr/B553662"
SERVICES = {
    "숲길POI(fmmtnFrtrlPoi)": f"{BASE}/fmmtnFrtrlPoiInfoService/getFmmtnFrtrlPoiInfoList",
    "교통시설POI(trnspPoi)": f"{BASE}/trnspPoiInfoService/getTrnspPoiInfoList",
    # 2026-11-20 활용신청 승인된 4종. 오퍼레이션 이름은 참고문서 확인 전이라 추정값이다
    # (호출이 실패하면 그 오류를 그대로 출력하므로 로그로 정확한 이름을 확인한다).
    "100대명산봉우리(peakPoi)": f"{BASE}/peakPoiInfoService/getPeakPoiInfoList",
    "국가숲길POI(ntnFrtrl)": f"{BASE}/ntnFrtrlInfoService/getNtnFrtrlInfoList",
    "건강효과POI(hlthEffct)": f"{BASE}/hlthEffctInfoService/getHlthEffctInfoList",
    "위험지역POI(danger)": f"{BASE}/dangerInfoService/getDangerInfoList",
}
CODES = ["TOILET", "SPRING", "REST", "SHELTER", "STORE", "FOOD", "PARK", "TRANS", "INFO", "SIGN", "ENTRY",
         "CAMP", "VIEW", "PHOTO", "DANGER", "PEAK", "SCENERY", "CULTURAL", "WILD"]


def safe(t: str) -> str:
    t = str(t)
    for k in {KEY, urllib.parse.quote(KEY, safe="")}:
        if k:
            t = t.replace(k, "***")
    return t


def get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def call(endpoint, **params):
    q = {"serviceKey": KEY, "type": "json", **params}
    url = endpoint + "?" + urllib.parse.urlencode(q, quote_via=urllib.parse.quote)
    text = None
    for attempt in range(4):
        try:
            text = get(url)
            break
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", "replace")[:300]
            except Exception:  # noqa: BLE001
                pass
            if e.code >= 500 and attempt < 3:  # 서버 시간 초과는 잠깐 쉬었다 다시
                time.sleep(3 * (attempt + 1))
                continue
            return None, f"HTTP {e.code} {safe(body)}"
        except Exception as e:  # noqa: BLE001
            if attempt < 3:
                time.sleep(3 * (attempt + 1))
                continue
            return None, f"요청 실패 {safe(e)}"
    try:
        j = json.loads(text)
    except ValueError:
        return None, "JSON 아님: " + safe(text[:300])
    body = j.get("response", j)
    head = body.get("header", {})
    if str(head.get("resultCode", "00")) not in ("00", "0"):
        return None, f"resultCode {head.get('resultCode')} {head.get('resultMsg')}"
    items = (body.get("body") or {}).get("items") or {}
    items = items.get("item", items) if isinstance(items, dict) else items
    if isinstance(items, dict):
        items = [items]
    return {"total": int((body.get("body") or {}).get("totalCount") or 0), "items": items or []}, None


def probe_services():
    for name, ep in SERVICES.items():
        print(f"\n===== {name}")
        r, err = call(ep, pageNo=1, numOfRows=1)
        if err:
            print("  호출 실패:", err)
            print("  → 이 서비스에 활용신청이 안 됐거나 키가 맞지 않을 수 있다.")
            continue
        print("  전체 지점 수:", r["total"])
        if r["items"]:
            print("  첫 응답 필드:", sorted(r["items"][0].keys()))
        print("  장소유형코드별 지점 수:")
        for c in CODES:
            rr, e = call(ep, pageNo=1, numOfRows=1, srchPlaceTpeCd=c)
            print(f"    {c:9s}", rr["total"] if rr else f"오류 {e}")
            time.sleep(0.15)
        # 화장실·샘터·쉼터는 내려받아 분포를 본다.
        if "fmmtnFrtrlPoi" not in name:
            continue
        for c in ("TOILET", "SPRING", "REST"):
            rows, page = [], 1
            while page <= 12:
                rr, e = call(ep, pageNo=page, numOfRows=1000, srchPlaceTpeCd=c)
                if not rr or not rr["items"]:
                    break
                rows += rr["items"]
                if len(rows) >= rr["total"]:
                    break
                page += 1
            if not rows:
                continue
            trails = collections.Counter(r.get("frtrlNm") for r in rows)
            years = collections.Counter(str(r.get("crtrDt", ""))[:4] for r in rows)
            ok = sum(1 for r in rows if r.get("lat") and r.get("lot"))
            print(f"  [{c}] 받은 {len(rows)}건 · 좌표 있음 {ok} · 숲길 {len(trails)}곳 · 기준연도 {dict(sorted(years.items()))}")
            print("     많은 숲길:", trails.most_common(5))
            for r in rows[:3]:
                print("     예:", {k: r.get(k) for k in ("frtrlNm", "placeNm", "lat", "lot", "crtrDt", "dscrtCn")})


# ── 우리 코스 경로와 맞춰 보기 ───────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poi_lib as L  # noqa: E402

NEAR_M = L.NEAR_M
COV_CODES = [("fmmtn", "TOILET"), ("fmmtn", "SPRING"), ("fmmtn", "REST"), ("fmmtn", "SHELTER"), ("fmmtn", "PARK"),
             ("fmmtn", "INFO"), ("fmmtn", "VIEW"), ("fmmtn", "SIGN"), ("fmmtn", "STORE"), ("trnsp", "TRANS")]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_routes():
    routes = {}
    for f in glob.glob(os.path.join(ROOT, "field", "*.json")):
        if os.path.basename(f) == "index.json":
            continue
        try:
            d = json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if d.get("path"):
            routes["두루누비:" + str(d.get("id"))] = d["path"]
    try:
        g = json.load(open(os.path.join(ROOT, "data", "forest_trails_geo.json"), encoding="utf-8"))
        for k, pts in g.items():
            routes["숲길:" + k] = pts
    except (OSError, ValueError):
        pass
    return routes


def fetch_all(ep, code, cap_pages=60):
    rows, page = [], 1
    while page <= cap_pages:
        rr, err = call(ep, pageNo=page, numOfRows=1000, srchPlaceTpeCd=code)
        if not rr or not rr["items"]:
            if err:
                print(f"    [{code}] {page}쪽 오류 {err}")
            break
        rows += rr["items"]
        if len(rows) >= rr["total"]:
            break
        page += 1
    return rows


def probe_coverage():
    routes = load_routes()
    print(f"\n===== 우리 코스 경로와 맞춰 보기 (경로 {len(routes)}곳, 경로에서 {NEAR_M}m 안)")
    if not routes:
        print("  경로 자료를 읽지 못했다.")
        return
    grid, _ = L.build_grid(routes)
    eps = {"fmmtn": SERVICES["숲길POI(fmmtnFrtrlPoi)"], "trnsp": SERVICES["교통시설POI(trnspPoi)"]}
    per_route = collections.defaultdict(set)  # 경로 → 잡힌 유형
    for svc, code in COV_CODES:
        rows = fetch_all(eps[svc], code)
        near, covered = 0, set()
        for r in rows:
            try:
                lat, lon = float(r.get("lat")), float(r.get("lot"))
            except (TypeError, ValueError):
                continue
            hit = set(L.snap(grid, lat, lon))
            if hit:
                near += 1
                covered |= hit
        for rid in covered:
            per_route[rid].add(code)
        by_src = collections.Counter(rid.split(":")[0] for rid in covered)
        print(f"  {code:8s} 받은 {len(rows):6d}건 · 경로 {NEAR_M}m 안 {near:5d}건 · 걸친 코스 {len(covered)}곳 {dict(by_src)}")
    both = [r for r, t in per_route.items() if "TOILET" in t and "SPRING" in t]
    anyfac = [r for r, t in per_route.items() if t & {"TOILET", "SPRING", "REST", "SHELTER"}]
    print(f"  화장실·샘터 둘 다 잡힌 코스 {len(both)}곳 · 화장실·샘터·쉼터·대피소 중 하나라도 잡힌 코스 {len(anyfac)}곳 / 전체 {len(routes)}곳")


def probe_danger():
    """위험지역 POI(dangerInfoService)가 장소유형이 다양한 전체 지점 목록인지, 우리 코스에 얼마나 걸리는지 본다."""
    ep = SERVICES["위험지역POI(danger)"]
    print("\n===== 위험지역POI 전체 내려받기 (장소유형코드 분포)")
    rows, total, failed, streak, t0 = [], None, [], 0, time.time()
    size, page = 300, 1
    # 한 쪽을 작게 받고, 실패한 쪽은 건너뛰며 끝까지 간다(서버가 큰 쪽에서 시간 초과를 낸다).
    while time.time() - t0 < 1500:
        rr, err = call(ep, pageNo=page, numOfRows=size)
        if not rr:
            failed.append(page)
            streak += 1
            if streak >= 12 or (total and (page - 1) * size >= total):
                print(f"  {page}쪽 실패: {err}" if streak >= 12 else "")
                break
        else:
            streak = 0
            total = rr["total"]
            rows += rr["items"]
            if not rr["items"] or page * size >= total:
                break
        page += 1
    print(f"  실패한 쪽 {len(failed)}개 {failed[:20]}")
    print(f"  받은 {len(rows)}건 / 전체 {total}")
    if not rows:
        return
    cnt = collections.Counter(str(r.get("plcTypeCd")) for r in rows)
    ex = {}
    for r in rows:
        ex.setdefault(str(r.get("plcTypeCd")), []).append(r.get("plcNm"))
    for code, n in cnt.most_common():
        print(f"  {code:10s} {n:6d}건  예: {[x for x in ex[code][:3]]}")
    years = collections.Counter(str(r.get("crtrDt", ""))[:4] for r in rows)
    print("  기준일 연도:", dict(sorted(years.items())))
    routes = load_routes()
    print(f"\n===== 우리 코스 경로와 맞춰 보기 (경로 {len(routes)}곳, 경로에서 {NEAR_M}m 안)")
    grid, _ = L.build_grid(routes)
    per_code = collections.defaultdict(set)
    near = collections.Counter()
    for r in rows:
        try:
            lat, lon = float(r.get("lat")), float(r.get("lot"))
        except (TypeError, ValueError):
            continue
        hit = set(L.snap(grid, lat, lon))
        if hit:
            c = str(r.get("plcTypeCd"))
            near[c] += 1
            per_code[c] |= hit
    for code, n in cnt.most_common():
        print(f"  {code:10s} 경로 안 {near[code]:5d}건 · 걸친 코스 {len(per_code[code])}곳 / {len(routes)}곳")


OVERPASS = "https://overpass-api.de/api/interpreter"
AREAS = {"북한산": (37.60, 126.90, 37.72, 127.05), "설악산": (38.05, 128.25, 38.25, 128.55),
         "지리산": (35.20, 127.45, 35.45, 127.85), "한라산": (33.30, 126.40, 33.45, 126.75)}
TAGS = [("화장실", 'amenity"="toilets'), ("식수대", 'amenity"="drinking_water'), ("샘", 'natural"="spring'),
        ("쉼터", 'amenity"="shelter'), ("벤치", 'amenity"="bench')]


def overpass_count(bbox, tag):
    s, w, n, e = bbox
    q = f'[out:json][timeout:60];node["{tag}"]({s},{w},{n},{e});out count;'
    try:
        req = urllib.request.Request(OVERPASS, data=urllib.parse.urlencode({"data": q}).encode(), headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=90) as r:
            j = json.loads(r.read().decode())
        return int(j["elements"][0]["tags"]["nodes"])
    except Exception as ex:  # noqa: BLE001
        return f"오류 {ex}"


def probe_osm():
    print("\n===== OpenStreetMap (노드 수, 대표 산악 지역 상자)")
    for area, bb in AREAS.items():
        row = {}
        for label, tag in TAGS:
            row[label] = overpass_count(bb, tag)
            time.sleep(2)
        print(f"  {area}: {row}")


if __name__ == "__main__":
    if not KEY:
        print("DATA_GO_KR_KEY 가 없다. 공공데이터 점검은 건너뛰고 OSM 만 센다.")
    else:
        probe_danger()
    probe_osm()

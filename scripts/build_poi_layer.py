"""
시설 지점 자료 만들기: 한국등산트레킹지원센터 POI 를 우리 코스 경로에 맞춰 data/course_pois.json 으로 쓴다.

점검(probe_poi.py)에서 응답과 지점 수를 확인한 뒤에 쓴다. 이 단계에서는 화면에 쓰이지 않는다.
각 지점은 코스 경로 80m 안에 있는 것만 담고, 출발점부터의 거리(m)를 붙인다.

  python scripts/build_poi_layer.py                  # API 를 불러 만든다 (DATA_GO_KR_KEY 필요)
  python scripts/build_poi_layer.py --rows rows.json # 받아 둔 지점 목록으로 만든다 (시험용, 네트워크 없음)

출력 모양:
  {"built": "YYYY-MM-DD", "source": "...", "near_m": 80,
   "routes": {"두루누비:dr-1234": {"lengthM": 12345, "pois": [[거리m, 종류, 이름, 원천코드, 기준일], ...]}}}
자료에 없는 지점을 만들어 넣지 않는다. 지점이 없는 코스는 pois 가 빈 목록이고, 그것은 '자료에 없음'이지 '실제로 없음'이 아니다.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poi_lib as L  # noqa: E402

KIND = {"TOILET": "화장실", "SPRING": "약수터·샘터", "REST": "쉼터", "SHELTER": "대피소", "PARK": "주차장",
        "INFO": "안내소", "VIEW": "전망", "SIGN": "갈림길", "STORE": "편의점", "TRANS": "대중교통"}
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "course_pois.json")
DUP_M = 15  # 같은 종류가 이 거리 안에 겹치면 하나로 본다


def build(rows, routes):
    """rows: [{'code','lat','lot','placeNm','crtrDt'}...], routes: {이름: 경로}"""
    grid, length = L.build_grid(routes)
    per = {rid: [] for rid in routes}
    skipped = 0
    for r in rows:
        try:
            lat, lon = float(r["lat"]), float(r["lot"])
        except (KeyError, TypeError, ValueError):
            skipped += 1
            continue
        kind = KIND.get(r.get("code"))
        if not kind:
            continue
        for rid, (cum, off) in L.snap(grid, lat, lon).items():
            per[rid].append([round(cum), kind, (r.get("placeNm") or "").strip()[:30], r.get("code"), str(r.get("crtrDt") or "")[:10]])
    for rid, lst in per.items():
        lst.sort()
        keep = []
        for it in lst:
            if any(k[1] == it[1] and abs(k[0] - it[0]) <= DUP_M for k in keep[-6:]):
                continue
            keep.append(it)
        per[rid] = keep
    out = {rid: {"lengthM": round(length[rid]), "pois": per[rid]} for rid in routes}
    return out, skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", help="받아 둔 지점 목록(JSON). 없으면 API 를 부른다")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    import probe_poi as P
    routes = P.load_routes()
    if a.rows:
        rows = json.load(open(a.rows, encoding="utf-8"))
    else:
        if not P.KEY:
            print("DATA_GO_KR_KEY 가 없다.")
            return 1
        eps = {"fmmtn": P.SERVICES["숲길POI(fmmtnFrtrlPoi)"], "trnsp": P.SERVICES["교통시설POI(trnspPoi)"]}
        rows = []
        for svc, code in P.COV_CODES:
            got = P.fetch_all(eps[svc], code)
            print(f"{code}: {len(got)}건")
            if not got:
                print(f"  {code} 를 받지 못했다. 활용신청이나 응답을 확인해야 한다. 중단한다.")
                return 1
            rows += [{"code": code, "lat": g.get("lat"), "lot": g.get("lot"), "placeNm": g.get("placeNm"), "crtrDt": g.get("crtrDt")} for g in got]
    out, skipped = build(rows, routes)
    day = (datetime.now(timezone.utc) + timedelta(hours=9)).strftime("%Y-%m-%d")
    withp = sum(1 for v in out.values() if v["pois"])
    doc = {"built": day, "source": "한국등산트레킹지원센터 POI 정보 서비스(공공데이터포털)", "near_m": L.NEAR_M, "routes": out}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    print(f"코스 {len(out)}곳 중 지점이 잡힌 코스 {withp}곳 · 좌표 없는 지점 {skipped}건 → {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

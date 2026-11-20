"""산림청 등산로 원자료(mountain.zip 안의 *_geojson.zip)에서 '지점(SPOT)'만 뽑아 data/mountain_spots.json 을 만든다.

- 사용자가 내려받은 원자료를 로컬에서 한 번 돌리는 용도. 원자료 zip 은 저장소에 넣지 않는다.
- 우리 사이트에 있는 산(data/mountains.json)만 남긴다. 좌표는 EPSG:5186(중부원점 TM) → WGS84.
- 자료 기준일은 원자료 설명에 적힌 2016-12-31 이다. 현장 확인 없음을 그대로 쓴다.
usage: python3 scripts/build_mountain_spots.py <원자료 폴더>
"""
import json, sys, zipfile, collections
from pathlib import Path
from pyproj import Transformer

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1])
# 지도에 쓸 종류만(분기점·시종점·기타는 개수가 많아 제외)
KEEP = {"화장실": "toilet", "음수대": "water", "정자": "shelter", "대피소": "shelter", "벤치": "bench",
        "헬기장": "heli", "위험지역": "danger", "조망점": "view", "정상": "peak", "정상부": "peak",
        "이정표": "sign", "주차장": "parking", "야영장": "camp", "안내판또는지도": "info"}
tf = Transformer.from_crs("EPSG:5186", "EPSG:4326", always_xy=True)
mt = {m["id"]: m for m in json.load(open(ROOT / "data/mountains.json", encoding="utf-8"))["mountains"]}
out, kinds = {}, collections.Counter()
for zp in sorted(SRC.glob("*_geojson.zip")):
    try:
        z = zipfile.ZipFile(zp)
    except zipfile.BadZipFile:
        continue
    for n in z.namelist():
        if not n.endswith(".json") or "SPOT" not in n:
            continue
        raw = z.read(n)
        try:
            j = json.loads(raw.decode("utf-8"))
        except ValueError:
            j = json.loads(raw.decode("cp949"))
        for f in j.get("features", []):
            a, g = f.get("attributes", {}), f.get("geometry") or {}
            mid = str(a.get("MNTN_ID") or "").strip()
            k = KEEP.get(str(a.get("MANAGE_SP2") or "").strip())
            if mid not in mt or not k or "x" not in g:
                continue
            lon, lat = tf.transform(g["x"], g["y"])
            if not (124 < lon < 132 and 33 < lat < 39):
                continue
            out.setdefault(mid, []).append([k, round(lat, 5), round(lon, 5)])
            kinds[k] += 1
res = {"note": "산림청 등산로 원자료의 지점(SPOT). 자료 기준일 2016-12-31, 현장 확인 없음.",
       "source": "산림청 등산로 데이터(2016-12-31 최종수정), 국민안전처·지자체·지방산림청 원시자료",
       "kinds": dict(kinds), "mountains": out}
(ROOT / "data/mountain_spots.json").write_text(json.dumps(res, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(len(out), "산", sum(kinds.values()), "지점", dict(kinds))

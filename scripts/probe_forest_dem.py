"""산림청 등산로(2D 선)에 30m 고도 자료(Copernicus DEM)를 입혀 쓸 만한지 확인한다. 로그에만 남긴다.

- 인증키는 환경변수 DURUNUBI_API_KEY 에서만 읽고 어떤 출력에도 찍지 않는다. 파일은 저장하지 않는다.
- 확인하려는 것
  1) 좌표계가 맞는지(EPSG:5186 으로 바꿨을 때 우리나라 안에 떨어지는지)
  2) 등산로를 따라 고도를 읽었을 때 최고점이 산림청이 적은 산 높이와 얼마나 가까운지
  3) 구간 속성(SECTN_*)이 무엇을 담는지(값 몇 개를 그대로 본다)
"""
import io, math, os, re, sys, urllib.parse, zipfile, tempfile
import numpy as np
import requests
import shapefile  # pyshp
import rasterio
from pyproj import Transformer

RAW = os.environ.get("DURUNUBI_API_KEY", "").strip()
if not RAW:
    print("DURUNUBI_API_KEY 가 비어 있습니다."); sys.exit(1)
KEY = urllib.parse.unquote(RAW)
SECRETS = {RAW, KEY, urllib.parse.quote(KEY, safe="")}
def mask(t):
    t = str(t)
    for s in SECRETS:
        if s: t = t.replace(s, "***")
    return t

H = "https://apis.data.go.kr/1400000"
def api(path, **p):
    p.update({"serviceKey": KEY})
    r = requests.get(f"{H}/{path}", params=p, timeout=60, headers={"User-Agent": "calrank-probe"})
    return mask(r.text)
def field(it, k):
    m = re.search(rf"<{k}>(.*?)</{k}>", it, re.S)
    return m.group(1).strip() if m else ""

tf = Transformer.from_crs("EPSG:5186", "EPSG:4326", always_xy=True)
tile_cache = {}
def tile(lat, lon):
    la, lo = math.floor(lat), math.floor(lon)
    name = f"Copernicus_DSM_COG_10_N{la:02d}_00_E{lo:03d}_00_DEM"
    if name not in tile_cache:
        url = f"/vsicurl/https://copernicus-dem-30m.s3.amazonaws.com/{name}/{name}.tif"
        tile_cache[name] = rasterio.open(url)
    return tile_cache[name]

def resample(coords, step=25.0):
    out = [coords[0]]; carry = 0.0
    for a, b in zip(coords, coords[1:]):
        d = math.hypot(b[0] - a[0], b[1] - a[1])
        pos = step - carry
        while pos <= d:
            f = pos / d
            out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)); pos += step
        carry = (carry + d) % step if d else carry
    return out

def height_of(name):
    t = api("service/cultureInfoService2/mntInfoOpenAPI2", searchWrd=name, numOfRows=20, pageNo=1)
    hs = []
    for it in re.findall(r"<item>(.*?)</item>", t, re.S):
        if field(it, "mntiname") == name and field(it, "mntihigh"):
            hs.append((field(it, "mntihigh"), field(it, "mntiadd")))
    return hs

t = api("trailInfoService/getforestspatialdataservice", numOfRows=12, pageNo=1)
items = re.findall(r"<item>(.*?)</item>", t, re.S)
print("대상 산:", len(items))
for it in items:
    nm, url = field(it, "mntnnm"), field(it, "mntnfile")
    try:
        z = requests.get(url, timeout=120, headers={"User-Agent": "calrank-probe"})
        zf = zipfile.ZipFile(io.BytesIO(z.content))
        d = tempfile.mkdtemp()
        zf.extractall(d)
        shp = None
        for root, _, fs in os.walk(d):
            for f in fs:
                if f.lower().endswith(".shp") and "WG_MT_WAY" in f:
                    shp = os.path.join(root, f)
        sf = shapefile.Reader(shp, encoding="cp949")
        recs = sf.records()
        paths = []
        for s in sf.shapes():
            pts = s.points
            parts = list(s.parts) + [len(pts)]
            for a, b in zip(parts, parts[1:]):
                if b - a >= 2: paths.append(pts[a:b])
        allpts = [p for pa in paths for p in pa]
        lon, lat = tf.transform([p[0] for p in allpts[:1]], [p[1] for p in allpts[:1]])
        print(f"== {nm}: 선 {len(paths)}개, 첫 점 위경도 {lat[0]:.4f},{lon[0]:.4f}")
        if recs:
            print("   속성 예:", dict(zip([f[0] for f in sf.fields[1:]], recs[0])))
        elevs = []; gains = []; tot = 0.0
        for pa in paths:
            rs = resample(pa)
            if len(rs) < 3: continue
            lons, lats = tf.transform([p[0] for p in rs], [p[1] for p in rs])
            ds = tile(lats[0], lons[0])
            vals = np.array([v[0] for v in ds.sample(list(zip(lons, lats)))], dtype=float)
            elevs.extend(vals.tolist())
            sm = np.convolve(vals, np.ones(5) / 5, mode="same")
            gains.append(float(np.clip(np.diff(sm), 0, None).sum()))
            tot += 25.0 * (len(rs) - 1)
        e = np.array(elevs)
        hs = height_of(nm)
        print(f"   등산로 길이 약 {tot / 1000:.1f}km, DEM 고도 {e.min():.0f}~{e.max():.0f}m, 오르막 합 {sum(gains):.0f}m, 산림청 산 높이 {hs[:3]}")
    except Exception as ex:
        print("  실패:", nm, mask(type(ex).__name__ + ": " + str(ex))[:200])

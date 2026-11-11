"""산림청 등산로 구간(2D 선)에 Copernicus 30m DEM 고도를 입혀 data/mountains.json 을 만든다 (Actions 전용).

- 인증키는 환경변수 DURUNUBI_API_KEY 에서만 읽고 어떤 출력에도 찍지 않는다. 내려받은 zip 은 저장하지 않는다.
- 구간 선의 방향은 자료마다 제멋대로라서, 항상 '낮은 쪽 끝 → 높은 쪽 끝'으로 맞춰 오르막을 잰다.
- 산림청 속성값(SECTN_UPLN/GNGD/DGDF)은 뜻을 문서로 확인하기 전이라 이름 그대로 저장한다.
"""
import io, json, math, os, re, signal, sys, tempfile, time, urllib.parse, zipfile
from pathlib import Path
os.environ.setdefault("GDAL_HTTP_TIMEOUT", "30")
os.environ.setdefault("GDAL_HTTP_MAX_RETRY", "3")
os.environ.setdefault("GDAL_HTTP_RETRY_DELAY", "2")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")
import numpy as np
import requests
import shapefile
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

OUT = Path(__file__).resolve().parent.parent / "data" / "mountains.json"
H = "https://apis.data.go.kr/1400000"
UA = {"User-Agent": "calrank-mountains"}
tf = Transformer.from_crs("EPSG:5186", "EPSG:4326", always_xy=True)

def get(url, **kw):
    last = None
    for wait in (0, 3, 8, 20):
        time.sleep(wait)
        try:
            return requests.get(url, timeout=120, headers=UA, **kw)
        except Exception as e:
            last = e
    raise last

def api(path, **p):
    p["serviceKey"] = KEY
    return mask(get(f"{H}/{path}", params=p).text)

def field(it, k):
    m = re.search(rf"<{k}>(.*?)</{k}>", it, re.S)
    return m.group(1).strip() if m else ""

# ── 30m DEM: 타일마다 필요한 창만 읽어 쌍선형 보간 ─────────────────────────────
tiles = {}
def tile(la, lo):
    k = (la, lo)
    if k not in tiles:
        n = f"Copernicus_DSM_COG_10_N{la:02d}_00_E{lo:03d}_00_DEM"
        tiles[k] = rasterio.open(f"/vsicurl/https://copernicus-dem-30m.s3.amazonaws.com/{n}/{n}.tif")
    return tiles[k]

def elevations(lons, lats):
    lons = np.asarray(lons); lats = np.asarray(lats)
    out = np.full(lons.shape, np.nan)
    for la in set(np.floor(lats).astype(int)):
        for lo in set(np.floor(lons).astype(int)):
            m = (np.floor(lats).astype(int) == la) & (np.floor(lons).astype(int) == lo)
            if not m.any(): continue
            ds = tile(int(la), int(lo))
            T = ~ds.transform
            cols, rows = T * (lons[m], lats[m])
            cols -= 0.5; rows -= 0.5
            r0, r1 = max(0, int(rows.min()) - 1), min(ds.height, int(rows.max()) + 3)
            c0, c1 = max(0, int(cols.min()) - 1), min(ds.width, int(cols.max()) + 3)
            a = ds.read(1, window=rasterio.windows.Window(c0, r0, c1 - c0, r1 - r0)).astype(float)
            rr = np.clip(rows - r0, 0, a.shape[0] - 1.001); cc = np.clip(cols - c0, 0, a.shape[1] - 1.001)
            i, j = np.floor(rr).astype(int), np.floor(cc).astype(int); fr, fc = rr - i, cc - j
            v = (a[i, j] * (1 - fr) * (1 - fc) + a[i + 1, j] * fr * (1 - fc) + a[i, j + 1] * (1 - fr) * fc + a[i + 1, j + 1] * fr * fc)
            out[m] = v
    return out

def resample(pts, step=25.0):
    out = [pts[0]]; carry = 0.0
    for a, b in zip(pts, pts[1:]):
        d = math.hypot(b[0] - a[0], b[1] - a[1])
        if d == 0: continue
        pos = step - carry
        while pos <= d:
            f = pos / d
            out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)); pos += step
        carry = (carry + d) % step
    return out

def smooth(v, k=5):
    pad = k // 2
    p = np.pad(v, pad, mode="edge")
    return np.convolve(p, np.ones(k) / k, mode="valid")

def dp(pts, tol):
    """Douglas-Peucker (평면 좌표, 미터)."""
    n = len(pts)
    if n < 3: return list(range(n))
    keep = [False] * n; keep[0] = keep[-1] = True
    st = [(0, n - 1)]
    while st:
        a, b = st.pop()
        ax, ay = pts[a]; dx, dy = pts[b][0] - ax, pts[b][1] - ay; L = math.hypot(dx, dy) or 1.0
        mx, mi = 0.0, -1
        for i in range(a + 1, b):
            d = abs((pts[i][0] - ax) * dy - (pts[i][1] - ay) * dx) / L
            if d > mx: mx, mi = d, i
        if mx > tol and mi > 0:
            keep[mi] = True; st += [(a, mi), (mi, b)]
    return [i for i, k in enumerate(keep) if k]


def section_stats(pts):
    rs = resample(pts)
    if len(rs) < 4: return None
    lons, lats = tf.transform([p[0] for p in rs], [p[1] for p in rs])
    e = elevations(lons, lats)
    if np.isnan(e).any(): return None
    s = smooth(e)
    if s[0] > s[-1]: s = s[::-1]; lons = list(lons)[::-1]; lats = list(lats)[::-1]   # 낮은 쪽 → 높은 쪽
    d = np.diff(s)
    step = 25.0
    g = d / step * 100
    gain = float(np.clip(d, 0, None).sum()); loss = float(np.clip(-d, 0, None).sum())
    L = step * (len(s) - 1)
    idx = dp(pts, 8.0)
    ll = tf.transform([pts[i][0] for i in idx], [pts[i][1] for i in idx])
    path = [[round(float(la), 5), round(float(lo), 5)] for lo, la in zip(ll[0], ll[1])]
    return {"path": path, "lenM": round(L), "startM": round(float(s[0])), "endM": round(float(s[-1])), "gainM": round(gain), "lossM": round(loss),
            "meanGrade": round(float((s[-1] - s[0]) / L * 100), 1), "maxGrade": round(float(np.abs(g).max()), 1),
            "steepKm": round(float((np.abs(g) >= 12).sum() * step / 1000), 2),
            "lat": round(float(lats[0]), 5), "lon": round(float(lons[0]), 5)}

def official_heights(name):
    t = api("service/cultureInfoService2/mntInfoOpenAPI2", searchWrd=name, numOfRows=50, pageNo=1)
    res = []
    for it in re.findall(r"<item>(.*?)</item>", t, re.S):
        if field(it, "mntiname") == name:
            try: res.append((float(field(it, "mntihigh")), field(it, "mntiadd")))
            except ValueError: pass
    return res

def main():
    items = []
    page = 1
    while True:
        t = api("trailInfoService/getforestspatialdataservice", numOfRows=100, pageNo=page)
        its = re.findall(r"<item>(.*?)</item>", t, re.S)
        items += its
        total = int((re.search(r"<totalCount>(\d+)", t) or [0, 0])[1])
        if not its or len(items) >= total: break
        page += 1
    print("산 수:", len(items))
    limit = int(os.environ.get("LIMIT", "0") or 0)
    if limit: items = items[:limit]
    # ONLY 가 있으면 그 이름의 산만 다시 받아 기존 파일에 합친다(실패한 산 재시도용).
    only = [x.strip() for x in os.environ.get("ONLY", "").split(",") if x.strip()]
    prev = []
    if only:
        items = [it for it in items if field(it, "mntnnm") in only]
        prev = [m for m in json.loads(OUT.read_text(encoding="utf-8"))["mountains"] if m["name"] not in only]
        print("다시 받을 산:", len(items))
    out, fails, cmp_ = [], [], []
    for n, it in enumerate(items, 1):
        nm, url, info = field(it, "mntnnm"), field(it, "mntnfile"), field(it, "mntninfourl")
        signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TimeoutError("산 하나가 4분을 넘김")))
        signal.alarm(240)
        try:
            z = get(url)
            if z.content[:2] != b"PK":
                print("  zip 아님:", nm, z.status_code, z.headers.get("content-type"), len(z.content), "bytes, 앞부분:", mask(z.content[:120].decode("utf-8", "ignore")).replace("\n", " "))
            zf = zipfile.ZipFile(io.BytesIO(z.content))
            d = tempfile.mkdtemp(); zf.extractall(d)
            shp = next((os.path.join(r, f) for r, _, fs in os.walk(d) for f in fs if f.lower().endswith(".shp") and "WG_MT_WAY" in f), None)
            if not shp: fails.append((nm, "WG_MT_WAY 없음")); continue
            sf = shapefile.Reader(shp, encoding="cp949")
            fn = [f[0] for f in sf.fields[1:]]
            secs = []
            for s, rec in zip(sf.shapes(), sf.records()):
                r = dict(zip(fn, rec))
                pts = s.points; parts = list(s.parts) + [len(pts)]
                for a, b in zip(parts, parts[1:]):
                    if b - a < 2: continue
                    st = section_stats(pts[a:b])
                    if not st: continue
                    st.update({"dstn": r.get("SECTN_DSTN"), "upln": r.get("SECTN_UPLN"), "gngd": r.get("SECTN_GNGD"), "dgdf": r.get("SECTN_DGDF")})
                    secs.append(st); break
            if not secs: fails.append((nm, "구간 없음")); continue
            hi = max(s["endM"] for s in secs)
            code = field(it, "mntnfile").rsplit("/", 1)[-1].replace(".zip", "")
            off = official_heights(nm)
            best = min(off, key=lambda x: abs(x[0] - hi)) if off else None
            if best and abs(best[0] - hi) <= 25:
                height, region = best
                cmp_.append(hi - height)
            else:
                height, region = None, ""
            out.append({"id": code, "name": nm, "info": info, "officialHeightM": height, "region": region.strip(),
                        "demMaxM": hi, "sections": secs})
        except BaseException as e:
            if isinstance(e, KeyboardInterrupt): raise
            fails.append((nm, mask(type(e).__name__ + ": " + str(e))[:120]))
            tiles.clear()
        finally:
            signal.alarm(0)
        if n % 25 == 0: print(f"  {n}/{len(items)} 처리, 실린 {len(out)}, 실패 {len(fails)}", flush=True)
        time.sleep(0.4)
    print("실린 산:", len(out), "실패:", len(fails))
    for f in fails[:25]: print("  실패", f)
    if cmp_:
        a = np.array(cmp_)
        print(f"산림청 높이와 비교 {len(a)}곳: DEM 최고점 − 산림청 높이 중앙값 {np.median(a):.1f}m, 절대차 중앙값 {np.median(np.abs(a)):.1f}m, 90% {np.percentile(np.abs(a), 90):.1f}m")
    # 속성 값의 뜻을 가늠하는 점검 (문서 확인 전이라 숫자만 본다)
    allsec = [s for m in out for s in m["sections"] if s.get("upln") is not None and s.get("gngd") is not None]
    if allsec:
        for lv in sorted({str(s["dgdf"]) for s in allsec}):
            g = [s for s in allsec if str(s["dgdf"]) == lv]
            print(f"  DGDF={lv}: {len(g)}구간, 평균경사 중앙값 {np.median([abs(s['meanGrade']) for s in g]):.1f}%, 구간길이 중앙값 {np.median([s['lenM'] for s in g]):.0f}m")
        up = np.array([s["upln"] for s in allsec], float); dn = np.array([s["gngd"] for s in allsec], float); L = np.array([s["lenM"] for s in allsec], float)
        print(f"  UPLN > GNGD 인 구간 비율 {np.mean(up > dn) * 100:.0f}%, UPLN 상관(길이) {np.corrcoef(up, L)[0, 1]:.2f}, (오르막) {np.corrcoef(up, [s['gainM'] for s in allsec])[0, 1]:.2f}")
    if only:
        out = prev + out
    if len(out) < 20:
        print("실린 산이 너무 적어 파일을 바꾸지 않습니다."); sys.exit(1)
    out.sort(key=lambda m: m["name"])
    OUT.write_text(json.dumps({"note": "산림청 등산로 구간(2D) + Copernicus DEM 30m 고도. 구간은 낮은 쪽→높은 쪽으로 정렬.", "fetched": time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600)), "mountains": out}, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

main()

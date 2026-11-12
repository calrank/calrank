"""고도가 비어 있는 둘레길 코스(국가숲길 코스 GPX 는 고도 칸이 전부 0)에 Copernicus 30m DEM 고도를 입힌다 (Actions 전용).

- 입력: data/forest_trails.json 에서 needsDem 인 코스, data/forest_trails_geo.json 의 25m 간격 위경도.
- 고도는 5점 이동평균(약 100m)으로 다듬는다. 30m DSM 은 나무 높이가 섞여 있어, 페이지에 그 사실을 적는다.
- 인증키를 쓰지 않는다. 내려받은 타일은 저장하지 않는다(원격 읽기만 한다).
"""
import json, math, os, signal, sys, time
from pathlib import Path
os.environ.setdefault("GDAL_HTTP_TIMEOUT", "30")
os.environ.setdefault("GDAL_HTTP_MAX_RETRY", "3")
os.environ.setdefault("GDAL_HTTP_RETRY_DELAY", "2")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "forest_trails.json"
GEO = ROOT / "data" / "forest_trails_geo.json"
FAKE = os.environ.get("FAKE_DEM") == "1"          # 흐름 시험용(가짜 고도). 커밋하지 않는다.
tiles = {}


def tile(la, lo):
    import rasterio
    k = (la, lo)
    if k not in tiles:
        n = f"Copernicus_DSM_COG_10_N{la:02d}_00_E{lo:03d}_00_DEM"
        tiles[k] = rasterio.open(f"/vsicurl/https://copernicus-dem-30m.s3.amazonaws.com/{n}/{n}.tif")
    return tiles[k]


def elevations(lons, lats):
    lons = np.asarray(lons); lats = np.asarray(lats)
    if FAKE:
        return 200 + 80 * np.sin(np.arange(len(lons)) / 40.0)
    import rasterio
    out = np.full(lons.shape, np.nan)
    for la in set(np.floor(lats).astype(int)):
        for lo in set(np.floor(lons).astype(int)):
            m = (np.floor(lats).astype(int) == la) & (np.floor(lons).astype(int) == lo)
            if not m.any(): continue
            ds = tile(int(la), int(lo)); T = ~ds.transform
            cols, rows = T * (lons[m], lats[m]); cols -= 0.5; rows -= 0.5
            r0, r1 = max(0, int(rows.min()) - 1), min(ds.height, int(rows.max()) + 3)
            c0, c1 = max(0, int(cols.min()) - 1), min(ds.width, int(cols.max()) + 3)
            a = ds.read(1, window=rasterio.windows.Window(c0, r0, c1 - c0, r1 - r0)).astype(float)
            rr = np.clip(rows - r0, 0, a.shape[0] - 1.001); cc = np.clip(cols - c0, 0, a.shape[1] - 1.001)
            i, j = np.floor(rr).astype(int), np.floor(cc).astype(int); fr, fc = rr - i, cc - j
            out[m] = (a[i, j] * (1 - fr) * (1 - fc) + a[i + 1, j] * fr * (1 - fc) + a[i, j + 1] * (1 - fr) * fc + a[i + 1, j + 1] * fr * fc)
    return out


def smooth(v, k=5):
    pad = k // 2
    return np.convolve(np.pad(v, pad, mode="edge"), np.ones(k) / k, mode="valid")


def hav(a, b):
    R = 6371000.0; r = math.pi / 180
    dla = (b[0] - a[0]) * r; dlo = (b[1] - a[1]) * r
    x = math.sin(dla / 2) ** 2 + math.cos(a[0] * r) * math.cos(b[0] * r) * math.sin(dlo / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))


class Timeout(Exception): pass
def _alarm(*_): raise Timeout()
signal.signal(signal.SIGALRM, _alarm)


def main():
    doc = json.loads(DATA.read_text(encoding="utf-8")); geo = json.loads(GEO.read_text(encoding="utf-8"))
    todo = [c for c in doc["courses"] if c.get("needsDem") and c["id"] in geo]
    print("고도를 채울 코스:", len(todo))
    done, fails = 0, []
    for c in todo:
        pts = geo[c["id"]]
        try:
            signal.alarm(240)
            z = elevations([p[1] for p in pts], [p[0] for p in pts])
            signal.alarm(0)
            bad = np.isnan(z) | (z < -50) | (z > 3000)
            if bad.mean() > 0.05:
                fails.append((c["name"], f"고도 없는 점 {bad.mean():.0%}")); continue
            if bad.any():
                idx = np.arange(len(z)); z[bad] = np.interp(idx[bad], idx[~bad], z[~bad])
            zs = smooth(z, 5)
            cum = [0.0]
            for a, b in zip(pts, pts[1:]): cum.append(cum[-1] + hav(a, b))
            stride = max(1, math.ceil(len(zs) / 300))
            prof = [[round(cum[i]), round(float(zs[i]), 1)] for i in range(0, len(zs), stride)]
            if prof[-1][0] != round(cum[-1]): prof.append([round(cum[-1]), round(float(zs[-1]), 1)])
            gain = float(sum(max(0.0, zs[i] - zs[i - 1]) for i in range(1, len(zs))))
            raw = float(sum(max(0.0, z[i] - z[i - 1]) for i in range(1, len(z))))
            c["profile"] = prof; c["needsDem"] = False
            c["quality"].update({"rawGainM": round(raw), "smoothGainM": round(gain), "points": len(pts), "spacingM": 25.0})
            c["elevSource"] = "Copernicus DEM GLO-30"
            done += 1
        except Exception as e:
            signal.alarm(0); fails.append((c["name"], type(e).__name__ + ": " + str(e)[:100]))
        if done % 10 == 0: print(f"  {done}/{len(todo)}", flush=True)
    print("채움:", done, "실패:", len(fails))
    for f in fails[:20]: print("  실패", f)
    if FAKE:
        print("가짜 고도 시험이라 저장하지 않습니다."); return
    if done == 0 and todo:
        print("하나도 채우지 못해 파일을 바꾸지 않습니다."); sys.exit(1)
    DATA.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


main()

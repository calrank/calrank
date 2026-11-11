"""산림청 '산림공간정보' API 가 주는 압축파일에 등산로 좌표·고도가 들어 있는지 확인한다.

- 인증키는 환경변수 DURUNUBI_API_KEY 에서만 읽고 어떤 출력에도 찍지 않는다.
- 파일은 저장소에 저장하지 않는다(실행 중 임시 폴더에서만 연다). 확인하려는 것:
  1) 건수와 산 이름  2) 압축파일 안에 어떤 파일이 있는지  3) 도형 종류, 좌표계 파일, 고도(Z) 유무
"""
import io, os, re, struct, sys, urllib.parse, zipfile
import requests

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

URL = "https://apis.data.go.kr/1400000/trailInfoService/getforestspatialdataservice"
r = requests.get(URL, params={"serviceKey": KEY, "numOfRows": 10, "pageNo": 1}, timeout=60, headers={"User-Agent": "calrank-probe"})
t = mask(r.text)
print("상태", r.status_code, "전체 건수", (re.search(r"<totalCount>(\d+)", t) or [None, "?"])[1])
items = re.findall(r"<item>(.*?)</item>", t, re.S)
rows = []
for it in items:
    g = lambda k: (re.search(rf"<{k}>(.*?)</{k}>", it, re.S) or [None, ""])[1].strip()
    rows.append({"nm": g("mntnnm"), "file": g("mntnfile"), "info": g("mntninfourl")})
for x in rows[:10]:
    print(" -", x["nm"], x["file"])

for x in rows[:3]:
    if not x["file"]:
        continue
    print("== 내려받기:", x["nm"], x["file"])
    try:
        z = requests.get(x["file"], timeout=120, headers={"User-Agent": "calrank-probe"})
    except Exception as e:
        print("  실패:", mask(e)); continue
    print("  상태", z.status_code, "크기", len(z.content), "bytes", z.headers.get("content-type"))
    try:
        zf = zipfile.ZipFile(io.BytesIO(z.content))
    except Exception as e:
        print("  zip 아님:", mask(e)); continue
    for i in zf.infolist()[:30]:
        print("   ", i.filename, i.file_size)
    for i in zf.infolist():
        if i.filename.lower().endswith(".shp"):
            b = zf.read(i)
            stype = struct.unpack("<i", b[32:36])[0]
            names = {1: "Point", 3: "PolyLine", 5: "Polygon", 8: "MultiPoint", 11: "PointZ", 13: "PolyLineZ", 15: "PolygonZ", 18: "MultiPointZ", 21: "PointM", 23: "PolyLineM", 25: "PolygonM"}
            xmin, ymin, xmax, ymax = struct.unpack("<4d", b[36:68])
            zmin, zmax = struct.unpack("<2d", b[68:84])
            print("   ", i.filename, "도형", names.get(stype, stype), "범위", round(xmin, 4), round(ymin, 4), round(xmax, 4), round(ymax, 4), "Z", round(zmin, 1), round(zmax, 1))
        if i.filename.lower().endswith(".prj"):
            print("    좌표계:", zf.read(i).decode("utf-8", "ignore")[:160])
        if i.filename.lower().endswith(".dbf"):
            b = zf.read(i)
            n = struct.unpack("<I", b[4:8])[0]; hl = struct.unpack("<H", b[8:10])[0]
            fields = []
            p = 32
            while p < hl - 1 and b[p] != 0x0D:
                fields.append(b[p:p+11].split(b"\0")[0].decode("ascii", "ignore")); p += 32
            print("    속성 건수", n, "필드", fields)

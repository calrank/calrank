#!/usr/bin/env python3
"""산림청 산정보 서비스(국내 소재 3,368개 설명)에서 산 이름·높이·소재지를 받고,
소재지로 좌표를 찾아 data/mountain_names.json 을 만든다.

왜 필요한가: 트레일루트 코스의 약 140개는 근처에 등산로 자료(data/mountains.json)가
없어 산 이름이 제목에 못 들어간다. 사람들은 "○○산"으로 검색하므로 이름과 좌표만이라도
있으면 코스와 이어 줄 수 있다.

인증키는 환경변수 DATA_GO_KR_KEY 로만 받고 출력하지 않는다.
이 API는 일반 인터넷에서만 열려 있어 GitHub Actions 에서 돌린다.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data/mountain_names.json"
CACHE = ROOT / "data/mountain_geocache.json"
KEY = os.environ.get("DATA_GO_KR_KEY", "").strip()
# 시크릿에 인코딩된 키(%3D%3D 포함)를 넣어 둔 경우가 많다. 한 번 풀고 다시 인코딩해서 이중 인코딩을 막는다.
KEY = urllib.parse.unquote(KEY)
LIMIT = int(os.environ.get("LIMIT") or 0)
SKIP_GEO = os.environ.get("SKIP_GEO") == "1"

BASE = "https://apis.data.go.kr/1400000/service/cultureInfoService2"
OPS = ["mntInfoOpenAPI2", "mntInfoOpenAPI", "mntnInfoOpenAPI2"]
UA = "calrank-mountain-names/1.0 (https://calrank.kr)"


def get(url, timeout=40):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def safe(url):
    # 로그에 키가 나가지 않게 한다 (Actions 가 시크릿을 가리지만 한 번 더).
    return url.replace(urllib.parse.quote(KEY, safe=""), "***").replace(KEY, "***")


def items_of(xml_text):
    root = ET.fromstring(xml_text)
    code = (root.findtext(".//resultCode") or "").strip()
    msg = (root.findtext(".//resultMsg") or "").strip()
    total = root.findtext(".//totalCount")
    rows = []
    for it in root.iter("item"):
        rows.append({c.tag: (c.text or "").strip() for c in it})
    return code, msg, int(total) if total and total.isdigit() else None, rows


def fetch_list():
    q = urllib.parse.quote(KEY, safe="")
    for op in OPS:
        url = f"{BASE}/{op}?serviceKey={q}&pageNo=1&numOfRows=100"
        try:
            text = get(url)
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", "replace")[:300]
            except Exception:  # noqa: BLE001
                pass
            print(f"[{op}] HTTP {e.code}: {safe(body)}")
            continue
        except Exception as e:  # noqa: BLE001
            print(f"[{op}] 요청 실패: {safe(str(e))}")
            continue
        try:
            code, msg, total, rows = items_of(text)
        except ET.ParseError:
            print(f"[{op}] XML 이 아님: {safe(text[:200])}")
            continue
        print(f"[{op}] code={code} msg={msg} total={total} rows={len(rows)}")
        if not rows:
            continue
        print("첫 항목 필드:", {k: v[:30] for k, v in rows[0].items()})
        allrows = list(rows)
        page = 2
        while total and len(allrows) < total:
            if LIMIT and len(allrows) >= LIMIT:
                break
            u = f"{BASE}/{op}?serviceKey={q}&pageNo={page}&numOfRows=100"
            try:
                _, _, _, more = items_of(get(u))
            except Exception as e:  # noqa: BLE001
                print(f"  {page}쪽 실패: {safe(str(e))}")
                break
            if not more:
                break
            allrows += more
            page += 1
            time.sleep(0.2)
        return op, allrows
    return None, []


def pick(row, pats):
    for k, v in row.items():
        lk = k.lower()
        if v and any(re.search(p, lk) for p in pats):
            return v
    return ""


def normalize(rows):
    out, seen = [], set()
    for r in rows:
        name = pick(r, [r"nm$", r"name$", r"mntnnm", r"mntiname"])
        hght = pick(r, [r"hght", r"high"])
        addr = pick(r, [r"add", r"plc", r"loc", r"poflc"])
        mid = pick(r, [r"mntnid", r"listno", r"^id$"])
        if not name:
            continue
        key = (name, addr)
        if key in seen:
            continue
        seen.add(key)
        try:
            h = float(re.sub(r"[^0-9.]", "", hght)) if hght else None
        except ValueError:
            h = None
        out.append({"id": mid, "name": name, "heightM": h, "addr": addr})
    return out


def geocode(name, addr, cache):
    """Nominatim. 1초에 1건. 소재지의 시·군까지만 붙여 찾고, 안 되면 이름만으로 찾는다."""
    parts = addr.replace(",", " ").split()
    area = " ".join(parts[:2])
    for q in ([f"{name} {area}"] if area else []) + [name]:
        if q in cache:
            hit = cache[q]
        else:
            u = ("https://nominatim.openstreetmap.org/search?format=jsonv2&limit=3&countrycodes=kr"
                 "&accept-language=ko&q=" + urllib.parse.quote(q))
            try:
                hit = json.loads(get(u))
            except Exception as e:  # noqa: BLE001
                print(f"  지오코딩 실패 {q}: {e}")
                hit = []
            cache[q] = hit
            time.sleep(1.1)
        for h in hit:
            try:
                lat, lng = float(h["lat"]), float(h["lon"])
            except (KeyError, ValueError):
                continue
            if not (33 <= lat <= 39 and 124 <= lng <= 132):
                continue
            # 산·봉우리·능선 종류만 받는다 (같은 이름의 식당·역을 거른다).
            if h.get("category") == "natural" or h.get("class") == "natural":
                return [round(lat, 5), round(lng, 5)]
    return None


def main():
    if not KEY:
        print("DATA_GO_KR_KEY 가 없습니다.")
        return 1
    op, rows = fetch_list()
    if not rows:
        print("목록을 받지 못했습니다. 위 로그의 code/msg 를 확인하세요.")
        return 2
    mts = normalize(rows)
    print(f"{op}: 원자료 {len(rows)}건 → 산 {len(mts)}개")
    if LIMIT:
        mts = mts[:LIMIT]
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    if not SKIP_GEO:
        ok = 0
        for i, m in enumerate(mts, 1):
            m["latlng"] = geocode(m["name"], m["addr"], cache)
            ok += bool(m["latlng"])
            if i % 100 == 0:
                print(f"  {i}/{len(mts)} 좌표 {ok}개")
                CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        print(f"좌표를 찾은 산 {ok}/{len(mts)}")
    OUT.write_text(json.dumps({
        "note": "산림청_산정보 서비스(공공데이터포털). 좌표는 OpenStreetMap Nominatim 으로 찾은 근사값이다.",
        "mountains": mts,
    }, ensure_ascii=False, indent=0), encoding="utf-8")
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())

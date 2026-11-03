#!/usr/bin/env python3
"""대회가 열리는 날, 그 지역이 보통 어떤 날씨였는지를 붙인다.

왜 이걸 하나
-------------
다음 회차 참가자가 실제로 궁금해하는 건 "그날 몇 도였나"다. 뭘 입을지와
어떤 페이스로 갈지가 거기서 갈린다. 그런데 이건 남의 후기를 베끼지 않고도
공식 자료로 답할 수 있다 — 기상청 종관기상관측(ASOS) 일자료가 1904년부터
있다. 우리가 계산한 값이라 중복 문제도 없고, 해마다 한 점씩 쌓인다.

쓰는 것
-------
1) 기상청 지상기상관측 지점정보 조회서비스  → 지점번호·이름·위경도
2) 기상청 지상(종관, ASOS) 일자료 조회서비스 → 과거 일별 기온·강수

둘 다 공공데이터포털이고 DATA_GO_KR_KEY 하나로 쓰지만, 서비스마다 활용신청이
따로다. 권한이 없으면 아래에서 어느 서비스가 막혔는지 분명히 찍어 준다.

캐시
----
원자료를 그대로 들고 있으면 파일이 커진다. 받자마자 (지점, 월일) 단위
평년값으로 접어서 data/race_climate.json 에 둔다. 한 번 만들어 두면 다음
실행은 빠지는 날짜만 더 받는다.

쓰임:
  python scripts/fetch_race_climate.py --selftest   # 권한과 응답만 확인
  python scripts/fetch_race_climate.py              # events.json 에 붙인다
"""

import argparse
import datetime as dt
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVENTS = ROOT / "events.json"
DATA_DIR = ROOT / "data"
CLIMATE = DATA_DIR / "race_climate.json"
STATIONS = DATA_DIR / "asos_stations.json"

HOSTS = ["https://apis.data.go.kr", "http://apis.data.go.kr"]
# 일자료 서비스 기본 주소는 공공데이터포털 메타데이터에서 확인했다
# (contentUrl: https://apis.data.go.kr/1360000/AsosDalyInfoService)
PATH_DAILY = "/1360000/AsosDalyInfoService/getWthrDataList"

# 지점 목록은 경로가 공개 메타데이터에 없다. 추측으로 박으면 대회마다 엉뚱한
# 지역 기온이 조용히 들어가므로, 되는 경로를 차례로 눌러 보고 안 되면 멈춘다.
# 틀린 날씨를 넣느니 안 넣는 쪽이 낫다.
# 맞는 서비스는 "기상청_지점정보(기상관측, 특보구역) 조회서비스" 이고 기본 주소는
# apis.data.go.kr/1360000/WethrBasicInfoService 다(포털 메타데이터에서 확인).
# 그 안의 '지상관측지점정보조회' 가 stnId·stnKo·lat·lon·ht 를 준다.
# 다만 오퍼레이션 영문명이 공개 명세에 없어서, 되는 이름을 눌러 본다.
PATH_STN_CANDIDATES = [
    "/1360000/WethrBasicInfoService/getWeatherStnList",
    "/1360000/WethrBasicInfoService/getStnInfo",
    "/1360000/WethrBasicInfoService/getSfcStnInfo",
    "/1360000/WethrBasicInfoService/getGrndStnInfo",
    "/1360000/WethrBasicInfoService/getWeatherStnInfo",
    "/1360000/SfcInfoService/getStnInfo",
]
# 지상관측지점정보조회는 국가 코드가 필수다(대한민국 2180).
STN_EXTRA = {"cc": "2180"}
# 기상청 API허브. 여기에 전체 지상관측 지점표가 있다(지점번호·이름·위경도·고도).
# 공공데이터포털 키와 다른 키라서 KMA_APIHUB_KEY 가 있을 때만 쓴다.
#
# 경로는 stn_inf.php 다. 처음에 바깥 문서를 보고 kma_stnlist.php 로 적었는데,
# API허브 '활용신청 현황'에 찍힌 실제 경로가 /url/stn_inf.php 였다.
APIHUB_BASE = "https://apihub.kma.go.kr/api/typ01/url/"
APIHUB_STN_PATHS = ["stn_inf.php", "kma_stnlist.php"]

# 일자료 서비스가 열려 있는지 볼 때 쓰는 지점 후보. 맞는 번호를 모르는 상태라
# 몇 개를 눌러 본다 — 하나라도 자료가 오면 서비스는 열려 있는 것이다.
PROBE_STATIONS = [108, 112, 159, 143, 156, 101, 105, 133]

YEARS_BACK = 10          # 최근 몇 해를 평년으로 볼지
WINDOW = 3               # 대회 날 ±며칠까지 같이 볼지 (그날 하루는 표본이 너무 적다)
MIN_YEARS = 4            # 이보다 적게 모이면 말하지 않는다


def http_bytes(url, tries=3, timeout=20):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "calrank/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:                      # noqa: BLE001
            last = e
            time.sleep(1.0 * (i + 1))
    raise RuntimeError("요청 실패: %s" % last)


def http_get(url, tries=3, timeout=20):
    return http_bytes(url, tries, timeout).decode("utf-8", "replace")


def http_get_korean(url, tries=3, timeout=20):
    """API허브 typ01 평문은 EUC-KR 로 온다.

    UTF-8 로 읽으면 지점 이름이 통째로 깨지고, 한글을 못 찾은 줄이 버려져
    105곳이 19곳으로 줄어든다. 실제로 그렇게 됐었다.
    """
    raw = http_bytes(url, tries, timeout)
    for enc in ("euc-kr", "cp949", "utf-8"):
        try:
            got = raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
        if any("가" <= c <= "힣" for c in got):
            return got
    return raw.decode("utf-8", "replace")


def call(base_path, params, key):
    """공공데이터포털 호출. (items, 오류문구) 를 돌려준다."""
    q = dict(params)
    q["serviceKey"] = key
    q.setdefault("dataType", "JSON")
    qs = urllib.parse.urlencode(q)
    last_err = None
    for host in HOSTS:
        try:
            raw = http_get(host + base_path + "?" + qs)
        except Exception as e:                      # noqa: BLE001
            last_err = str(e)
            continue
        if raw.lstrip().startswith("<"):
            for tag in ("returnAuthMsg", "errMsg", "returnReasonCode", "resultMsg"):
                s = raw.find("<%s>" % tag)
                if s >= 0:
                    e = raw.find("</%s>" % tag, s)
                    return None, raw[s + len(tag) + 2:e].strip()
            return None, raw[:160].replace("\n", " ")
        try:
            d = json.loads(raw)
        except Exception:                           # noqa: BLE001
            return None, raw[:160].replace("\n", " ")
        head = d.get("response", {}).get("header", {})
        code = head.get("resultCode")
        if code not in ("00", "0"):
            return None, "%s %s" % (code, head.get("resultMsg", ""))
        body = d.get("response", {}).get("body", {}) or {}
        items = (body.get("items") or {}).get("item", [])
        if isinstance(items, dict):
            items = [items]
        return items, None
    return None, last_err or "어느 주소로도 닿지 못했습니다"


# ── 지점 ────────────────────────────────────────────────────────────

def load_stations(key, force=False):
    """지점번호·이름·위경도. 한 번 받아 두면 파일로 재사용한다."""
    if STATIONS.exists() and not force:
        try:
            got = json.loads(STATIONS.read_text(encoding="utf-8"))
        except Exception:                           # noqa: BLE001
            got = []
        # 성한 캐시만 다시 쓴다. 전에 인코딩이 깨져 105곳이 19곳으로 줄고
        # 이름이 뭉개진 채 저장된 적이 있다. 그대로 쓰면 대회마다 엉뚱한
        # 관측소가 붙는다.
        ok = (len(got) >= 50
              and sum(1 for x in got
                      if any("가" <= c <= "힣" for c in x.get("name", "")))
                  >= len(got) * 0.9)
        if ok:
            print("[climate] 지점 %d곳 (캐시)" % len(got))
            return got
        if got:
            print("[climate] 캐시가 성하지 않습니다(%d곳). 다시 받습니다." % len(got))

    # 1) API허브 키가 있으면 그쪽이 가장 깔끔하다 (한 번에 전체 지점표)
    hub = os.environ.get("KMA_APIHUB_KEY", "").strip()
    if hub:
        got = _stations_from_apihub(hub)
        if got:
            _save_stations(got)
            return got
        print("[climate] API허브 지점표를 못 받았습니다. 포털 쪽으로 넘어갑니다.")

    # 2) 공공데이터포털의 지점정보 서비스. 경로가 공개돼 있지 않아 차례로 눌러 본다.
    out, used, last_err = [], None, None
    for path in PATH_STN_CANDIDATES:
        probe, err = call(path, dict(STN_EXTRA, pageNo="1", numOfRows="10"), key)
        if err:
            last_err = "%s → %s" % (path, err)
            continue
        if probe:
            used = path
            print("[climate] 지점정보 경로: %s" % path)
            break
    if not used:
        print("[climate] 지점정보를 받을 경로를 찾지 못했습니다. 마지막 응답: %s"
              % last_err, file=sys.stderr)
        return None

    page = 1
    while page <= 12:
        items, err = call(used, dict(STN_EXTRA, pageNo=str(page), numOfRows="100"), key)
        if err:
            print("[climate] 지점정보 서비스 — %s" % err, file=sys.stderr)
            return None
        if not items:
            break
        for it in items:
            try:
                raw_id = int(str(it.get("stnId") or it.get("stnID") or "").strip())
                lat = float(it.get("lat"))
                lon = float(it.get("lon"))
            except (TypeError, ValueError):
                continue
            # 지점정보는 WMO 번호(서울 47108)로 오고, 일자료는 기상청 번호(108)를
            # 받는다. 그대로 넘기면 전부 빈 응답이 온다. 뒤 세 자리를 쓴다.
            sid = raw_id % 1000 if raw_id >= 1000 else raw_id
            name = (it.get("stnNm") or it.get("stnKo") or "").strip()
            if not name:
                continue
            out.append({"id": sid, "name": name, "lat": lat, "lon": lon})
        page += 1
        time.sleep(0.1)

    # 같은 지점이 이력별로 여러 줄 올 수 있다. 번호 하나만 남긴다.
    uniq = {}
    for s in out:
        uniq[s["id"]] = s
    out = sorted(uniq.values(), key=lambda s: s["id"])
    if out:
        _save_stations(out)
    return out or None


def _save_stations(rows):
    DATA_DIR.mkdir(exist_ok=True)
    STATIONS.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n",
                        encoding="utf-8")
    print("[climate] 지점 %d곳 받음" % len(rows))


def _stations_from_apihub(auth):
    """API허브의 지상관측 지점표. 공백으로 칸을 나눈 평문으로 온다."""
    # inf=SFC 가 지상(종관) 지점이다. AWS·북한·자외선은 각각 AWS·NKO·UV 로,
    # 빠뜨리면 엉뚱한 지점 묶음이 온다. (API허브 '지상관측 지점정보 조회' 명세)
    qs = urllib.parse.urlencode(
        {"inf": "SFC", "stn": "0", "help": "0", "authKey": auth})
    raw = None
    for path in APIHUB_STN_PATHS:
        try:
            got = http_get_korean(APIHUB_BASE + path + "?" + qs)
        except Exception as e:                      # noqa: BLE001
            print("[climate] API허브 %s — %s" % (path, e))
            continue
        # 인증 실패나 빈 응답은 본문 길이로 가려낸다
        if got and len(got) > 400 and "#" in got:
            print("[climate] API허브 지점표 경로: %s" % path)
            raw = got
            break
        print("[climate] API허브 %s — 응답이 비었거나 짧습니다(%d자)"
              % (path, len(got or "")))
    if raw is None:
        return None
    rows = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        f = line.split()
        if len(f) < 4:
            continue
        try:
            sid = int(f[0]); lon = float(f[1]); lat = float(f[2])
        except ValueError:
            continue
        # 이름은 뒤쪽 칸에 한글로 온다. 숫자가 아닌 첫 한글 칸을 집는다.
        name = next((x for x in f[3:] if any("가" <= c <= "힣" for c in x)), "")
        if not name or not (32 < lat < 44 and 124 < lon < 132):
            continue
        rows.append({"id": sid, "name": name, "lat": lat, "lon": lon})
    uniq = {}
    for r in rows:
        uniq[r["id"]] = r
    return sorted(uniq.values(), key=lambda r: r["id"]) or None


def haversine(a_lat, a_lon, b_lat, b_lon):
    r = 6371.0
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp = p2 - p1
    dl = math.radians(b_lon - a_lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def nearest(stations, lat, lon):
    best, bd = None, 1e9
    for s in stations:
        d = haversine(lat, lon, s["lat"], s["lon"])
        if d < bd:
            bd, best = d, s
    return best, bd


# ── 과거 자료 ───────────────────────────────────────────────────────

def fetch_days(key, stn, start, end):
    """한 지점의 기간 일자료. {YYYYMMDD: {...}}"""
    got = {}
    page = 1
    while page <= 6:
        items, err = call(PATH_DAILY, {
            "dataCd": "ASOS", "dateCd": "DAY",
            "startDt": start, "endDt": end, "stnIds": str(stn),
            "pageNo": str(page), "numOfRows": "720",
        }, key)
        if err:
            return got, err
        if not items:
            break
        for it in items:
            tm = (it.get("tm") or "").replace("-", "")
            if len(tm) != 8:
                continue
            def num(k):
                v = str(it.get(k) or "").strip()
                try:
                    return float(v)
                except ValueError:
                    return None
            got[tm] = {"avg": num("avgTa"), "min": num("minTa"),
                       "max": num("maxTa"), "rn": num("sumRn") or 0.0}
        if len(items) < 720:
            break
        page += 1
        time.sleep(0.12)
    return got, None


def summarize(days, target_md, years):
    """(월일) 둘레 며칠을 해마다 모아 평년값으로 접는다."""
    per_year = defaultdict(list)
    mm, dd = target_md
    for y in years:
        try:
            base = dt.date(y, mm, dd)
        except ValueError:          # 2월 29일
            continue
        for off in range(-WINDOW, WINDOW + 1):
            d = base + dt.timedelta(days=off)
            row = days.get(d.strftime("%Y%m%d"))
            if row and row.get("min") is not None:
                per_year[y].append(row)
    if len(per_year) < MIN_YEARS:
        return None

    mins, maxs, rain_years, hottest = [], [], 0, None
    for y, rows in per_year.items():
        ymin = min(r["min"] for r in rows if r["min"] is not None)
        ymax = max(r["max"] for r in rows if r["max"] is not None)
        mins.append(ymin)
        maxs.append(ymax)
        # 대회 당일만 비를 본다 (둘레까지 세면 비 온 해가 과장된다)
        try:
            day = days.get(dt.date(y, mm, dd).strftime("%Y%m%d"))
        except ValueError:
            day = None
        if day and (day.get("rn") or 0) >= 1.0:
            rain_years += 1
        if hottest is None or ymax > hottest[1]:
            hottest = (y, ymax)
    return {
        "years": len(per_year),
        "minAvg": round(sum(mins) / len(mins), 1),
        "maxAvg": round(sum(maxs) / len(maxs), 1),
        "rainYears": rain_years,
        "hottestYear": hottest[0] if hottest else None,
        "hottestMax": round(hottest[1], 1) if hottest else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--refresh-stations", action="store_true")
    args = ap.parse_args()

    key = os.environ.get("DATA_GO_KR_KEY", "").strip()
    if not key:
        print("DATA_GO_KR_KEY 가 없습니다.", file=sys.stderr)
        return 1
    if "%" in key:
        key = urllib.parse.unquote(key)

    # 1) 일자료부터 확인한다. 이게 본체고, 지점 목록은 거기에 딸린 문제다.
    #    전에는 순서가 반대여서 지점에서 막히자 정작 본체를 시험도 못 했다.
    today = dt.date.today()
    probe_end = today - dt.timedelta(days=2)
    probe_start = probe_end - dt.timedelta(days=5)
    daily_ok, probe_stn, days = False, None, {}
    for cand in PROBE_STATIONS:
        days, err = fetch_days(key, cand, probe_start.strftime("%Y%m%d"),
                               probe_end.strftime("%Y%m%d"))
        if err:
            print("[climate] 일자료 지점 %s — %s" % (cand, err))
            # 인증 문제면 지점을 바꿔도 소용없다
            if any(w in str(err).upper() for w in
                   ("SERVICE", "KEY", "AUTH", "REGIST", "DENIED", "허용")):
                break
            continue
        if days:
            daily_ok, probe_stn = True, cand
            break
    if not daily_ok:
        print("[climate] ASOS 일자료를 받지 못했습니다. 공공데이터포털에서 "
              "'기상청_지상(종관, ASOS) 일자료 조회서비스'에 활용신청이 되어 "
              "있는지 확인해 주세요.", file=sys.stderr)
        return 2
    print("[climate] ASOS 일자료 됩니다 — 지점 %s, %d일치" % (probe_stn, len(days)))
    for k in sorted(days)[-2:]:
        print("   %s %s" % (k, days[k]))

    # 2) 지점 목록
    stations = load_stations(key, force=args.refresh_stations)
    if not stations:
        print("[climate] 일자료는 되는데 지점 목록을 못 받았습니다. "
              "KMA_APIHUB_KEY(기상청 API허브) 를 넣어 주시면 전체 지점표를 "
              "한 번에 받습니다.", file=sys.stderr)
        return 3
    if args.selftest:
        print("[climate] 자체 점검 통과 — 일자료 OK, 지점 %d곳" % len(stations))
        return 0

    # 3) 대회마다 가장 가까운 지점과 월일을 모은다
    events = json.loads(EVENTS.read_text(encoding="utf-8"))
    years = list(range(today.year - YEARS_BACK, today.year))
    need = defaultdict(set)      # 지점 → {(월, 일)}
    plan = {}
    for ev in events:
        lat, lng, d = ev.get("lat"), ev.get("lng"), ev.get("date")
        if not (lat and lng and d):
            continue
        try:
            day = dt.date.fromisoformat(d)
        except ValueError:
            continue
        st, dist = nearest(stations, float(lat), float(lng))
        if not st or dist > 60:      # 60km 넘게 떨어지면 그 지점 기온이라 하기 어렵다
            continue
        need[st["id"]].add((day.month, day.day))
        plan[ev.get("id")] = (st, dist, (day.month, day.day))

    print("[climate] 대회 %d개 · 쓰는 지점 %d곳" % (len(plan), len(need)))

    cache = json.loads(CLIMATE.read_text(encoding="utf-8")) if CLIMATE.exists() else {}
    calls = 0
    for stn, mds in sorted(need.items()):
        missing = [md for md in mds if "%d:%02d%02d" % (stn, md[0], md[1]) not in cache]
        if not missing:
            continue
        # 한 지점은 해마다 통째로 받는 편이 호출이 적다
        days_all = {}
        for y in years:
            got, err = fetch_days(key, stn, "%d0101" % y, "%d1231" % y)
            calls += 1
            if err:
                print("[climate] 지점 %s %d년 — %s" % (stn, y, err))
                break
            days_all.update(got)
            time.sleep(0.12)
        for md in mds:
            s = summarize(days_all, md, years)
            if s:
                cache["%d:%02d%02d" % (stn, md[0], md[1])] = s

    DATA_DIR.mkdir(exist_ok=True)
    CLIMATE.write_text(json.dumps(cache, ensure_ascii=False, sort_keys=True) + "\n",
                       encoding="utf-8")

    filled = 0
    for ev in events:
        got = plan.get(ev.get("id"))
        if not got:
            ev.pop("climate", None)
            continue
        st, dist, md = got
        s = cache.get("%d:%02d%02d" % (st["id"], md[0], md[1]))
        if not s:
            ev.pop("climate", None)
            continue
        ev["climate"] = dict(s, station=st["name"], stationKm=round(dist))
        filled += 1

    EVENTS.write_text(json.dumps(events, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print("[climate] 붙임 %d개 · 호출 %d회 · 캐시 %d칸" % (filled, calls, len(cache)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

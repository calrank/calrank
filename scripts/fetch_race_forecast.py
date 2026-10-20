#!/usr/bin/env python3
"""다가오는 대회에 기상청 단기예보를 붙인다.

왜 단기예보인가
---------------
중기예보는 열흘까지 보지만 지역코드(regId) 표를 들고 있어야 한다. 코드를 하나
잘못 적으면 엉뚱한 도시의 예보가 조용히 들어간다 — API 가 지역 이름을 돌려주지
않아 틀린 줄도 모른다. 단기예보는 대회 좌표를 격자로 바꿔 부르니 그럴 일이 없다.
대신 사흘까지만 본다. 뭘 입고 갈지 정하는 건 보통 그 즈음이다.

격자 변환은 기상청이 공개한 람베르트 정각원추도법 식을 그대로 쓴다.
서울시청(37.5665, 126.9780)이 (60, 127)로 나오는지 먼저 확인하고 시작한다.

쓰임:
  python scripts/fetch_race_forecast.py --selftest
  python scripts/fetch_race_forecast.py
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
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVENTS = ROOT / "events.json"

HOSTS = ["https://apis.data.go.kr", "http://apis.data.go.kr"]
PATH = "/1360000/VilageFcstInfoService_2.0/getVilageFcst"
BASE = None

# 기상청 격자 변환 상수
RE, GRID = 6371.00877, 5.0
SLAT1, SLAT2 = 30.0, 60.0
OLON, OLAT = 126.0, 38.0
XO, YO = 43, 136


def to_grid(lat, lon):
    DEGRAD = math.pi / 180.0
    re_ = RE / GRID
    slat1, slat2 = SLAT1 * DEGRAD, SLAT2 * DEGRAD
    olon, olat = OLON * DEGRAD, OLAT * DEGRAD
    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
    sf = (sf ** sn) * math.cos(slat1) / sn
    ro = math.tan(math.pi * 0.25 + olat * 0.5)
    ro = re_ * sf / (ro ** sn)
    ra = math.tan(math.pi * 0.25 + lat * DEGRAD * 0.5)
    ra = re_ * sf / (ra ** sn)
    theta = lon * DEGRAD - olon
    if theta > math.pi:
        theta -= 2.0 * math.pi
    if theta < -math.pi:
        theta += 2.0 * math.pi
    theta *= sn
    return (int(ra * math.sin(theta) + XO + 0.5),
            int(ro - ra * math.cos(theta) + YO + 0.5))


def http_get(url, tries=3, timeout=15):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "calrank/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:          # noqa: BLE001
            last = e
            time.sleep(1.0 * (i + 1))
    raise RuntimeError("요청 실패: %s" % last)


def base_time(now):
    """단기예보 발표시각. 02/05/08/11/14/17/20/23시에 나오고 10분쯤 뒤부터 받을 수 있다."""
    slots = [23, 20, 17, 14, 11, 8, 5, 2]
    d = now
    for h in slots:
        if now.hour > h or (now.hour == h and now.minute >= 15):
            return d.strftime("%Y%m%d"), "%02d00" % h
    d = now - dt.timedelta(days=1)
    return d.strftime("%Y%m%d"), "2300"


def call_fcst(key, nx, ny, bd, bt):
    q = urllib.parse.urlencode({
        "serviceKey": key, "dataType": "JSON", "numOfRows": "1000", "pageNo": "1",
        "base_date": bd, "base_time": bt, "nx": str(nx), "ny": str(ny),
    })
    raw = http_get(BASE + "?" + q)
    if raw.lstrip().startswith("<"):
        for tag in ("returnAuthMsg", "errMsg", "returnReasonCode"):
            s = raw.find("<%s>" % tag)
            if s >= 0:
                e = raw.find("</%s>" % tag, s)
                return None, raw[s + len(tag) + 2:e].strip()
        return None, raw[:160].replace("\n", " ")
    try:
        d = json.loads(raw)
    except Exception:                   # noqa: BLE001
        return None, raw[:160].replace("\n", " ")
    head = d.get("response", {}).get("header", {})
    if head.get("resultCode") not in ("00", "0"):
        return None, "%s %s" % (head.get("resultCode"), head.get("resultMsg", ""))
    items = (d.get("response", {}).get("body", {})
              .get("items", {}) or {}).get("item", [])
    return items, None


SKY = {"1": "맑음", "3": "구름많음", "4": "흐림"}
PTY = {"0": "", "1": "비", "2": "비/눈", "3": "눈", "4": "소나기",
       "5": "빗방울", "6": "빗방울/눈날림", "7": "눈날림"}


def summarize(items, ymd):
    """하루치 예보를 사람이 읽을 한 줄로 줄인다."""
    tmn = tmx = None
    pops, skies, ptys, temps = [], [], [], []
    for it in items:
        if it.get("fcstDate") != ymd:
            continue
        cat, val, t = it.get("category"), it.get("fcstValue"), it.get("fcstTime", "")
        try:
            hour = int(t[:2])
        except ValueError:
            hour = -1
        if cat == "TMN":
            tmn = float(val)
        elif cat == "TMX":
            tmx = float(val)
        elif cat == "TMP":
            temps.append((hour, float(val)))
        elif 6 <= hour <= 12:           # 대회는 대개 아침에 열린다
            if cat == "POP":
                pops.append(int(val))
            elif cat == "SKY":
                skies.append(val)
            elif cat == "PTY":
                ptys.append(val)
    if tmn is None and temps:
        tmn = min(v for _, v in temps)
    if tmx is None and temps:
        tmx = max(v for _, v in temps)
    morning = [v for h, v in temps if 6 <= h <= 10]
    if tmn is None and tmx is None and not morning:
        return None
    sky = ""
    if ptys and any(p != "0" for p in ptys):
        for p in ptys:
            if p != "0":
                sky = PTY.get(p, "")
                break
    elif skies:
        sky = SKY.get(max(set(skies), key=skies.count), "")
    return {
        "tmn": tmn, "tmx": tmx,
        "morningTa": round(sum(morning) / len(morning), 1) if morning else None,
        "pop": max(pops) if pops else None,
        "sky": sky,
        "src": "KMA 단기예보",
    }


def main():
    global BASE
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    # 격자 변환이 맞는지 먼저 확인한다. 서울시청은 (60, 127) 이어야 한다.
    gx, gy = to_grid(37.5665, 126.9780)
    print("[fcst] 격자 변환 확인 — 서울시청 → (%d, %d)" % (gx, gy))
    if (gx, gy) != (60, 127):
        print("[fcst] 격자 변환이 틀렸습니다. 멈춥니다.", file=sys.stderr)
        return 3

    key = os.environ.get("DATA_GO_KR_KEY", "").strip()
    if not key:
        print("DATA_GO_KR_KEY 가 없습니다.", file=sys.stderr)
        return 1
    if "%" in key:
        key = urllib.parse.unquote(key)

    now = dt.datetime.utcnow() + dt.timedelta(hours=9)   # KST
    bd, bt = base_time(now)
    print("[fcst] 발표 %s %s 기준" % (bd, bt))

    ok = None
    for host in HOSTS:
        BASE = host + PATH
        try:
            items, err = call_fcst(key, 60, 127, bd, bt)
        except Exception as e:          # noqa: BLE001
            print("[fcst] %s — %s" % (host, e))
            continue
        if err:
            print("[fcst] %s — %s" % (host, err))
            if "NO_DATA" not in str(err):
                return 2
            continue
        if items:
            print("[fcst] %s — 됩니다 (항목 %d개)" % (host, len(items)))
            ok = host
            break
    if not ok:
        print("[fcst] 어느 주소로도 예보를 받지 못했습니다.", file=sys.stderr)
        return 2
    if args.selftest:
        s = summarize(items, now.strftime("%Y%m%d"))
        print("[fcst] 서울 오늘 요약: %s" % s)
        return 0

    events = json.loads(EVENTS.read_text(encoding="utf-8"))
    today = now.date()
    horizon = today + dt.timedelta(days=3)
    cache, filled, cleared = {}, 0, 0

    for ev in events:
        d = ev.get("date")
        if not d:
            continue
        try:
            day = dt.date.fromisoformat(d)
        except ValueError:
            continue
        # 지난 대회나 사흘 너머 대회에 남은 예보는 지운다
        if day < today or day > horizon:
            if ev.pop("forecast", None) is not None:
                cleared += 1
            continue
        lat, lng = ev.get("lat"), ev.get("lng")
        if not lat or not lng:
            if ev.pop("forecast", None) is not None:
                cleared += 1
            continue
        nx, ny = to_grid(float(lat), float(lng))
        if (nx, ny) not in cache:
            items, err = call_fcst(key, nx, ny, bd, bt)
            time.sleep(0.12)
            cache[(nx, ny)] = None if err else items
        items = cache[(nx, ny)]
        if not items:
            continue
        s = summarize(items, d.replace("-", ""))
        if not s:
            continue
        s["asOf"] = now.strftime("%Y-%m-%d %H:%M")
        ev["forecast"] = s
        filled += 1

    EVENTS.write_text(
        json.dumps(events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("[fcst] 붙임 %d · 지움 %d · 부른 격자 %d곳" % (filled, cleared, len(cache)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

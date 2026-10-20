#!/usr/bin/env python3
"""대회 당일 기온을 events.json 에 채운다.

왜 필요한가
-----------
같은 53분이라도 8℃에서 뛴 것과 22℃에서 뛴 것은 다른 기록이다. 등급을 매길 때
이 차이를 모른 척하면, 더운 날 대회에 나간 사람은 자기 실력보다 낮은 등급을 받는다.

기상청 종관기상관측(ASOS) 일자료에서 대회일의 평균·최저·최고기온을 받아
events.json 각 대회에 넣어 둔다. 지난 날씨는 바뀌지 않으니 한 번 받으면 끝이고,
이미 채워진 대회는 건너뛴다.

지점은 기억에 의존하지 않는다
-----------------------------
아래 STATIONS 표의 지점번호가 맞는지 기계가 직접 확인한다. 각 지점으로 한 번
호출해서 돌아온 지점명이 표에 적힌 이름과 다르면 그 지점은 쓰지 않고 보고한다.
숫자를 잘못 외워서 엉뚱한 도시의 기온을 넣는 일이 없도록.

쓰임:
  python scripts/fetch_race_weather.py --selftest   키와 지점표만 확인
  python scripts/fetch_race_weather.py --limit 80   최대 80개 대회 채우기
"""

import argparse
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

API = "https://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList"

# 기상청 종관기상관측(ASOS) 주요 지점. (지점번호, 지점명, 위도, 경도)
# 지점명은 확인용이다 — API 가 돌려준 이름과 다르면 그 지점은 쓰지 않는다.
STATIONS = [
    (90, "속초", 38.2509, 128.5647),
    (100, "대관령", 37.6771, 128.7183),
    (101, "춘천", 37.9026, 127.7357),
    (105, "강릉", 37.7515, 128.8910),
    (108, "서울", 37.5714, 126.9658),
    (112, "인천", 37.4776, 126.6249),
    (114, "원주", 37.3376, 127.9466),
    (119, "수원", 37.2573, 126.9830),
    (127, "충주", 36.9705, 127.9527),
    (129, "서산", 36.7766, 126.4939),
    (130, "울진", 36.9918, 129.4130),
    (131, "청주", 36.6392, 127.4407),
    (133, "대전", 36.3720, 127.3721),
    (135, "추풍령", 36.2203, 127.9946),
    (136, "안동", 36.5729, 128.7073),
    (138, "포항", 36.0325, 129.3800),
    (140, "군산", 36.0053, 126.7614),
    (143, "대구", 35.8853, 128.6190),
    (146, "전주", 35.8215, 127.1547),
    (152, "울산", 35.5602, 129.3200),
    (155, "창원", 35.1700, 128.5728),
    (156, "광주", 35.1729, 126.8916),
    (159, "부산", 35.1047, 129.0320),
    (162, "통영", 34.8453, 128.4356),
    (165, "목포", 34.8169, 126.3812),
    (168, "여수", 34.7393, 127.7405),
    (184, "제주", 33.5141, 126.5297),
    (189, "서귀포", 33.2461, 126.5653),
    (192, "진주", 35.1639, 128.0400),
    (201, "강화", 37.7073, 126.4462),
    (202, "양평", 37.4886, 127.4946),
    (203, "이천", 37.2638, 127.4842),
    (211, "인제", 38.0598, 128.1678),
    (221, "제천", 37.1593, 128.1944),
    (226, "보은", 36.4876, 127.7343),
    (232, "천안", 36.7766, 127.1213),
    (235, "보령", 36.3273, 126.5575),
    (236, "부여", 36.2724, 126.9207),
    (238, "금산", 36.1056, 127.4817),
    (243, "부안", 35.7297, 126.7166),
    (244, "임실", 35.6122, 127.2863),
    (245, "정읍", 35.5633, 126.8390),
    (247, "남원", 35.4049, 127.3327),
    (256, "순창", 35.3744, 127.1375),
    (260, "장흥", 34.6886, 126.9196),
    (261, "해남", 34.5538, 126.5690),
    (262, "고흥", 34.6182, 127.2759),
    (271, "봉화", 36.9434, 128.9139),
    (272, "영주", 36.8719, 128.5169),
    (273, "문경", 36.6272, 128.1487),
    (277, "영덕", 36.5331, 129.4094),
    (278, "의성", 36.3561, 128.6886),
    (279, "구미", 36.1309, 128.3206),
    (281, "영천", 35.9773, 128.9516),
    (283, "경주", 35.8428, 129.2114),
    (284, "거창", 35.6711, 127.9115),
    (285, "합천", 35.5651, 128.1699),
    (288, "밀양", 35.4915, 128.7441),
    (289, "산청", 35.4130, 127.8791),
    (294, "거제", 34.8882, 128.6046),
    (295, "남해", 34.8166, 127.9264),
]

# 지역 이름만 있고 좌표가 없을 때 쓰는 대표 지점
REGION_FALLBACK = {
    "서울": 108, "인천": 112, "경기": 119, "강원": 105, "충북": 131,
    "충남": 129, "대전": 133, "세종": 133, "전북": 146, "전남": 165,
    "광주": 156, "경북": 143, "대구": 143, "경남": 155, "부산": 159,
    "울산": 152, "제주": 184,
}


def http_get(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "calrank/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:          # noqa: BLE001
            last = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError("요청 실패: %s" % last)


def call_asos(key, stn, ymd):
    """하루치 ASOS 자료. (payload, 오류문자열) 을 돌려준다."""
    q = urllib.parse.urlencode({
        "serviceKey": key,
        "dataType": "JSON",
        "dataCd": "ASOS",
        "dateCd": "DAY",
        "startDt": ymd,
        "endDt": ymd,
        "stnIds": str(stn),
        "numOfRows": "10",
        "pageNo": "1",
    })
    raw = http_get(API + "?" + q)
    if raw.lstrip().startswith("<"):
        # 공공데이터포털은 키가 틀리면 JSON 요청에도 XML 오류를 돌려준다
        for tag in ("returnAuthMsg", "errMsg", "returnReasonCode"):
            s = raw.find("<%s>" % tag)
            if s >= 0:
                e = raw.find("</%s>" % tag, s)
                return None, raw[s + len(tag) + 2:e].strip()
        return None, raw[:200].replace("\n", " ")
    try:
        d = json.loads(raw)
    except Exception:                    # noqa: BLE001
        return None, raw[:200].replace("\n", " ")
    head = d.get("response", {}).get("header", {})
    code = head.get("resultCode")
    if code not in ("00", "0"):
        return None, "%s %s" % (code, head.get("resultMsg", ""))
    items = (d.get("response", {}).get("body", {})
              .get("items", {}) or {}).get("item", [])
    return (items[0] if items else None), None


def verify_stations(key, probe_date):
    """표에 적은 지점번호가 실제로 그 지점인지 확인한다."""
    good, bad = {}, []
    for stn, name, lat, lng in STATIONS:
        item, err = call_asos(key, stn, probe_date)
        if err:
            bad.append((stn, name, err))
        elif not item:
            bad.append((stn, name, "자료 없음"))
        elif item.get("stnNm") and item["stnNm"] != name:
            bad.append((stn, name, "실제 지점명 %s" % item["stnNm"]))
        else:
            good[stn] = (name, lat, lng)
        time.sleep(0.12)
    return good, bad


def nearest(good, lat, lng):
    best, bd = None, 1e18
    for stn, (name, slat, slng) in good.items():
        dx = (lng - slng) * math.cos(math.radians(lat)) * 111.3
        dy = (lat - slat) * 111.3
        d = dx * dx + dy * dy
        if d < bd:
            bd, best = d, stn
    return best, math.sqrt(bd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--limit", type=int, default=120)
    args = ap.parse_args()

    key = os.environ.get("DATA_GO_KR_KEY", "").strip()
    if not key:
        print("DATA_GO_KR_KEY 가 없습니다.", file=sys.stderr)
        return 1
    # 인코딩 키를 넣으면 한 번 더 인코딩돼 서명이 깨진다. 먼저 되돌린다.
    if "%" in key:
        key = urllib.parse.unquote(key)
        print("[weather] 키에 %가 있어 디코딩해서 씁니다 (Encoding 키로 보입니다)")

    probe = "20240501"
    item, err = call_asos(key, 108, probe)
    if err:
        print("[weather] 시험 호출 실패: %s" % err, file=sys.stderr)
        print("[weather] 공공데이터포털에서 '지상(종관) 일자료' 활용신청이 "
              "승인됐는지, 키를 Decoding 쪽으로 넣었는지 확인해 주세요.",
              file=sys.stderr)
        return 2
    print("[weather] 키 확인 — 서울 %s 평균기온 %s℃" % (probe, item.get("avgTa")))

    good, bad = verify_stations(key, probe)
    print("[weather] 지점 확인 — 쓸 수 있는 곳 %d, 못 쓰는 곳 %d" % (len(good), len(bad)))
    for stn, name, why in bad:
        print("   · %s(%s) 제외 — %s" % (name, stn, why))
    if args.selftest:
        return 0
    if len(good) < 10:
        print("[weather] 쓸 수 있는 지점이 너무 적습니다. 멈춥니다.", file=sys.stderr)
        return 3

    events = json.loads(EVENTS.read_text(encoding="utf-8"))
    today = time.strftime("%Y-%m-%d")
    todo = []
    for ev in events:
        d = ev.get("date")
        if not d or d > today:
            continue
        if ev.get("weather"):
            continue
        if d < "2010-01-01":          # ASOS 는 더 옛날도 있지만 대회 자료가 없다
            continue
        todo.append(ev)
    todo.sort(key=lambda x: x.get("date", ""), reverse=True)
    todo = todo[: args.limit]
    print("[weather] 채울 대회 %d개" % len(todo))

    filled = skipped = 0
    for ev in todo:
        lat, lng = ev.get("lat"), ev.get("lng")
        if lat and lng:
            stn, dist = nearest(good, float(lat), float(lng))
            if dist > 60:             # 60km 넘게 떨어지면 그 날씨라고 하기 어렵다
                skipped += 1
                continue
        else:
            stn = REGION_FALLBACK.get(ev.get("region") or "")
            if stn not in good:
                skipped += 1
                continue
            dist = None
        ymd = ev["date"].replace("-", "")
        item, err = call_asos(key, stn, ymd)
        time.sleep(0.12)
        if err or not item:
            skipped += 1
            continue
        def num(k):
            v = item.get(k)
            try:
                return round(float(v), 1)
            except (TypeError, ValueError):
                return None
        avg, tmin, tmax = num("avgTa"), num("minTa"), num("maxTa")
        if avg is None and tmax is None:
            skipped += 1
            continue
        ev["weather"] = {
            "station": good[stn][0],
            "stationId": stn,
            "avgTa": avg,
            "minTa": tmin,
            "maxTa": tmax,
            "rn": num("sumRn"),
            "rhm": num("avgRhm"),
            "awayKm": None if dist is None else round(dist, 1),
            "src": "KMA ASOS",
        }
        filled += 1

    EVENTS.write_text(
        json.dumps(events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("[weather] 채움 %d · 건너뜀 %d" % (filled, skipped))
    return 0


if __name__ == "__main__":
    sys.exit(main())

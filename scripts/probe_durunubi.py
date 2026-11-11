"""두루누비 API 시험 호출 (결과 요약만 로그에 남긴다).

- 인증키는 환경변수 DURUNUBI_API_KEY 에서만 읽고, 어떤 출력에도 찍지 않는다.
- 파일로 저장하지 않는다. 확인하려는 것은 세 가지다.
  1) 코스 목록 호출이 되는지
  2) 응답에 GPX 주소가 있는지
  3) GPX 안에 좌표와 고도(ele)가 들어 있는지
"""
import json
import os
import re
import sys
import urllib.parse

import requests

BASE = "https://apis.data.go.kr/B551011/Durunubi"
RAW = os.environ.get("DURUNUBI_API_KEY", "").strip()
if not RAW:
    print("DURUNUBI_API_KEY 가 비어 있습니다.")
    sys.exit(1)
KEY = urllib.parse.unquote(RAW)  # 포털이 %3D 처럼 인코딩된 값을 보여 주므로 풀어서 쓴다.
SECRETS = {RAW, KEY, urllib.parse.quote(KEY, safe="")}


def mask(text):
    text = str(text)
    for s in SECRETS:
        if s:
            text = text.replace(s, "***")
    return text


def call(op, **extra):
    params = {"serviceKey": KEY, "MobileOS": "ETC", "MobileApp": "calrank", "_type": "json",
              "numOfRows": 5, "pageNo": 1}
    params.update(extra)
    r = requests.get(f"{BASE}/{op}", params=params, timeout=30,
                     headers={"User-Agent": "calrank-probe"})
    return r


def items_of(data):
    try:
        it = data["response"]["body"]["items"]["item"]
    except Exception:
        return []
    return it if isinstance(it, list) else [it]


def probe_gpx(url):
    r = requests.get(url, timeout=60, headers={"User-Agent": "calrank-probe"})
    print(f"  GPX 요청 상태 {r.status_code}, 크기 {len(r.content)} bytes")
    if r.status_code != 200:
        return
    t = r.text
    trkpt = len(re.findall(r"<trkpt\b", t))
    rtept = len(re.findall(r"<rtept\b", t))
    wpt = len(re.findall(r"<wpt\b", t))
    eles = [float(x) for x in re.findall(r"<ele>\s*([-0-9.]+)\s*</ele>", t)]
    print(f"  trkpt {trkpt}, rtept {rtept}, wpt {wpt}, ele 태그 {len(eles)}개")
    if eles:
        print(f"  고도 범위 {min(eles):.1f} ~ {max(eles):.1f} m, 서로 다른 값 {len(set(eles))}개")
    else:
        print("  고도(ele) 값이 없습니다.")


def main():
    for op in ("courseList", "routeList"):
        print(f"== {op} ==")
        try:
            r = call(op)
        except Exception as e:
            print("  호출 실패:", mask(e))
            continue
        print(f"  상태 {r.status_code}, 형식 {r.headers.get('content-type')}")
        body = mask(r.text)
        try:
            data = json.loads(body)
        except Exception:
            print("  JSON 아님. 앞부분:", body[:300].replace("\n", " "))
            continue
        head = data.get("response", {}).get("header", {})
        print("  결과코드:", head.get("resultCode"), head.get("resultMsg"))
        tc = data.get("response", {}).get("body", {}).get("totalCount")
        print("  전체 건수:", tc)
        its = items_of(data)
        print("  받은 건수:", len(its))
        if its:
            print("  항목 필드 이름:", sorted(its[0].keys()))
            for it in its[:3]:
                gp = it.get("gpxpath") or it.get("gpxPath") or ""
                nm = it.get("crsKorNm") or it.get("routeNm") or it.get("themeNm") or ""
                dist = it.get("crsDstnc") or it.get("distance") or ""
                print(f"  - {nm} / 거리 {dist} / GPX {'있음' if gp else '없음'}")
            for it in its:
                gp = it.get("gpxpath") or it.get("gpxPath") or ""
                if gp:
                    print("  GPX 시험 대상 호스트:", urllib.parse.urlparse(gp).netloc)
                    try:
                        probe_gpx(gp)
                    except Exception as e:
                        print("  GPX 읽기 실패:", mask(e))
                    break


if __name__ == "__main__":
    main()

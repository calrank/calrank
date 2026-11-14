#!/usr/bin/env python3
"""참고 영상이 아직 살아 있는지 YouTube oEmbed 로 확인한다.

  - 404 / 401 / 403  → 삭제됐거나 비공개·퍼가기 금지. status 를 "dead" 로 바꾼다(카드가 빠진다).
  - 200              → 살아 있다. 전에 dead 였다면 되살린다.
  - 그 밖의 오류·접속 실패 → 판단하지 않고 그대로 둔다(일시 장애로 영상을 내리지 않는다).
  - 200 인데 채널 이름이 목록과 아주 다르면 경고만 한다(채널 이름 변경일 수 있다).

바뀐 게 있을 때만 data/videos.json 을 고친다. 매일 돌려도 커밋이 생기지 않는다.

  python scripts/check_videos.py
"""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "videos.json"


def probe(vid):
    url = "https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(f"https://www.youtube.com/watch?v={vid}", safe="")
    req = urllib.request.Request(url, headers={"User-Agent": "calrank-videocheck/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return None, None


def main():
    raw = json.loads(DATA.read_text(encoding="utf-8"))
    changed = 0
    cache = {}
    for v in raw.get("items", []):
        vid = v.get("id")
        if not vid:
            continue
        if vid not in cache:
            cache[vid] = probe(vid)
            time.sleep(0.3)
        code, info = cache[vid]
        if code in (401, 403, 404):
            if v.get("status") != "dead":
                v["status"] = "dead"
                changed += 1
                print("[videos] 내림:", vid, v.get("title", "")[:40])
        elif code == 200:
            if v.get("status") == "dead":
                v.pop("status", None)
                changed += 1
                print("[videos] 되살림:", vid)
            a = (info or {}).get("author_name", "")
            want = v.get("channel", "")
            if a and want and a.replace(" ", "")[:3] not in want.replace(" ", "") and want.replace(" ", "")[:3] not in a.replace(" ", ""):
                print("[videos] 채널 이름 확인 필요:", vid, "|", want, "→", a)
    if changed:
        DATA.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("[videos] 점검 %d개 · 바뀐 것 %d개" % (len(cache), changed))
    return 0


if __name__ == "__main__":
    sys.exit(main())

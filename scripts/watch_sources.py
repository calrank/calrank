"""규정 원문이 바뀌었는지 확인한다.

data/gear_rules.json 과 data/gear_dq.json 에 적힌 원문 주소를 내려받아, 내용의 지문(해시)을
data/source_watch.json 에 남긴다. 지난번과 지문이 다르면 changed 날짜를 갱신한다.
처음 보는 주소는 changed 를 비워 둔다(바뀐 것이 아니라 처음 본 것이므로).

지문은 "문서가 달라졌다"는 신호일 뿐, 무엇이 달라졌는지는 알려 주지 않는다. 쪽 번호나
게시 시각 같은 바뀌어도 상관없는 부분이 섞여 있으면 헛경보가 날 수 있어서, 화면에는
"원문이 바뀌었을 수 있으니 확인" 까지만 말한다. 받지 못한 주소는 지난 값을 그대로 둔다.
"""
import hashlib, json, re, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "source_watch.json"
KST = timezone(timedelta(hours=9))
UA = "Mozilla/5.0 (compatible; calrank-source-watch/1.0; +https://calrank.vercel.app)"


def urls() -> list[str]:
    found = []
    rules = json.loads((ROOT / "data/gear_rules.json").read_text(encoding="utf-8"))
    for r in rules.get("rules", []):
        if r.get("url"):
            found.append(r["url"])
    p = ROOT / "data/gear_dq.json"
    if p.exists():
        for s in json.loads(p.read_text(encoding="utf-8")).get("sources", {}).values():
            if s.get("url"):
                found.append(s["url"])
    seen, out = set(), []
    for u in found:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def fingerprint(resp: requests.Response) -> str:
    ctype = resp.headers.get("content-type", "")
    body = resp.content
    if "html" in ctype:
        t = body.decode(resp.encoding or "utf-8", "ignore")
        t = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", t)
        t = re.sub(r"(?s)<[^>]+>", " ", t)
        body = re.sub(r"\s+", " ", t).strip().encode()
    return hashlib.sha256(body).hexdigest()[:16]


def main() -> int:
    prev = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    today = datetime.now(KST).date().isoformat()
    res = {}
    for u in urls():
        old = prev.get(u, {})
        rec = dict(old)
        try:
            r = requests.get(u, headers={"User-Agent": UA}, timeout=60)
            r.raise_for_status()
            fp = fingerprint(r)
            rec["checked"] = today
            rec["ok"] = True
            if old.get("hash") and old["hash"] != fp:
                rec["changed"] = today
            rec["hash"] = fp
            print("ok  ", fp, "CHANGED" if rec.get("changed") == today else "", u[:80])
        except Exception as e:  # 받지 못하면 지난 값 유지
            rec["ok"] = False
            rec["error"] = type(e).__name__
            print("fail", type(e).__name__, u[:80])
        res[u] = rec
        time.sleep(1)
    out = json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    if not OUT.exists() or OUT.read_text(encoding="utf-8") != out:
        OUT.write_text(out, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""docs/new-page-criteria.md 의 기계로 잴 수 있는 기준을 현재 사이트에 돌려 본다. (보고만 한다)

  python3 scripts/audit_pages.py

점검 항목
  1. 사이트맵에 있는데 noindex 인 페이지 (신호 충돌)
  2. canonical 이 없거나 둘 이상인 색인 대상 페이지
  3. 사이트맵 페이지 중 들어오는 내부 링크가 3개 미만인 것 (유형별)
  4. 별칭(event_aliases.json)의 이동 대상 파일이 없는 것
  5. 사이트맵에 없는 색인 대상 페이지
"""
import collections
import json
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
HOST = "https://calrank.vercel.app"


def kind(path: str) -> str:
    if path.startswith("/e/"):
        return "대회"
    n = path.lstrip("/").split("-")[0].split(".")[0]
    return n or "home"


def main():
    sm = set()
    for f in ("sitemap.xml", "sitemap-events.xml"):
        p = ROOT / f
        if p.exists():
            sm |= {unquote(u) for u in re.findall(r"<loc>%s(/[^<]*)</loc>" % re.escape(HOST), p.read_text(encoding="utf-8"))}

    files = {}
    for p in list(ROOT.glob("*.html")) + list((ROOT / "e").glob("*.html")):
        files["/" + str(p.relative_to(ROOT))] = p.read_text(encoding="utf-8")

    def noindex(t):
        return bool(re.search(r'<meta[^>]*noindex', t[:6000]))

    # 1
    conflict = [u for u in sm if u in files and noindex(files[u])]
    # 2
    bad_canon = []
    for u, t in files.items():
        if noindex(t) or u.endswith(("offline.html", "reset.html")):
            continue
        if u.startswith("/naver") or u in ("/widget.html", "/widget-course.html"):
            continue
        n = len(re.findall(r'<link rel="canonical"', t))
        if n != 1:
            bad_canon.append((u, n))
    # 3
    inl = collections.Counter()
    for u, t in files.items():
        s = t
        for h in set(re.findall(r'href="/?((?:e/)?[^"#?]+\.html)', s)):
            tgt = "/" + unquote(h)
            if tgt != u:
                inl[tgt] += 1
    weak = collections.defaultdict(list)
    for u in sm:
        if u in files and inl[u] < 3:
            weak[kind(u)].append(u)
    # 4
    al = json.loads((ROOT / "event_aliases.json").read_text(encoding="utf-8")) if (ROOT / "event_aliases.json").exists() else {}
    missing = [v for v in set(al.values()) if not (ROOT / "e" / f"{v}.html").exists()]
    # 5
    unlisted = [u for u, t in files.items()
                if u not in sm and not noindex(t) and u != "/index.html"
                and not u.startswith(("/naver", "/widget"))
                and u.lstrip("/") not in ("offline.html", "reset.html", "event.html", "profile.html")]

    print(f"사이트맵 {len(sm)}개 · 페이지 파일 {len(files)}개")
    print(f"1. 사이트맵에 있는 noindex: {len(conflict)}개", conflict[:5])
    print(f"2. canonical 이상: {len(bad_canon)}개", bad_canon[:5])
    print(f"3. 들어오는 링크 3개 미만: {sum(len(v) for v in weak.values())}개")
    for k, v in sorted(weak.items(), key=lambda x: -len(x[1])):
        print(f"   {k}: {len(v)}개 예) {v[0]}")
    print(f"4. 별칭 대상 파일 없음: {len(missing)}개", missing[:5])
    print(f"5. 사이트맵에 없는 색인 대상: {len(unlisted)}개", unlisted[:8])


if __name__ == "__main__":
    main()

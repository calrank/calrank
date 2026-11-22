"""사이트맵에 빠진 색인 대상 페이지를 채운다.

칼럼 20여 개가 생성기별로 사이트맵 갱신을 빠뜨려 검색엔진에 알려지지 않고 있었다.
noindex 페이지, 인증 파일, 동적 페이지는 넣지 않는다. 이미 있는 항목은 건드리지 않는다.
"""
import hashlib
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {"profile.html", "event.html", "index.html", "terms.html", "privacy.html", "reset.html",
        "contact.html", "welcome.html", "greeting.html", "widget.html", "widget-course.html", "saved-events.html"}


SIG = ROOT / "data" / "sitemap_sig.json"   # 배포에서는 뺀다(.vercelignore)


def body_sig(path: Path) -> str:
    """머리글·바닥글·내비·스크립트를 뺀 본문의 서명. 본문이 바뀐 날만 lastmod 를 올리려는 것이다."""
    t = path.read_text(encoding="utf-8", errors="replace")
    t = re.sub(r"<(nav|header|footer|script|style|svg)\b.*?</\1>", "", t, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return hashlib.sha256(t.encode("utf-8")).hexdigest()[:16]


def refresh_lastmod(xml: str) -> str:
    """처음 채운 날짜가 영영 그대로이던 문제를 고친다. 내용이 달라진 페이지만 오늘 날짜로 올린다.
    서명 대장이 없던 페이지는 지금 날짜를 그대로 두고 서명만 적는다(가짜 변경을 만들지 않는다)."""
    try:
        book = json.loads(SIG.read_text(encoding="utf-8"))
    except Exception:
        book = {}
    today = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d")
    bumped = 0

    def fix(m):
        nonlocal bumped
        block = m.group(0)
        loc = re.search(r"<loc>(.*?)</loc>", block)
        lm = re.search(r"<lastmod>(.*?)</lastmod>", block)
        if not loc or not lm:
            return block
        name = loc.group(1).rsplit("/", 1)[-1] or "index.html"
        f = ROOT / name
        if "/" in name or not f.is_file():
            return block
        sig = body_sig(f)
        old = book.get(name)
        book[name] = sig
        if old is not None and old != sig and lm.group(1) != today:
            bumped += 1
            return block.replace(lm.group(0), f"<lastmod>{today}</lastmod>", 1)
        return block

    new = re.sub(r"<url>.*?</url>", fix, xml, flags=re.S)
    SIG.parent.mkdir(exist_ok=True)
    SIG.write_text(json.dumps(book, ensure_ascii=False, sort_keys=True, indent=0) + "\n", encoding="utf-8")
    if bumped:
        print(f"사이트맵: 본문이 바뀐 {bumped}개 페이지의 lastmod 를 갱신")
    return new


def main():
    sm = ROOT / "sitemap.xml"
    xml = sm.read_text(encoding="utf-8")
    have = {u.rsplit("/", 1)[-1] for u in re.findall(r"<loc>(.*?)</loc>", xml)}
    add = []
    for f in sorted(ROOT.glob("*.html")):
        if f.name in SKIP or f.name in have or f.name.startswith("naver"):
            continue
        if "noindex" in f.read_text(encoding="utf-8")[:4000]:
            continue
        add.append(f.name)
    # 날짜(lastmod)가 없는 항목은 그 파일을 마지막으로 고친 커밋 날짜로 채운다.
    def fill(m):
        block = m.group(0)
        if "<lastmod>" in block:
            return block
        name = re.search(r"<loc>(.*?)</loc>", block).group(1).rsplit("/", 1)[-1] or "index.html"
        d = subprocess.run(["git", "log", "-1", "--format=%cs", "--", name], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        return block.replace("</loc>", f"</loc>\n    <lastmod>{d}</lastmod>", 1) if d else block
    filled = re.sub(r"<url>.*?</url>", fill, xml, flags=re.S)
    if filled != xml:
        sm.write_text(filled, encoding="utf-8")
        xml = filled
        print("사이트맵: 날짜 없는 항목에 lastmod 채움")
    refreshed = refresh_lastmod(xml)
    if refreshed != xml:
        sm.write_text(refreshed, encoding="utf-8")
        xml = refreshed
    if not add:
        print("사이트맵: 빠진 페이지 없음")
        return
    out = ""
    for n in add:
        d = subprocess.run(["git", "log", "-1", "--format=%cs", "--", n], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        out += (f"  <url>\n    <loc>https://calrank.kr/{n}</loc>\n"
                + (f"    <lastmod>{d}</lastmod>\n" if d else "")
                + "    <changefreq>monthly</changefreq>\n    <priority>0.6</priority>\n  </url>\n")
    sm.write_text(xml.replace("</urlset>", out + "</urlset>"), encoding="utf-8")
    print("사이트맵에 추가:", len(add), add[:5])


if __name__ == "__main__":
    main()

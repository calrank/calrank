"""사이트맵에 빠진 색인 대상 페이지를 채운다.

칼럼 20여 개가 생성기별로 사이트맵 갱신을 빠뜨려 검색엔진에 알려지지 않고 있었다.
noindex 페이지, 인증 파일, 동적 페이지는 넣지 않는다. 이미 있는 항목은 건드리지 않는다.
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {"profile.html", "event.html", "index.html", "terms.html", "privacy.html", "reset.html",
        "contact.html", "welcome.html", "greeting.html", "widget.html", "widget-course.html", "saved-events.html"}


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

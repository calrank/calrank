"""
calrank 새 콘텐츠 RSS 피드(rss.xml) 생성

feed.xml(종목뉴스 피드)은 협회·언론사 원문으로 링크해서 네이버가 "소유확인된 사이트와 같은
도메인"이라는 규칙 때문에 거부했고, 방문자를 외부로 보내기도 한다. 이 피드는 calrank 도메인의
페이지만 담는다.

담는 것
- 칼럼(column-*.html)
- 앞으로 열리는 대회의 정적 상세페이지(e/<id>.html)

발행일(pubDate)은 그 페이지가 저장소에 처음 생긴 날짜(git 기록)다. 지어내지 않는다.
lastBuildDate도 가장 최신 항목의 발행일로 두어, 새 항목이 없으면 파일이 바뀌지 않는다.
"""
import html
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://calrank.vercel.app"
KST = timezone(timedelta(hours=9))
MAX_COLUMNS = 20
MAX_EVENTS = 30


def git(*args) -> str:
    return subprocess.run(["git", "-c", "core.quotepath=false", *args], cwd=ROOT,
                          capture_output=True, text=True, check=True).stdout


def created_dates() -> dict:
    """파일 -> 저장소에 처음 추가된 시각. 얕은 복제(shallow)면 정확하지 않으므로 중단한다."""
    if git("rev-parse", "--is-shallow-repository").strip() == "true":
        raise RuntimeError("얕은 복제(shallow clone)입니다. 워크플로우에서 fetch-depth: 0 으로 체크아웃하세요.")
    out = git("log", "--diff-filter=A", "--name-only", "--pretty=format:@@%aI", "--", "column-*.html", "e/*.html")
    dates, cur = {}, None
    for line in out.splitlines():
        if line.startswith("@@"):
            cur = line[2:]
        elif line:
            dates[line] = cur  # 최신 -> 과거 순이라 마지막 값이 최초 생성일
    return dates


def page_meta(path: Path):
    text = path.read_text(encoding="utf-8")
    t = re.search(r"<title[^>]*>(.*?)</title>", text, re.S)
    d = re.search(r'<meta name="description" content="(.*?)">', text, re.S)
    title = html.unescape(t.group(1)).strip() if t else path.stem
    desc = html.unescape(d.group(1)).strip() if d else title
    return title, desc


def item_xml(title, link, desc, dt, category) -> str:
    return (
        "  <item>\n"
        f"    <title>{escape(title)}</title>\n"
        f"    <link>{escape(link)}</link>\n"
        f"    <guid isPermaLink=\"true\">{escape(link)}</guid>\n"
        f"    <pubDate>{format_datetime(dt)}</pubDate>\n"
        f"    <author>calrank</author>\n"
        f"    <category>{escape(category)}</category>\n"
        f"    <description>{escape(desc)}</description>\n"
        "  </item>"
    )


def main():
    dates = created_dates()
    today = datetime.now(KST).date().isoformat()
    events = json.loads((ROOT / "events.json").read_text(encoding="utf-8"))

    items = []  # (datetime, xml)

    cols = []
    for p in ROOT.glob("column-*.html"):
        iso = dates.get(p.name)
        if iso:
            cols.append((datetime.fromisoformat(iso), p))
    for dt, p in sorted(cols, key=lambda x: x[0], reverse=True)[:MAX_COLUMNS]:
        title, desc = page_meta(p)
        items.append((dt, item_xml(title, f"{SITE}/{p.name}", desc, dt, "칼럼")))

    evs = []
    for e in events:
        if (e.get("date") or "") < today:
            continue
        rel = f"e/{e['id']}.html"
        iso = dates.get(rel)
        if iso and (ROOT / rel).exists():
            evs.append((datetime.fromisoformat(iso), e.get("date"), e, rel))
    # 최근 생긴 순, 같은 날이면 대회일이 가까운 순
    evs.sort(key=lambda x: (-x[0].timestamp(), x[1]))
    for dt, _, e, rel in evs[:MAX_EVENTS]:
        title, desc = page_meta(ROOT / rel)
        items.append((dt, item_xml(title, f"{SITE}/e/{quote(e['id'])}.html", desc, dt,
                                   e.get("sportLabel") or "대회")))

    items.sort(key=lambda x: x[0], reverse=True)
    newest = items[0][0] if items else datetime.now(KST)
    rss = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>\n'
        "  <title>calrank — 전종목 대회 캘린더 새 소식</title>\n"
        f"  <link>{SITE}/index.html</link>\n"
        "  <description>마라톤·자전거·트레일러닝·철인3종·인라인 대회 일정과 새 칼럼을 알려드립니다.</description>\n"
        "  <language>ko</language>\n"
        f"  <lastBuildDate>{format_datetime(newest)}</lastBuildDate>\n"
        f'  <atom:link href="{SITE}/rss.xml" rel="self" type="application/rss+xml"/>\n'
        "  <generator>calrank</generator>\n"
        + "\n".join(x for _, x in items) +
        "\n</channel></rss>\n"
    )
    out = ROOT / "rss.xml"
    if not out.exists() or out.read_text(encoding="utf-8") != rss:
        out.write_text(rss, encoding="utf-8")
    print(f"[rss] 칼럼 {min(len(cols), MAX_COLUMNS)}개 + 대회 {min(len(evs), MAX_EVENTS)}개 = {len(items)}개 항목")


if __name__ == "__main__":
    main()

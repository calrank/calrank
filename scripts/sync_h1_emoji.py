"""허브·목록 페이지의 제목(h1) 앞에 이모지를 하나씩 붙인다. 멱등이라 여러 번 돌려도 같다.

크기·정렬은 style.css 의 .emo 한 곳에서만 정한다. 제목 안에 다른 태그가 있는 페이지
(첫 화면의 종목 줄 등)는 줄 구성이 깨질 수 있어 건드리지 않는다.
sync_nav 와 같이 워크플로에서 매번 돌려, 생성기가 이모지 없는 제목을 다시 써도 교정되게 한다.
"""
import re
import sys
from pathlib import Path

from site_emoji import emo

ROOT = Path(__file__).resolve().parent.parent
# 파일 이름(앞부분) → 이모지. 월별 페이지처럼 이름이 여럿인 것은 접두어로 맞춘다.
BY_FILE = {
    "gear.html": "running-shoe", "grade.html": "sports-medal", "column.html": "memo",
    "regions.html": "round-pushpin", "running-weather.html": "sun-behind-small-cloud",
    "level.html": "stopwatch", "guides.html": "books", "goals.html": "stopwatch",
    "distances.html": "person-running", "ranking.html": "trophy", "myrank.html": "chart-increasing",
    "news.html": "newspaper", "saved-events.html": "red-heart",
}
BY_PREFIX = [("monthly", "calendar"), ("trail-monthly", "calendar"), ("cycling-monthly", "calendar"),
             ("triathlon-monthly", "calendar"), ("grade-", "sports-medal"), ("goal-", "stopwatch"),
             ("landing-", "round-pushpin"), ("guide-", "books"), ("column-", "memo")]
H1_RE = re.compile(r'(<h1\b[^>]*>)([^<]*)(</h1>)')
LEAD_TEXT_EMOJI = re.compile(r'^[\s❤️🤍]+')


def pick(name: str):
    if name in BY_FILE:
        return BY_FILE[name]
    for pre, em in BY_PREFIX:
        if name.startswith(pre):
            return em
    return None


def apply(html: str, name: str) -> str:
    em = pick(name)
    if not em:
        return html
    m = H1_RE.search(html)
    if not m or '<img class="emo"' in m.group(2):
        return html
    text = LEAD_TEXT_EMOJI.sub("", m.group(2)) if name == "saved-events.html" else m.group(2)
    return html[:m.start()] + m.group(1) + emo(em) + text + m.group(3) + html[m.end():]


def main() -> None:
    check = "--check" in sys.argv
    changed = []
    for f in sorted(ROOT.glob("*.html")):
        s = f.read_text(encoding="utf-8")
        new = apply(s, f.name)
        if new != s:
            changed.append(f.name)
            if not check:
                f.write_text(new, encoding="utf-8")
    print(f"[h1-emoji] 제목에 이모지를 붙인 페이지 {len(changed)}개")
    if check and changed:
        print("      " + ", ".join(changed[:10]))
        sys.exit(1)


if __name__ == "__main__":
    main()

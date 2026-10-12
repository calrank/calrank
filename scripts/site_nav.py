"""사이트 목차(헤더 네비게이션)를 한 곳에서 정의한다.

전에는 생성기 9개와 손으로 만든 페이지들이 각자 목차를 적고 있었다.
그래서 114개 페이지에 목차가 8종류로 갈라져 있었다. 칼럼을 누르면
"지역별"이 사라지고, 등급표를 누르면 "등급표"가 사라지는 식이었다.

이제 목차를 바꾸려면 이 파일만 고치면 된다. 생성기는 site_header() 를
부르고, 손으로 만든 페이지는 scripts/sync_nav.py 로 한꺼번에 맞춘다.
"""

# (링크, 글자, 활성 표시에 쓰는 이름)
NAV_ITEMS = [
    ("index.html", "캘린더", "calendar"),
    ("regions.html", "지역별", "regions"),
    ("ranking.html", "대회랭킹", "ranking"),
    ("news.html", "종목뉴스", "news"),
    ("column.html", "칼럼", "column"),
    ("grade.html", "등급표", "grade"),
    ("myrank.html", "내 랭크", "myrank"),
]

# 어느 페이지가 어느 메뉴에 속하는지. 파일 이름 앞부분으로 찾는다.
ACTIVE_BY_PREFIX = [
    ("column", "column"),
    ("grade", "grade"),
    ("myrank", "myrank"),
    ("news", "news"),
    ("ranking", "ranking"),
    ("regions", "regions"),
    ("landing-", "regions"),
    ("saved-events", "saved"),
    ("events-index", "calendar"),
    ("events-archive", "calendar"),
    ("monthly", "calendar"),
    ("trail-monthly", "calendar"),
    ("cycling-monthly", "calendar"),
    ("open-registration", "calendar"),
    ("kids-marathon", "calendar"),
    ("ultra-marathon", "calendar"),
    ("night-run", "calendar"),
    ("walking-events", "calendar"),
    ("aquathlon", "calendar"),
    ("index", "calendar"),
    # 기록증 판독·등급 계산기는 등급표 묶음이다
    ("cert", "grade"),
    ("level", "grade"),
    ("zone2-heart-rate", "grade"),
    ("record-issue-diagnosis", "grade"),
    ("distances", "calendar"),
    ("triathlon-monthly", "calendar"),
    ("race-finder-quiz", "calendar"),
    ("race-checklist", "calendar"),
]


def active_for(filename: str) -> str:
    """파일 이름으로 어느 메뉴를 켤지 고른다. 못 찾으면 아무것도 켜지 않는다."""
    name = str(filename or "").rsplit("/", 1)[-1]
    for prefix, key in sorted(ACTIVE_BY_PREFIX, key=lambda kv: -len(kv[0])):
        if name.startswith(prefix):
            return key
    return ""


def nav_html(active: str = "") -> str:
    """<nav class="main-nav"> … </nav>"""
    rows = []
    for href, label, key in NAV_ITEMS:
        cls = "nav-link active" if key == active else "nav-link"
        rows.append(f'<a href="{href}" class="{cls}">{label}</a>')
    saved_cls = "nav-link nav-link-saved" + (" active" if active == "saved" else "")
    rows.append(f'<a href="saved-events.html" class="{saved_cls}">'
                '❤️<span class="nav-text-full"> 찜한 대회</span></a>')
    rows.append('<a href="contact.html" class="nav-contact-link">제휴문의</a>')
    return '<nav class="main-nav">\n' + "\n".join(rows) + "\n</nav>"


def site_header(active: str = "") -> str:
    """헤더 전체."""
    return ('<header class="site-header">\n'
            '<div class="wrap header-inner">\n'
            '<a href="index.html" class="wordmark">CALRANK</a>\n'
            + nav_html(active) + "\n"
            "</div>\n</header>")

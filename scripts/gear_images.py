"""기어 페이지 대표 사진. Unsplash 라이선스 사진을 images.unsplash.com 주소로 바로 불러온다.
(Unsplash 가 권하는 방식이라 파일을 내려받아 두지 않는다. 사진을 바꾸려면 아래 값만 고치면 된다.)"""
import re

IMG = {
    "sole":    ("1548801133-da353ebb1d97", "러닝화 밑창 바닥면", "j7zu2kpTnwY", "Ryan Waring"),
    "plate":   ("1755194757953-a9301005114b", "러닝화 옆모습과 밑창", "p5C9ZTeDzko", "Fujiphilm"),
    "store":   ("1633464130613-0a9154299ac2", "매장 벽면에 진열된 신발", "O8_sTTWaJ14", "Mick Haupt"),
    "shoe":    ("1571008887538-b36bb32f4571", "러닝화 한 켤레", "XiZ7pRvCzro", "sporlab"),
    "shoe2":   ("1542291026-7eec264c27ff", "빨간 러닝화 한 짝", "164_6wVEHfI", ""),
    "race5":   ("1759674861540-afed9f86f94a", "레이스 중인 러너들", "W2pBsQaT6FQ", ""),
    "half":    ("1758684051120-60735855c088", "도로 위를 달리는 마라톤 러너", "0-di3PxkxTQ", "Quan-You Zhang"),
    "full":    ("1760315972424-1637530daead", "마라톤 출발 무리", "laxDhpYqZZc", ""),
    "poles":   ("1623783593139-f4f36b7bbb2f", "트레일 폴을 쥔 손", "zW8NsaUruMU", ""),
    "slope":   ("1518214598173-1666bc921d66", "언덕 위의 러너", "CVvFVQ_-oUg", ""),
    "pack":    ("1635745488837-ffa006eaf9cf", "배낭을 멘 채 걷는 사람", "hHdJNsiCzfI", ""),
    "jacket":  ("1548883354-94bcfe321cbb", "후드가 달린 방수 재킷을 입은 사람", "6TIoPIpMvLc", "Kyle Loftus"),
    "kit":     ("1562571373-e12c2f3a53ec", "트레일 레이스를 준비하는 러너", "tT-SvVAbK_w", "Zan Lazarevic"),
    "wheel":   ("1540838005002-0bb3287af8ae", "자전거 바퀴", "9oYHSMxt7tg", "Clint McKoy"),
    "tyre":    ("1523357585206-175e971f2ad9", "자전거 타이어", "cAY9X4rPG3g", "Alessandra Caretto"),
    "helmet":  ("1749174899667-4553e4f248e2", "헬멧을 쓰고 달리는 사이클리스트", "tO0E-LxByjw", "Ricardo IV Tamayo"),
    "road":    ("1623858898311-55c0c487f5f9", "로드 레이싱 자전거", "vj4Qi9ToRXQ", "Markus Spiske"),
    "saddle":  ("1722546487377-abae21517fe6", "자전거 안장", "d_slcwt-6Us", "Jason Ng"),
    "frame":   ("1721909749841-2280947e91ec", "로드바이크 프레임", "5KJ8UGxY2Ss", "Acelane Bikes"),
    "tribike": ("1516820612845-a13894592046", "레이스 중인 사이클리스트", "fZglO1JkwoM", "Jacek Dylag"),
    "wetsuit": ("1572882657877-2babd674b3e5", "웻슈트를 입은 사람", "4REu755ehEQ", ""),
    "wetbeach": ("1619707282084-b63b3336f5ef", "웻슈트를 입고 서 있는 사람", "ad0ms1fF8Hc", ""),
    "swimstart": ("1628689529124-3e0db67e984c", "철인3종 수영 출발", "Vr3Xi8_2NgY", "Ashley de Lotz"),
    "openwater": ("1658748721978-68fc04f3739b", "오픈워터를 헤엄치는 사람들", "XcvocqxlQ-A", "Markus Spiske"),
    "skate":   ("1707126755171-28ca4aeb3150", "인라인 스케이트 한 켤레", "52mu-L69Uzc", ""),
    "skate2":  ("1571032800240-1cc2e680b00c", "롤러 스케이트 한 짝", "hyvIttJtKPI", "Luke Southern"),
}

# Wikimedia Commons 사진(공개 도메인·CC BY). 촬영자와 라이선스를 사진 아래에 적는다.
CC2 = ("CC BY 2.0", "https://creativecommons.org/licenses/by/2.0/")
PD = ("공개 도메인", "")
COMMONS = {
    "tri-helmet": ("Couple_preparing_for_bike_ride.jpg", "자전거 타기 전에 헬멧을 쓴 두 사람", "Bill Branson", PD),
    "tri-draft":  ("USMC-110925-M-0992R-275.jpg", "철인3종 경기 자전거 구간", "미 해병대", PD),
    "tri-bib":    ("A_Photo_by_William_W._Ward,_\"Untitled.\"_(15162148422).jpg", "배번을 단 철인3종 선수", "Billie Grace Ward", CC2),
    "tri-swim":   ("Swim_start_Ironman_Brazil_2011.jpg", "아이언맨 수영 출발 모습", "Arcadiuš", CC2),
}

def commons_url(k, w):
    import urllib.parse
    return "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(COMMONS[k][0]) + f"?width={w}"

def commons_page(k):
    import urllib.parse
    return "https://commons.wikimedia.org/wiki/File:" + urllib.parse.quote(COMMONS[k][0])

def commons_fig(k, cls="gi-hero-img"):
    f, alt, who, lic = COMMONS[k]
    l = f'<a href="{lic[1]}" rel="noopener" target="_blank">{lic[0]}</a>' if lic[1] else lic[0]
    return (f'<figure class="{cls}"><img src="{commons_url(k,960)}" alt="{alt}" loading="lazy" decoding="async">'
            f'<figcaption>사진 {who} · {l} · <a href="{commons_page(k)}" rel="noopener" target="_blank">Wikimedia Commons</a></figcaption></figure>')

# 페이지마다 그 페이지가 다루는 물건이 보이는 사진을 따로 고른다.
SLUG = {
    "gear-wa-stack-height": "plate", "gear-wa-rigid-plate": "sole", "gear-wa-availability": "store",
    "gear-carbon-plate": "shoe", "gear-carbon-plate-5km": "race5", "gear-carbon-plate-10km": "race5",
    "gear-carbon-plate-half": "half", "gear-carbon-plate-full": "full", "gear-shoe-mass": "shoe2",
    "gear-utmb-jacket": "jacket", "gear-utmb-kit": "kit", "gear-trail-poles": "poles",
    "gear-trail-poles-by-gradient": "pack", "gear-trail-pack-weight": "kit",
    "gear-aero-wheel": "wheel", "gear-aero-wheel-40km": "wheel", "gear-aero-wheel-100km": "wheel",
    "gear-tyre-rolling": "tyre", "gear-tyre-rolling-40km": "tyre", "gear-tyre-rolling-100km": "tyre",
    "gear-aero-helmet": "helmet", "gear-aero-helmet-40km": "helmet", "gear-aero-helmet-100km": "helmet",
    "gear-uci-min-weight": "road", "gear-uci-saddle-setback": "saddle", "gear-uci-frame-approval": "frame",
    "gear-wt-bike-agegroup": "tribike", "gear-wt-wetsuit-thickness": "tri-swim", "gear-wetsuit": "wetbeach",
    "gear-wt-wetsuit-temp": "openwater", "gear-wetsuit-by-temp": "swimstart",
    "gear-ws-wheel-diameter": "skate", "gear-inline-bearings": "skate",
}

# 사진마다 잘려도 되는 쪽이 다르다. 기본은 위쪽 가까이(머리·배낭이 위에 있는 사진이 많다).
POS = {}

def group_of(s):
    g = SLUG.get(s.replace(".html", ""))
    return g

def image_url(slug):
    g = group_of(slug)
    if g in COMMONS: return commons_url(g, 1200)
    return url(g, 1200) if g else None

def url(g, w):
    return f"https://images.unsplash.com/photo-{IMG[g][0]}?auto=format&fit=crop&w={w}&q=70"

def add_image(slug, html):
    g = group_of(slug)
    if not g or "gi-hero-img" in html:
        return html
    if g in COMMONS:
        og = f'<meta property="og:image" content="{commons_url(g,1200)}">\n<meta name="twitter:image" content="{commons_url(g,1200)}">\n'
        html = html.replace('<meta name="twitter:card"', og + '<meta name="twitter:card"', 1)
        return html.replace("</section>\n", "</section>\n\n" + commons_fig(g) + "\n", 1)
    pid, alt, ph, who = IMG[g]
    og = f'<meta property="og:image" content="{url(g,1200)}">\n<meta name="twitter:image" content="{url(g,1200)}">\n'
    html = html.replace('<meta name="twitter:card"', og + '<meta name="twitter:card"', 1)
    # 대표 사진이 화면 맨 위라 가장 큰 요소(LCP)다. 연결을 미리 열고 먼저 받는다.
    pre = ('<link rel="preconnect" href="https://images.unsplash.com">\n'
           f'<link rel="preload" as="image" href="{url(g, 960)}" fetchpriority="high">\n')
    html = html.replace('<link rel="canonical"', pre + '<link rel="canonical"', 1)
    credit = f' · 사진 {who}' if who else ''
    fig = (f'<figure class="gi-hero-img"><img src="{url(g,960)}" width="960" height="640" '
           f'alt="{alt}" decoding="async" fetchpriority="high">'
           f'<figcaption><a href="https://unsplash.com/photos/{ph}" rel="noopener" target="_blank">Unsplash</a>{credit}</figcaption></figure>\n')
    return html.replace("</section>\n", "</section>\n\n" + fig, 1)

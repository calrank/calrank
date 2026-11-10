"""기어 페이지 대표 사진. Unsplash 라이선스 사진을 images.unsplash.com 주소로 바로 불러온다.
(Unsplash 가 권하는 방식이라 파일을 내려받아 두지 않는다. 사진을 바꾸려면 아래 값만 고치면 된다.)"""
import re

IMG = {
    "shoe":   ("1571008887538-b36bb32f4571", "러닝화 한 켤레", "XiZ7pRvCzro", "sporlab"),
    "poles":  ("1623783593139-f4f36b7bbb2f", "트레일 폴을 쥔 손", "zW8NsaUruMU", ""),
    "pack":   ("1635745488837-ffa006eaf9cf", "배낭을 멘 채 걷는 사람", "hHdJNsiCzfI", ""),
    "trail":  ("1718248028293-934f04a578db", "트레일을 달리는 러너", "-UYedjT31zY", ""),
    "wheel":  ("1540838005002-0bb3287af8ae", "자전거 바퀴", "9oYHSMxt7tg", "Clint McKoy"),
    "tyre":   ("1523357585206-175e971f2ad9", "자전거 타이어", "cAY9X4rPG3g", "Alessandra Caretto"),
    "helmet": ("1749174899667-4553e4f248e2", "헬멧을 쓰고 달리는 사이클리스트", "tO0E-LxByjw", "Ricardo IV Tamayo"),
    "road":   ("1623858898311-55c0c487f5f9", "로드 레이싱 자전거", "vj4Qi9ToRXQ", "Markus Spiske"),
    "wetsuit": ("1572882657877-2babd674b3e5", "웻슈트를 입은 사람", "4REu755ehEQ", ""),
    "inline": ("1707126755171-28ca4aeb3150", "인라인 스케이트 한 켤레", "52mu-L69Uzc", ""),
}

def group_of(s):
    if "wetsuit" in s or s == "gear-wt-wetsuit-temp.html":
        return "wetsuit"
    if "bike-agegroup" in s or s.startswith("gear-uci-"):
        return "road"
    if "poles" in s:
        return "poles"
    if "pack" in s:
        return "pack"
    if "trail" in s or "utmb" in s:
        return "trail"
    if "aero-wheel" in s:
        return "wheel"
    if "tyre" in s:
        return "tyre"
    if "aero-helmet" in s:
        return "helmet"
    if "inline" in s or s.startswith("gear-ws-"):
        return "inline"
    if "carbon" in s or "shoe" in s or s.startswith("gear-wa-"):
        return "shoe"
    return None

def url(g, w):
    return f"https://images.unsplash.com/photo-{IMG[g][0]}?auto=format&fit=crop&w={w}&q=70"

def add_image(slug, html):
    g = group_of(slug)
    if not g or "gi-hero-img" in html:
        return html
    pid, alt, ph, who = IMG[g]
    og = f'<meta property="og:image" content="{url(g,1200)}">\n<meta name="twitter:image" content="{url(g,1200)}">\n'
    html = html.replace('<meta name="twitter:card"', og + '<meta name="twitter:card"', 1)
    credit = f' · 사진 {who}' if who else ''
    fig = (f'<figure class="gi-hero-img"><img src="{url(g,960)}" width="960" height="640" '
           f'alt="{alt}" decoding="async" fetchpriority="high">'
           f'<figcaption><a href="https://unsplash.com/photos/{ph}" rel="noopener" target="_blank">Unsplash</a>{credit}</figcaption></figure>\n')
    return html.replace("</section>\n", "</section>\n\n" + fig, 1)

"""field.html(코스 현장 보기)을 만든다. 머리·바닥은 kit.html 것을 그대로 가져와 사이트 공통 틀과 맞춘다.

실행 뒤에는 python3 scripts/sync_all.py 로 끼워 넣는 블록을 복구한다(다른 생성기와 같다).
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
kit = (ROOT / "kit.html").read_text(encoding="utf-8")

TITLE = "코스 현장 보기 — 달리는 중 지금 오르막인지 내리막인지 한눈에 | 칼랭크 CALRANK"
DESC = ("트레일·둘레길 코스에서 지금 평지, 오르막, 내리막 중 어디인지와 다음 지형 변화까지 남은 거리를 큰 글씨로 보여 줍니다. "
        "GPS로 코스 위 내 위치를 확인하고, 계산은 내 기기 안에서만 합니다.")
URL = "https://calrank.kr/field.html"

FAQ = [
    ("지금 평지, 오르막, 내리막은 어떤 기준으로 나누나요?",
     "평균 경사 3% 이상이고 길이 500m 이상인 구간을 오르막이나 내리막으로 봅니다. Garmin ClimbPro가 오르막으로 치는 최소 길이 500m와 최소 평균 경사 3%를 참고했습니다. 연구 결과가 아니라 달리는 중에 읽기 쉽도록 칼랭크가 정한 표시 기준입니다."),
    ("내 위치가 코스와 맞는지는 어떻게 알 수 있나요?",
     "GPS를 켜면 코스 선에서 몇 m 떨어져 있는지와 기기가 알려 주는 GPS 오차를 함께 보여 줍니다. 오차 25m 이하이고 코스에서 30m 이내면 코스 위로 보고, 그보다 어긋나면 갈림길에서 표지판과 함께 확인하라고 안내합니다. 코스에서 100m 넘게 벗어나면 벗어났다고 알립니다."),
    ("인터넷이 없는 산에서도 쓸 수 있나요?",
     "GPS 위치는 통신이 없어도 잡히지만, 코스 자료는 처음 열 때 받아 옵니다. 출발 전에 같은 기기로 한 번 열어 두세요. 오프라인 저장은 준비 중이라 지금은 보장하지 못합니다."),
    ("화면이 꺼지지 않게 할 수 있나요?",
     "GPS를 켜면 브라우저의 화면 켜짐 유지 기능(Screen Wake Lock)을 요청합니다. 다른 앱으로 넘어가거나 화면이 가려지면 풀리고, 절전 모드에서는 지원되지 않을 수 있습니다."),
    ("내 위치가 서버로 전송되나요?",
     "아니요. 위치와 계산은 이 기기의 브라우저 안에서만 처리하고 칼랭크 서버로 보내지 않습니다."),
    ("해발과 오르막 값은 얼마나 정확한가요?",
     "코스의 고도는 공공자료로 계산한 값이라 실제와 차이가 있을 수 있는 참고용입니다. 웹에서는 기압계를 쓸 수 없어서, 현재 해발도 코스 자료의 값이며 GPS 고도와 비교하지 않습니다."),
]

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

head, rest = kit.split("</head>", 1)
body_head, rest2 = rest.split('<main class="tp">', 1)
_, footer = rest2.split("</main>", 1)

def sub(pat, rep, s, flags=0):
    new, n = re.subn(pat, lambda m: rep, s, count=1, flags=flags)
    assert n == 1, pat
    return new

head = sub(r"<title>.*?</title>", f"<title>{esc(TITLE)}</title>", head, re.S)
head = sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{esc(DESC)}">', head)
head = sub(r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{URL}">', head)
head = sub(r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{esc(TITLE)}">', head)
head = sub(r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{esc(DESC)}">', head)
head = sub(r'<meta property="og:url" content="[^"]*">', f'<meta property="og:url" content="{URL}">', head)
head = re.sub(r'<script type="application/ld\+json">.*?</script>\n?', "", head, flags=re.S)
head = head.replace('<link rel="stylesheet" href="tools.css">', '<link rel="stylesheet" href="tools.css">\n<link rel="stylesheet" href="field.css">', 1)
ld = [
    {"@context": "https://schema.org", "@type": "WebApplication", "name": "코스 현장 보기", "url": URL, "applicationCategory": "SportsApplication",
     "operatingSystem": "All", "inLanguage": "ko-KR", "description": DESC, "offers": {"@type": "Offer", "price": "0", "priceCurrency": "KRW"},
     "isPartOf": {"@type": "WebSite", "name": "calrank", "url": "https://calrank.kr/"}},
    {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ]},
    {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "calrank", "item": "https://calrank.kr/index.html"},
        {"@type": "ListItem", "position": 2, "name": "트레일루트", "item": "https://calrank.kr/trailroot.html"},
        {"@type": "ListItem", "position": 3, "name": "코스 현장 보기"}]},
]
head += "".join(f'<script type="application/ld+json">{json.dumps(o, ensure_ascii=False, separators=(",", ":"))}</script>\n' for o in ld)

faq_html = "".join(f"<h3>{esc(q)}</h3><p>{esc(a)}</p>" for q, a in FAQ)
main = f'''<main class="tp fd">
<h1 class="tp-title"><img class="emo" src="/emoji/mountain.svg" alt="" width="24" height="24" decoding="async" aria-hidden="true">코스 현장 보기</h1>
<p class="tp-sub">달리는 중에 보는 화면입니다. 지금 평지인지 오르막인지 내리막인지, 다음 지형이 바뀌기까지 얼마나 남았는지를 큰 글씨로 보여 줍니다. 위치와 계산은 이 기기 안에서만 처리합니다.</p>
<p class="fd-msg" id="fdMsgTop" role="status"></p>

<section class="fd-card" id="fdPick">
<h3>코스 고르기</h3>
<input class="fd-q" id="fdQ" type="search" inputmode="search" placeholder="코스 이름이나 지역" aria-label="코스 이름이나 지역으로 찾기" autocomplete="off">
<ul class="fd-list" id="fdList"></ul>
<p class="fd-small">트레일·둘레길 코스 149곳의 자료가 있습니다. 대회 코스는 공식 GPX 파일을 구할 수 있을 때 같은 화면으로 확장할 예정입니다.</p>
</section>

<div id="fdApp" hidden>
<div class="fd-top"><h2 id="fdName"></h2><span id="fdTotal"></span></div>
<section class="fd-hero" id="fdHero" data-t="flat">
<p class="fd-now" id="fdNow"></p>
<div class="fd-state"><i id="fdGlyph"></i><b id="fdState"></b></div>
<p class="fd-big" id="fdBig"></p>
<div class="fd-stats">
<div><b id="fdGain">-</b><span>남은 상승</span></div>
<div><b id="fdGrade">-</b><span>남은 평균 경사</span></div>
<div><b id="fdElev">-</b><span>현재 해발</span></div>
</div>
<p class="fd-next" id="fdNext"></p>
</section>

<section class="fd-card"><h3>코스 모양과 내 위치</h3>
<div id="fdMini"></div>
<div class="fd-row" role="group" aria-label="지도 확대">
<button type="button" class="fd-btn" data-z="0" aria-pressed="true">전체</button>
<button type="button" class="fd-btn" data-z="1" aria-pressed="false">앞뒤 1km</button>
<button type="button" class="fd-btn" data-z="2" aria-pressed="false">앞뒤 250m</button>
</div>
<p class="fd-conf" id="fdConf" data-s="manual" aria-live="polite"></p>
</section>

<section class="fd-card"><h3>코스 전체 고도</h3><div id="fdChart"></div></section>

<section class="fd-card"><h3>내 위치</h3>
<input class="fd-pos" id="fdPos" type="range" min="0" step="50" value="0" aria-label="코스에서 내 위치">
<div class="fd-row"><button type="button" class="fd-btn" id="fdBack">100m 뒤로</button><button type="button" class="fd-btn" id="fdFwd">100m 앞으로</button></div>
<div class="fd-row"><button type="button" class="fd-btn main" id="fdGps">GPS로 따라가기</button></div>
<p class="fd-msg" id="fdMsg" role="status"></p>
</section>

<section class="fd-card"><h3>구간 한눈에</h3><ul class="fd-segs" id="fdSegs"></ul></section>
<p class="fd-small"><a href="field.html" id="fdOther">다른 코스 고르기</a></p>
<p class="fd-small" id="fdSrc"></p>
</div>

<section class="tp-card"><h2 class="tp-h2">이 화면이 보여 주는 것과 한계</h2>
<p class="tp-p">코스를 평지, 오르막, 내리막으로 나누고, 지금 위치에서 현재 구간이 끝나기까지의 거리와 남은 상승, 다음 구간을 보여 줍니다. 1km마다 평균 경사를 적은 표는 한 구간 안의 오르막과 내리막을 섞어 버려서 달리는 중에 읽기 어렵기 때문에, 지형이 바뀌는 곳에서 나누었습니다.</p>
<p class="tp-p">오르막과 내리막은 평균 경사 3% 이상, 길이 500m 이상일 때만 세며, Garmin ClimbPro의 최소 기준을 참고한 표시 기준입니다(<a href="https://www8.garmin.com/manuals/webhelp/GUID-16B12CFE-F96E-4DE9-9F5F-8C4A5936D3B9/EN-US/GUID-EBAEC138-B55A-4730-8C10-DF21A40302A9.html" rel="noopener" target="_blank">Garmin 매뉴얼</a>). 평균 경사 10% 이상이면 급경사로 따로 표시합니다.</p>
<p class="tp-p">코스의 고도와 경로는 한국관광공사 두루누비 코스 정보(공공데이터포털)로 계산했고, 실제와 차이가 있을 수 있는 참고용입니다. 시계나 사이클 컴퓨터를 대신하는 것이 아니라 보조 화면으로 써 주세요.</p></section>
<section class="tp-sec tp-faq"><h2 class="tp-h2">자주 묻는 것</h2>{faq_html}</section>
</main>'''

tail = footer
tail = re.sub(r'<script src="gear-rules.js"></script>\s*<script src="calrank-local.js"></script>\s*<script src="source-watch.js"></script>\s*<script src="kit.js"></script>',
              '<script src="field.js"></script>', tail)
assert 'field.js' in tail
(ROOT / "field.html").write_text(head + "</head>" + body_head + main + tail, encoding="utf-8")
print("field.html 생성")

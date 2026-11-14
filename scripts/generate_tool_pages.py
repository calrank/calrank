"""도구 페이지 세 개를 만든다: kit.html(내 장비 서랍), age-curve.html(나이 곡선), ledger.html(예상 기록 노트).

머리말·바닥글은 gear-prices.html 에서 그대로 가져온다. 끝낸 뒤 sync_all.py 를 돌려야 한다.
여러 번 돌려도 같은 결과가 나온다.
"""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://calrank.vercel.app/"
SRC = (ROOT / "gear-prices.html").read_text(encoding="utf-8")
HEAD_COMMON = SRC[SRC.find('<link rel="preconnect"'):SRC.find('<link rel="stylesheet" href="style.css">')]
HEADER = SRC[SRC.find('<header class="site-header">'):SRC.find('</header>') + 9]
FOOTER = SRC[SRC.find('<footer class="site-footer">'):SRC.find('</footer>') + 9]
HEADER = HEADER.replace('class="nav-link active"', 'class="nav-link"').replace(
    '<a href="gear.html" class="nav-link">', '<a href="gear.html" class="nav-link active">')


def ld(o):
    return '<script type="application/ld+json">' + json.dumps(o, ensure_ascii=False, separators=(",", ":")) + "</script>"


def faq_ld(items):
    return ld({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": re.sub("<[^>]+>", "", a)}} for q, a in items]})


def page(slug, title, desc, h1, sub, body, scripts, faq, crumb=("기어", "gear.html"), place=None, modified=None):
    app_name = h1
    url = BASE + slug
    crumbs = ld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "calrank", "item": BASE + "index.html"},
        {"@type": "ListItem", "position": 2, "name": crumb[0], "item": BASE + crumb[1]},
        {"@type": "ListItem", "position": 3, "name": app_name}]})
    if place:
        pl = {"@type": place["type"], "name": place["name"],
              "geo": {"@type": "GeoCoordinates", "latitude": place["lat"], "longitude": place["lon"]}}
        if place.get("ele") is not None:
            pl["geo"]["elevation"] = place["ele"]
        if place.get("region"):
            pl["address"] = {"@type": "PostalAddress", "addressCountry": "KR", "addressRegion": place["region"]}
        wp = {"@context": "https://schema.org", "@type": "WebPage", "name": app_name, "url": url, "inLanguage": "ko-KR",
              "description": desc, "about": pl, "isPartOf": {"@type": "WebSite", "name": "칼랭크", "url": BASE}}
        if modified:
            wp["dateModified"] = modified
        app = ld(wp)
    else:
        app = ld({"@context": "https://schema.org", "@type": "WebApplication", "name": app_name, "url": url,
                  "applicationCategory": "HealthApplication", "operatingSystem": "All", "inLanguage": "ko-KR",
                  "description": desc, "offers": {"@type": "Offer", "price": "0", "priceCurrency": "KRW"},
                  "isPartOf": {"@type": "WebSite", "name": "calrank", "url": BASE}})
    faq_html = '<section class="tp-sec tp-faq"><h2 class="tp-h2">자주 묻는 것</h2>' + "".join(
        f"<h3>{q}</h3><p>{a}</p>" for q, a in faq) + "</section>"
    scr = "\n".join(f'<script src="{s}"></script>' for s in scripts)
    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | 칼랭크 CALRANK</title>
<meta name="description" content="{desc}">
{HEAD_COMMON}<link rel="stylesheet" href="style.css">
<link rel="stylesheet" href="tools.css">
<script defer src="/_vercel/insights/script.js"></script>
<script defer src="/track.js"></script>
<link rel="canonical" href="{url}">
<meta property="og:title" content="{title} | 칼랭크 CALRANK">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}og-image.png">
<meta property="og:locale" content="ko_KR">
<meta property="og:site_name" content="칼랭크 CALRANK">
<meta name="twitter:card" content="summary">
{app}
{faq_ld(faq)}
{crumbs}
</head>
<body>

{HEADER}

<main class="tp">
<h1 class="tp-title">{h1}</h1>
<p class="tp-sub">{sub}</p>
{body}
{faq_html}
</main>

{FOOTER}
{scr}
</body>
</html>
'''


KIT = page(
    "kit.html", "내 장비 서랍 — 가진 장비가 연맹 규정에 맞는지 한 번에",
    "신발 두께, 자전거 무게, 웻슈트 두께 같은 내 장비 수치를 한 번 적어 두면 세계육상·UCI·월드트라이애슬론·UTMB 규정에 맞는지 바로 판정합니다. 값은 내 기기에만 저장됩니다.",
    "내 장비 서랍",
    "가진 장비의 수치를 한 번 적어 두면, 연맹 규정에 맞는지 한 화면에서 봅니다. 적은 값은 이 기기의 브라우저에만 저장되고 서버로 가지 않습니다.",
    '''<div id="kitChanges" class="tp-alert" hidden></div>
<p id="kitSummary" class="tp-note" role="status" aria-live="polite">불러오는 중입니다.</p>
<div id="kitList"></div>
<p class="tp-small" id="kitStore"></p>
<p><button type="button" class="tp-btn ghost" id="kitClear">저장된 수치 지우기</button></p>
<section class="tp-card"><h2 class="tp-h2">내 신발이 공식 목록에 있는지</h2>
<p class="tp-p">월드애슬레틱스는 2024년 6월에 신발 확인 웹앱을 열어 승인된 대회용 신발을 검색할 수 있게 했고, 승인되면 바로 목록에 추가된다고 밝혔습니다(700종 이상 등재, 월드애슬레틱스 보도자료). 연맹 규정이 적용되는 대회에 나간다면 신발 모델명을 한 번 확인해 보세요. 동호인 대회에는 적용되지 않는 경우가 많으니 대회 요강을 먼저 보시면 됩니다.</p>
<p class="tp-p"><a href="https://certcheck.worldathletics.org/" rel="noopener" target="_blank">World Athletics 신발 확인 열기</a> · <a href="https://worldathletics.org/news/press-releases/world-athletics-launches-shoe-check-application" rel="noopener" target="_blank">출시 보도자료</a></p></section>
<p class="tp-src">규정의 출처와 기준 시점은 각 항목의 &lsquo;판정 자세히&rsquo;에서 원문 링크와 함께 확인할 수 있습니다. 대회 요강이 연맹 규정보다 엄격할 수 있어, 출전 전에는 요강도 확인해 주세요.</p>''',
    ["gear-rules.js", "calrank-local.js", "source-watch.js", "kit.js"],
    [("적은 수치는 어디에 저장되나요?", "이 기기의 브라우저 안(localStorage)에만 저장됩니다. 칼랭크 서버로 보내지 않아서 다른 기기에서는 보이지 않고, 브라우저 데이터를 지우면 함께 지워집니다."),
     ("규정이 바뀌면 알려 주나요?", "칼랭크가 가진 규정 값이 지난번에 본 때와 달라졌으면 이 페이지를 열었을 때 알려 드립니다. 연맹이 규정을 고친 경우일 수도 있고 칼랭크가 값을 바로잡은 경우일 수도 있어서, '바뀐 항목이 있으니 다시 확인하세요'까지만 말씀드립니다. 푸시 알림은 보내지 않습니다."),
     ("여기서 통과하면 대회에서도 통과인가요?", "연맹 규정 기준으로는 그렇습니다. 다만 대회 요강이 규정보다 엄격한 경우가 있고, 현장 검사 방식도 대회마다 다릅니다. 출전 전에 요강을 함께 확인해 주세요.")])

AGE = page(
    "age-curve.html", "나이 곡선 — 같은 기록이면 몇 살에 어느 등급인가",
    "내 기록을 그대로 유지한다고 가정하고 나이별 연령등급(WMA 2025 기준표)을 곡선과 표로 보여 줍니다. 예측이 아니라 환산이며, 지금 등급을 지키는 데 필요한 기록도 함께 계산합니다.",
    "나이 곡선",
    "5km·10km·하프·풀코스 기록 하나를 넣으면, 같은 기록을 나이별로 환산한 연령등급과 지금 등급을 지키는 데 필요한 기록을 보여 줍니다. 앞날의 기록을 맞히는 도구는 아니고, 기준표를 따라 환산한 값입니다.",
    '''<section class="tp-card"><div class="tp-grid">
<label class="tp-field">성별<select id="acGender"><option value="male">남성</option><option value="female">여성</option></select></label>
<label class="tp-field">거리<select id="acDist"><option value="5km">5km</option><option value="10km" selected>10km</option><option value="half">하프</option><option value="full">풀코스</option></select></label>
<label class="tp-field">기록<input id="acTime" type="text" inputmode="numeric" placeholder="52:30" autocomplete="off"></label>
<label class="tp-field">지금 나이<input id="acAge" type="number" inputmode="numeric" min="15" max="95" placeholder="40"></label>
</div></section>
<div id="acOut" hidden>
<p id="acSummary" class="tp-p" role="status" aria-live="polite"></p>
<section class="tp-card ac-wrap"><figure class="ac-fig"><div id="acChart"></div>
<figcaption>같은 기록을 유지한다고 가정한 값입니다. 점선은 등급 경계입니다.</figcaption></figure></section>
<div id="acTable"></div>
</div>
<p class="tp-src">기준: WMA(World Masters Athletics) 2025 도로 연령 기준표(CC0). 연령등급 = 그 나이·성별의 기준기록 ÷ 내 기록 × 100. 나이에 따른 실제 기록 저하 속도는 사람마다 크게 달라서 곡선은 예측으로 읽으면 안 됩니다. 참고: Tanaka &amp; Seals, 2008, J Physiol 586(1):55–63.</p>''',
    ["wma-standards.js", "grade-model.js", "calrank-local.js", "age-curve.js"],
    [("연령등급은 어떻게 계산하나요?", "WMA가 내는 기준표에서 내 나이·성별·거리의 기준기록을 찾아 내 기록으로 나눈 뒤 100을 곱합니다. 나이가 들수록 기준기록이 느려지므로 같은 기록의 연령등급은 올라갑니다."),
     ("이 곡선이 내 미래 기록 예측인가요?", "아닙니다. 같은 기록을 유지한다고 가정하고 기준표로 환산한 값입니다. 나이 들면서 실제로 얼마나 느려지는지는 훈련량과 부상 이력에 따라 사람마다 크게 다릅니다."),
     ("'지금 등급을 지키는 기록'은 무엇인가요?", "그 나이의 기준기록으로 거꾸로 계산해서, 지금 등급의 경계에 해당하는 기록입니다. 이 시간 안쪽이면 그 나이에도 같은 등급입니다.")])

COURSE = page(
    "course.html", "코스 판정 — GPX 올리면 난이도와 평지 환산 거리",
    "GPX 파일이나 거리·오르막을 넣으면 칼랭크 난이도, Km-effort, 평지 몇 km에 해당하는지를 계산하고, 내 평지 페이스로 걸리는 시간을 알려 줍니다. 산악 러너 실험(Minetti 2002)의 에너지 비용 식을 씁니다.",
    "코스 판정",
    "거리와 누적 상승·하강, 또는 GPX 파일을 넣으면 칼랭크 난이도와 Km-effort를 매기고, 코스를 평지 거리로 환산해 내 평지 페이스로 걸리는 시간을 계산합니다. GPX 파일은 서버로 보내지 않고 이 브라우저 안에서만 읽습니다.",
    '''<section class="tp-card"><div class="tp-grid">
<label class="tp-field">GPX 파일(선택)<input id="cvFile" type="file" accept=".gpx,application/gpx+xml,text/xml"></label>
<label class="tp-field">평지 페이스 (분:초 / km)<input id="cvPace" type="text" inputmode="numeric" value="6:30" autocomplete="off"></label>
</div>
<p class="tp-small">GPX가 없으면 아래에 직접 적어도 됩니다. 처음에 보이는 값은 예시입니다.</p>
<div class="tp-grid">
<label class="tp-field">거리 (km)<input id="cvDist" type="number" inputmode="decimal" min="1" step="0.1" value="21"></label>
<label class="tp-field">누적 상승 (m)<input id="cvGain" type="number" inputmode="numeric" min="0" value="1000"></label>
<label class="tp-field">누적 하강 (m)<input id="cvLoss" type="number" inputmode="numeric" min="0" value="1000"></label>
<label class="tp-field">오르막 평균 경사<select id="cvUpg"><option value="0.08">8%</option><option value="0.12" selected>12%</option><option value="0.16">16%</option></select></label>
</div>
<div class="kit-row"><button type="button" id="cvRun" class="tp-btn">계산하기</button>
<label class="cv-check"><input type="checkbox" id="cvDown"> 내리막에서 빨라지는 것까지 반영</label></div>
<p id="cvMsg" class="tp-small" role="status" aria-live="polite"></p></section>
<div id="cvOut" hidden>
<section class="tp-card"><p class="tp-small">기준: <span id="cvSource"></span></p>
<p class="cv-big"><b id="cvIndex">1.00</b><span> 코스 부하 지수 · <span id="cvBand"></span></span></p>
<table class="cv-table"><tbody id="cvTable"></tbody></table>
<p class="tp-small" id="cvRawNote" hidden></p><p class="tp-small">칼랭크 난이도와 Km-effort는 거리와 누적 오르막으로만 계산한 값입니다. <a href="dg-method.html">계산 방법과 근거</a></p><p class="tp-small">마라톤 대회 코스라면 <a href="yardage.html">대회 코스 야디지북</a>에서 구간별 오르막과 보정 페이스를 볼 수 있습니다.</p></section>
<section class="tp-card" id="cvChartWrap" hidden><div id="cvChart"></div></section>
</div>
<section class="tp-sec"><h2 class="tp-h2">산출 방법</h2>
<p class="tp-p">경사에 따라 달릴 때 쓰는 에너지가 달라진다는 연구 결과를 구간마다 적용합니다. 평지에서 같은 힘을 낸다고 보고, 오르막에서는 더 느려지고 내리막에서는 덜 힘들다고 계산합니다. 그 합이 "평지로 환산한 거리"이고, 코스 부하 지수는 환산한 거리를 실제 거리로 나눈 값입니다. 1.00이면 평지와 같습니다.</p>
<p class="tp-p">내리막은 처음에는 평지와 같다고 계산합니다. 실험에서는 내리막이 덜 힘들게 나오지만, 코스가 거칠면 실제로 그만큼 빨리 내려가기 어렵기 때문입니다. 위 체크 상자를 켜면 그 이득까지 넣습니다.</p>
<p class="tp-p"><b>이 계산이 모르는 것</b>: 바위·뿌리·진흙 같은 노면, 날씨, 고도, 피로, 가파른 구간에서 걷는 것은 들어 있지 않습니다. 실험 참가자는 남성 엘리트 산악 러너 10명이라 모든 사람에게 그대로 맞는다고 할 수 없습니다. 부하 지수의 구분(평지에 가까움, 오르내림 있는 코스, 산악 코스, 매우 힘든 산악 코스)은 연구가 정한 기준이 아니라 칼랭크가 나눈 것입니다. 시간은 예측이 아니라 이 가정 아래의 환산값입니다.</p></section>
<p class="tp-src">근거: Minetti AE, Moia C, Roi GS, Susta D, Ferretti G. Energy cost of walking and running at extreme uphill and downhill slopes. J Appl Physiol 93:1039–1046, 2002 (doi:10.1152/japplphysiol.01177.2001). 경사 −45%~+45%에서 잰 달리기 에너지 비용의 5차 다항식을 씁니다.</p>''',
    ["course.js"],
    [("코스 부하 지수는 무엇인가요?", "코스를 평지 거리로 환산한 값을 실제 거리로 나눈 수입니다. 1.00이면 평지와 같고, 1.40이면 같은 거리를 평지에서 1.4배 달리는 정도의 에너지가 든다는 뜻입니다."),
     ("GPX 파일을 올리면 서버에 저장되나요?", "아닙니다. 파일은 이 브라우저 안에서만 읽고, 서버로 보내지 않으며 저장하지 않습니다."),
     ("가파른 오르막에서 걷는 것은 반영되나요?", "반영되지 않습니다. 달리는 비용으로 계산하므로, 실제로 걷는 구간이 많은 코스에서는 계산보다 시간이 다르게 나올 수 있습니다.")])


LEDGER = page(
    "ledger.html", "예상 기록 노트 — 대회 전에 적고, 끝난 뒤 맞춰 보기",
    "대회 전에 내 예상 기록을 적어 두고 끝난 뒤 실제 기록과 비교합니다. 카본화 효과를 연구 근거 범위로 환산해 적을 수도 있습니다. 기록은 내 기기에만 저장됩니다.",
    "예상 기록 노트",
    "대회 전에 예상 기록을 적어 두고, 끝난 뒤 실제 기록과 맞춰 봅니다. 맞히는 쪽은 칼랭크가 아니라 나입니다. 몇 번 쌓이면 내 예측이 어느 쪽으로 치우치는지 보입니다.",
    '''<p id="lgNudge" class="tp-alert" hidden role="status"></p>
<section class="tp-card">
<div class="tp-grid">
<label class="tp-field">대회 이름<input id="lgName" type="text" list="lgNames" autocomplete="off" placeholder="대회 이름"></label>
<label class="tp-field">대회 날짜<input id="lgDate" type="date"></label>
<label class="tp-field">거리<select id="lgDist"><option value="5km">5km</option><option value="10km">10km</option><option value="half">하프</option><option value="full" selected>풀코스</option></select></label>
<label class="tp-field">예측 방식<select id="lgBasis"><option value="gut">내 감으로</option><option value="carbon">카본화 효과 환산</option></select></label>
<label class="tp-field" id="lgPredWrap">예측 기록<input id="lgPred" type="text" inputmode="numeric" placeholder="3:45:00"></label>
<label class="tp-field" id="lgBaseWrap" hidden>지금 신발로 낸 최근 기록<input id="lgBase" type="text" inputmode="numeric" placeholder="3:50:00"></label>
</div>
<datalist id="lgNames"></datalist>
<p class="tp-small" id="lgCarbonNote" hidden>카본화 신발을 신었을 때 줄어드는 시간의 범위를 연구 근거로 환산해 함께 저장합니다. 대회 뒤에는 실제로 줄어든 시간이 그 범위 안이었는지 봅니다. 연구는 대부분 남성 엘리트·상급자 대상이고, 시간으로 옮기는 비율(0.70)은 칼랭크의 가정입니다.</p>
<p style="margin-top:12px"><button type="button" class="tp-btn" id="lgAdd">노트에 적기</button></p>
<p class="tp-note" id="lgMsg" role="status" aria-live="polite"></p>
</section>
<div id="lgSum" hidden class="tp-card"></div>
<section class="tp-card"><h2 class="tp-h2">내 노트</h2><div id="lgList"></div></section>
<p class="tp-small" id="lgStore"></p>''',
    ["wma-standards.js", "grade-model.js", "gear-model.js", "calrank-local.js", "ledger.js"],
    [("기록은 어디에 저장되나요?", "이 기기의 브라우저 안에만 저장됩니다. 서버로 보내지 않으므로 다른 기기에서는 보이지 않고, 브라우저 데이터를 지우면 함께 지워집니다."),
     ("카본화 효과는 어떤 근거로 계산하나요?", "동료 심사를 거친 연구들의 결과를 모아 근거 등급(A–D)을 매긴 칼랭크의 장비 판정 자료를 씁니다. 연구 대부분이 남성 엘리트·상급자 대상이라 동호회 선수에게는 범위가 달라질 수 있고, 근거가 없는 속도 구간에서는 환산을 하지 않습니다."),
     ("칼랭크가 예측해 주나요?", "아닙니다. 예측은 내가 적고, 칼랭크는 끝난 뒤 실제 기록과 비교만 합니다. 환산 방식을 고르면 연구 범위를 계산해 줄 뿐입니다.")])

# ── 종목별 기준 페이지: 수치 기준(gear_rules) + 실격·벌칙(gear_dq) ─────────────
RULES = json.loads((ROOT / "data/gear_rules.json").read_text(encoding="utf-8"))
DQ = json.loads((ROOT / "data/gear_dq.json").read_text(encoding="utf-8"))
SPORT_META = {
    "triathlon": ("철인3종", "World Triathlon", "standards-triathlon.html",
                  "철인3종 장비·규칙 기준 — 실격되는 것과 벌칙 정리"),
    "running": ("러닝", "World Athletics", "standards-running.html",
                "러닝화 규칙 기준 — 밑창 두께 40mm와 플레이트 규정"),
    "trail": ("트레일", "UTMB 말레이시아", "standards-trail.html",
              "트레일 대회 벌칙 예시 — 필수 장비가 없으면 어떻게 될까"),
    "cycling": ("사이클", "UCI", "standards-cycling.html",
                "사이클 장비·규칙 기준 — 최소 무게와 안장 위치"),
}


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


import sys as _s; _s.path.insert(0, str(ROOT / "scripts"))
from gear_images import commons_fig
import course_insights
FIG = {"tr-safety": commons_fig("ccc-gear", "dq-fig"), "wa-stack": commons_fig("shoe-section", "dq-fig"), "uci-setback": commons_fig("uci-saddle", "dq-fig"), "wt-helmet": commons_fig("tri-helmet", "dq-fig"), "wt-draft-zone": commons_fig("tri-draft", "dq-fig"), "wt-bib": commons_fig("tri-bib", "dq-fig")}


FAQS = {"trail": [
    ("트레일 대회에서 필수 장비가 없으면 어떻게 되나요?", "UTMB 말레이시아 벌칙표 기준으로 필수 안전 장비가 없으면 즉시 실격이고, 그 밖의 필수 장비가 없으면 30분 벌칙입니다. 다른 대회는 다를 수 있어서 대회 규정을 확인해야 합니다."),
    ("트레일 대회에서 스마트폰을 꺼 두면 벌칙이 있나요?", "UTMB 말레이시아에서는 스마트폰을 끄거나 비행기 모드로 두면 15분 벌칙입니다. 다른 대회의 기준은 대회 요강을 확인해 주세요."),
    ("트레일 폴을 중간에 버려도 되나요?", "UTMB 말레이시아에서는 처음부터 들고 가지 않은 폴을 쓰거나 경기 중에 폴을 버리면 30분 벌칙입니다."),
], "running": [
    ("마라톤 러닝화 두께 한도는 몇 mm인가요?", "부칙 2에 따라 도로 달리기는 40mm입니다. 신발 안쪽 윗면에서 바깥 밑면까지를 앞꿈치 중심과 뒤꿈치 중심에서 재고(8.3–8.4), 기준 크기는 270mm(US 8.5)입니다."),
    ("카본 플레이트가 있는 러닝화도 괜찮나요?", "8.5.1에 따라 스파이크 없는 신발은 단단한 구조물을 하나까지만 넣을 수 있습니다. 두 개 이상이면 안 됩니다."),
    ("트레일 러닝화에도 40mm 한도가 있나요?", "3.3과 부칙 2에서 산·트레일 경주와 크로스컨트리는 두께 한도 표에서 빠져 있습니다. 대회 요강이 따로 정한 것이 있는지는 확인해 주세요."),
    ("시중에 팔지 않는 신발은 신어도 되나요?", "세계랭킹 대회에서는 신발을 살 수 있어야 합니다(11.1). 개발 중인 신발은 세계육상 시리즈와 올림픽에서는 안 되고, 다른 세계랭킹 대회에서는 사전 서면 승인을 받아 최대 12개월까지 신을 수 있습니다(7.1–7.3). 동호인 대회에 같은 기준이 적용되는지는 요강을 확인해 주세요."),
], "cycling": [
    ("UCI 자전거 최소 무게는 몇 kg인가요?", "1.3.019에 따라 자전거 무게는 6.8kg보다 가벼울 수 없습니다. UCI 규정의 조항입니다. 동호인 대회에 그대로 적용되는지는 대회 요강을 확인해 주세요."),
    ("UCI 안장은 크랭크 축에서 얼마나 뒤에 있어야 하나요?", "1.3.013에 따라 안장 끝점이 크랭크 축 수직면보다 최소 5cm 뒤에 있어야 합니다. 체형 때문에 필요하면 경기 전 장비 검사에서 알리고 예외를 요청할 수 있습니다."),
    ("안장은 얼마나 기울여도 되나요?", "1.3.014에 따라 안장의 가장 높은 앞·뒤 점을 지나는 면이 수평에서 최대 9도까지 기울 수 있습니다."),
]}


def standards_page(sid):
    label, body_name, slug, title = SPORT_META[sid]
    items = DQ["sports"][sid]["items"]
    rules = [r for r in RULES["rules"] if r["sport"] == sid]
    src = DQ["sources"]
    used = []
    for it in items:
        if it["source"] not in used:
            used.append(it["source"])
    cards = ""
    for order, tag in (("실격", "실격"), ("벌칙·실격", "벌칙·실격"), ("시간 벌칙", "시간 벌칙"), ("규정", "규정")):
        for it in [i for i in items if i["severity"] == order]:
            cls = "dq-tag dq" if "실격" in it["severity"] else "dq-tag"
            cards += (f'<div class="dq-card" id="{it["id"]}"><div class="dq-top"><h3 class="dq-title">{esc(it["title"])}</h3>'
                      f'<span class="{cls}">{esc(it["severity"])}</span><span class="dq-clause">{esc(it["clause"])}</span></div>'
                      f'<p class="dq-text">{esc(it["text"])}</p>{FIG.get(it["id"], "")}</div>')
    links = "".join(f'<a class="dq-link" href="gear-{r["id"]}.html"><b>{esc(r["label"])}</b><span>{esc(r["headline"])}</span></a>' for r in rules)
    srcs = "".join(
        f'<p class="tp-src">출처: {esc(src[k]["label"])} — <a href="{esc(src[k]["url"])}" rel="noopener" target="_blank">원문 열기</a>. '
        f'{esc(src[k].get("note", ""))}<br><span class="dq-watch" data-watch="{esc(src[k]["url"])}">원문 확인 현황은 매주 자동으로 갱신됩니다.</span></p>'
        for k in used)
    edited = DQ["sports"][sid].get("edited", "")
    if sid == "trail":
        h2 = "벌칙 예시"
        intro = "트레일은 대회마다 필수 장비와 벌칙이 다릅니다. 이 페이지는 UTMB 말레이시아 한 대회의 벌칙표를 옮긴 예시이고, 모든 트레일 대회의 기준이 아닙니다. 신청한 대회의 규정을 먼저 확인해 주세요."
    elif sid == "running":
        h2 = "신발 기준"
        intro = "World Athletics 신발 규정 원문에서 조항 번호와 함께 옮겼습니다. 이 규정은 세계랭킹 대회와 국제 대회를 대상으로 하므로, 동호인 대회에 그대로 적용되는지는 대회 요강으로 먼저 확인해 주세요."
    elif sid == "cycling":
        h2 = "장비 기준"
        intro = "UCI 규정 원문에서 조항 번호와 함께 옮겼습니다. UCI 규정이라 동호인 대회에 그대로 적용되는지는 대회 요강으로 먼저 확인해 주세요. 현장 판정은 심판단이 합니다."
    else:
        h2 = "실격과 벌칙"
        intro = "에이지그룹(동호인) 경기에 적용되는 조항을 규정 원문에서 조항 번호와 함께 옮겼습니다. 대회 요강이 더 엄격할 수 있고, 현장 판정은 심판장이 합니다."
    body = f"""<p class="tp-small">내용 수정 {edited} · 고친 내용은 <a href="gear-changes.html">변경 기록</a>에 남깁니다.</p>
<section class="tp-sec"><h2 class="tp-h2">{h2}</h2>
<p class="tp-p">{intro}</p>
{cards}</section>
<section class="tp-sec"><h2 class="tp-h2">내 장비가 기준에 맞는지 보기</h2>{links}
<p class="tp-p"><a href="kit.html">내 장비 서랍</a>에 수치를 적어 두면 한 화면에서 판정합니다.</p></section>
{srcs}"""
    faq = FAQS.get(sid) or [
        ("트라이애슬론에서 헤드폰을 쓰면 실격인가요?",
         "규정 2.1 a) (xv)는 주변에 온전히 주의를 기울이지 못하게 하는 기기를 쓰지 말라고 하고, 음악 재생을 그런 사용의 예로 듭니다. 이를 어기면 실격입니다. 헤드폰이라는 말이 직접 적혀 있지는 않지만, 음악을 듣는 것은 여기에 해당합니다."),
        ("트라이애슬론 드래프팅은 몇 미터인가요?",
         "5.5 c) (iv)에 따라 앞 선수 앞바퀴 앞끝에서 12m가 드래프팅 구간이고, 다른 선수의 구간을 통과하는 데는 최대 25초까지 허용됩니다."),
        ("드래프팅 벌칙은 몇 분인가요?",
         "3.3 e) (i)에 따라 에이지그룹은 롱 3분, 미들 2분, 스탠더드 1분, 스프린트 이하 30초입니다. 위반이 반복되면 실격이 될 수 있습니다(스탠더드 이하는 두 번째, 미들·롱은 세 번째 위반)."),
        ("자전거에서 헬멧 턱끈은 언제 채워야 하나요?",
         "5.2 g) (iv)에 따라 헬멧은 항상 단단히 채워야 하고, 자전거 구간으로 돌아가거나 다시 타기 전에 턱끈을 먼저 채워야 합니다."),
    ]
    h1 = f"{label} 장비·규칙 기준"
    sub = f"{body_name} 규정에서 실격이 되는 것, 시간 벌칙이 붙는 것, 장비 수치 기준을 한곳에 모았습니다. 판정마다 조항 번호와 원문 링크를 달았습니다."
    desc = f"{label} 에이지그룹 규정의 실격 사유와 벌칙을 조항 번호와 함께 정리했습니다. 헬멧, 드래프팅 12m와 벌칙 시간, 헤드폰, 배번, 웻슈트 기준까지."
    if sid == "trail":
        sub = "UTMB 말레이시아 벌칙표에서 실격이 되는 것과 시간 벌칙이 붙는 것을 옮긴 한 대회의 예시입니다. 트레일은 대회마다 규정이 다릅니다."
        desc = "트레일 대회에서 필수 장비가 없으면 실격인지 시간 벌칙인지, UTMB 말레이시아 벌칙표 예시로 정리했습니다. 스마트폰, 폴, 배번 벌칙까지."
    if sid == "running":
        sub = "World Athletics 신발 규정에서 밑창 두께 한도, 플레이트 규정, 시판·개발 신발, 스파이크 기준을 한곳에 모았습니다. 판정마다 조항 번호와 원문 링크를 달았습니다."
        desc = "World Athletics 러닝화 규정의 도로 40mm 두께 한도, 단단한 구조물 하나 제한, 시판·개발 신발, 스파이크 기준을 조항 번호와 함께 정리했습니다."
    if sid == "cycling":
        sub = "UCI 규정에서 자전거 최소 무게, 안장 위치와 각도, 장비 승인 기준을 한곳에 모았습니다. 판정마다 조항 번호와 원문 링크를 달았습니다."
        desc = "UCI 규정의 자전거 최소 무게 6.8kg, 안장 5cm 뒤 위치, 안장 각도 9도, 장비 승인 기준을 조항 번호와 함께 정리했습니다."
    return slug, page(slug, title, desc, h1, sub, body, ["source-watch.js"], faq)


# ── 코스 페이지 (data/courses.json 의 코스마다 한 장) ─────────────────────────
import os as _os
COURSES = json.loads(Path(_os.environ.get("CALRANK_COURSES") or (ROOT / "data/courses.json")).read_text(encoding="utf-8")).get("courses", [])

# 둘레길(한국등산트레킹지원센터 GPX) — 고도를 채운 코스만 싣는다. 경로만 있고 고도가 아직 없는 코스는 건너뛴다.
_ftp = Path(_os.environ.get("CALRANK_FOREST") or (ROOT / "data/forest_trails.json"))
try:
    FOREST = [c for c in json.loads(_ftp.read_text(encoding="utf-8")).get("courses", []) if not c.get("needsDem") and len(c.get("profile") or []) >= 20]
except Exception:
    FOREST = []
COURSES = COURSES + FOREST
COPDEM_FT = ("produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 "
             "provided under COPERNICUS by the European Union and ESA; all rights reserved.")


def walk_time(prof):
    """걷는 시간 가늠(분). Naismith 규칙(5km/h + 오르막 600m당 1시간)과 Tobler 하이킹 함수의 두 값을 돌려준다."""
    km = prof[-1][0] / 1000.0
    gain = sum(max(0.0, b_[1] - a_[1]) for a_, b_ in zip(prof, prof[1:]))
    nais = (km / 5.0 + gain / 600.0) * 60.0
    tob = 0.0
    for a_, b_ in zip(prof, prof[1:]):
        d = b_[0] - a_[0]
        if d <= 0:
            continue
        sl = (b_[1] - a_[1]) / d
        v = 6.0 * _math_exp(-3.5 * abs(sl + 0.05))
        tob += (d / 1000.0) / max(v, 0.3) * 60.0
    return nais, tob

# ── 코스와 산 잇기 ─────────────────────────────────────────────────────────
# 사람들은 코스 이름보다 "OO산 둘레길"처럼 산 이름으로 찾는다. 코스 경로에서 1km 안에
# 산림청 등산로가 지나는 산을 찾아 서로 잇는다. 경로 좌표끼리의 거리일 뿐, 공식 연결이 아니다.
import math as _math
import re as _re2
from math import exp as _math_exp


def _mt_raw():
    _p = Path(_os.environ.get("CALRANK_MOUNTAINS") or (ROOT / "data/mountains.json"))
    try:
        out = json.loads(_p.read_text(encoding="utf-8")).get("mountains", [])
    except Exception:
        return []
    # 100대 명산 중 등산로 자료(mountains.json)에 없는 31개(지리산·설악산·한라산·북한산 등).
    # 산 페이지는 만들지 않고 코스 제목·본문에 이름을 붙이는 데만 쓴다.
    try:
        out += json.loads((ROOT / "data/mountains_extra.json").read_text(encoding="utf-8")).get("mountains", [])
    except Exception:
        pass
    # 산림청 산정보 서비스(전국 산 이름·높이·소재지) + 지오코딩 좌표. 좌표를 찾은 산만 쓰고,
    # 위 두 자료에 이미 있는 이름은 건너뛴다. 산 하나가 점 하나라서 코스와의 거리를 적어 보여 준다.
    try:
        have = {m["name"] for m in out}
        raw = [m for m in json.loads((ROOT / "data/mountain_names.json").read_text(encoding="utf-8")).get("mountains", [])
               if m.get("latlng")]
        # 좌표는 이름 검색으로 얻은 근사값이라 엉뚱한 지방의 같은 이름이 걸릴 수 있다.
        # 같은 시·군 소재 산들의 중앙값에서 40km 넘게 떨어진 점은 버린다.
        grp = {}
        for m in raw:
            grp.setdefault(" ".join((m.get("addr") or "").split()[:2]), []).append(m["latlng"])

        def _med(v):
            v = sorted(v)
            return v[len(v) // 2]
        cen = {k: (_med([p[0] for p in v]), _med([p[1] for p in v])) for k, v in grp.items() if len(v) >= 3}
        for m in raw:
            if m["name"] in have:
                continue
            ll = m["latlng"]
            c = cen.get(" ".join((m.get("addr") or "").split()[:2]))
            if c and _math.hypot((ll[0] - c[0]) * 111.0, (ll[1] - c[1]) * 111.0 * _math.cos(_math.radians(c[0]))) > 40:
                continue
            have.add(m["name"])
            out.append({"id": "n-" + str(m.get("id") or m["name"]), "name": m["name"], "extra": True, "point": True,
                        "maxEleM": round(m["heightM"]) if m.get("heightM") else None, "addr": m.get("addr", ""),
                        "sections": [{"path": [ll]}]})
    except Exception:
        pass
    return out


def _link_courses_mountains(courses, mts, radius_km=1.0):
    def _pts(m):
        out = []
        for sc in m["sections"]:
            out += sc.get("path") or ([[sc["lat"], sc["lon"]]] if sc.get("lat") is not None else [])
        return out
    mp = {m["id"]: _pts(m) for m in mts}
    box = {}
    for mid, P in mp.items():
        if P:
            box[mid] = (min(q[0] for q in P), max(q[0] for q in P), min(q[1] for q in P), max(q[1] for q in P))
    cn, mn = {}, {}
    pad = 0.02
    for c in courses:
        cp = c.get("path") or []
        if not cp:
            continue
        clo = (min(q[0] for q in cp) - pad, max(q[0] for q in cp) + pad, min(q[1] for q in cp) - pad, max(q[1] for q in cp) + pad)
        hits = []
        for m in mts:
            b = box.get(m["id"])
            if not b or b[1] < clo[0] or b[0] > clo[1] or b[3] < clo[2] or b[2] > clo[3]:
                continue
            best = min(_math.hypot((a[0] - q[0]) * 111.0, (a[1] - q[1]) * 111.0 * _math.cos(_math.radians(a[0])))
                       for a in mp[m["id"]][::2] for q in cp[::2])
            if best <= radius_km:
                hits.append((best, m))
        hits.sort(key=lambda t: (bool(t[1].get("point")), t[0], t[1]["id"]))
        if hits:
            cn[c["id"]] = hits[:4]
            for d_, m in hits[:4]:
                mn.setdefault(m["id"], []).append((d_, c))
    return cn, mn


def _mt_label(m):
    r = (m.get("region") or "").split()
    return f'{m["name"]}' + (f' ({r[1]})' if len(r) > 1 else "")


# 1km 안은 "근처", 3km까지는 거리를 적어 "인근"으로 쓴다. 산 이름으로 찾는 사람이 많아서
# 범위를 넓히되, 멀수록 거리를 숫자로 보여 같은 길이라는 인상을 주지 않는다.
NEAR_KM, WIDE_KM = 1.0, 3.0
COURSE_NEAR, MT_NEAR_COURSES = _link_courses_mountains(COURSES, _mt_raw(), radius_km=WIDE_KM)


def _mt_dist(d_):
    return f"약 {max(d_ * 1000, 10):.0f}m" if d_ < 1.0 else f"약 {d_:.1f}km"


def _near_word(d_):
    return "근처" if d_ <= NEAR_KM else "인근"


def _near_li(d_, m):
    if m.get("point"):
        hi_ = f' 높이 약 {m["maxEleM"]}m.' if m.get("maxEleM") else ""
        ad_ = f' 소재지 {esc(m["addr"])}.' if m.get("addr") else ""
        return (f'<li>{esc(m["name"])} <span class="tp-small">경로에서 {_mt_dist(d_)}</span><br>'
                f'<span class="tp-small">산림청 산정보 서비스 기준.{hi_}{ad_}</span></li>')
    if m.get("extra"):
        hi_ = f' 등산로 기록 기준 최고 해발 약 {m["maxEleM"]}m.' if m.get("maxEleM") else ""
        return (f'<li>{esc(m["name"])} <span class="tp-small">경로에서 {_mt_dist(d_)}</span><br>'
                f'<span class="tp-small">산림청 100대 명산입니다.{hi_}</span></li>')
    S = m["sections"]
    tot = sum(x["lenM"] for x in S) / 1000
    hi = max(max(x["startM"], x["endM"]) for x in S)
    steep = sum(x["lenM"] for x in S if abs(x["meanGrade"]) >= 15) / 1000
    steep_txt = f"평균 경사 15%를 넘는 구간이 {steep:.1f}km 있습니다." if steep >= 0.1 else "평균 경사 15%를 넘는 구간은 거의 없습니다."
    return (f'<li><a href="mountain-{m["id"]}.html">{esc(_mt_label(m))}</a> <span class="tp-small">경로에서 {_mt_dist(d_)}</span><br>'
            f'<span class="tp-small">산림청 등산로 구간 {len(S)}개, 합계 {tot:.1f}km, 구간 최고 해발 약 {hi:.0f}m. {steep_txt}</span></li>')


def _near_txt(c):
    h = [x for x in COURSE_NEAR.get(c["id"], []) if not x[1].get("point")]
    if not h:
        return ""
    return " · " + _near_word(h[0][0]) + " 산 " + ", ".join(esc(m["name"]) for _, m in h[:3])
TECH = [
    (1, "넓고 평탄한 길", "임도나 포장길처럼 폭이 넓고 노면이 고릅니다."),
    (2, "정리된 산길", "잔돌이나 작은 계단이 있지만 걸음을 크게 바꾸지 않아도 됩니다."),
    (3, "좁은 산길", "돌과 뿌리가 있어 한 줄로 달리고, 보폭을 조절해야 합니다."),
    (4, "거칠고 미끄러운 길", "젖으면 미끄러운 바위나 흙, 가파른 내리막이 있어 조심해서 내려가야 합니다."),
    (5, "손을 써야 하는 길", "바위 구간이나 노출된 곳이 있어 손을 짚거나 집중해서 이동해야 합니다."),
]
CHK_ITEMS = [("parking", "주차"), ("toilet", "화장실"), ("water", "식수"), ("signal", "휴대폰 신호"), ("escape", "하산로·탈출로"), ("transit", "대중교통")]
CHK_POINTS = [("start", "출발 지점"), ("mid", "중간 지점"), ("finish", "도착 지점")]


def josa(word, a, b):
    """받침이 있으면 a, 없으면 b (예: 이/가, 은/는)."""
    ch = word.strip()[-1:] if word.strip() else ""
    if "가" <= ch <= "힣":
        return a if (ord(ch) - 0xAC00) % 28 else b
    return b


def fmt_min(m):
    if not m:
        return ""
    h, mm = divmod(int(round(m)), 60)
    return f"{h}시간 {mm}분" if h and mm else (f"{h}시간" if h else f"{mm}분")


GRADE_BANDS = [  # (상한 %, 클래스, 이름)
    (-1.0, "gp-d", "내리막"), (3.0, "gp-0", "완만(3% 미만)"), (7.0, "gp-1", "오르막 3~7%"),
    (12.0, "gp-2", "가파름 7~12%"), (999, "gp-3", "매우 가파름 12% 이상")]


def grade_cls(g):
    for lim, cl, _ in GRADE_BANDS:
        if g < lim:
            return cl
    return "gp-3"


def _km_step(total_km):
    for st in (0.5, 1, 2, 5, 10, 20, 50):
        if total_km / st <= 6:
            return st
    return 100


def profile_svg(prof):
    """경사 색 단면도. 스크립트 없이도 보이도록 서버에서 SVG 로 그린다(색만으로 구분하지 않게 범례 글자도 함께).

    색 단면도 자체는 흔한 표현이라, 칼랭크 것으로 읽히는 건 이 경로의 값을 직접 읽어 준 부분이다:
    거리·고도 눈금, 출발·도착 고도, 가장 가파른 오르막 한 곳의 위치와 경사.
    """
    W, H = 440, 160
    L, R, T, B = 34, 8, 14, 22
    total = prof[-1][0] or 1
    es = [p[1] for p in prof]
    lo, hi = min(es), max(es)
    span = max(hi - lo, 20.0)
    top = hi + span * 0.05
    bot = lo - span * 0.05
    def X(d): return L + (W - L - R) * d / total
    def Y(e): return T + (H - T - B) * (top - e) / (top - bot)
    base = H - B
    cols, best = [], None
    for a, b in zip(prof, prof[1:]):
        d = b[0] - a[0]
        if d <= 0:
            continue
        g = (b[1] - a[1]) / d * 100
        x0, x1 = X(a[0]), X(b[0])
        cols.append(f'<path class="{grade_cls(g)}" d="M{x0:.1f},{base} L{x0:.1f},{Y(a[1]):.1f} L{x1:.1f},{Y(b[1]):.1f} L{x1:.1f},{base}Z"/>')
        if best is None or g > best[0]:
            best = (g, (a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    line = "M" + " L".join(f"{X(p[0]):.1f},{Y(p[1]):.1f}" for p in prof)
    # 눈금
    grid = (f'<line class="gp-grid" x1="{L}" x2="{W - R}" y1="{Y(hi):.1f}" y2="{Y(hi):.1f}"/>'
            f'<text class="gp-tx" x="{L - 5}" y="{Y(hi) + 4:.1f}" text-anchor="end">{hi:.0f}m</text>'
            f'<text class="gp-tx" x="{L - 5}" y="{Y(lo) + 4:.1f}" text-anchor="end">{lo:.0f}m</text>')
    st = _km_step(total / 1000)
    k = 0.0
    while k * 1000 <= total + 1:
        x = X(k * 1000)
        anchor = "start" if k == 0 else "middle"
        lab = f"{k:g}" + ("km" if k + st > total / 1000 + 1e-9 else "")
        grid += (f'<line class="gp-tick" x1="{x:.1f}" x2="{x:.1f}" y1="{base}" y2="{base + 4}"/>'
                 f'<text class="gp-tx" x="{x:.1f}" y="{H - 5}" text-anchor="{anchor}">{lab}</text>')
        k += st
    # 출발·도착, 가장 가파른 오르막
    marks = (f'<circle class="gp-dot" cx="{X(prof[0][0]):.1f}" cy="{Y(prof[0][1]):.1f}" r="3"/>'
             f'<circle class="gp-dot" cx="{X(prof[-1][0]):.1f}" cy="{Y(prof[-1][1]):.1f}" r="3"/>')
    note = ""
    if best and best[0] >= 3:
        g, d, e = best
        cx, cy = X(d), Y(e)
        right = cx > W * 0.55
        tx = cx - 8 if right else cx + 8
        ty = max(cy - 6, T + 6)
        marks += (f'<circle class="gp-peak" cx="{cx:.1f}" cy="{cy:.1f}" r="4.5"/>'
                  f'<text class="gp-tx gp-tx-b" x="{tx:.1f}" y="{ty:.1f}" text-anchor="{"end" if right else "start"}">최대 {g:.0f}%</text>')
        note = f" 고리 표시는 가장 가파른 오르막(약 {g:.0f}%, 출발점에서 {d / 1000:.1f}km 지점)입니다."
    leg = "".join(f'<li><i class="gp-sw {cl}"></i>{nm}</li>' for _, cl, nm in GRADE_BANDS)
    return (f'<figure class="gp-fig"><div class="gp-tag">칼랭크 경사 단면도</div>'
            f'<svg class="gp-svg" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="고도 단면도. 낮은 곳 {lo:.0f}m, 높은 곳 {hi:.0f}m, 전체 {total / 1000:.1f}km">'
            f'{grid}{"".join(cols)}<path class="gp-line" d="{line}" fill="none"/>{marks}</svg>'
            f'<figcaption class="tp-small">가로는 거리 0~{total / 1000:.1f}km, 세로는 고도 {lo:.0f}~{hi:.0f}m입니다. 색은 그 구간의 경사입니다.{note}</figcaption>'
            f'<ul class="gp-leg">{leg}</ul></figure>')


ROUTES = {"해파랑길": ("haeparang", "동해안을 따라 부산에서 고성까지 이어지는 길입니다."), "남파랑길": ("nampa", "남해안을 따라 부산에서 해남까지 이어지는 길입니다."),
          "서해랑길": ("seohae", "서해안을 따라 해남에서 인천 강화까지 이어지는 길입니다."), "DMZ 평화의 길": ("dmz", "비무장지대 접경을 따라 이어지는 길입니다."),
          "서울둘레길": ("seoul-dulle", "서울의 산과 하천, 공원을 이어 한 바퀴 도는 둘레길입니다."),
          "지리산둘레길": ("jirisan-dulle", "지리산 자락의 마을과 숲을 잇는 둘레길로, 전남·전북·경남에 걸쳐 있습니다."),
          "한라산둘레길": ("hallasan-dulle", "제주 한라산 중산간의 숲길을 걷는 둘레길입니다."),
          "DMZ펀치볼둘레길": ("dmz-punchbowl", "강원 양구 펀치볼 분지를 둘러싼 국가숲길입니다."),
          "내포문화숲길": ("naepo", "충남 내포 지역의 역사와 종교 이야기를 따라 걷는 국가숲길입니다."),
          "대관령숲길": ("daegwallyeong", "강원 대관령 일대의 숲길과 백두대간 구간을 모은 국가숲길입니다."),
          "백두대간트레일": ("baekdudaegan", "백두대간을 따라 이어지는 국가숲길입니다."),
          "울진금강소나무숲길": ("uljin", "경북 울진의 금강소나무 숲을 지나는 국가숲길입니다.")}
SIDO = {"강원": "gangwon", "경기": "gyeonggi", "경남": "gyeongnam", "경북": "gyeongbuk", "부산": "busan", "서울": "seoul",
        "울산": "ulsan", "인천": "incheon", "전남": "jeonnam", "전북": "jeonbuk", "충남": "chungnam", "충북": "chungbuk",
        "대구": "daegu", "광주": "gwangju", "대전": "daejeon", "세종": "sejong", "제주": "jeju"}


def _prog_sec(label, cs, href=""):
    """길 하나의 완주판. 칸 수만 적어 두고 채우는 건 trail-mark.js 가 이 기기 안에서 한다."""
    hs = ",".join(f"course-{x['id']}.html" for x in cs)
    kms = ",".join(f"{course_stats(x)[0]:.2f}" for x in cs)
    gs = ",".join(f"{course_stats(x)[1]:.0f}" for x in cs)
    ns = "|".join(x["name"].replace("|", " ") for x in cs)
    return (f'<section class="tp-sec tr-prog" data-name="{esc(label)}" data-hrefs="{hs}" data-km="{kms}" data-gain="{gs}" data-names="{esc(ns)}" data-link="{esc(href)}">'
            f'<h2 class="tp-h2">내 {esc(label)} 완주판</h2><div class="tr-prog-b"></div></section>')


def route_of(c):
    for k in ROUTES:
        if c["name"].startswith(k):
            return k
    return ""


def sido_of(c):
    return (c.get("region") or "").split()[0] if c.get("region") else ""


def course_stats(c):
    prof = c["profile"]
    km = prof[-1][0] / 1000
    gain = sum(max(0, b[1] - a[1]) for a, b in zip(prof, prof[1:]))
    loss = sum(max(0, a[1] - b[1]) for a, b in zip(prof, prof[1:]))
    steep = 0.0
    for a, b in zip(prof, prof[1:]):
        if b[0] > a[0] and (b[1] - a[1]) / (b[0] - a[0]) >= 0.07:
            steep += b[0] - a[0]
    return km, gain, loss, steep / 1000


DG_BANDS = [(50, "쉬움"), (100, "보통"), (150, "조금 힘듦"), (200, "힘듦"), (1e9, "매우 힘듦")]


def diff_grade(km, gain):
    """미국 국립공원관리청(Shenandoah) 식: sqrt(오르막(ft) x 2 x 거리(mile)). 구간 50/100/150/200."""
    score = (2 * gain * 3.28084 * km * 0.621371) ** 0.5
    for i, (lim, nm_) in enumerate(DG_BANDS):
        if score < lim:
            return score, i, nm_
    return score, 4, "매우 힘듦"


# ITRA(국제트레일러닝협회)의 Km-effort: 거리 1km = 1, 누적 오르막 100m = 1. 0~6점 구간 경계.
KE_BANDS = [25, 45, 75, 115, 155, 210]



def sun_block(c, wt):
    """코스 시작점의 일몰과, 출발 시각에 걷는 시간을 더한 하산 시각을 견주는 칸(sunmargin.js).
    걷는 시간 가늠(Naismith·Tobler)이 있는 코스에만 붙인다. 계산은 방문자 브라우저에서 한다."""
    path = c.get("path") or []
    if not wt or not path:
        return ""
    lat, lon = path[0][0], path[0][1]
    return (f'<section class="tp-card" id="sunMargin" data-lat="{lat:.5f}" data-lon="{lon:.5f}" '
            f'data-min="{min(wt):.0f}" data-max="{max(wt):.0f}"><h2 class="tp-h2">일몰까지 남는 시간</h2>'
            '<p class="tp-p">출발 날짜와 시각을 넣으면 걷는 시간 가늠을 더해 하산 시각을 구하고, 그날 일몰과 비교합니다.</p>'
            '<div class="tp-grid"><label class="tp-field">출발 날짜<input id="smDate" type="date"></label>'
            '<label class="tp-field">출발 시각<input id="smTime" type="time"></label></div>'
            '<div id="smOut" role="status" aria-live="polite"></div>'
            '<p class="tp-small">일몰은 미국 해양대기청(NOAA) 태양 위치 계산식으로 코스 출발점 좌표에서 구했고, 공표 값과 1분 안팎으로 맞습니다. '
            '걷는 시간은 Naismith 규칙과 Tobler 하이킹 함수 두 값의 범위이며 쉬는 시간, 짐, 노면, 날씨는 들어 있지 않습니다. 공식 시간이 아닙니다.</p>'
            '<script defer src="/sunmargin.js"></script></section>')

def km_effort(km, gain):
    ke = km + gain / 100.0
    pts = sum(1 for b in KE_BANDS if ke >= b)
    return ke, pts


def dg_of(c):
    k_, g_, _l, _s = course_stats(c)
    return diff_grade(k_, g_)


def _med(v):
    v = sorted(v); n = len(v)
    return 0 if not n else (v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2)


LV_MED = {}
for _lv in (1, 2, 3):
    _g = [course_stats(c)[1] / course_stats(c)[0] for c in COURSES if (c.get("official") or {}).get("level") == _lv and course_stats(c)[0] > 0]
    if _g:
        LV_MED[_lv] = (_med(_g), len(_g))


def map_block(data, legend=""):
    j = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return ('<section class="tp-sec"><h2 class="tp-h2">지도</h2>'
            '<p class="tp-small">버튼을 누르면 OpenStreetMap 지도를 불러옵니다. 누르기 전에는 지도 서버로 아무것도 보내지 않습니다.</p>'
            '<p><button type="button" class="tp-btn ghost" id="mapBtn">지도 보기</button></p>'
            f'<div id="mapBox" class="rm-box" hidden></div>{legend}'
            f'<script type="application/json" id="mapData">{j}</script></section>')


# ── 코스 × 장비: 이 코스의 경사 분포를 폴 연구의 경사 구간에 맞춰 본다 ──
# 근거 숫자는 data/gear_claims.json(trail-poles)에서 읽는다. 여기에 숫자를 다시 적지 않는다.
def _gear_claim(cid):
    try:
        for x in json.loads((ROOT / "data" / "gear_claims.json").read_text(encoding="utf-8"))["claims"]:
            if x["id"] == cid:
                return x
    except Exception:
        pass
    return None


def grade_shares(prof, win=200):
    """고도 단면을 약 win m 창으로 다듬어 경사(%)별 거리 비율을 낸다. 다듬지 않으면 GPS 흔들림이 경사를 부풀린다."""
    xs = [p_[0] for p_ in prof]; es = [p_[1] for p_ in prof]
    n = len(xs)
    if n < 6 or xs[-1] < 1000:
        return None
    gs = []
    for i in range(n):
        lo = i; hi = i
        while lo > 0 and xs[i] - xs[lo] < win / 2: lo -= 1
        while hi < n - 1 and xs[hi] - xs[i] < win / 2: hi += 1
        if xs[hi] - xs[lo] >= win * 0.6:
            gs.append((es[hi] - es[lo]) / (xs[hi] - xs[lo]) * 100)
    if not gs:
        return None
    m = len(gs)
    return {"lt5": sum(1 for g in gs if g < 5) / m, "mid": sum(1 for g in gs if 5 <= g < 20) / m,
            "ge20": sum(1 for g in gs if g >= 20) / m, "ge28": sum(1 for g in gs if g >= 28) / m, "down10": sum(1 for g in gs if g <= -10) / m,
            "max_up": max(gs), "max_down": -min(gs)}


def course_gear_html(c, km):
    """폴 연구(Saller 2023 종설, Giovanelli 2019 실험)가 말하는 경사 구간에 이 코스를 올려 본다."""
    cl = _gear_claim("trail-poles")
    sh = grade_shares(c["profile"])
    if not cl or not sh:
        return ""
    ox = [e for e in cl["effects"] if e["id"] == "oxygen_cost"][0]
    ev = {tuple(e["applies"]["gradient_pct"]): e for e in ox["evidence"]}
    low = ev.get((None, 5)); mid = ev.get((5, 20)); high = ev.get((20, None))
    if not (low and mid and high):
        return ""
    pct = lambda v: f"{v * 100:.0f}%" if v >= 0.005 else "1% 미만"
    rows = [("5% 미만 (평지·완만)", pct(sh["lt5"]), f"산소 소모가 늘었다는 보고 · 근거 {low['grade']}"),
            ("5~20%", pct(sh["mid"]), f"차이가 분명하지 않음 · 근거 {mid['grade']}"),
            ("20% 이상", pct(sh["ge20"]), f"약 47~73%의 아주 가파른 구간에서만 소모가 줄었다는 보고 · 근거 {high['grade']}")]
    tr = "".join(f"<li><b>경사 {a} · 이 코스의 {b}</b><br>{d}</li>" for a, b, d in rows)
    if sh["ge20"] < 0.01:
        verdict = (f"이 코스에는 폴이 에너지를 줄인다는 근거가 있는 가파른 구간이 사실상 없습니다. "
                   f"200m 구간 평균으로 가장 가파른 곳이 약 {sh['max_up']:.0f}%입니다. 연구에서 에너지 절감은 경사 약 47~73%(25~36도)의 아주 가파른 구간에서만 보고됐습니다.")
    else:
        verdict = (f"경사 20% 이상인 구간이 전체의 {pct(sh['ge20'])}({km * sh['ge20']:.1f}km쯤) 있습니다. "
                   f"다만 연구가 에너지 절감을 확인한 것은 이보다 훨씬 가파른 약 47~73% 구간뿐이라, 이 코스의 가파른 구간에서 폴이 에너지를 줄여 주는지는 아직 알 수 없습니다.")
        if sh["ge28"] >= 0.005:
            verdict += (f" 경사 약 28%(15.5도) 이상인 구간은 {pct(sh['ge28'])}입니다. 산악 러너 14명의 실험에서 이 정도 경사부터는 힘들다고 느끼는 정도(RPE)가 "
                        f"14~19% 낮아졌다고 보고됐습니다.")
    down = ""
    if sh["down10"] >= 0.03:
        down = (f" 내리막이 가파른 구간(경사 -10% 이하)은 전체의 {pct(sh['down10'])}입니다. 폴이 다리에 걸리는 힘을 평균 11% 줄였다는 보고가 있어 "
                f"이 구간에서는 에너지보다 다리 부담 쪽 이점을 기대할 수 있습니다(근거 C, 연구마다 측정 방식이 다름).")
    return ('<section class="tp-sec"><h2 class="tp-h2">트레일 폴 사용 적합성</h2>'
            f'<p class="tp-p">{esc(verdict)}{esc(down)}</p>'
            f'<ul class="cp-list">{tr}</ul>'
            '<p class="tp-small">경사는 약 200m 구간으로 다듬은 평균입니다. 폴 연구는 대부분 참가자 9~29명의 소규모 실험이라 근거 등급은 C입니다. '
            'Saller 외(2023, Bioengineering 10:497) 종설과 Giovanelli 외(2019, Eur J Appl Physiol 119:1557)를 바탕으로 했고, '
            '<a href="gear-trail-poles-by-gradient.html">경사별 폴 효과</a>에 근거와 한계를 정리했습니다.</p></section>')


def course_fuel_html(c, hours):
    """걸리는 시간에 맞는 탄수화물 섭취 범위. Burke 2011(IOC 합의문)과 Jeukendrup 2014의 초록에 적힌 수치만 쓴다."""
    if not hours or hours < 0.5:
        return ""
    h = f"{hours:.1f}".rstrip("0").rstrip(".")
    if hours <= 1.1:
        body = (f"예상 소요시간은 약 {h}시간입니다. 1시간 안팎의 운동에서는 탄수화물을 많이 먹는 것보다 소량을 먹거나 입을 헹구는 것만으로도 "
                f"수행에 도움이 된다고 보고됩니다. 먹는 양보다 출발 전 준비가 중요한 시간대입니다.")
        rng = ""
    elif hours <= 2.5:
        lo, hi = round(30 * hours), round(60 * hours)
        body = (f"예상 소요시간은 약 {h}시간입니다. 이보다 긴 운동에서는 시간당 30~60g이 적절한 목표로 제시됩니다. "
                f"이 코스에 대입하면 걷는 동안 탄수화물을 대략 {lo}~{hi}g 먹는 계산입니다.")
        rng = ""
    else:
        lo, hi = round(30 * hours), round(60 * hours)
        body = (f"예상 소요시간은 약 {h}시간입니다. 시간당 30~60g이 목표로 제시되고, 2.5시간을 넘는 운동에서는 최대 90g까지 도움이 될 수 있다고 합니다. "
                f"30~60g 기준으로 대입하면 이 코스에서 대략 {lo}~{hi}g입니다. 시간당 60g을 넘기려면 서로 다른 종류의 탄수화물을 섞은 제품이 흡수에 유리하다고 합니다.")
    wp = (c.get("waypoints") or {}).get("counts") or {}
    water = wp.get("약수터·샘터")
    water_txt = (f" 자료에 찍힌 지점 가운데 경로에서 80m 안에 약수터·샘터가 {water}곳 있습니다. 마실 수 있는 물인지는 확인된 것이 아니니 물은 넉넉히 챙기세요."
                 if water else "")
    return ('<section class="tp-sec"><h2 class="tp-h2">이 코스의 보급 가늠</h2>'
            f'<p class="tp-p">{esc(body)}{esc(water_txt)}</p>'
            '<p class="tp-small">소요시간은 두루누비 표기 시간(없으면 고도 단면으로 가늠한 걷는 시간)입니다. 이 권고는 지구력 운동 기준이라 천천히 걷는 낮은 강도에서는 낮춰도 된다고 하며(Jeukendrup 2014), 개인에 맞춰 조정하는 것을 전제로 합니다. 의학적 조언이 아닙니다. '
            'Burke 외(2011, J Sports Sci 29 Suppl 1:S17-27, 국제올림픽위원회 합의문)와 Jeukendrup(2014, Sports Med 44 Suppl 1:S25-33)을 바탕으로 했습니다.</p></section>')


def course_page(c):
    cid = c["id"]; slug = f"course-{cid}.html"
    prof = c["profile"]
    km, gain, loss, steep_km = course_stats(c)
    off = c.get("official") or {}
    q = c.get("quality") or {}
    tech = c.get("technical") or {}
    lv = tech.get("level")
    region = c.get("region") or ""
    nm = c["name"]
    if lv:
        name, desc_ = [(n, d) for l, n, d in TECH if l == lv][0]
        tech_html = (f'<p class="cp-lv"><b>{lv}단계</b> · {esc(name)}</p><p class="tp-p">{esc(desc_)}</p>'
                     f'<p class="tp-small">정한 근거: {esc(tech.get("basis", ""))} {esc(tech.get("note", ""))}</p>')
    else:
        tech_html = '<p class="tp-p">노면 같은 기술 난이도는 아직 평가하지 않았습니다. 현장을 확인한 뒤에만 단계를 적습니다.</p>'
    legend = "".join(f"<li><b>{l}단계 {esc(n)}</b> — {esc(d)}</li>" for l, n, d in TECH)
    _nm = COURSE_NEAR.get(cid, [])
    mt_near_html = ""
    if _nm:
        mt_near_html = ('<section class="tp-sec"><h2 class="tp-h2">근처·인근 산</h2><p class="tp-p">이 코스 경로 3km 안에 있는 산입니다. 산림청 등산로 자료와 산정보 서비스를 함께 보았습니다. 1km 안은 근처, 그보다 멀면 인근으로 보고 거리를 적었습니다. '
                        '가까운 순이고, 경로 좌표로 잰 값이라 같은 길이라는 뜻은 아닙니다.</p><ul class="cp-list">' +
                        "".join(_near_li(d_, m) for d_, m in _nm) + "</ul></section>")
    rows = ""
    for pk, plabel in CHK_POINTS:
        pc = (c.get("checks") or {}).get(pk, {})
        cells = ""
        for ik, ilabel in CHK_ITEMS:
            it = pc.get(ik) or {}
            if it.get("status") == "확인":
                cells += f'<li><b>{ilabel}</b> {esc(it.get("text", ""))} <span class="cp-v">{esc(it.get("verified", ""))} 확인 · {esc(it.get("source", ""))}</span></li>'
            else:
                cells += f'<li class="cp-un"><b>{ilabel}</b> 미확인</li>'
        rows += f'<div class="dq-card"><h3 class="dq-title">{plabel}</h3><ul class="cp-list">{cells}</ul></div>'
    s = c.get("source", {})
    data = json.dumps({"profile": prof}, ensure_ascii=False, separators=(",", ":"))
    where = f"{region}에 있는 " if region else ""
    t_off = fmt_min(off.get("min"))
    lead = (f"{nm}{josa(nm, '은', '는')} {where}{km:.1f}km 코스입니다. 누적 오르막은 {gain:.0f}m, 내리막은 {loss:.0f}m이고, "
            f"7% 넘게 가파른 구간은 모두 합쳐 {steep_km:.1f}km입니다.")
    if t_off:
        lead += f" 두루누비가 적은 소요시간은 {t_off}입니다."
    _ft = c.get("trail")
    wt = walk_time(prof) if _ft else None
    if _ft:
        _sib = [o for o in COURSES if o.get("trail") == _ft]
        lead = (f"{nm}{josa(nm, '은', '는')} {_ft}의 한 코스입니다. 거리는 {km:.1f}km이고, 누적 오르막은 {gain:.0f}m, 내리막은 {loss:.0f}m입니다. "
                f"7% 넘게 가파른 구간은 모두 합쳐 {steep_km:.1f}km입니다.")
        if wt:
            lead += f" 걸어서 {fmt_min(round(min(wt)))}~{fmt_min(round(max(wt)))} 정도로 가늠합니다."
    _fuel_h = (off.get("min") / 60.0) if off.get("min") else ((sum(wt) / len(wt) / 60.0) if wt else None)
    dg_score, dg_i, dg_name = diff_grade(km, gain)
    ke, ke_pts = km_effort(km, gain)
    stat_rows = [("칼랭크 난이도", f"{dg_name} (점수 {dg_score:.0f})"), ("Km-effort(ITRA식)", f"{ke:.0f} (0~6점 중 {ke_pts}점)"), ("거리", f"{km:.1f} km"), ("누적 오르막", f"{gain:.0f} m"), ("누적 내리막", f"{loss:.0f} m"),
                 ("1km당 오르막", f"{gain / km:.0f} m"), ("7% 넘게 가파른 구간", f"{steep_km:.1f} km")]
    if off.get("level"):
        stat_rows.append(("두루누비 표기 난이도", f'{off["level"]} (1~3 중)'))
        if off["level"] in LV_MED:
            stat_rows.append((f'같은 난이도 코스의 1km당 오르막(중앙값, {LV_MED[off["level"]][1]}개)', f'{LV_MED[off["level"]][0]:.0f} m'))
    if t_off:
        stat_rows.append(("두루누비 표기 소요시간", t_off))
    if _ft and wt:
        stat_rows.append(("걷는 시간 가늠(공식 시간 아님)", f"{fmt_min(round(min(wt)))} ~ {fmt_min(round(max(wt)))}"))
        _ks = sorted(_sib, key=lambda o: -course_stats(o)[0]); _gs = sorted(_sib, key=lambda o: -course_stats(o)[1])
        _ps = sorted(_sib, key=lambda o: -(course_stats(o)[1] / max(course_stats(o)[0], 0.1)))
        stat_rows.append((f"{_ft} {len(_sib)}개 코스 중 거리 순위", f"{_ks.index(c) + 1}번째로 긺"))
        stat_rows.append((f"{_ft} {len(_sib)}개 코스 중 오르막 순위", f"{_gs.index(c) + 1}번째로 많음"))
        stat_rows.append((f"{_ft} {len(_sib)}개 코스 중 1km당 오르막", f"{_ps.index(c) + 1}번째로 가파름"))
    stat_html = "".join(f"<tr><th>{a}</th><td>{b}</td></tr>" for a, b in stat_rows)
    # 코스마다 달라지는 문장: 가장 크게 이어서 오르는 구간과 가장 높은 지점
    notable = ""
    e = [p_[1] for p_ in prof]; d_ = [p_[0] for p_ in prof]
    parts_ = []
    best = (0.0, 0, 0); j = 0
    for i_ in range(len(d_)):
        if j < i_: j = i_
        while j < len(d_) - 1 and d_[j] - d_[i_] < 1000:
            j += 1
        if d_[j] - d_[i_] >= 800 and e[j] - e[i_] > best[0]:
            best = (e[j] - e[i_], i_, j)
    if best[0] >= 15:
        a_, b_ = best[1], best[2]
        parts_.append(f"가장 가파르게 오르는 1km는 {d_[a_] / 1000:.1f}km 지점부터 {d_[b_] / 1000:.1f}km 지점까지입니다. 고도가 {e[a_]:.0f}m에서 {e[b_]:.0f}m로 {best[0]:.0f}m 올라가 평균 경사는 약 {best[0] / max(d_[b_] - d_[a_], 1) * 100:.0f}%입니다.")
    hi_i = e.index(max(e))
    if max(e) - min(e) >= 15:
        parts_.append(f"코스에서 가장 높은 곳은 {d_[hi_i] / 1000:.1f}km 지점의 약 {max(e):.0f}m이고, 가장 낮은 곳은 약 {min(e):.0f}m입니다.")
    if parts_:
        notable = '<section class="tp-sec"><h2 class="tp-h2">눈여겨볼 곳</h2><p class="tp-p">' + esc(" ".join(parts_)) + "</p></section>"
    qual = ""
    if q.get("rawGainM") and q.get("smoothGainM"):
        _dist_txt = f'경로 파일의 거리는 공식 거리의 {q["distRatio"] * 100:.0f}%였습니다. ' if q.get("distRatio") else ""
        qual = ('<p class="tp-small">자료 점검: ' + _dist_txt +
                f'GPS 고도는 작게 흔들려서 파일에 적힌 값을 그대로 더하면 오르막이 {q["rawGainM"]}m로 나옵니다. '
                f'이 페이지는 약 100m 구간으로 다듬어 {gain:.0f}m로 계산했습니다.</p>')
    same = [o for o in COURSES if o["id"] != cid and region and o.get("region") == region][:6]
    rel = ""
    _lk = []
    _r = route_of(c)
    _pg = _sib if _ft else ([o for o in COURSES if route_of(o) == _r] if _r else [])
    _prog_html = _prog_sec(_ft or _r, _pg, (f"trailroute-{ROUTES[_r][0]}.html" if _r else "")) if len(_pg) >= 3 else ""
    _ins_html = course_insights.build(
        c, course_stats(c), (_fuel_h * 60 if _fuel_h else None), _pg, (_ft or _r),
        course_stats, lambda g: f"course-{g['id']}.html")
    if _r:
        _lk.append(f'<li><a href="trailroute-{ROUTES[_r][0]}.html">{esc(_r)} 코스 모음</a></li>')
    _s = sido_of(c)
    if _s in SIDO:
        _lk.append(f'<li><a href="trailarea-{SIDO[_s]}.html">{esc(_s)} 지역 코스 모음</a></li>')
    if _lk:
        rel += '<section class="tp-sec"><h2 class="tp-h2">같은 길·지역의 코스 모음</h2><ul class="cp-list">' + "".join(_lk) + "</ul></section>"
    if same:
        rel += ('<section class="tp-sec"><h2 class="tp-h2">같은 지역의 다른 코스</h2><ul class="cp-list">' +
               "".join(f'<li><a href="course-{o["id"]}.html">{esc(o["name"])}</a> · {o["profile"][-1][0] / 1000:.1f}km · 난이도 {dg_of(o)[2]}</li>' for o in same) +
               '</ul></section>')
    ft_extra = ""
    if _ft:
        wp = c.get("waypoints") or {}
        cnt = wp.get("counts") or {}
        pois = [p_ for p_ in (wp.get("pois") or []) if p_[1].strip() and not _re2.match(r"^[ㄱ-ㅎㅏ-ㅣ]", p_[1].strip()) and not _re2.search(r"직진|방향|^[A-Za-z]\s", p_[1].strip()) and len(p_[1].strip()) >= 2]
        parts = []
        order = ["화장실", "쉼터", "전망", "약수터·샘터", "안내소", "주차장", "스탬프", "갈림길"]
        trs_ = "".join(f"<tr><th>{k}</th><td>{cnt[k]}곳</td></tr>" for k in order if cnt.get(k))
        if trs_:
            parts.append(f'<h2 class="tp-h2">길 위의 시설</h2><p class="tp-p">자료에 찍힌 지점 가운데 경로에서 80m 안에 있는 것만 셌습니다. 같은 시설을 두 번 찍은 경우가 있어 실제와 조금 다를 수 있습니다.</p><table class="cv-table"><tbody>{trs_}</tbody></table>')
        if pois:
            lis = "".join(f'<li>{p_[0] / 1000:.1f}km 지점 · {esc(p_[1].strip())}' + (f' <span class="tp-small">해발 {p_[2]}m</span>' if p_[2] is not None else "") + "</li>" for p_ in pois)
            parts.append(f'<h2 class="tp-h2">이름이 있는 지점</h2><ul class="cp-list">{lis}</ul>')
        if wt:
            parts.append(f'<h2 class="tp-h2">걷는 시간 가늠</h2><p class="tp-p">고도 단면으로 두 가지 알려진 식에 넣어 보았습니다. Naismith 규칙(평지 시속 5km에 오르막 600m당 1시간 더함)으로는 {fmt_min(round(wt[0]))}, '
                         f'Tobler의 하이킹 함수(경사에 따라 속도가 달라지는 식, 1993)로는 {fmt_min(round(wt[1]))}입니다. 짐, 쉬는 시간, 노면은 들어 있지 않으니 공식 안내 시간과 다를 수 있습니다.</p>')
        if c.get("elevSource"):
            parts.append(f'<p class="tp-small">원본 GPX에는 고도 값이 없어 위성 고도 자료(Copernicus DEM 30m)로 고도를 채웠습니다. 이 자료는 나무 높이가 섞여 있어 숲길의 오르막은 실제보다 조금 크게 나올 수 있습니다. 고도: {COPDEM_FT}</p>')
        parts.append(f'<p class="tp-small">경로는 한국등산트레킹지원센터가 {"2023년 8월" if "국가숲길" in (s.get("label") or "") else "2022년 1월"} 기준으로 올린 일회성 자료라 현재 노선과 다를 수 있습니다. 출발 전에 관리 기관의 안내를 확인해 주세요.</p>')
        ft_extra = '<section class="tp-sec">' + "".join(parts) + "</section>"
    _who = {0: "처음 걷는 분도 부담이 적은 편입니다.", 1: "평소 걷는 분이라면 무리 없이 걸을 수 있는 정도입니다.",
            2: "오르막이 꽤 있어서 물과 간식, 쉬는 시간을 넉넉히 잡는 편이 좋습니다.", 3: "체력이 필요한 코스입니다. 시간을 넉넉히 잡고 이른 시간에 출발하세요.",
            4: "매우 힘든 편입니다. 걷기에 익숙하고 체력이 충분할 때 도전하세요."}[dg_i]
    _rank = ""
    if _ft and len(_sib) > 1:
        _ds = sorted(_sib, key=lambda o: -dg_of(o)[0])
        _rank = f" {_ft} {len(_sib)}개 코스 중 난이도 점수는 {_ds.index(c) + 1}번째로 높습니다."
    _seg = "".join(f'<li class="{"on" if i == dg_i else ""}"><span>{n}</span></li>' for i, (_l, n) in enumerate(DG_BANDS))
    dg_html = (f'<section class="tp-sec dg"><p class="dg-top"><span class="dg-lab">칼랭크 난이도</span><b class="dg-name">{dg_name}</b>'
               f'<span class="dg-score">점수 {dg_score:.0f}</span></p><ol class="dg-scale" aria-label="난이도 5단계 중 {dg_i + 1}단계">{_seg}</ol>'
               f'<p class="tp-p">{esc(nm)}의 거리 {km:.1f}km와 누적 오르막 {gain:.0f}m로 계산한 점수는 {dg_score:.0f}점으로 "{dg_name}"입니다. {_who}{esc(_rank)}</p>'
               f'<p class="tp-small">트레일러닝 대회에서 쓰는 방식(ITRA)으로 환산하면 Km-effort는 {ke:.0f}(거리 {km:.1f}km + 오르막 {gain:.0f}m÷100)이고, 0~6점 중 {ke_pts}점에 해당합니다(이 점수의 범위는 Km-effort {("24 이하" if ke_pts == 0 else (f"{KE_BANDS[ke_pts-1]} 이상" if ke_pts == 6 else f"{KE_BANDS[ke_pts-1]}~{KE_BANDS[ke_pts]-1}"))}). {"트레일러닝 대회로 치면 가장 낮은 구간이라, 입문 거리에 가깝습니다. " if ke_pts == 0 else ""}<a href="dg-method.html#km-effort">환산 방법</a></p>'
               '<details class="tp-p"><summary>난이도 산정 방법</summary>'
               '<p class="tp-small">미국 국립공원관리청(셰넌도어 국립공원)이 하이킹 난이도를 가늠할 때 쓰는 식입니다. 누적 오르막(피트)에 2를 곱하고 거리(마일)를 곱한 뒤 제곱근을 취합니다. '
               '50 미만 쉬움, 50~100 보통, 100~150 조금 힘듦, 150~200 힘듦, 200 이상 매우 힘듦이고, 이름은 한국어로 옮겼습니다. '
               '거리와 오르막만 보는 식이라 노면, 날씨, 짧고 가파른 구간은 반영하지 못합니다. 공원관리청도 이 식이 "완벽하지 않다"고 밝혔습니다. '
               '그래서 위의 경사 단면도와 7% 넘게 가파른 구간 길이를 함께 보세요. 걷기 기준이며 달리기 난이도와는 다릅니다.</p>'
               '<p class="tp-small">출처: <a href="https://home.nps.gov/shen/planyourvisit/how-to-determine-hiking-difficulty.htm" rel="noopener" target="_blank">NPS, How to Determine Hiking Difficulty</a> · <a href="dg-method.html">계산 과정과 근거 자세히 보기</a></p></details></section>')
    body = f"""<section class="tp-sec"><p class="tp-p">{esc(lead)}</p></section>
{dg_html}
<section class="tp-sec">{profile_svg(prof)}
<table class="cv-table"><tbody>{stat_html}</tbody></table>{qual}</section>
{notable}
{course_gear_html(c, km)}
{course_fuel_html(c, _fuel_h)}
{_ins_html}
{ft_extra}{sun_block(c, wt)}
{map_block({"path": c["path"]}, '<p class="tp-small">초록 점이 출발, 파란 점이 도착입니다.</p>') if c.get("path") else ""}
<section class="tp-card"><h2 class="tp-h2">달린다면 걸리는 시간</h2><div class="tp-grid">
<label class="tp-field">평지 페이스 (분:초 / km)<input id="cpPace" type="text" inputmode="numeric" value="6:30" autocomplete="off"></label>
<label class="cv-check"><input type="checkbox" id="cpDown"> 내리막에서 빨라지는 것까지 반영</label></div>
<p><button type="button" class="tp-btn ghost" id="cpMine" hidden>내 최근 기록의 페이스로 채우기</button></p>
<p id="cpMsg" class="tp-small" role="status" aria-live="polite"></p>
<p class="cv-big"><b id="cpIndex">1.00</b><span> 코스 부하 지수 · <span id="cpBand"></span></span></p>
<table class="cv-table"><tbody id="cpTable"></tbody></table>
<p class="tp-small">달리는 사람의 에너지 비용 식(Minetti 등, J Appl Physiol 93:1039–1046, 2002)으로 계산합니다. {"걷는 시간은 위의 걷는 시간 가늠을 참고해 주세요." if _ft else "걷는 시간은 위의 두루누비 표기 소요시간을 참고해 주세요."} 걷기에 이 식이 맞는지는 아직 검증하지 못했습니다. 평지 기록으로 언덕 코스 시간을 어림한 연구(Crowell, bioRxiv 프리프린트, 동료 심사 전)에서도 대체로 10~20% 안에서 맞았고, 가파른 오르막 코스는 시간을 짧게 예측했습니다. 개인차와 노면에 따라 더 벌어질 수 있으니 여유를 두고 보세요.</p></section>
{"" if _ft else f'''<section class="tp-sec"><h2 class="tp-h2">기술 난이도 (칼랭크 구분)</h2>{tech_html}
<details class="tp-p"><summary>단계 설명</summary><ul class="cp-list">{legend}</ul></details>
<p class="tp-small">이 단계는 SAC 등급, Maverick 등 해외 사례를 참고해 칼랭크가 나눈 의견이고, 계산으로 나온 값이 아닙니다.</p></section>
<section class="tp-sec"><h2 class="tp-h2">현장 확인표</h2><p class="tp-p">확인한 항목만 내용과 확인한 날을 적었습니다. 확인하지 못한 항목은 미확인으로 두었습니다.</p>{rows}</section>'''}
{mt_near_html}
<section class="tp-sec" id="trMark" data-href="course-{c["id"]}.html" data-name="{esc(c["name"])}" data-km="{km:.2f}" data-gain="{gain:.0f}"><h2 class="tp-h2">내 목록에 담기</h2></section>
{_prog_html}
{rel}
<p class="tp-src">자료: {esc(s.get("label", ""))} — <a href="{esc(s.get("url", ""))}" rel="noopener" target="_blank">원문</a> ({esc(s.get("license", ""))}, {esc(s.get("fetched", ""))} 받음). 오르막·경사는 경로 파일의 고도로 칼랭크가 계산했습니다. <a href="trailroot.html">다른 코스 보기</a></p>
<script type="application/json" id="cpData">{data}</script>"""
    _tm = (f"걸어서 {fmt_min(round(min(wt)))}~{fmt_min(round(max(wt)))} 정도로 가늠합니다(Naismith 규칙과 Tobler 함수 기준, 공식 시간 아님)." if wt else
           (f"두루누비가 적은 소요시간은 {t_off}입니다." if t_off else "경로 거리와 오르막으로 가늠한 시간은 페이지의 계산기에서 내 페이스로 확인할 수 있습니다."))
    faq = [(f"{nm} 난이도는 어느 정도인가요?", f"칼랭크 기준으로 \"{dg_name}\"입니다. 거리 {km:.1f}km, 누적 오르막 {gain:.0f}m로 미국 국립공원관리청의 하이킹 난이도 식에 넣으면 {dg_score:.0f}점입니다. {_who}"),
           (f"{nm} 소요시간은 얼마나 걸리나요?", _tm),
           (f"{nm} 초보도 갈 수 있나요?", f"{_who} 다만 노면과 날씨는 점수에 들어 있지 않으니 출발 전에 관리 기관 안내를 확인해 주세요."),
           ("코스 부하 지수는 무엇인가요?", "코스를 평지 거리로 환산한 값을 실제 거리로 나눈 수입니다. 1.00이면 평지와 같습니다. 노면과 날씨는 들어 있지 않습니다."),
           (f"{nm}의 오르막은 얼마나 되나요?", f"경로 파일의 고도를 약 100m 구간으로 다듬어 계산하면 누적 오르막은 {gain:.0f}m, 내리막은 {loss:.0f}m입니다.")]
    faq.append((f"{nm}{josa(nm, '은', '는')} 몇 km인가요?", f"경로 파일 기준 {km:.1f}km입니다." + (f" 두루누비 표기 소요시간은 {t_off}입니다." if t_off else "")))
    if _ft:
        _cn2 = (c.get("waypoints") or {}).get("counts") or {}
        _has = [f"{k} {_cn2[k]}곳" for k in ("화장실", "쉼터", "전망", "약수터·샘터", "주차장") if _cn2.get(k)]
        faq.append((f"{nm}에 화장실이나 쉼터가 있나요?",
                    (f"자료에 찍힌 지점 가운데 경로에서 80m 안에 있는 것은 {', '.join(_has)}입니다. 같은 시설이 두 번 찍힌 경우가 있어 실제와 조금 다를 수 있습니다."
                     if _has else "자료에서 경로 80m 안의 화장실·쉼터 지점을 찾지 못했습니다. 자료에 없다는 뜻일 뿐 실제로 없다는 뜻은 아니니 출발 전에 관리 기관 안내를 확인해 주세요.")))
        _easy = [o for o in sorted(_sib, key=lambda o: dg_of(o)[0]) if o is not c and dg_of(o)[0] < dg_score][:2]
        if _easy:
            faq.append((f"{_ft}에서 {nm}보다 쉬운 코스는 어디인가요?",
                        "칼랭크 난이도 점수로 " + ", ".join(f"{o['name']}({dg_of(o)[2]}, {course_stats(o)[0]:.1f}km)" for o in _easy) + "가 더 쉽습니다."))
    elif _nm:
        faq.append((f"{nm} 근처·인근에 있는 산은 어디인가요?", "경로 3km 안에 있는 산은 " + ", ".join(m["name"] + "(" + _mt_dist(d_) + ")" for d_, m in _nm[:3]) + "입니다. 경로 좌표로 잰 값이라 같은 길이라는 뜻은 아닙니다."))
    if off.get("level"):
        faq.append((f"{nm}의 두루누비 난이도는 몇 단계인가요?", f"두루누비는 이 코스를 {off['level']}단계(1~3단계 중)로 적었습니다. 칼랭크 난이도 \"{dg_name}\"은 거리와 오르막으로 따로 계산한 값이라 두 표기가 다를 수 있습니다."))
    base = nm if (nm.endswith("코스") or _ft) else nm + " 코스"
    # 제목은 "산 이름 + 근처 + 코스 이름" 순서로 쓴다. 해파랑길·남파랑길 같은 코스 이름은
    # 일반인이 검색하지 않고 "OO산 근처", "강릉 걷기" 처럼 산·동네 이름으로 찾기 때문이다.
    # 이름만 있는 작은 산(좌표 한 점)은 본문에만 쓴다. 제목에 넣으면 지역명을 밀어내는데
    # 그 이름으로 검색하는 사람은 거의 없고, 좌표도 근사값이다.
    _tn = [h for h in _nm if not h[1].get("point")]
    _mt1 = _tn[0][1]["name"] if _tn and _tn[0][1]["name"] not in nm else ""
    _mtw = f"{_mt1} {_near_word(_tn[0][0])} " if _mt1 else ""
    _rg = " ".join(region.split()[:2])
    _rgw = (_rg + " ") if (_rg and not _mt1 and _rg not in nm) else ""
    h1 = f"{_mtw}{base} 난이도와 오르막"
    if _ft:
        _cn = (c.get("waypoints") or {}).get("counts") or {}
        _fac = ", ".join(f"{k} {_cn[k]}곳" for k in ("화장실", "쉼터", "전망") if _cn.get(k))
        desc = (f'{nm} 난이도 {dg_name}, {km:.1f}km, 누적 오르막 {gain:.0f}m, 걷는 시간 약 {fmt_min(round(min(wt)))}~{fmt_min(round(max(wt)))}. '
                f'{_ft} {len(_sib)}개 코스 중 어디쯤 가파른지, 경로 지도와 경사 색 단면도' + (f', {_fac}' if _fac else '') + '까지 정리했습니다.' + (f' {_near_word(_nm[0][0])} 산: {", ".join(m["name"] for _, m in _nm[:3])}.' if _nm else ''))
    else:
        desc = (f'{nm}{"(" + region + ")" if region else ""} 난이도 {dg_name}, {km:.1f}km, 누적 오르막 {gain:.0f}m. 경로 지도와 경사 색 단면도, 두루누비 표기 소요시간, 내 페이스로 걸리는 시간을 정리했습니다.' + (f' {_near_word(_nm[0][0])} 산: {", ".join(m["name"] for _, m in _nm[:3])}.' if _nm else ''))
    desc = (_mtw + desc) if _mt1 else (_rgw + desc)
    _tt = f"{_mtw}{_rgw}{nm} 난이도·소요시간·지도"
    return slug, page(slug, _tt, desc, h1,
                      f'{region + " · " if region else ""}{km:.1f}km · 오르막 {gain:.0f}m', body,
                      ["calrank-local.js", "trail-mark.js", "course.js", "course-page.js", "route-map.js"], faq, crumb=("트레일루트", "trailroot.html"),
                      place=({"type": "Place", "name": nm, "lat": c["path"][0][0], "lon": c["path"][0][1], "region": region} if c.get("path") else None),
                      modified=s.get("fetched") or None)


COURSE_PAGES = [course_page(c) for c in COURSES]


def dg_method_page():
    """칼랭크 난이도의 근거를 한곳에 모은 페이지. 숫자는 모두 코스 자료에서 그때그때 계산한다."""
    import statistics as _st
    cnt = [0] * 5
    for c in COURSES:
        cnt[dg_of(c)[1]] += 1
    n_all = len(COURSES)
    # 예시: 실제 코스 하나로 계산 과정을 보여 준다
    ex = next((c for c in COURSES if c["name"].startswith("해파랑길 5코스")), COURSES[0])
    ek, eg, _l, _s = course_stats(ex)
    e_ft = eg * 3.28084; e_mi = ek * 0.621371
    e_score, e_i, e_nm = diff_grade(ek, eg)
    # 두루누비 단계별 점수 분포 (공식 단계가 있는 코스만)
    byl = {1: [], 2: [], 3: []}
    for c in COURSES:
        lv = (c.get("official") or {}).get("level")
        if lv in byl:
            byl[lv].append(dg_of(c)[0])
    def _rk(v):
        o = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0] * len(v); i = 0
        while i < len(o):
            j = i
            while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
                j += 1
            for k in range(i, j + 1):
                r[o[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    _sc = []; _lv = []
    for c in COURSES:
        lv = (c.get("official") or {}).get("level")
        if lv in byl:
            _sc.append(dg_of(c)[0]); _lv.append(lv)
    _ra, _rb = _rk(_sc), _rk(_lv); _ma, _mb = _st.mean(_ra), _st.mean(_rb)
    rho = sum((x - _ma) * (y - _mb) for x, y in zip(_ra, _rb)) / (sum((x - _ma) ** 2 for x in _ra) * sum((y - _mb) ** 2 for y in _rb)) ** 0.5
    lvname = {1: "1단계(쉬움)", 2: "2단계(보통)", 3: "3단계(어려움)"}
    lv_rows = "".join(f"<tr><th>{lvname[k]}</th><td>{len(v)}개</td><td>{_st.median(v):.0f}점</td></tr>" for k, v in byl.items() if v)
    # 거리×오르막 환산표
    dists = [5, 10, 15, 20, 30]; gains = [100, 300, 500, 800, 1200]
    grid_head = "<tr><th>거리＼오르막</th>" + "".join(f"<th>{g}m</th>" for g in gains) + "</tr>"
    grid_rows = ""
    for d_ in dists:
        cells = "".join(f"<td>{diff_grade(d_, g_)[0]:.0f}점<br><span class=\"tp-small\">{diff_grade(d_, g_)[2]}</span></td>" for g_ in gains)
        grid_rows += f"<tr><th>{d_}km</th>{cells}</tr>"
    # 두루누비 단계와 크게 어긋나는 코스(단계 1인데 칼랭크는 '힘듦' 이상, 단계 3인데 칼랭크는 '보통' 이하)
    _hi = [c for c in COURSES if (c.get("official") or {}).get("level") == 1 and dg_of(c)[1] >= 3]
    _lo = [c for c in COURSES if (c.get("official") or {}).get("level") == 3 and dg_of(c)[1] <= 1]
    def _mm_rows(lst, k=6):
        lst = sorted(lst, key=lambda c: -abs(dg_of(c)[0] - 100))[:k]
        return "".join(f'<tr><th><a href="course-{c["id"]}.html">{esc(c["name"])}</a></th><td>{course_stats(c)[0]:.1f}km · {course_stats(c)[1]:.0f}m</td><td>{dg_of(c)[2]} ({dg_of(c)[0]:.0f}점)</td></tr>' for c in lst)
    n_lv = sum(len(v) for v in byl.values())
    who = ["처음 걷는 분도 부담이 적은 편입니다.", "평소 걷는 분이라면 무리 없이 걸을 수 있는 정도입니다.",
           "오르막이 꽤 있어서 물과 간식, 쉬는 시간을 넉넉히 잡는 편이 좋습니다.", "체력이 필요한 코스입니다. 시간을 넉넉히 잡고 이른 시간에 출발하세요.",
           "매우 힘든 편입니다. 걷기에 익숙하고 체력이 충분할 때 도전하세요."]
    ranges = ["50점 미만", "50~100점", "100~150점", "150~200점", "200점 이상"]
    band_rows = "".join(f"<tr><th>{DG_BANDS[i][1]}</th><td>{ranges[i]}</td><td>{who[i]}</td><td>{cnt[i]}개</td></tr>" for i in range(5))
    body = f"""<section class="tp-sec"><p class="tp-p">칼랭크 난이도는 코스의 거리와 누적 오르막, 이 두 숫자로 계산합니다. 식은 미국 국립공원관리청(NPS)이 셰넌도어 국립공원 안내에서 하이킹 난이도를 가늠할 때 쓰는 것을 그대로 따랐고, 점수 구간의 이름만 한국어로 옮겼습니다. 사람이 느낌으로 나눈 단계가 아니라 같은 숫자를 넣으면 누구나 같은 점수가 나오는 식입니다.</p></section>
<section class="tp-sec"><h2 class="tp-h2">계산은 이렇게 합니다</h2>
<p class="tp-p">누적 오르막(피트)에 2를 곱하고, 거리(마일)를 곱한 뒤 제곱근을 취합니다. 국립공원관리청 안내의 예시는 거리 10마일에 오르막 2,200피트인 코스로, 2,200 × 2 × 10 = 44,000이고 제곱근은 약 209.8이라 가장 높은 단계인 '매우 힘듦'에 해당합니다.</p>
<p class="tp-p">우리 코스로 해 보면 이렇습니다. {esc(ex["name"])}는 거리 {ek:.1f}km, 누적 오르막 {eg:.0f}m입니다. 단위를 바꾸면 {ek:.1f}km는 약 {e_mi:.1f}마일, {eg:.0f}m는 약 {e_ft:.0f}피트입니다. {e_ft:.0f} × 2 × {e_mi:.1f} = {e_ft * 2 * e_mi:,.0f}이고 제곱근은 {e_score:.0f}이므로 "{e_nm}"입니다.</p></section>
<section class="tp-sec"><h2 class="tp-h2">거리와 오르막을 함께 반영하는 이유</h2>
<p class="tp-p">오르막이 같아도 거리가 길면 그만큼 오래 걷고, 거리가 같아도 오르막이 많으면 한 걸음마다 더 힘이 듭니다. 곱셈으로 묶으면 둘 중 하나만 큰 코스보다 둘 다 큰 코스가 훨씬 높게 나옵니다. 제곱근은 점수가 너무 빨리 커지지 않게 눈금을 고르게 펴 주는 역할이라, 거리가 두 배가 되면 점수는 약 1.4배가 됩니다.</p>
<p class="tp-p">오르막이 얼마나 부담이 되는지는 생리학 측정으로도 확인됩니다. 이탈리아 연구진이 트레드밀의 경사를 -45%에서 +45%까지 바꿔 가며 에너지 소모를 잰 연구(Minetti 외, 2002)에서, 걷기에 드는 에너지는 +45% 오르막에서 평지 최소치의 약 10배까지 올라갔습니다. 반대로 -10% 안팎의 내리막에서 가장 적게 들었습니다. 다만 이 연구는 경사와 에너지의 관계를 잰 것이고, 위의 식과 직접 이어서 검증한 연구는 아닙니다. 식이 가진 한계는 아래에 따로 적었습니다.</p></section>
<section class="tp-sec"><h2 class="tp-h2">다섯 단계의 뜻</h2>
<div class="mt-wrap"><table class="mt-table"><thead><tr><th>단계</th><th>점수</th><th>이런 정도입니다</th><th>칼랭크 코스 수</th></tr></thead><tbody>{band_rows}</tbody></table></div>
<p class="tp-small">칼랭크에 실린 코스 {n_all}개를 같은 식으로 계산한 분포입니다. 걷기 기준이고, 달리기 난이도와는 다릅니다.</p></section>
<section class="tp-sec"><h2 class="tp-h2">거리와 오르막으로 보는 점수표</h2>
<p class="tp-p">내가 가려는 길의 거리와 오르막을 알면 코스를 찾지 않아도 대략의 단계를 알 수 있습니다.</p>
<div class="mt-wrap"><table class="mt-table"><thead>{grid_head}</thead><tbody>{grid_rows}</tbody></table></div>
<p class="tp-small">같은 식으로 계산한 값이고, 거리는 km, 오르막은 m입니다.</p></section>
<section class="tp-sec"><h2 class="tp-h2">공식 난이도와 맞춰 봤습니다</h2>
<p class="tp-p">한국관광공사 두루누비에는 코스마다 1~3단계 난이도가 붙어 있습니다. 두루누비 단계가 있는 코스에서 칼랭크 점수의 중앙값을 단계별로 나눠 보면 단계가 올라갈수록 점수도 올라갑니다.</p>
<div class="mt-wrap"><table class="mt-table"><thead><tr><th>두루누비 단계</th><th>코스 수</th><th>칼랭크 점수 중앙값</th></tr></thead><tbody>{lv_rows}</tbody></table></div>
<p class="tp-small">순위를 매겨 견준 상관계수(스피어만)는 {rho:.2f}였습니다. 방향은 같지만 완전히 같은 기준은 아닙니다. 두루누비 단계를 어떻게 정했는지는 이 비교에서 확인하지 못했습니다.</p></section>
<section class="tp-sec" id="mismatch"><h2 class="tp-h2">두 기준이 크게 어긋나는 코스</h2>
<p class="tp-p">두루누비 단계가 있는 코스 {n_lv}개 가운데, 두루누비는 1단계(쉬움)인데 칼랭크 점수는 '힘듦' 이상인 코스가 {len(_hi)}개, 두루누비는 3단계(어려움)인데 칼랭크는 '보통' 이하인 코스가 {len(_lo)}개입니다. 거의 모든 코스에서 두 기준이 크게 벌어지지 않고, 벌어진 코스는 아래에 모두 적었습니다.</p>
<h3 class="tp-h3">두루누비 1단계인데 칼랭크는 힘듦 이상</h3>
<div class="mt-wrap"><table class="mt-table"><thead><tr><th>코스</th><th>거리·오르막</th><th>칼랭크 난이도</th></tr></thead><tbody>{_mm_rows(_hi)}</tbody></table></div>
<h3 class="tp-h3">두루누비 3단계인데 칼랭크는 보통 이하</h3>
<div class="mt-wrap"><table class="mt-table"><thead><tr><th>코스</th><th>거리·오르막</th><th>칼랭크 난이도</th></tr></thead><tbody>{_mm_rows(_lo)}</tbody></table></div>
<p class="tp-small">칼랭크 점수는 거리와 오르막만 보므로 노면이나 길찾기 같은 요소는 들어 있지 않습니다. 두루누비가 그런 요소를 반영했는지는 기준 문서를 찾지 못해 확인하지 못했고, 어느 쪽이 맞는지는 이 비교만으로 알 수 없습니다.</p></section>
<section class="tp-sec" id="km-effort"><h2 class="tp-h2">트레일러닝 대회식(Km-effort)으로도 환산합니다</h2>
<p class="tp-p">국제트레일러닝협회(ITRA)는 대회 코스의 난이도를 Km-effort로 나타냅니다. 거리 1km를 1로 치고, 누적 오르막 100m마다 1을 더하는 단순한 환산입니다. 이 값을 0~6점으로 나눠 대회에 붙이는데, 경계는 25, 45, 75, 115, 155, 210입니다. 칼랭크는 이 방식을 참고용으로 코스 페이지에 함께 적습니다. 예를 들어 {esc(ex["name"])}는 {ek:.1f} + {eg:.0f}÷100 = {km_effort(ek, eg)[0]:.0f}이고 {km_effort(ek, eg)[1]}점입니다.</p>
<p class="tp-p">두 방식은 보는 눈이 다릅니다. 칼랭크 난이도는 걷는 하이킹의 부담을, Km-effort는 달리는 대회의 환산 거리를 말합니다. 그래서 같은 코스라도 단계가 다르게 나올 수 있고, 하나가 틀리고 하나가 맞는 관계는 아닙니다. 이 페이지의 칼랭크 난이도는 걷기 기준입니다. 산 페이지에는 Km-effort를 적지 않습니다. 산 하나의 등산로를 모두 더한 값은 한 번에 걷는 한 코스가 아니라서, 합쳐서 환산하면 실제 산행과 다른 숫자가 나오기 때문입니다.</p></section>
<section class="tp-sec"><h2 class="tp-h2">이 식이 못 보는 것</h2>
<p class="tp-p">국립공원관리청도 이 식이 "완벽하지 않다"고 밝혔습니다. 안내에 나온 예로 Dark Hollow Falls는 점수가 36.3이라 가장 쉬운 단계에 들지만, 짧은 거리에 경사가 가팔라서 공원은 한 단계 위인 '보통'으로 따로 분류합니다. 그래서 점수만 보지 말고 거리와 오르막을 함께 보라고 안내합니다.</p>
<p class="tp-p">칼랭크도 같은 이유로 코스 페이지에 경사 단면도와 7% 넘게 가파른 구간의 길이를 점수 옆에 나란히 둡니다. 노면, 날씨, 배낭 무게, 개인의 체력은 점수에 들어 있지 않습니다. 걷기 기준이라 달릴 때의 난이도와도 다릅니다.</p></section>
<section class="tp-sec" id="embed"><h2 class="tp-h2">내 블로그·클럽 페이지에 넣기</h2>
<p class="tp-p">코스 하나의 칼랭크 난이도를 작은 카드로 넣을 수 있습니다. 아래 코드의 <code>course-dr-4190</code> 자리에 코스 페이지 주소의 이름(course-로 시작하는 부분, .html 앞까지)을 넣으면 됩니다. 카드를 누르면 계산 근거가 있는 코스 페이지로 이어집니다.</p>
<pre class="tp-small" style="overflow-x:auto;white-space:pre-wrap">&lt;iframe src="https://calrank.vercel.app/widget-course.html?c=course-dr-4190" width="320" height="150" style="border:0" loading="lazy" title="칼랭크 난이도"&gt;&lt;/iframe&gt;</pre></section>
<section class="tp-sec"><h2 class="tp-h2">출처</h2>
<ul class="cp-list"><li><a href="https://home.nps.gov/shen/planyourvisit/how-to-determine-hiking-difficulty.htm" rel="noopener" target="_blank">미국 국립공원관리청 셰넌도어 국립공원, How to Determine Hiking Difficulty</a></li>
<li>국제트레일러닝협회(ITRA), Discover Trail Running의 Km-effort와 코스 난이도 점수 안내(itra.run)</li>
<li><a href="https://iris.unibs.it/handle/11379/540545" rel="noopener" target="_blank">Minetti AE 외, Energy cost of walking and running at extreme uphill and downhill slopes, Journal of Applied Physiology 93(3), 2002</a></li></ul>
<p class="tp-small">코스 거리와 오르막은 두루누비와 산림청 자료를 바탕으로 칼랭크가 계산했고, 코스 페이지마다 출처를 적었습니다.</p></section>"""
    faq = [("칼랭크 난이도는 누가 정했나요?", "미국 국립공원관리청이 하이킹 난이도를 가늠할 때 쓰는 식을 그대로 따랐습니다. 칼랭크가 만든 식이 아니고, 점수 구간의 이름만 한국어로 옮겼습니다."),
           ("난이도 점수는 어떻게 계산하나요?", "누적 오르막(피트)에 2를 곱하고 거리(마일)를 곱한 뒤 제곱근을 취합니다. 50 미만 쉬움, 50~100 보통, 100~150 조금 힘듦, 150~200 힘듦, 200 이상 매우 힘듦입니다."),
           ("점수가 낮으면 쉬운 길이라고 믿어도 되나요?", "짧은 거리에 가파른 구간이 있으면 점수는 낮아도 힘들 수 있습니다. 국립공원관리청도 같은 한계를 밝히고 있어, 코스 페이지의 경사 단면도와 가파른 구간 길이를 함께 보시길 권합니다.")]
    return page("dg-method.html", "코스 난이도 계산 방법 — 거리와 오르막으로 매기는 칼랭크 난이도",
                "코스 난이도를 거리와 누적 오르막으로 계산하는 방법을 모두 공개합니다. 미국 국립공원관리청 식, 점수 구간, 두루누비 난이도와 맞춰 본 결과, 식이 못 보는 것까지 적었습니다.",
                "칼랭크 난이도 산정 방법", "거리와 누적 오르막으로 계산하고, 계산 과정과 근거, 한계를 모두 적었습니다.", body, [], faq, crumb=("트레일루트", "trailroot.html"))


DGM = dg_method_page() if COURSES else None


# ── 길 이름별·시도별 모음 (코스가 속한 긴 길 4곳, 시도) ───────────────────────
import re as _re2
def _num(c):
    if c.get("trail"):
        m_ = _re2.search(r"-(\d+)$", c["id"])
        return (int(m_.group(1)) if m_ else 999, 0, c["name"])
    m = _re2.search(r"(\d+)(?:-(\d+))?\s*코스", c["name"]) or _re2.search(r"(\d+)", c["name"])
    return (int(m.group(1)) if m else 999, int(m.group(2)) if (m and m.lastindex and m.lastindex > 1 and m.group(2)) else 0, c["name"])


def ft_group_page(slug, name, intro, cs):
    cs = sorted(cs, key=_num)
    st = {c["id"]: course_stats(c) for c in cs}
    wt = {c["id"]: walk_time(c["profile"]) for c in cs}
    km = sum(v[0] for v in st.values()); gain = sum(v[1] for v in st.values())
    per = lambda c: st[c["id"]][1] / max(st[c["id"]][0], 0.1)
    easy = sorted(cs, key=per)[:3]; hard = sorted(cs, key=lambda c: -per(c))[:3]
    short = sorted(cs, key=lambda c: st[c["id"]][0])[:3]
    longest = max(cs, key=lambda c: st[c["id"]][0])
    nm_short = lambda c: c["name"].replace(name, "").strip() or c["name"]
    any_fac = any(((c.get("waypoints") or {}).get("counts") or {}).get(x) for c in cs for x in ("화장실", "쉼터", "전망"))
    rows = ""
    for c in cs:
        k_, g_, _l, sk = st[c["id"]]; w_ = wt[c["id"]]
        cn = ((c.get("waypoints") or {}).get("counts") or {})
        fac = " · ".join(f"{x} {cn[x]}" for x in ("화장실", "쉼터", "전망") if cn.get(x)) or "-"
        _hm = lambda m_: f"{int(round(m_)) // 60}:{int(round(m_)) % 60:02d}"
        rows += (f'<tr><td><a href="course-{c["id"]}.html">{esc(nm_short(c))}</a></td><td>{k_:.1f}km</td><td>{g_:.0f}m</td><td>{diff_grade(k_, g_)[2]}</td><td class="hide-sm">{g_ / max(k_, 0.1):.0f}m</td>'
                 f'<td>{_hm(min(w_))}~{_hm(max(w_))}</td><td class="hide-sm">{max(p_[1] for p_ in c["profile"]):.0f}m</td>' + (f'<td class="hide-sm">{fac}</td>' if any_fac else '') + '</tr>')
    table = ('<div class="mt-wrap"><table class="mt-table"><thead><tr><th>코스</th><th>거리</th><th>오르막</th><th>난이도</th><th class="hide-sm">1km당</th><th>걷는 시간<span class="hide-sm"> (시:분)</span></th><th class="hide-sm">최고점</th>' + ('<th class="hide-sm">시설</th>' if any_fac else '') + '</tr></thead>'
             f'<tbody>{rows}</tbody></table></div>')
    lk = lambda lst: "".join(f'<li><a href="course-{c["id"]}.html">{esc(c["name"])}</a> · {st[c["id"]][0]:.1f}km · 1km당 오르막 {per(c):.0f}m · 난이도 {dg_of(c)[2]}</li>' for c in lst)
    lead = (f"{name}{josa(name, '은', '는')} 칼랭크에 코스 {len(cs)}개가 실려 있고, 모두 합치면 {km:.0f}km이며 누적 오르막은 {gain:.0f}m입니다. "
            f"가장 긴 코스는 {nm_short(longest)}({st[longest['id']][0]:.1f}km)입니다. 1km당 오르막으로 가장 가파른 코스는 {nm_short(hard[0])}(약 {per(hard[0]):.0f}m), 가장 완만한 코스는 {nm_short(easy[0])}(약 {per(easy[0]):.0f}m)입니다.")
    body = f"""<section class="tp-sec"><p class="tp-p">{esc((intro + " ") if intro else "")}{esc(lead)}</p></section>
{_prog_sec(name, cs)}
<section class="tp-sec"><h2 class="tp-h2">{esc(name)} 코스별 한눈에 보기</h2>{table}
<p class="tp-small">걷는 시간은 Naismith 규칙과 Tobler 하이킹 함수 두 값의 범위로 가늠한 것이고 공식 시간이 아닙니다. 최고점은 고도 자료로 잰 코스 안의 가장 높은 곳입니다. 휴대폰 화면에서는 1km당 오르막, 최고점, 시설 열을 줄였고, 코스 이름을 누르면 모두 볼 수 있습니다. 시설은 자료에 찍힌 지점 중 경로에서 80m 안에 있는 것의 수이며, 자료에 시설 지점이 없는 길은 이 열을 두지 않았습니다.</p></section>
<section class="tp-sec"><h2 class="tp-h2">처음이라면 완만한 코스부터</h2><ul class="cp-list">{lk(easy)}</ul>
<p class="tp-small">1km당 오르막이 적은 순입니다. 짧은 코스는 {nm_short(short[0])}({st[short[0]['id']][0]:.1f}km)처럼 반나절 안에 걸을 수 있는지 가늠해 보세요.</p></section>
<section class="tp-sec"><h2 class="tp-h2">체력이 필요한 코스</h2><ul class="cp-list">{lk(hard)}</ul></section>
<p class="tp-src">자료: {esc((cs[0].get("source") or {}).get("label", ""))} — <a href="{esc((cs[0].get("source") or {}).get("url", ""))}" rel="noopener" target="_blank">원문</a> ({esc((cs[0].get("source") or {}).get("license", ""))}). 일회성으로 올라온 자료라 현재 노선과 다를 수 있습니다. 거리·오르막·시간은 칼랭크가 계산했습니다. <a href="trailroot.html">전체 코스 보기</a></p>"""
    faq = [(f"{name}에서 가장 가파른 코스는 어디인가요?", f"1km당 오르막으로 보면 {hard[0]['name']}(약 {per(hard[0]):.0f}m)가 가장 높습니다."),
           (f"{name}에서 초보가 걷기 좋은 코스는 어디인가요?", f"1km당 오르막이 가장 적은 {easy[0]['name']}(약 {per(easy[0]):.0f}m)부터 보시길 권합니다. 거리({st[easy[0]['id']][0]:.1f}km)도 함께 확인하세요."),
           (f"{name}은 전체 몇 km인가요?", f"칼랭크에 실린 {len(cs)}개 코스를 합치면 약 {km:.0f}km입니다. 코스가 겹치는 구간이 있으면 실제 길이와 다를 수 있습니다.")]
    return slug, page(slug, f"{name} 코스별 거리·오르막·난이도 정리", f"{name} {len(cs)}개 코스의 거리, 누적 오르막, 걷는 시간 가늠, 화장실·쉼터 수를 표로 모았습니다. 완만한 코스와 힘든 코스를 데이터로 나눠 보았습니다.",
                      f"{name} 코스 모음", f"{len(cs)}개 코스 · {km:.0f}km · 오르막 합계 {gain:.0f}m", body, ["calrank-local.js", "trail-mark.js"], faq, crumb=("트레일루트", "trailroot.html"))


def group_page(slug, name, intro, cs):
    stats = [course_stats(c) for c in cs]
    km = sum(s[0] for s in stats); gain = sum(s[1] for s in stats)
    lv = {1: 0, 2: 0, 3: 0}
    for c in cs:
        l_ = (c.get("official") or {}).get("level")
        if l_ in lv:
            lv[l_] += 1
    def per(c):
        k_, g_, _, _ = course_stats(c)
        return g_ / max(k_, 0.1)
    hardest = sorted(cs, key=lambda c: -per(c))[:5]
    def li(c):
        k_, g_, _, _ = course_stats(c)
        l2 = (c.get("official") or {}).get("level")
        return (f'<li><a href="course-{c["id"]}.html">{esc(c["name"])}</a> · {esc(c.get("region") or "")} · {k_:.1f}km · 오르막 {g_:.0f}m · 난이도 {dg_of(c)[2]}'
                + (f' · 두루누비 난이도 {l2}' if l2 else "") + _near_txt(c) + "</li>")
    if cs and all(c.get("trail") for c in cs):
        return ft_group_page(slug, name, intro, cs)
    lead = (f"{name}에서 칼랭크에 실린 코스는 {len(cs)}개입니다. 모두 합치면 {km:.0f}km이고 누적 오르막은 {gain:.0f}m입니다. "
            f"두루누비 난이도로는 1단계 {lv[1]}개, 2단계 {lv[2]}개, 3단계 {lv[3]}개입니다.")
    body = f"""<section class="tp-sec"><p class="tp-p">{esc((intro + " ") if intro else "")}{esc(lead)}</p>
<p class="tp-small">경로 파일의 거리가 공식 거리와 맞는 코스만 실었습니다. 빠진 코스는 아직 검증하지 못한 것입니다.</p></section>
{_prog_sec(name, cs) if name in ROUTES else ""}
<section class="tp-sec"><h2 class="tp-h2">1km당 오르막이 많은 코스</h2><ul class="cp-list">{"".join(li(c) for c in hardest)}</ul></section>
<section class="tp-sec"><h2 class="tp-h2">전체 코스</h2><ul class="cp-list">{"".join(li(c) for c in sorted(cs, key=_num))}</ul></section>
<p class="tp-src">자료: 한국관광공사 두루누비 코스 정보(공공데이터포털 오픈 API). 계산과 표시는 칼랭크가 했습니다. <a href="trailroot.html">전체 코스 보기</a></p>"""
    faq = [(f"{name}에서 오르막이 가장 많은 코스는 어디인가요?", f"1km당 오르막으로 보면 {hardest[0]['name']}({per(hardest[0]):.0f}m/km)가 가장 높습니다.")]
    return slug, page(slug, f"{name} 코스 모음 — 난이도와 오르막", f"{name}의 코스 {len(cs)}개: 거리, 누적 오르막, 난이도를 코스별로 정리했습니다. 코스마다 경로 지도와 경사 단면도가 있습니다.",
                      f"{name} 코스 모음", f"{len(cs)}개 코스 · {km:.0f}km · 오르막 합계 {gain:.0f}m", body, ["calrank-local.js", "trail-mark.js"], faq, crumb=("트레일루트", "trailroot.html"))


_groups = []
for _r, (_sl, _in) in ROUTES.items():
    _cs = [c for c in COURSES if route_of(c) == _r]
    if len(_cs) >= 3:
        _groups.append((f"trailroute-{_sl}.html", _r, _in, _cs))
for _s, _sl in SIDO.items():
    _cs = [c for c in COURSES if sido_of(c) == _s]
    if len(_cs) >= 3:
        _groups.append((f"trailarea-{_sl}.html", f"{_s} 지역", "", _cs))
GROUP_PAGES = [group_page(sl, nm_, it_, cs_) for sl, nm_, it_, cs_ in _groups]
GROUP_LINKS = [(sl, nm_, len(cs_)) for sl, nm_, it_, cs_ in _groups]


def hub_page():
    by = {}
    for c in COURSES:
        by.setdefault((c.get("region") or "지역 미표기").split()[0], []).append(c)
    def li(c):
        km, gain, _, _ = course_stats(c)
        lv = (c.get("official") or {}).get("level")
        return (f'<li><a href="course-{c["id"]}.html">{esc(c["name"])}</a> · {esc(c.get("region") or "")} · {km:.1f}km · 오르막 {gain:.0f}m · 난이도 {dg_of(c)[2]}'
                + (f' · 두루누비 난이도 {lv}' if lv else "") + _near_txt(c) + "</li>")
    secs = ""
    for reg in sorted(by, key=lambda r: (r == "지역 미표기", r)):
        cs = sorted(by[reg], key=lambda c: c["name"])
        secs += f'<section class="tp-sec"><h2 class="tp-h2">{esc(reg)} ({len(cs)})</h2><ul class="cp-list">{"".join(li(c) for c in cs)}</ul></section>'
    steepest = sorted(COURSES, key=lambda c: -course_stats(c)[1] / max(course_stats(c)[0], 0.1))[:10]
    top = "".join(li(c) for c in steepest)
    lvtab = ""
    if LV_MED:
        rows_ = "".join(f"<tr><th>두루누비 난이도 {lv}</th><td>{v[0]:.0f} m ({v[1]}개)</td></tr>" for lv, v in sorted(LV_MED.items()))
        lvtab = ('<section class="tp-sec"><h2 class="tp-h2">두루누비 난이도별 1km당 오르막</h2>'
                 f'<table class="cv-table"><tbody>{rows_}</tbody></table>'
                 '<p class="tp-small">여기 실린 코스의 중앙값입니다. 난이도 숫자가 클수록 1km당 오르막이 많은 경향이 있습니다.</p></section>')
    body = f"""<section class="tp-sec"><p class="tp-p">걷는 길마다 거리, 누적 오르막, 경사 색 단면도를 한 장에 모았습니다. 경로 파일의 고도로 계산했고, 흔들린 GPS 고도는 약 100m 구간으로 다듬었습니다. 지금 {len(COURSES)}개 코스가 있습니다.</p>
{('<p class="tp-small">산 코스는 <a href="mountains.html">산별 등산로</a>에서 볼 수 있습니다. 코스마다 붙는 칼랭크 난이도는 <a href="dg-method.html">어떻게 계산하는지</a> 근거와 함께 적어 두었습니다.</p>' if MOUNTAINS else "")}
<p class="tp-small">직접 만든 경로(GPX)는 <a href="course.html">코스 판정</a>에서 바로 계산해 볼 수 있습니다. 대회 코스 GPX는 <a href="yardage.html">대회 코스 야디지북</a>에서 구간별로 볼 수 있습니다. 파일은 이 기기 밖으로 나가지 않습니다.</p></section>
<section class="tp-sec mn" id="trMine" hidden><h2 class="tp-h2">내 목록</h2></section>
<div class="mn-import"><span class="mn-import-t">다른 기기에서 저장한 백업이 있으면 불러올 수 있습니다.</span><label class="tp-btn ghost mn-file">백업 불러오기<input type="file" id="trImport" accept="application/json,.json"></label><span id="trImportMsg" class="tp-small" role="status"></span></div>
<section class="tp-sec"><label class="tp-field">이름·지역으로 찾기<input id="listQ" type="search" placeholder="예: 해파랑길, 서울둘레길 (산 이름도 찾아 줍니다)" autocomplete="off"></label><p id="listMsg" class="tp-small" role="status" aria-live="polite"></p><ul id="listMore" class="cp-list" data-other="mountains.html"></ul></section>
{lvtab}
<section class="tp-sec"><h2 class="tp-h2">길과 지역으로 보기</h2><ul class="cp-list">{"".join(f'<li><a href="{sl}">{esc(nm_)}</a> · {n_}개 코스</li>' for sl, nm_, n_ in GROUP_LINKS)}</ul></section>
<section class="tp-sec"><h2 class="tp-h2">1km당 오르막이 많은 순</h2><ul class="cp-list">{top}</ul></section>
{secs}
<p class="tp-src">자료: 한국관광공사 두루누비 코스 정보(공공데이터포털 오픈 API), 한국등산트레킹지원센터 오감만족 숲길·국가숲길 코스(공공데이터포털 파일데이터, 둘 다 이용허락범위 제한 없음). 계산과 표시는 칼랭크가 했습니다.</p>"""
    faq = [("거리가 같아도 힘든 정도가 왜 다른가요?", "오르막이 많으면 같은 거리도 더 힘듭니다. 그래서 거리와 함께 누적 오르막, 가파른 구간 길이를 같이 보여 드립니다."),
           ("고도는 어떻게 계산했나요?", "경로 파일에 적힌 GPS 고도를 약 100m 구간으로 다듬어 계산했습니다. 그대로 더하면 오르막이 실제보다 크게 나올 수 있어서입니다.")]
    return "trailroot.html", page("trailroot.html", "트레일루트 코스 모음 — 걷기 코스 오르막과 소요시간",
        f"걷기 좋은 {len(COURSES)}개 코스의 거리, 누적 오르막, 경사 색 단면도를 지역별로 모았습니다. 내 페이스로 걸리는 시간도 계산해 볼 수 있습니다.",
        "트레일루트", f"걷는 길의 오르막을 한눈에 · {len(COURSES)}개 코스", body, ["calrank-local.js", "trail-mark.js", "list-filter.js"], faq, crumb=("트레일루트", "trailroot.html"))



# ── 산 페이지 (data/mountains.json 의 산마다 한 장) ──────────────────────────
MOUNTAINS = []
_mp = Path(_os.environ.get("CALRANK_MOUNTAINS") or (ROOT / "data/mountains.json"))
if _mp.exists():
    MOUNTAINS = json.loads(_mp.read_text(encoding="utf-8")).get("mountains", [])
MT_FETCHED = ""
if _mp.exists():
    MT_FETCHED = json.loads(_mp.read_text(encoding="utf-8")).get("fetched", "")
MT_VERIFIED = False  # 산림청 구간 속성(상행·하행 시간, 난이도)의 뜻을 문서로 확인하면 True 로 바꾼다.
COPDEM = ("produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 "
          "provided under COPERNICUS by the European Union and ESA; all rights reserved.")
G_BANDS = [(5, "gp-0", "5% 미만"), (10, "gp-1", "5~10%"), (15, "gp-2", "10~15%"), (999, "gp-3", "15% 이상")]


_NAME_N = {}
for _m in MOUNTAINS:
    _k = (_m["name"], _m.get("region") or "")
    _NAME_N[_k] = _NAME_N.get(_k, 0) + 1
_NAME_ANY = {}
for _m in MOUNTAINS:
    _NAME_ANY[_m["name"]] = _NAME_ANY.get(_m["name"], 0) + 1


def mt_title(m):
    """같은 이름의 산이 여럿이면 지역을, 지역을 모르면 구간 최고 고도를 붙여 구분한다."""
    nm = m["name"]
    if m.get("region") and _NAME_N.get((nm, m["region"]), 0) <= 1:
        return f'{nm}({m["region"]})'
    hi = max(s["endM"] for s in m["sections"])
    if m.get("region"):
        return f'{nm}({m["region"]}, 약 {hi:.0f}m)'
    return f'{nm}(약 {hi:.0f}m)' if _NAME_ANY.get(nm, 0) > 1 else nm


def mt_stats(m):
    S = m["sections"]
    tot = sum(s["lenM"] for s in S) / 1000
    steep = sum(s["steepKm"] for s in S)
    hi = max(s["endM"] for s in S); lo = min(s["startM"] for s in S)
    return tot, steep, hi, lo


def grade_bar(S):
    tot = sum(s["lenM"] for s in S) or 1
    parts, leg = "", ""
    for i, (lim, cl, nm) in enumerate(G_BANDS):
        lo_ = G_BANDS[i - 1][0] if i else 0
        L = sum(s["lenM"] for s in S if lo_ <= abs(s["meanGrade"]) < lim)
        pct = L / tot * 100
        if pct >= 0.5:
            parts += f'<span class="gb-seg {cl}" style="width:{pct:.1f}%"></span>'
        leg += f'<li><i class="gp-sw {cl}"></i>구간 평균 경사 {nm} · {pct:.0f}%</li>'
    return f'<div class="gb-bar" role="img" aria-label="구간 평균 경사별 길이 비율">{parts}</div><ul class="gp-leg">{leg}</ul>'


MT_SIDO = {"서울특별시": ("서울", "seoul"), "부산광역시": ("부산", "busan"), "대구광역시": ("대구", "daegu"), "인천광역시": ("인천", "incheon"),
           "광주광역시": ("광주", "gwangju"), "대전광역시": ("대전", "daejeon"), "울산광역시": ("울산", "ulsan"), "세종특별자치시": ("세종", "sejong"),
           "경기도": ("경기", "gyeonggi"), "강원특별자치도": ("강원", "gangwon"), "강원도": ("강원", "gangwon"), "충청북도": ("충북", "chungbuk"),
           "충청남도": ("충남", "chungnam"), "전북특별자치도": ("전북", "jeonbuk"), "전라북도": ("전북", "jeonbuk"), "전라남도": ("전남", "jeonnam"),
           "경상북도": ("경북", "gyeongbuk"), "경상남도": ("경남", "gyeongnam"), "제주도": ("제주", "jeju"), "제주특별자치도": ("제주", "jeju")}


def mt_sido(m):
    r = (m.get("region") or "").split()
    return MT_SIDO.get(r[0]) if r else None


_mg = {}
for _m in MOUNTAINS:
    _k = mt_sido(_m)
    if _k:
        _mg.setdefault(_k, []).append(_m)


def _mt_prof(m):
    S = m["sections"]; tot = sum(x["lenM"] for x in S) or 1
    r15 = sum(x["lenM"] for x in S if abs(x["meanGrade"]) >= 15) / tot * 100
    gain = sum(x["gainM"] for x in S)
    return r15, gain, tot / 1000


_MT_R15 = sorted(_mt_prof(o)[0] for o in MOUNTAINS if _mt_prof(o)[2] >= 2)
_MT_GAIN = sorted(_mt_prof(o)[1] for o in MOUNTAINS if _mt_prof(o)[2] >= 2)


def _pct_above(arr, v):
    """arr 중 v보다 작은 값의 비율(%)"""
    import bisect
    return bisect.bisect_left(arr, v) / len(arr) * 100 if arr else 0


def mountain_page(m):
    mid = m["id"]; slug = f"mountain-{mid}.html"
    S = m["sections"]; nm = m["name"]
    tot, steep, hi, lo = mt_stats(m)
    off = m.get("officialHeightM")
    where = f'{m["region"]}에 있는 ' if m.get("region") else ""
    lead = (f"{nm}{josa(nm, '은', '는')} {where}산입니다. 산림청 자료에는 등산로 구간이 {len(S)}개 있고, 모두 합치면 {tot:.1f}km입니다. "
            f"구간 중 가장 높은 곳은 해발 약 {hi:.0f}m이고, 평균 경사가 15%를 넘는 구간이 {sum(s['lenM'] for s in S if abs(s['meanGrade']) >= 15) / 1000:.1f}km 있습니다.")
    rows = [("등산로 구간 수", f"{len(S)}개"), ("구간 길이 합계", f"{tot:.1f} km"),
            ("구간 최고 고도(30m 고도 자료)", f"{hi:.0f} m"), ("구간 최저 고도", f"{lo:.0f} m")]
    if off:
        rows.append(("산림청 산 높이", f"{off:.0f} m"))
    rows.append(("경사 12% 넘는 길", f"{steep:.1f} km"))
    stat_html = "".join(f"<tr><th>{a}</th><td>{b}</td></tr>" for a, b in rows)
    top = sorted(S, key=lambda s: -abs(s["meanGrade"]))[:12]
    th = ["구간 길이", "고도(낮은 곳→높은 곳)", "평균 경사", "오르막 합"]
    if MT_VERIFIED:
        th += ["산림청 상행", "산림청 하행", "산림청 난이도"]
    trs = ""
    for s in top:
        tds = [f'{s["lenM"]}m', f'{s["startM"]}→{s["endM"]}m', f'{abs(s["meanGrade"]):.0f}%', f'{s["gainM"]}m']
        if MT_VERIFIED:
            tds += [f'{s["upln"]:.0f}분', f'{s["gngd"]:.0f}분', f'{s["dgdf"]}']
        trs += "<tr>" + "".join(f"<td>{t}</td>" for t in tds) + "</tr>"
    table = ('<div class="mt-wrap"><table class="mt-table"><thead><tr>' + "".join(f"<th>{t}</th>" for t in th) + f"</tr></thead><tbody>{trs}</tbody></table></div>")
    _r15, _gain, _km = _mt_prof(m)
    mt_prof_html = ""
    if _km >= 2:
        _pr = _pct_above(_MT_R15, _r15); _pg = _pct_above(_MT_GAIN, _gain)
        _steep_txt = ("가파른 길이 거의 없는 편" if _r15 < 5 else "가파른 길이 일부 섞인 편" if _r15 < 20 else "가파른 길이 꽤 많은 편" if _r15 < 40 else "가파른 길이 대부분인 편")
        mt_prof_html = (f'<section class="tp-sec"><h2 class="tp-h2">{esc(nm)} 한눈에 보기</h2>'
            f'<p class="tp-p">구간 평균 경사로 보면 {esc(nm)}{josa(nm, "은", "는")} {_steep_txt}입니다. 전체 등산로 중 평균 경사 15% 이상인 길이 {_r15:.0f}%이고, '
            f'이 비율은 칼랭크에 실린 산(등산로 2km 이상)의 {_pr:.0f}%보다 높습니다. '
            f'구간별 오르막을 전부 더하면 {_gain:,.0f}m입니다. 산 전체 등산로의 합이라, 한 번의 산행에서 오르는 높이와는 다릅니다.</p>'
            f'<p class="tp-small">경사 15%는 약 8.5도입니다. 구간의 낮은 끝과 높은 끝을 이은 평균값이라, 구간 안의 짧은 급경사는 드러나지 않습니다. 산행 계획에는 아래 가파른 구간과 지도를 함께 보세요.</p></section>')
    mt_map = ""
    if all(s.get("path") for s in S):
        mt_map = map_block({"secs": [{"p": s["path"], "g": s["meanGrade"]} for s in S]},
                           '<p class="tp-small">선의 색은 구간 평균 경사입니다. 연두 5% 미만, 노랑 5~10%, 주황 10~15%, 빨강 15% 이상.</p>')
    _sd = mt_sido(m)
    area_link = (f'<p class="tp-small"><a href="mountainarea-{_sd[1]}.html">{_sd[0]} 지역 산 모아 보기</a></p>' if _sd and len(_mg.get(_sd, [])) >= 3 else "")
    import math
    def _ll(o):
        t = next((x for x in o["sections"] if x.get("lat") is not None and x.get("lon") is not None), None)
        return (t["lat"], t["lon"]) if t else None
    me = _ll(m)
    near = []
    if me:
        for o in MOUNTAINS:
            q = _ll(o) if o["id"] != mid else None
            if not q: continue
            dk = math.hypot((q[0] - me[0]) * 111.0, (q[1] - me[1]) * 111.0 * math.cos(math.radians(me[0])))
            if dk <= 40: near.append((dk, o))
        near.sort(key=lambda t: (t[0], t[1]["id"]))
    rel = ""
    if near:
        rel = ('<section class="tp-sec"><h2 class="tp-h2">가까운 다른 산</h2><ul class="cp-list">' +
               "".join(f'<li><a href="mountain-{o["id"]}.html">{esc(mt_title(o))}</a> <span class="tp-small">직선 약 {dk:.0f}km</span></li>' for dk, o in near[:6]) + "</ul></section>")
    _cn = MT_NEAR_COURSES.get(mid, [])
    mt_courses_html = ""
    if _cn:
        mt_courses_html = ('<section class="tp-sec"><h2 class="tp-h2">근처 걷기 코스</h2><p class="tp-p">이 산의 등산로 가까이를 지나는 두루누비 코스입니다. 경로 좌표로 잰 값이라 같은 길이라는 뜻은 아닙니다.</p><ul class="cp-list">' +
                           "".join(f'<li><a href="course-{c["id"]}.html">{esc(c["name"])}</a> <span class="tp-small">{esc(c.get("region") or "")} · {_mt_dist(d_)} 거리</span></li>' for d_, c in sorted(_cn, key=lambda t: t[0])[:6]) + "</ul></section>")
    body = f"""<section class="tp-sec"><p class="tp-p">{esc(lead)}</p>
<table class="cv-table"><tbody>{stat_html}</tbody></table></section>
{mt_prof_html}
{mt_map}
<section class="tp-sec"><h2 class="tp-h2">길의 경사는 이렇게 나뉩니다</h2>{grade_bar(S)}
<p class="tp-small">구간마다 낮은 쪽 끝에서 높은 쪽 끝까지 평균 경사를 잰 뒤, 경사별로 길이를 더했습니다.</p></section>
<section class="tp-sec"><h2 class="tp-h2">가파른 구간 12곳</h2>{table}
<p class="tp-small">구간은 산림청이 나눈 단위이고, 한 구간이 하나의 산행 코스는 아닙니다. 평균 경사는 구간의 낮은 끝과 높은 끝을 이은 값입니다. 고도는 30m 간격의 고도 자료로 읽은 값이라 몇 m에서 십수 m까지 다를 수 있습니다.</p></section>
{mt_courses_html}
<section class="tp-sec" id="trMark" data-href="{slug}" data-name="{esc(mt_title(m))}"><h2 class="tp-h2">내 목록에 담기</h2></section>
{rel}
{area_link}
<p class="tp-src">자료: 산림청 산림공간정보 등산로정보(공공데이터포털, 이용허락범위 제한 없음){(' — <a href="' + esc(m["info"]) + '" rel="noopener" target="_blank">산림청 안내</a>') if m.get("info") else ""}. 고도: {COPDEM} 계산과 표시는 칼랭크가 했고, 현장 상황과 다를 수 있으니 산행 전 안내를 확인해 주세요. <a href="mountains.html">다른 산 보기</a></p>"""
    faq_extra = ([(f"{nm}{josa(nm, '은', '는')} 얼마나 가파른가요?", f"평균 경사 15% 이상인 길이 전체 등산로의 약 {_r15:.0f}%입니다. 구간 평균 기준이라 짧은 급경사는 반영되지 않습니다."),
                  (f"{nm} 등산로는 모두 몇 km인가요?", f"산림청 등산로 구간을 모두 더하면 {tot:.1f}km입니다. 한 번에 걷는 거리가 아니라 산 전체 등산로의 합입니다.")] if _km >= 2 else [])
    faq = faq_extra + [(f"{nm}의 가파른 구간은 어디인가요?", f"산림청 구간 중 평균 경사가 가장 큰 곳은 약 {abs(top[0]['meanGrade']):.0f}%입니다(구간 길이 {top[0]['lenM']}m)."),
           ("고도는 어떻게 구했나요?", "산림청 등산로 선에 약 30m 간격의 지표 고도 자료를 겹쳐 읽었습니다. 나무 높이가 섞일 수 있어 정상부는 조금 높게 나올 수 있습니다.")]
    desc = (f'{mt_title(m)} 등산로 {len(S)}개 구간, 합계 {tot:.1f}km. 구간별 경사와 가파른 곳, 고도를 산림청 자료로 정리했습니다.')
    return slug, page(slug, f"{mt_title(m)} 등산로 경사와 가파른 구간", desc, f"{mt_title(m)} 등산로",
                      f"구간 {len(S)}개 · {tot:.1f}km · 최고 약 {hi:.0f}m", body, ["calrank-local.js", "trail-mark.js", "route-map.js"], faq, crumb=("산", "mountains.html"),
                      place={"type": "Mountain", "name": nm, "lat": S[0].get("lat"), "lon": S[0].get("lon"), "ele": off if off else hi,
                             "region": (m.get("region") or "").split()[0] if m.get("region") else ""},
                      modified=MT_FETCHED or None)


MOUNTAIN_PAGES = [mountain_page(m) for m in MOUNTAINS]


# ── 시도별 산 모음 ─────────────────────────────────────────────────────────
def mt_group_page(short, slug, ms):
    ms = sorted(ms, key=lambda m: -mt_stats(m)[2])
    tot = sum(mt_stats(m)[0] for m in ms)
    def li(m):
        tt, steep, hi, lo = mt_stats(m)
        return f'<li><a href="mountain-{m["id"]}.html">{esc(mt_title(m))}</a> · 구간 {len(m["sections"])}개 · {tt:.1f}km · 최고 약 {hi:.0f}m</li>'
    body = f"""<section class="tp-sec"><p class="tp-p">{short} 지역에서 산림청 등산로 자료로 정리한 산은 {len(ms)}곳입니다. 등산로 구간을 모두 합치면 {tot:.0f}km이고, 구간 최고 고도가 가장 높은 산은 {esc(ms[0]["name"])}(약 {mt_stats(ms[0])[2]:.0f}m)입니다.</p>
<p class="tp-small">위치를 확인할 수 있는 산만 실었습니다. 같은 이름의 산이 다른 지역에도 있을 수 있습니다.</p></section>
<section class="tp-sec"><h2 class="tp-h2">구간 최고 고도가 높은 순</h2><ul class="cp-list">{"".join(li(m) for m in ms)}</ul></section>
<p class="tp-src">자료: 산림청 산림공간정보 등산로정보(공공데이터포털). 고도: {COPDEM} <a href="mountains.html">전체 산 보기</a></p>"""
    faq = [(f"{short} 지역에서 가장 높은 산은 어디인가요?", f"칼랭크에 실린 {short} 지역 산 중에서는 {ms[0]['name']}이(가) 구간 최고 고도 약 {mt_stats(ms[0])[2]:.0f}m로 가장 높습니다.")]
    return f"mountainarea-{slug}.html", page(f"mountainarea-{slug}.html", f"{short} 산 등산로 모음 — 경사와 가파른 구간",
        f"{short} 지역 산 {len(ms)}곳의 등산로 구간 길이, 경사, 구간 최고 고도를 산림청 산림공간정보 등산로 자료와 코페르니쿠스 DEM으로 정리했습니다.", f"{short} 지역 산 등산로", f"{len(ms)}개 산 · 구간 합계 {tot:.0f}km",
        body, [], faq, crumb=("산", "mountains.html"))


MT_GROUP_PAGES = [mt_group_page(k[0], k[1], v) for k, v in sorted(_mg.items(), key=lambda kv: kv[0][1]) if len(v) >= 3]
MT_GROUP_LINKS = [(f"mountainarea-{k[1]}.html", k[0], len(v)) for k, v in sorted(_mg.items(), key=lambda kv: kv[0][1]) if len(v) >= 3]


def mountains_hub():
    CHO = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
    def cho(s):
        c = s[:1]
        if "가" <= c <= "힣":
            i = (ord(c) - 0xAC00) // 588
            return {"ㄲ": "ㄱ", "ㄸ": "ㄷ", "ㅃ": "ㅂ", "ㅆ": "ㅅ", "ㅉ": "ㅈ"}.get(CHO[i], CHO[i])
        return "기타"
    by = {}
    for m in sorted(MOUNTAINS, key=lambda m: m["name"]):
        by.setdefault(cho(m["name"]), []).append(m)
    def li(m):
        tot, steep, hi, lo = mt_stats(m)
        return f'<li><a href="mountain-{m["id"]}.html">{esc(mt_title(m))}</a> · 구간 {len(m["sections"])}개 · {tot:.1f}km · 최고 약 {hi:.0f}m</li>'
    secs = "".join(f'<section class="tp-sec"><h2 class="tp-h2">{k} ({len(v)})</h2><ul class="cp-list">{"".join(li(m) for m in v)}</ul></section>' for k, v in by.items())
    tall = "".join(li(m) for m in sorted(MOUNTAINS, key=lambda m: -mt_stats(m)[2])[:12])
    body = f"""<section class="tp-sec"><p class="tp-p">산림청이 공개한 등산로 자료에 고도를 겹쳐, 산마다 길이와 경사, 가파른 구간을 정리했습니다. 지금 {len(MOUNTAINS)}개 산이 있습니다.</p></section>
<section class="tp-sec mn" id="trMine" hidden><h2 class="tp-h2">내 목록</h2></section>
<div class="mn-import"><span class="mn-import-t">다른 기기에서 저장한 백업이 있으면 불러올 수 있습니다.</span><label class="tp-btn ghost mn-file">백업 불러오기<input type="file" id="trImport" accept="application/json,.json"></label><span id="trImportMsg" class="tp-small" role="status"></span></div>
<section class="tp-sec"><label class="tp-field">이름·지역으로 찾기<input id="listQ" type="search" placeholder="예: 마이산, 계방산, 진안" autocomplete="off"></label><p id="listMsg" class="tp-small" role="status" aria-live="polite"></p><ul id="listMore" class="cp-list" data-other="trailroot.html"></ul></section>
<section class="tp-sec"><h2 class="tp-h2">지역으로 보기</h2><ul class="cp-list">{"".join(f'<li><a href="{sl}">{esc(nm_)}</a> · {n_}개 산</li>' for sl, nm_, n_ in MT_GROUP_LINKS)}</ul></section>
<section class="tp-sec"><h2 class="tp-h2">구간 최고 고도가 높은 산</h2><ul class="cp-list">{tall}</ul></section>
{secs}
<p class="tp-src">자료: 산림청 산림공간정보 등산로정보(공공데이터포털). 고도: {COPDEM}</p>"""
    faq = [("같은 이름의 산이 여러 곳인가요?", "이름이 같은 산이 전국에 여럿 있어서, 위치를 알 수 있는 산은 이름 옆에 지역을 적었습니다."),
           ("등산로 길이는 어디까지 포함하나요?", "산림청 등산로 구간을 모두 더한 값이라, 한 번의 산행 거리와는 다릅니다.")]
    return "mountains.html", page("mountains.html", "산별 등산로 경사와 가파른 구간 모음",
        f"산림청 등산로 자료로 {len(MOUNTAINS)}개 산의 구간 길이, 경사, 가파른 곳을 정리했습니다. 산 이름이나 지역으로 찾고, 오르막이 가파른 구간을 미리 확인하세요.",
        "산별 등산로", f"{len(MOUNTAINS)}개 산 · 구간별 경사", body, ["calrank-local.js", "trail-mark.js", "list-filter.js"], faq, crumb=("산", "mountains.html"))


STANDARDS = [standards_page(s) for s in SPORT_META]


def changes_page():
    rows = "".join(
        f'<div class="dq-card"><div class="dq-top"><h3 class="dq-title">{esc(c["title"])}</h3><span class="dq-clause">{esc(c["date"])}</span></div>'
        f'<p class="dq-text">{esc(c["text"])}</p></div>' for c in sorted(DQ["changelog"], key=lambda c: c["date"], reverse=True))
    body = f"""<section class="tp-sec"><p class="tp-p">기어 판정 페이지에는 날짜가 두 가지 나옵니다.
<b>원문 마지막 확인</b>은 연맹 문서가 지난번과 같은지 자동으로 살펴본 날이고, <b>내용 수정</b>은 칼랭크가 판정 내용을 실제로 고친 날입니다. 확인만 하고 고친 것이 없으면 수정일은 바뀌지 않습니다.</p>
<p class="tp-p">고친 내용과 이유는 여기에 남깁니다. 잘못된 곳을 발견하셨다면 <a href="contact.html">문의 페이지</a>로 알려 주세요.</p></section>
<section class="tp-sec"><h2 class="tp-h2">변경 기록</h2>{rows}</section>"""
    faq = [("'원문 마지막 확인'과 '내용 수정'은 무엇이 다른가요?", "확인은 연맹 원문이 지난번과 같은지 본 날이고, 수정은 칼랭크 페이지의 내용을 고친 날입니다. 원문이 그대로면 확인일만 바뀝니다."),
           ("원문이 바뀌면 어떻게 알 수 있나요?", "매주 자동으로 원문을 받아 지난번과 내용이 달랐는지 비교합니다. 달랐다는 것만 알 수 있어서, 페이지에 '원문이 바뀌었을 수 있으니 다시 확인해 주세요'라고 표시합니다.")]
    return "gear-changes.html", page("gear-changes.html", "기어 판정 변경 기록 — 무엇을 언제 고쳤는지",
        "칼랭크 기어 판정 페이지에서 고친 내용과 날짜를 남깁니다. 원문 확인일과 내용 수정일이 어떻게 다른지도 설명합니다.",
        "기어 판정 변경 기록", "규정 원문을 언제 확인했고, 칼랭크가 내용을 언제 고쳤는지 기록합니다.", body, [], faq)


STANDARDS.append(changes_page())
STANDARDS += COURSE_PAGES
STANDARDS += GROUP_PAGES
STANDARDS += MT_GROUP_PAGES
if COURSES:
    STANDARDS.append(hub_page())
STANDARDS += MOUNTAIN_PAGES
if MOUNTAINS:
    STANDARDS.append(mountains_hub())

# ---- 이모지 붙이기: 제목 옆에 하나씩, 같은 자리·같은 크기로 (크기는 style.css 의 .emo) ----
from site_emoji import emo as _emo  # noqa: E402

_H1_EMO = [("course", "hiking-boot"), ("trail", "hiking-boot"), ("mountain", "mountain"),
           ("kit", "backpack"), ("age-curve", "chart-increasing"), ("ledger", "memo"),
           ("gear-changes", "memo"), ("standards-triathlon", "person-swimming"),
           ("standards-trail", "mountain"), ("standards-running", "running-shoe"),
           ("standards-cycling", "bicycle")]
# 소제목 글자에 이 말이 들어 있으면 이 이모지. 위에서부터 먼저 맞는 것을 쓴다.
_H2_EMO = [("지도", "world-map"), ("시간", "stopwatch"), ("처음이라면", "seedling"),
           ("눈여겨", "mountain"), ("가파른", "mountain"), ("체력이", "mountain"), ("오르막", "mountain"),
           ("고도", "mountain"), ("경사", "mountain"), ("근처", "round-pushpin"), ("가까운", "round-pushpin"),
           ("같은 지역", "round-pushpin"), ("지역으로", "round-pushpin"), ("시설", "round-pushpin"),
           ("이름이 있는 지점", "round-pushpin"), ("같은 길", "footprints"), ("길과 지역", "footprints"),
           ("전체 코스", "footprints"), ("내 목록", "star"), ("내 노트", "memo"), ("내 신발", "running-shoe"),
           ("내 장비", "backpack"), ("자주 묻는", "light-bulb"), ("어떻게 계산", "balance-scale"),
           ("변경 기록", "memo"), ("기술 난이도", "warning"), ("현장 확인", "memo")]


_UL_RE = re.compile(r'<ul class="cp-list">(.*?)</ul>', re.S)
_LI_RE = re.compile(r'<li><a href="([^"]+)">([^<]+)</a>(.*?)</li>', re.S)


def _cards(html):
    """누르는 목록을 카드 한 줄로 바꾼다.
    이름(굵게) → 수치(항목 단위로만 줄이 바뀜) → 근처 산(따로 한 줄), 오른쪽 끝에 화살표.
    밑줄 링크를 쭉 이어 쓰면 눌러야 하는 곳인지 모르고, 줄도 항목 한가운데서 끊긴다."""
    def one(m):
        href, name, rest = m.group(1), m.group(2).strip(), m.group(3)
        if "<a " in rest:
            return m.group(0)
        parts = [x.strip() for x in re.sub(r"<[^>]+>", "", rest).split(" · ") if x.strip()]
        addr = re.match(r"^(.+?)\((.+)\)$", name)
        place = ""
        if addr:
            name, place = addr.group(1).strip(), re.sub(r"\s+", " ", addr.group(2)).strip()
        near = [x for x in parts if x.startswith(("근처 산", "인근 산"))]
        meta = [x for x in parts if not x.startswith(("근처 산", "인근 산"))]
        inner = '<span class="cp-name">' + name + "</span>"
        if place:
            inner += '<span class="cp-near">' + place + "</span>"
        if meta:
            inner += '<span class="cp-meta">' + "".join(f"<span>{x}</span>" for x in meta) + "</span>"
        for x in near:
            inner += '<span class="cp-near">' + x + "</span>"
        return f'<li class="cp-card"><a class="cp-row" href="{href}">{inner}</a></li>'
    return _UL_RE.sub(lambda u: '<ul class="cp-list">' + _LI_RE.sub(one, u.group(1)) + "</ul>", html)


def _decorate(name, html):
    if "tp-title" not in html:
        return html
    for key, em in _H1_EMO:
        if name.startswith(key):
            html = html.replace('<h1 class="tp-title">', '<h1 class="tp-title">' + _emo(em), 1)
            break

    def _h2(m):
        txt = m.group(1)
        for key, em in _H2_EMO:
            if key in txt:
                return '<h2 class="tp-h2">' + _emo(em) + txt + "</h2>"
        return m.group(0)
    # 소제목(h2)에는 이모지를 붙이지 않는다. 섹션마다 다른 그림이 붙으면 어수선해진다. 이모지는 페이지 제목에만 둔다.
    return _cards(html)


YARD = page(
    "yardage.html", "대회 코스 야디지북 — 공식 GPX로 구간별 오르막과 페이스 계획",
    "마라톤 대회 코스의 공식 GPX를 올리면 구간(km)마다 오르막·내리막·경사와, 목표 기록에 맞춘 구간별 보정 페이스를 표로 보여 줍니다. 파일은 내 기기 안에서만 읽습니다.",
    "대회 코스 야디지북",
    "주최측이 공개한 코스 GPX를 올리고 목표 기록을 적으면, 구간마다 오르막과 내리막, 평균 경사, 같은 노력으로 달릴 때의 페이스를 계산합니다. 파일은 서버로 보내지 않고 이 브라우저 안에서만 읽습니다.",
    '''<section class="tp-card"><div class="tp-grid">
<label class="tp-field">대회 코스 GPX 파일<input id="ydFile" type="file" accept=".gpx,application/gpx+xml,text/xml"></label>
<label class="tp-field">목표 기록 (시:분:초)<input id="ydTime" type="text" inputmode="numeric" value="3:30:00" autocomplete="off"></label>
<label class="tp-field">공식 거리<select id="ydDist"><option value="42.195" selected>풀 42.195km</option><option value="21.0975">하프 21.0975km</option><option value="10">10km</option><option value="5">5km</option><option value="0">파일 그대로</option></select></label>
<label class="tp-field">구간 단위<select id="ydUnit"><option value="1">1km</option><option value="5" selected>5km</option></select></label>
</div>
<p class="tp-small">대회 홈페이지가 코스 GPX를 공개한 경우에만 쓸 수 있습니다. 칼랭크는 대회 코스 파일을 보관하거나 나눠 주지 않습니다.</p>
<p id="ydMsg" class="tp-small" role="status" aria-live="polite"></p></section>
<div id="ydOut" hidden>
<section class="tp-card"><p class="tp-small" id="ydSum"></p><p class="tp-small" id="ydNote"></p>
<div class="mt-wrap"><table class="mt-table yd-table"><thead><tr><th>구간 km</th><th>오르/내리 m</th><th>경사</th><th>페이스 /km</th><th>누적</th></tr></thead><tbody id="ydBody"></tbody></table></div><p class="tp-small">오르/내리는 구간의 누적 오르막과 내리막(m), 페이스는 보정 페이스입니다.</p></section>
<section class="tp-card"><h2 class="tp-h2">큰 오르막</h2><ul class="cp-list" id="ydClimbs"></ul></section>
</div>
<section class="tp-sec"><h2 class="tp-h2">산출 방법</h2>
<p class="tp-p">경사에 따라 달릴 때 드는 에너지가 달라진다는 실험 결과(Minetti 외, 2002)를 구간마다 적용해, 같은 노력으로 달릴 때 구간별 속도가 얼마나 달라지는지 계산합니다. 목표 기록을 코스 전체에 이 비율대로 나누기 때문에, 오르막 구간의 페이스는 느려지고 평지 구간은 그보다 빨라집니다. 내리막은 평지와 같다고 봅니다. 평지 대회에서 두 효과는 대체로 상쇄되고, 코스 시간을 이런 에너지 모델로 어림하면 대체로 10~20% 안에서 맞았다는 보고가 있습니다(Crowell, bioRxiv 프리프린트, 동료 심사 전).</p>
<p class="tp-p"><b>이 계산이 모르는 것</b>: 바람, 기온, 노면, 급수대 혼잡, 곡선 구간, 피로는 들어 있지 않습니다. GPS 고도는 흔들려서 파일에 따라 오르막 값이 달라질 수 있어 고도를 다듬어 계산합니다. 보정 페이스는 계획을 세울 때의 참고이고, 공식 코스도와 거리 표지판이 우선입니다.</p>
<p class="tp-src">근거: Minetti AE 외, J Appl Physiol 93:1039–1046, 2002. Crowell B, From treadmill to trails: predicting performance of runners (bioRxiv 2021, 프리프린트).</p></section>''',
    ["course.js", "yardage.js"],
    [("대회 코스 GPX는 어디서 받나요?", "대회 홈페이지가 공개한 경우에만 받을 수 있습니다. 공개하지 않는 대회도 많고, 칼랭크는 대회 코스 파일을 보관하거나 나눠 주지 않습니다."),
     ("파일이 서버에 저장되나요?", "아닙니다. 파일은 이 브라우저 안에서만 읽고 서버로 보내지 않습니다."),
     ("보정 페이스는 어떻게 나오나요?", "경사별 에너지 비용 식으로 구간마다 같은 노력의 속도를 계산한 뒤, 목표 기록에 맞게 전체를 맞춥니다. 오르막은 느려지고 평지는 상대적으로 빨라집니다.")],
    crumb=("코스 판정", "course.html"))

KIT, COURSE, AGE, LEDGER = (_decorate(n, h) for n, h in [("kit.html", KIT), ("course.html", COURSE), ("age-curve.html", AGE), ("ledger.html", LEDGER)])
STANDARDS = [(n, _decorate(n, h)) for n, h in STANDARDS]

for name, html in [("yardage.html", YARD), ("kit.html", KIT), ("course.html", COURSE), ("age-curve.html", AGE), ("ledger.html", LEDGER)] + STANDARDS + ([("dg-method.html", DGM)] if DGM else []):
    p = ROOT / name
    if not p.exists() or p.read_text(encoding="utf-8") != html:
        p.write_text(html, encoding="utf-8")
        print("wrote", name)

# 임베드 위젯: 코스 한 곳의 칼랭크 난이도 카드. 값은 같은 식으로 계산해 json 한 파일에 둔다.
if COURSES:
    import json as _json
    _cd = {}
    for _c in COURSES:
        _k, _g, _l, _s = course_stats(_c)
        _sc, _i, _nm = diff_grade(_k, _g)
        _ke, _kp = km_effort(_k, _g)
        _cd[f"course-{_c['id']}"] = [_c["name"], round(_k, 1), round(_g), round(_sc), _i, _nm, round(_ke), _kp]
    _txt = _json.dumps(_cd, ensure_ascii=False, separators=(",", ":"))
    _jp = ROOT / "course-diff.json"
    if not _jp.exists() or _jp.read_text(encoding="utf-8") != _txt:
        _jp.write_text(_txt, encoding="utf-8"); print("wrote course-diff.json")

# 자료에서 빠진 코스·산의 페이지는 지운다(고도 고정 코스 제외, 산 이름 정리 등으로 사라진 것)
_live = {s for s, _ in COURSE_PAGES} | {s for s, _ in MOUNTAIN_PAGES} | {s for s, _ in GROUP_PAGES} | {s for s, _ in MT_GROUP_PAGES}
_stale = [f.name for pat in ("course-dr-*.html", "course-ft-*.html", "mountain-*.html", "trailroute-*.html", "trailarea-*.html", "mountainarea-*.html") for f in ROOT.glob(pat) if f.name not in _live]
for _n in _stale:
    (ROOT / _n).unlink()
    print("지움", _n)
if _stale:
    _t = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    for _n in _stale:
        _t = __import__("re").sub(r"\s*<url>\s*<loc>[^<]*/" + __import__("re").escape(_n) + r"</loc>.*?</url>", "", _t, flags=__import__("re").S)
    (ROOT / "sitemap.xml").write_text(_t, encoding="utf-8")

# sitemap
sm = ROOT / "sitemap.xml"
t = sm.read_text(encoding="utf-8")
add = ""
for n in ("kit.html", "course.html", "yardage.html", "age-curve.html", "ledger.html", "standards-triathlon.html", "standards-cycling.html", "standards-running.html", "standards-trail.html", "gear-changes.html", *(["trailroot.html", "dg-method.html"] if COURSES else []), *(["mountains.html"] if MOUNTAINS else []), *[s for s, _ in MOUNTAIN_PAGES], *[s for s, _ in GROUP_PAGES], *[s for s, _ in MT_GROUP_PAGES], *[s for s, _ in COURSE_PAGES]):
    if f"/{n}</loc>" not in t:
        add += f"  <url>\n    <loc>{BASE}{n}</loc>\n    <changefreq>monthly</changefreq>\n    <priority>0.6</priority>\n  </url>\n"
if add:
    t = t.replace("</urlset>", add + "</urlset>")
    sm.write_text(t, encoding="utf-8")
    print("sitemap 추가")
# 코스·산 페이지에 lastmod (자료를 받은 날)
import re as _re
_dc = (COURSES[0].get("source", {}).get("fetched") if COURSES else "") or ""
_dm = MT_FETCHED
t = sm.read_text(encoding="utf-8")
def _lm(m_):
    loc = m_.group(1)
    day = _dc if ("/course-dr-" in loc or "/course-ft-" in loc or loc.endswith("/trailroot.html")) else (_dm if ("/mountain-" in loc or loc.endswith("/mountains.html")) else "")
    return m_.group(0) if not day else f"<loc>{loc}</loc>\n    <lastmod>{day}</lastmod>"
t2 = _re.sub(r"<loc>([^<]+)</loc>(?!\s*<lastmod>)", _lm, t)
if t2 != t:
    sm.write_text(t2, encoding="utf-8")
    print("sitemap lastmod")

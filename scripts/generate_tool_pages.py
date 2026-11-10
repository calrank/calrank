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


def page(slug, title, desc, h1, sub, body, scripts, faq):
    app_name = h1
    url = BASE + slug
    crumbs = ld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "calrank", "item": BASE + "index.html"},
        {"@type": "ListItem", "position": 2, "name": "기어", "item": BASE + "gear.html"},
        {"@type": "ListItem", "position": 3, "name": app_name}]})
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
<link rel="canonical" href="{url}">
<meta property="og:title" content="{title} | 칼랭크 CALRANK">
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
    "course.html", "코스 판정 — 이 코스는 평지 몇 km에 해당할까",
    "코스의 거리와 오르내림(또는 GPX 파일)으로 평지 몇 km에 해당하는지 환산하고, 내 평지 페이스로 걸리는 시간을 계산합니다. 산악 러너 실험(Minetti 2002)의 에너지 비용 식을 씁니다.",
    "코스 판정",
    "거리와 누적 상승·하강, 또는 GPX 파일을 넣으면 코스를 평지 거리로 환산하고 내 평지 페이스로 걸리는 시간을 계산합니다. GPX 파일은 서버로 보내지 않고 이 브라우저 안에서만 읽습니다.",
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
<table class="cv-table"><tbody id="cvTable"></tbody></table></section>
<section class="tp-card" id="cvChartWrap" hidden><div id="cvChart"></div></section>
</div>
<section class="tp-sec"><h2 class="tp-h2">어떻게 계산하나요</h2>
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

for name, html in [("kit.html", KIT), ("course.html", COURSE), ("age-curve.html", AGE), ("ledger.html", LEDGER)] + STANDARDS:
    p = ROOT / name
    if not p.exists() or p.read_text(encoding="utf-8") != html:
        p.write_text(html, encoding="utf-8")
        print("wrote", name)

# sitemap
sm = ROOT / "sitemap.xml"
t = sm.read_text(encoding="utf-8")
add = ""
for n in ("kit.html", "course.html", "age-curve.html", "ledger.html", "standards-triathlon.html", "standards-cycling.html", "standards-running.html", "standards-trail.html", "gear-changes.html"):
    if f"/{n}</loc>" not in t:
        add += f"  <url>\n    <loc>{BASE}{n}</loc>\n    <changefreq>monthly</changefreq>\n    <priority>0.6</priority>\n  </url>\n"
if add:
    sm.write_text(t.replace("</urlset>", add + "</urlset>"), encoding="utf-8")
    print("sitemap 추가")

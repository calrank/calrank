#!/usr/bin/env python3
"""기어 판정을 규정·주장마다 한 장씩 정적 페이지로 찍는다.

왜 필요한가
-----------
gear.html 하나에 규정 12건과 주장 5건이 전부 들어 있는데, 각각은
`gear.html?r=wa-stack-height` 처럼 쿼리 뒤에 숨어 있고 내용은 JS 가
가져온 뒤에야 그려진다. 사람에게는 잘 보이지만 검색엔진에는 거의
안 보인다. 주소가 하나로 뭉쳐 있어 제목·설명도 하나뿐이고, 사이트맵에
올릴 수도 없고, 가리키는 링크도 없다.

그런데 이 17건은 하나하나가 그대로 검색어다 — "카본화 밑창 두께",
"자전거 최소 중량", "웻슈트 수온 기준", "인라인 바퀴 110mm". 전부
지갑을 열기 직전에 치는 말이다. 묻어 두기엔 아깝다.

그래서 이 사이트가 대회 페이지 1093장을 찍는 방식 그대로, 판정도
한 건당 한 장으로 찍는다. 내용은 서버에서 다 그려 두고(크롤러가
읽는 건 이쪽이다), 그 위에 판정 도구를 얹는다(사람이 쓰는 건 이쪽이다).

숫자를 지어내지 않는다. 원자료에 없는 것은 페이지에도 없다.

쓰임:
  python3 scripts/generate_gear_pages.py
  python3 scripts/generate_gear_pages.py --check
"""
import argparse
import html
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from site_nav import nav_html, active_for  # noqa: E402
import wma_standards as wma  # noqa: E402
from gear_table_data import (  # noqa: E402
    RUN_DISTS, RUN_GOALS, BIKE_SPEEDS, BIKE_DISTS, RUN_TABLES, BIKE_TABLES,
    REF_AGE, REF_GENDER, tier_bounds, tier_of, run_model,
    WETSUIT_TEMPS, POLE_GRADIENTS)

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://calrank.vercel.app"
KST = timezone(timedelta(hours=9))
TODAY = datetime.now(KST).strftime("%Y-%m-%d")

GRADE_TEXT = {
    "A": "메타분석 또는 복수의 무작위 대조 연구",
    "B": "동료심사를 거친 단일 연구",
    "C": "소규모 연구·학회 초록·관찰 연구",
    "D": "제조사 자료 또는 검증되지 않은 주장",
}

# 종목마다 이미 있는 글. 새 페이지에서 이쪽으로 보내고, 이쪽에서도
# 판정으로 돌아오게 하면 둘 다 산다.
RELATED = {
    "running": [("gear-prices.html", "러닝화, 어디서 사나"),
                ("column-howto-marathon-shoe-selection.html", "마라톤 신발 고르기")],
    "trail": [("guide-trail-gear.html", "트레일러닝 장비 안내"),
              ("column-howto-trail-beginner-gear.html", "트레일 입문 장비"),
              ("column-howto-trail-poles-technique.html", "트레일 폴 쓰는 법")],
    "cycling": [("guide-cycling-gear.html", "자전거 장비 안내")],
    "triathlon": [("guide-triathlon-gear.html", "철인3종 장비 안내")],
    "inline": [],
}

SPORT_LABEL = {"running": "러닝", "trail": "트레일러닝", "cycling": "사이클링",
               "triathlon": "철인3종", "inline": "인라인"}


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def num(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return f"{v:,}"


def slug_for(kind, item_id):
    return f"gear-{item_id}.html"


# ── 본문 조각 ────────────────────────────────────────────────────
def rule_body(rule, bodies):
    out = []
    if rule.get("headline"):
        out.append(f'<p class="gi-headline">{esc(rule["headline"])}</p>')
    if rule.get("surprise"):
        out.append(f'<p class="gm-surprise">{esc(rule["surprise"])}</p>')

    limits = rule.get("limits") or []
    if limits:
        unit = (rule.get("check") or {}).get("unit", "")
        rows = []
        for l in limits:
            if "max" in l and l["max"] is None:
                val = "제한 없음"
            elif isinstance(l.get("max"), (int, float)):
                val = f"최대 {num(l['max'])}{unit}"
            elif isinstance(l.get("min"), (int, float)):
                val = f"최소 {num(l['min'])}{unit}"
            else:
                val = l.get("min_text", "")
            note = f'<span class="gm-note">{esc(l["note"])}</span>' if l.get("note") else ""
            rows.append(f"<tr><th>{esc(l['scope'])}</th><td>{esc(val)}{note}</td></tr>")
        out.append("<h2>규정 전문의 숫자</h2>"
                   f'<table class="gm-table"><tbody>{"".join(rows)}</tbody></table>')

    if rule.get("measure_note"):
        out.append("<h2>재는 방법과 덧붙는 조건</h2>"
                   f'<p class="gm-measure">{esc(rule["measure_note"])}</p>')

    b = bodies.get(rule.get("body"))
    if b:
        note = f'<span class="gm-note">{esc(b["note"])}</span>' if b.get("note") else ""
        out.append("<h2>이 규정을 쓰는 곳</h2>"
                   f'<p class="gm-body"><b>{esc(b["label"])}</b> ({esc(b["label_ko"])})<br>'
                   f'{esc(b["governs"])}{note}</p>')

    link = (f' <a href="{esc(rule["url"])}" target="_blank" rel="noopener">규정 원문 →</a>'
            if rule.get("url") else "")
    out.append(f'<p class="gm-src">출처 · {esc(rule["source"])}{link}'
               '<span class="gm-note">장비 규정은 거의 매년 바뀝니다. '
               '중요한 결정 전에는 원문을 한 번 더 확인해 주세요.</span></p>')
    return "\n".join(out)


def claim_body(claim):
    out = []
    if claim.get("headline"):
        out.append(f'<p class="gi-headline">{esc(claim["headline"])}</p>')
    if claim.get("surprise"):
        out.append(f'<p class="gm-surprise">{esc(claim["surprise"])}</p>')

    for eff in claim.get("effects", []):
        rows = []
        for ev in eff.get("evidence", []):
            applies = (ev.get("applies") or {}).get(claim.get("condition")) or [None, None]
            lo, hi = applies[0], applies[1]
            if lo is None and hi is None:
                scope = "모든 조건"
            elif lo is None:
                scope = f"{num(hi)} 미만"
            elif hi is None:
                scope = f"{num(lo)} 이상"
            else:
                scope = f"{num(lo)} ~ {num(hi)}"

            if ev.get("caveat") or eff.get("kind") == "caveat":
                val = "효과 수치가 아니라 주의사항입니다"
            elif ev.get("no_data"):
                val = "연구 없음"
            elif ev.get("model"):
                val = "검증된 모델로 계산"
            else:
                ci = ev.get("ci") or [ev.get("effect_pct"), ev.get("effect_pct")]
                lo2 = 0.0 if ev.get("significant") is False else ci[0]
                val = f"{lo2:.1f} ~ {ci[1]:.1f}%"
                if ev.get("significant") is False:
                    val += " <em>유의하지 않음</em>"
            meta = []
            if ev.get("studies"):
                meta.append(f"연구 {ev['studies']}편")
            if ev.get("n"):
                meta.append(f"참가자 {ev['n']}명")
            metatxt = (" · " + " · ".join(meta)) if meta else ""
            note = f'<span class="gm-note">{esc(ev["note"])}</span>' if ev.get("note") else ""
            rows.append(
                f"<tr><th>{esc(scope)}</th><td>"
                f'<span class="ge-grade ge-{esc(ev["grade"])}">근거 {esc(ev["grade"])}</span> '
                f"{val}<span class=\"gm-note\">{esc(GRADE_TEXT.get(ev['grade'], ''))}"
                f"{esc(metatxt)}</span>{note}"
                f'<span class="gm-note">{esc(ev["source"])}'
                + (f' <a href="{esc(ev["url"])}" target="_blank" rel="noopener">원문 →</a>'
                   if ev.get("url") else "")
                + "</span></td></tr>")
        detail = f' <span class="ge-detail">{esc(eff["detail"])}</span>' if eff.get("detail") else ""
        out.append(f"<h2>{esc(eff['label'])}{detail}</h2>"
                   f'<table class="gm-table"><tbody>{"".join(rows)}</tbody></table>')

    if claim.get("model_note"):
        out.append("<h2>이 숫자를 어떻게 냈나</h2>"
                   f'<p class="gm-measure">{esc(claim["model_note"])}</p>')
    if claim.get("transfer_note"):
        out.append("<h2>기록으로 바꿀 때의 가정</h2>"
                   f'<p class="gm-measure">{esc(claim["transfer_note"])}</p>')
    out.append('<p class="gm-src">연구에서 보고된 값이며, 개인의 결과를 보장하지 않습니다.'
               '<span class="gm-note">새 연구가 나오면 이 판정도 함께 갱신합니다.</span></p>')
    return "\n".join(out)


def related_block(sport, siblings, self_slug):
    bits = []
    sib = [(slug_for(k, i), lab) for (k, i, lab) in siblings if slug_for(k, i) != self_slug]
    for href, label in sib + RELATED.get(sport, []):
        bits.append(f'<a href="{esc(href)}">{esc(label)}</a>')
    if not bits:
        return ""
    return ('<p class="gi-links">같은 종목에서 더 보기 · '
            + " · ".join(bits) + "</p>")


PAGE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta property="og:type" content="article">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{base}/{slug}">
<meta property="og:locale" content="ko_KR">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Noto+Sans+KR:wght@400;700;900&display=swap" rel="stylesheet">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="icon" type="image/png" sizes="96x96" href="/favicon-96.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#F5F2EF" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0B0B0B" media="(prefers-color-scheme: dark)">
<link rel="canonical" href="{base}/{slug}">
<link rel="stylesheet" href="style.css">
<link rel="stylesheet" href="myrank.css">
<link rel="stylesheet" href="gear.css">
{jsonld}
</head>
<body{bodyattr}>

<header class="site-header">
<div class="wrap header-inner">
<a href="index.html" class="wordmark" aria-label="CALRANK">C<svg class="wm-a" viewBox="0 0 34 30" aria-hidden="true" focusable="false"><path fill-rule="evenodd" d="M0,30 L0,21 L6,21 L6,11 L11.5,11 L11.5,0 L22.5,0 L22.5,11 L28,11 L28,21 L34,21 L34,30 Z M12.4,22.6 L21.6,22.6 L19.4,11.4 L14.6,11.4 Z"/><rect class="wm-top" x="11.5" y="0" width="11" height="4.4"/></svg>LRANK</a>
{nav}
</div>
</header>

<main class="wrap myrank-wrap">

<nav class="gi-crumb"><a href="index.html">칼랭크</a> · <a href="gear.html">기어 판정</a> · {sport}</nav>

<section class="hero">
<h1 id="gearTitle">{h1}</h1>
<p class="hero-sub" id="gearQuestion">{question}</p>
</section>

<div class="gi-form-wrap" id="gearFormWrap">
<div class="gi-form" id="gearForm"></div>
</div>

<div id="gearResult" class="gi-result"></div>

<article class="gi-meta" id="gearMeta">
{body}
</article>

{related}

<nav class="gi-back"><a href="gear.html">← 기어 판정 전체 보기</a></nav>

</main>

<footer class="site-footer">
<div class="wrap">
<p>장비 규정은 각 연맹이 수시로 개정합니다. 칼랭크의 판정은 참고용이며, 대회 출전 전에는 반드시 해당 대회 요강과 연맹 규정 원문을 확인하세요. 효과 수치는 연구에서 보고된 값으로, 개인의 결과를 보장하지 않습니다.</p>
<p class="footer-links"><a href="about.html">소개</a> · <a href="terms.html">이용약관</a> · <a href="privacy.html">개인정보처리방침</a> · <a href="contact.html">제휴·광고 문의</a></p>
</div>
</footer>

<script src="wma-standards.js"></script>
<script src="grade-model.js"></script>
<script src="gear-model.js"></script>
<script src="gear-rules.js"></script>
<script src="gear.js"></script>
<script defer src="/_vercel/insights/script.js"></script>
</body>
</html>
"""


def jsonld_for(item, slug, title, desc, sport):
    qa = [(item.get("question") or title, item.get("headline") or desc)]
    # 화면에도 그대로 보이는 문항만 넣는다. 보이지 않는 질문을 마크업에만
    # 넣으면 검색엔진이 규정 위반으로 본다.
    qa += [(f["q"], f["a"]) for f in item.get("faq", [])]
    faq = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{
            "@type": "Question", "name": q,
            "acceptedAnswer": {"@type": "Answer", "text": a},
        } for q, a in qa],
    }
    from gear_images import image_url
    img = image_url(slug)
    article = {
        "@context": "https://schema.org", "@type": "Article",
        "headline": title, "description": desc,
        "mainEntityOfPage": f"{BASE}/{slug}",
        "inLanguage": "ko",
        "author": {"@type": "Organization", "name": "칼랭크", "url": f"{BASE}/about.html"},
        "publisher": {"@type": "Organization", "name": "칼랭크", "url": f"{BASE}/"},
    }
    if img:
        article["image"] = [img]
    crumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "calrank",
             "item": f"{BASE}/index.html"},
            {"@type": "ListItem", "position": 2, "name": "기어 판정",
             "item": f"{BASE}/gear.html"},
            {"@type": "ListItem", "position": 3, "name": title},
        ],
    }
    def dump(o):
        return ('<script type="application/ld+json">'
                + json.dumps(o, ensure_ascii=False, separators=(",", ":"))
                + "</script>")
    return dump(article) + "\n" + dump(faq) + "\n" + dump(crumb)


# 규정(허용되나)과 효과(얼마나 줄이나)는 같은 사람이 이어서 찾는다.
# 짝이 되는 판정끼리 서로 가리키게 해서, 한 페이지에서 들어와도 반대쪽 축까지 읽게 한다.
PAIRS = {
    "carbon-plate": [("wa-stack-height", "러닝화 밑창 두께 규정 — 로드 40mm 제한"),
                     ("wa-rigid-plate", "러닝화 플레이트 규정 — 강성 판 개수"),
                     ("shoe-mass", "신발 무게가 기록에 주는 영향")],
    "wa-stack-height": [("carbon-plate", "카본화 효과, 속도별 근거 등급")],
    "wa-rigid-plate": [("carbon-plate", "카본화 효과, 속도별 근거 등급")],
    "wa-availability": [("carbon-plate", "카본화 효과, 속도별 근거 등급")],
    "shoe-mass": [("carbon-plate", "카본화 효과, 속도별 근거 등급"),
                  ("wa-stack-height", "러닝화 밑창 두께 규정")],
    "utmb-kit": [("trail-pack-weight", "배낭 무게가 기록에 주는 영향"),
                 ("trail-poles", "트레일 폴 효과와 근거 등급")],
    "utmb-jacket": [("utmb-kit", "UTMB 필수 장비 목록"),
                    ("trail-pack-weight", "배낭 무게가 기록에 주는 영향")],
    "trail-pack-weight": [("utmb-kit", "UTMB 필수 장비 목록 규정"),
                          ("utmb-jacket", "UTMB 방수 재킷 규정")],
    "wetsuit-by-temp": [("wt-wetsuit-temp", "웻슈트 착용 수온 기준 규정"),
                        ("wetsuit", "웻슈트 효과와 근거 등급")],
    "trail-poles-by-gradient": [("trail-poles", "트레일 폴 효과와 근거 등급"),
                                ("utmb-kit", "UTMB 필수 장비 규정")],
    "trail-poles": [("utmb-kit", "UTMB 필수 장비와 폴 규정"),
                    ("trail-poles-by-gradient", "경사도별 트레일 폴 효과")],
    "uci-min-weight": [("aero-wheel", "에어로 휠 효과"), ("tyre-rolling", "타이어와 구름저항")],
    "uci-saddle-setback": [("uci-frame-approval", "UCI 승인 프레임 규정"), ("uci-min-weight", "UCI 최소 중량 규정")],
    "uci-frame-approval": [("aero-wheel", "에어로 휠 효과"), ("aero-helmet", "에어로 헬멧 효과")],
    "aero-wheel": [("uci-min-weight", "UCI 자전거 최소 중량 규정"),
                   ("uci-frame-approval", "UCI 승인 프레임 규정"),
                   ("tyre-rolling", "타이어와 구름저항")],
    "tyre-rolling": [("aero-wheel", "에어로 휠 효과"), ("uci-min-weight", "UCI 최소 중량 규정")],
    "aero-helmet": [("uci-saddle-setback", "UCI 안장 위치 규정"),
                    ("wt-bike-agegroup", "철인3종 에이지그룹 자전거 규정")],
    "wt-wetsuit-thickness": [("wetsuit", "웻슈트 효과와 근거 등급"),
                             ("wetsuit-by-temp", "수온별 웻슈트 착용 기준")],
    "wt-wetsuit-temp": [("wetsuit", "웻슈트 효과와 근거 등급"),
                        ("wetsuit-by-temp", "수온별 웻슈트 착용 기준")],
    "wt-bike-agegroup": [("aero-helmet", "에어로 헬멧 효과"), ("aero-wheel", "에어로 휠 효과")],
    "wetsuit": [("wt-wetsuit-thickness", "웻슈트 두께 규정"),
                ("wt-wetsuit-temp", "웻슈트 착용 수온 기준")],
    "ws-wheel-diameter": [("inline-bearings", "인라인 베어링 등급이 속도에 주는 영향")],
    "inline-bearings": [("ws-wheel-diameter", "인라인 바퀴 지름 규정")],
}


def pair_html(item_id, self_slug=""):
    rows = [(slug_for("x", i), lab) for i, lab in PAIRS.get(item_id, [])]
    rows = [(h, l) for h, l in rows if h != self_slug]
    if not rows:
        return ""
    li = "".join(f'<li><a href="{esc(h)}">{esc(l)}</a></li>' for h, l in rows)
    return ('<section class="gi-sec gi-pair"><h2>규정과 효과를 같이 보세요</h2>'
            '<p>규정은 연맹 문서에서, 효과는 논문에서 따로 정리했습니다. '
            f'함께 읽으면 쓸 수 있는지와 얼마나 도움이 되는지가 이어집니다.</p><ul>{li}</ul></section>')


def faq_html(item):
    faqs = item.get("faq") or []
    if not faqs:
        return ""
    rows = "".join(f'<h3>{esc(f["q"])}</h3><p>{esc(f["a"])}</p>' for f in faqs)
    return f'<section class="gi-sec gi-faq"><h2>자주 묻는 질문</h2>{rows}</section>'


def build_page(kind, item, bodies, siblings, tables=None):
    slug = slug_for(kind, item["id"])
    sport = SPORT_LABEL.get(item.get("sport"), "")
    q = item.get("question") or item["label"]

    # 제목과 설명은 자료 쪽 seo 칸에서 가져온다. 코드에 박아 두면 스무 장을
    # 손으로 고치게 되고, 주장을 더할 때마다 또 손이 간다.
    #
    # H1 은 제목의 앞토막(— 앞)을 쓴다. 검색어가 앞에 오고 길이도 적당하다.
    # 사이트 안에서 쓰는 짧은 이름(label)은 목차와 관련 링크에 그대로 두고,
    # 검색에서 들어온 사람에게는 자기가 친 말이 제목으로 보이게 한다.
    seo = item.get("seo") or {}
    seo_title = seo.get("title")
    if seo_title:
        title = f"{seo_title} | 칼랭크"
        h1 = seo_title.split("—")[0].strip()
    else:
        title = f"{item['label']} — {q} | 칼랭크 기어 판정"
        h1 = item["label"]
    desc = (seo.get("description") or item.get("headline") or q)[:155]
    body = rule_body(item, bodies) if kind == "rule" else claim_body(item)

    # 기록별·평속별 표로 보내는 길. 머리 가까이 둔다 — 자기 숫자를 넣기
    # 전에 "남들은 어떤가"를 먼저 보고 싶어 하는 사람이 많다.
    if tables:
        links = " · ".join(f'<a href="{esc(h)}">{esc(l)}</a>' for h, l in tables)
        body = (f'<p class="gi-tablinks">기록별로 미리 보기 · {links}</p>' + body)
    body += faq_html(item) + pair_html(item["id"], slug)
    attr = f' data-gear-{kind}="{esc(item["id"])}"'
    return slug, PAGE.format(
        title=esc(title), desc=esc(desc), base=BASE, slug=slug,
        jsonld=jsonld_for(item, slug, h1, desc, sport),
        nav=nav_html(active_for("gear.html")), sport=esc(sport),
        h1=esc(h1), question=esc(q), body=body,
        related=related_block(item.get("sport"), siblings, slug),
        bodyattr=attr)


def build_hub(rules, claims):
    """허브(gear.html)의 목록을 정적으로 박는다.

    JS 가 그리면 사람에게는 보이지만 크롤러에게는 17장으로 가는 길이
    없다. 내부 링크가 없는 페이지는 색인에서 밀린다. 그래서 목록만은
    서버에서 찍어 둔다 — JS 쪽은 이미 들어 있으면 손대지 않는다.
    """
    bodies = rules.get("bodies", {})
    out = [
        '<section class="gh-sport"><h2>내 도구<span class="gh-body">이 기기에만 저장</span></h2>'
        '<div class="gh-cols"><div class="gh-col">'
        '<a class="gh-item" href="kit.html"><b>내 장비 서랍</b><span class="gh-tag">내 수치로 확인</span>'
        '<span class="gh-q">가진 장비가 규정에 맞는지 한 화면에서 보고 싶다면</span></a>'
        '<a class="gh-item" href="ledger.html"><b>예상 기록 노트</b>'
        '<span class="gh-q">대회 전에 적은 예상 기록은 얼마나 맞았을까?</span></a></div>'
        '<div class="gh-col">'
        '<a class="gh-item" href="course.html"><b>코스 판정</b><span class="gh-tag">새로 나왔어요</span>'
        '<span class="gh-q">이 코스는 평지 몇 km에 해당할까?</span></a>'
        '<a class="gh-item" href="age-curve.html"><b>나이 곡선</b>'
        '<span class="gh-q">같은 기록이면 몇 살에 어느 등급일까?</span></a>'
        '<a class="gh-item" href="standards-triathlon.html"><b>철인3종 규칙 기준</b>'
        '<span class="gh-q">헬멧, 드래프팅, 헤드폰… 뭐가 실격일까?</span></a>'
        '<a class="gh-item" href="standards-trail.html"><b>트레일 벌칙 예시</b>'
        '<span class="gh-q">필수 장비가 없으면 실격일까, 시간 벌칙일까?</span></a>'
        '<a class="gh-item" href="standards-running.html"><b>러닝화 규칙 기준</b>'
        '<span class="gh-q">도로 40mm, 플레이트는 하나… 세계육상 신발 규정은?</span></a>'
        '<a class="gh-item" href="standards-cycling.html"><b>사이클 규칙 기준</b>'
        '<span class="gh-q">최소 6.8kg, 안장은 5cm 뒤… UCI 기준은?</span></a></div></div></section>']
    for sp in claims.get("sports", []):
        sid = sp["id"]
        rs = [r for r in rules.get("rules", []) if r.get("sport") == sid]
        cs = [c for c in claims.get("claims", []) if c.get("sport") == sid]
        names = sorted({bodies[r["body"]]["label"] for r in rs if r.get("body") in bodies})
        bodytxt = (f'<span class="gh-body">{esc(" · ".join(names))}</span>'
                   if names else "")

        def items(lst, tag):
            if not lst:
                return ('<p class="gh-empty">'
                        + ("아직 없습니다." if tag == "rule"
                           else "연구 자료를 정리하는 중입니다.")
                        + "</p>")
            bits = []
            for it in lst:
                chk = ('<span class="gh-tag">내 수치로 확인</span>'
                       if tag == "rule" and it.get("checkable") else "")
                bits.append(
                    f'<a class="gh-item" href="{esc(slug_for(tag, it["id"]))}">'
                    f'<b>{esc(it["label"])}</b>{chk}'
                    f'<span class="gh-q">{esc(it.get("question", ""))}</span></a>')
            return "".join(bits)

        out.append(
            f'<section class="gh-sport"><h2>{esc(sp["label"])}{bodytxt}</h2>'
            '<div class="gh-cols">'
            '<div class="gh-col"><h3>규정 <small>세계 최고 대회에서 쓸 수 있나</small></h3>'
            + items(rs, "rule") + "</div>"
            '<div class="gh-col"><h3>효과 <small>연구가 뭐라고 하나</small></h3>'
            + items(cs, "claim") + "</div>"
            "</div></section>")
    return "\n".join(out)


def update_hub(rules, claims, check=False):
    path = ROOT / "gear.html"
    if not path.exists():
        return False
    src = path.read_text(encoding="utf-8")
    block = build_hub(rules, claims)
    # 표식 사이만 바꾼다. 전에는 여는 div 와 "그 다음 </div>" 사이를 비탐욕으로
    # 잡았는데, 넣은 블록 안에도 </div> 가 있어서 두 번째 실행부터 블록 안쪽
    # 첫 </div> 에 걸렸다. 그래서 돌릴 때마다 목록이 통째로 덧붙었다 —
    # 다섯 번 돌리니 종목이 25개, 항목이 100개가 됐다. 경계는 눈에 보이는
    # 표식으로 두는 편이 안전하다.
    pat = re.compile(r"(<!-- gear-hub:start[^>]*-->).*?(<!-- gear-hub:end -->)", re.S)
    if not pat.search(src):
        print("  gear.html 에 gear-hub 표식이 없습니다 — 허브 목록을 건너뜁니다.")
        return False
    new = pat.sub(lambda m: m.group(1) + "\n" + block + "\n" + m.group(2), src, count=1)
    if new == src:
        return False
    if not check:
        path.write_text(new, encoding="utf-8")
    return True


# ── 기록별·평속별 효과표 ──────────────────────────────────────────
#
# 목표 시간 페이지가 먹힌 구조를 그대로 쓴다. 숫자 하나를 주면 여러 틀로
# 되돌려 주고, 읽는 사람이 표에서 자기 줄을 찾는다. 다만 줄이 서로 다른
# 답을 낼 때만 페이지를 만든다 — 카본화는 한 표 안에서 근거가 A 에서 C 로
# 뒤집히고, 타이어는 평속에 따라 단축이 3.5배 벌어진다. 웻슈트는 철인
# 전 거리가 한 근거 구간에 들어가 줄마다 같은 숫자가 나오므로 만들지 않는다.

def _clock(sec):
    sec = int(round(abs(sec)))
    h, m, r = sec // 3600, (sec % 3600) // 60, sec % 60
    return f"{h}:{m:02d}:{r:02d}" if h else f"{m}:{r:02d}"


def _gap(sec):
    sec = int(round(abs(sec)))
    m, r = sec // 60, sec % 60
    if not m:
        return f"{r}초"
    return f"{m}분 {r}초" if r else f"{m}분"


def _cut_text(eff):
    """단축 구간. 한 점으로만 보고된 근거는 범위로 적지 않는다."""
    if not eff.get("cutSec"):
        return "—"
    lo, hi = abs(eff["cutSec"]["lo"]), abs(eff["cutSec"]["hi"])
    if eff.get("significant") is False:
        lo = 0.0
    lo, hi = min(lo, hi), max(lo, hi)
    if abs(hi - lo) < 1:
        return _gap(hi)
    return f"{_gap(lo)} ~ {_gap(hi)}"


def run_table(claim, dist_key, dist_km, dist_label, bounds):
    goals = RUN_GOALS[dist_key]
    res = run_model([{"claim": claim["id"],
                      "input": {"finishSec": sec, "distanceKm": dist_km}}
                     for sec, _ in goals])
    rows, grades_seen = [], set()
    for (sec, label), r in zip(goals, res):
        if not r or not r["effects"]:
            continue
        e = r["effects"][0]
        if not e["hasEvidence"]:
            continue
        grades_seen.add(e["grade"])
        pct0 = wma.age_grade(sec, REF_GENDER, dist_key, REF_AGE)
        best = max(abs(e["cutSec"]["lo"]), abs(e["cutSec"]["hi"]))
        pct1 = wma.age_grade(max(1, sec - best), REF_GENDER, dist_key, REF_AGE)
        t0, t1 = tier_of(pct0, bounds), tier_of(pct1, bounds)
        pace = sec / dist_km
        rows.append({
            "label": label, "pace": f"{int(pace)//60}:{int(pace)%60:02d}",
            "speed": f"{r['speedKmh']:.1f}", "grade": e["grade"],
            "ns": e.get("significant") is False,
            "cut": _cut_text(e), "tier0": t0, "tier1": t1, "moved": t0 != t1,
        })
    return rows, grades_seen


def bike_table(claim, dist_km, bounds):
    res = run_model([{"claim": claim["id"],
                      "input": {"speed_kmh": v, "distanceKm": dist_km}}
                     for v in BIKE_SPEEDS])
    rows = []
    for v, r in zip(BIKE_SPEEDS, res):
        if not r:
            continue
        timed = [e for e in r["effects"] if e.get("cutSec")]
        if not timed:
            continue
        e = timed[0]
        base = dist_km * 1000 / (v / 3.6)
        rows.append({
            "label": f"{v}㎞/h", "speed": v,
            "cutSec": abs(e["cutSec"]["point"]),
            "watts": f"{round(r['effects'][0].get('watts') or 0)}",
            "share": r["effects"][0].get("sharePct"),
            "roll": r["effects"][0].get("rollSharePct"),
            "grade": e["grade"], "cut": _cut_text(e),
            "before": _clock(base), "after": _clock(base - e["cutSec"]["point"]),
        })
    return rows


def table_html(rows, kind):
    if kind == "run":
        head = ("<tr><th>목표 기록</th><th>페이스</th><th>속도</th>"
                "<th>근거</th><th>단축</th><th>등급</th></tr>")
        body = "".join(
            f'<tr><th>{esc(r["label"])}</th>'
            f'<td>{esc(r["pace"])}/km</td><td>{esc(r["speed"])}㎞/h</td>'
            f'<td><span class="ge-grade ge-{esc(r["grade"])}">{esc(r["grade"])}</span>'
            + ('<span class="gt-ns">유의하지 않음</span>' if r["ns"] else "")
            + f'</td><td>{esc(r["cut"])}</td>'
            f'<td>{esc(r["tier0"])}'
            + (f' → <b>{esc(r["tier1"])}</b>' if r["moved"] else " <em>그대로</em>")
            + "</td></tr>"
            for r in rows)
    else:
        head = ("<tr><th>평속</th><th>필요 출력</th><th>근거</th>"
                "<th>단축</th><th>완주 시간</th></tr>")
        body = "".join(
            f'<tr><th>{esc(r["label"])}</th><td>{esc(r["watts"])}W</td>'
            f'<td><span class="ge-grade ge-{esc(r["grade"])}">{esc(r["grade"])}</span></td>'
            f'<td>{esc(r["cut"])}</td>'
            f'<td>{esc(r["before"])} → <b>{esc(r["after"])}</b></td></tr>'
            for r in rows)
    return f'<div class="gt-wrap"><table class="gt"><thead>{head}</thead><tbody>{body}</tbody></table></div>'


def build_table_page(claim, ctx, bodies):
    """ctx: run 이면 (key, km, label), bike 이면 (km, label)"""
    bounds = tier_bounds()
    if ctx["kind"] == "run":
        rows, grades = run_table(claim, ctx["key"], ctx["km"], ctx["label"], bounds)
        if len(rows) < 2:
            return None
        slug = f'gear-{claim["id"]}-{ctx["key"]}.html'
        short = claim.get("short_label") or claim["label"]
        h1 = f'{ctx["label"]} {short} 효과'
        title = f'{h1} — {rows[0]["label"]}~{rows[-1]["label"]} 기록별 단축 시간 | 칼랭크'
        flip = len(grades) > 1
        moved = [r for r in rows if r["moved"]]

        # 글머리가 표에서 읽히는 것을 먼저 말한다. 등급이 하나도 안 움직이면
        # 그게 이 표의 결론이다 — 빈칸처럼 보이는 칸이 사실은 답이다.
        if moved:
            names = ", ".join(r["label"] for r in moved)
            lead = (f'{ctx["label"]} {len(rows)}줄 가운데 등급이 바뀌는 건 '
                    f'{names} 한 줄입니다.' if len(moved) == 1 else
                    f'{ctx["label"]} {len(rows)}줄 가운데 {len(moved)}줄에서 등급이 바뀝니다({names}).')
        else:
            lead = f'{ctx["label"]}에서는 어느 줄도 등급이 바뀌지 않습니다.'

        # 근거가 갈리는 것은 등급이 움직이는 줄이 있을 때만 덧붙인다.
        # 위에서 이미 "근거가 갈린다"는 뜻을 전한 경우 같은 말을 두 번 하게 된다.
        if flip and moved:
            lead += " 같은 신발이라도 표 윗줄과 아랫줄의 근거 수준은 다릅니다."
        elif flip:
            lead += " 다만 근거 수준은 기록에 따라 달라집니다."
        desc = (f'{ctx["label"]} {rows[0]["label"]}~{rows[-1]["label"]} 기록에서 {short}로 몇 초를 줄일 수 있는지 '
                f'연구 근거 등급(A~D)과 함께 표로 정리했습니다. {lead}')[:155]
        note = (
            '<h2>표를 읽을 때</h2>'
            '<p class="gm-measure">단축 초는 나이·성별과 무관합니다. 다만 그 초가 '
            '등급을 바꾸는지는 나이에 달려 있어서, 등급 칸은 '
            f'<b>{REF_AGE}세 {"남성" if REF_GENDER == "male" else "여성"}</b> 기준으로 적었습니다. '
            '내 나이로 보려면 <a href="level.html">등급 계산기</a>에서 기록을 넣어 보세요.</p>'
            '<p class="gm-measure">단축 초가 위에서 아래로 계속 늘거나 줄지는 않습니다. '
            '같은 근거 구간 안에서는 기록이 느릴수록 단축 초가 커지는데, 같은 비율이 더 긴 '
            '시간에 적용되기 때문입니다. 구간이 바뀌면 적용되는 연구가 달라져서 '
            '숫자가 바뀌는 지점이 생기고, 그 지점이 연구가 나뉘는 경계입니다.</p>')
        goal_links = " · ".join(
            f'<a href="goal-{ctx["key"]}-{sl}.html">{ctx["label"]} {nm}</a>'
            for sl, nm in ctx.get("goals", []))
        extra = (f'<p class="gi-links">목표 기록별 페이스와 구간 통과 시간 · {goal_links}</p>'
                 if goal_links else "")
        body = (f'<p class="gi-headline">{esc(lead)}</p>'
                + table_html(rows, "run") + note + extra)
    else:
        rows = bike_table(claim, ctx["km"], bounds)
        if len(rows) < 2:
            return None
        slug = f'gear-{claim["id"]}-{ctx["km"]}km.html'
        short = claim.get("short_label") or claim["label"]
        h1 = f'{ctx["label"]} {short} 효과'
        title = f'{h1} — 평속 {BIKE_SPEEDS[0]}~{BIKE_SPEEDS[-1]}㎞/h별 단축 시간 | 칼랭크'
        # 글머리가 표의 폭을 먼저 말한다. 느린 쪽이 더 받는지 덜 받는지가
        # 이 표에서 읽히는 유일한 결론이고, 장비마다 방향이 다르다.
        lo, hi = rows[0], rows[-1]
        wider = "느릴수록" if lo["cutSec"] > hi["cutSec"] else "빠를수록"
        a, b2 = (lo, hi) if lo["cutSec"] > hi["cutSec"] else (hi, lo)
        ratio = a["cutSec"] / b2["cutSec"] if b2["cutSec"] else 0
        lead = (f'{ctx["label"]}에서 {lo["label"]}는 {_gap(lo["cutSec"])}, '
                f'{hi["label"]}는 {_gap(hi["cutSec"])} 줄어듭니다. '
                + (f'{wider} 더 많이 줄어들고, 차이는 {ratio:.1f}배입니다.'
                   if ratio >= 1.3 else f'{wider} 조금 더 줄어듭니다.'))
        desc = (f'{ctx["label"]} 주행에서 평속 {BIKE_SPEEDS[0]}~{BIKE_SPEEDS[-1]}㎞/h별로 {short}이 몇 초를 줄이는지 '
                f'검증된 출력 모델로 계산했습니다. {lead}')[:155]
        note = (
            '<h2>표를 읽을 때</h2>'
            '<p class="gm-measure">공기저항은 속도의 세제곱으로, 구름저항은 속도에 비례해 '
            '커집니다. 그래서 빠를수록 공기저항 몫이 커지고 느릴수록 구름저항 몫이 커집니다. '
            '같은 퍼센트를 줄여도 빠른 사람은 휠·헬멧에서, 느린 사람은 타이어에서 더 많이 '
            '돌려받는 이유가 여기 있습니다.</p>'
            '<p class="gm-measure">필요 출력은 평지·무풍에서 그 평속을 유지하는 데 드는 힘입니다. '
            '총중량 80㎏, 공기밀도 1.225㎏/㎥, CdA 0.264㎡ 를 기본값으로 썼습니다. '
            '<a href="' + esc(slug_for("claim", claim["id"])) + '">판정 도구</a>에서 '
            '내 값으로 바꿔 넣을 수 있습니다.</p>')
        body = f'<p class="gi-headline">{esc(lead)}</p>' + table_html(rows, "bike") + note

    sibs = []
    if claim["id"] in RUN_TABLES:
        sibs = [(f'gear-{claim["id"]}-{k}.html', f'{lab} {claim.get("short_label") or claim["label"]} 효과')
                for (k, _, _, lab) in RUN_DISTS if f'gear-{claim["id"]}-{k}.html' != slug]
    else:
        sibs = [(f'gear-{claim["id"]}-{km}km.html', f'{lab} {claim.get("short_label") or claim["label"]} 효과')
                for km, lab in BIKE_DISTS if f'gear-{claim["id"]}-{km}km.html' != slug]
    if sibs:
        body += ('<p class="gi-links">다른 거리 표 · '
                 + " · ".join(f'<a href="{esc(h)}">{esc(l)}</a>' for h, l in sibs) + "</p>")
    body += pair_html(claim["id"], slug)
    body += (f'<p class="gm-src">근거와 출처는 '
             f'<a href="{esc(slug_for("claim", claim["id"]))}">{esc(claim["label"])} 판정</a>에 '
             f'자세히 적어 두었습니다.</p>')

    sport = SPORT_LABEL.get(claim.get("sport"), "")
    return slug, PAGE.format(
        title=esc(title), desc=esc(desc), base=BASE, slug=slug,
        jsonld=jsonld_for({"question": title, "headline": desc}, slug, h1, desc, sport),
        nav=nav_html(active_for("gear.html")), sport=esc(sport),
        h1=esc(h1), question=esc(claim.get("question", "")), body=body,
        related="", bodyattr="")


def table_index(claims_data):
    """claim 별 표 페이지 목록. 부모 판정 페이지가 이쪽을 가리키게 한다.

    가리키는 링크가 없으면 고아 페이지가 된다. 사이트맵에만 올라가 있고
    안에서 아무도 가리키지 않는 페이지는 색인에서 뒤로 밀린다.
    """
    idx = {}
    for cid in RUN_TABLES:
        if findc(claims_data, cid):
            idx[cid] = [(f"gear-{cid}-{key}.html", label)
                        for key, _km, _b, label in RUN_DISTS]
    for cid in BIKE_TABLES:
        if findc(claims_data, cid):
            idx[cid] = [(f"gear-{cid}-{km}km.html", label)
                        for km, label in BIKE_DISTS]
    return idx


def build_tables(claims_data, bodies):
    out = []
    goal_slug = {"5km": [("20min", "20분"), ("25min", "25분"), ("30min", "30분")],
                 "10km": [("40min", "40분"), ("45min", "45분"), ("50min", "50분"),
                          ("55min", "55분"), ("60min", "1시간")],
                 "half": [("1h30", "1시간 30분"), ("1h40", "1시간 40분"),
                          ("1h50", "1시간 50분"), ("2h", "2시간"), ("2h30", "2시간 30분")],
                 "full": [("3h", "3시간"), ("3h30", "3시간 30분"), ("4h", "4시간"),
                          ("4h30", "4시간 30분"), ("5h", "5시간")]}
    for cid in RUN_TABLES:
        claim = findc(claims_data, cid)
        if not claim:
            continue
        for key, km, slug_bit, label in RUN_DISTS:
            r = build_table_page(claim, {"kind": "run", "key": key, "km": km,
                                         "label": label,
                                         "goals": goal_slug.get(key, [])}, bodies)
            if r:
                out.append(r)
    for cid in BIKE_TABLES:
        claim = findc(claims_data, cid)
        if not claim:
            continue
        for km, label in BIKE_DISTS:
            r = build_table_page(claim, {"kind": "bike", "km": km, "label": label}, bodies)
            if r:
                out.append(r)
    return out


def findc(data, cid):
    for c in data.get("claims", []):
        if c["id"] == cid:
            return c
    return None


# ── 수온표: 규정과 효과가 한 화면에 ──────────────────────────────

def wetsuit_temp_page(rules, claims):
    rule = None
    for r in rules.get("rules", []):
        if r["id"] == "wt-wetsuit-temp":
            rule = r
            break
    claim = findc(claims, "wetsuit")
    if not rule or not claim:
        return None

    opts = (rule.get("check", {}).get("extra") or [{}])[0].get("options") or []
    if not opts:
        return None

    # 가로줄은 수온, 세로칸은 참가 구분. 자기 칸을 찾으면 그 자리에 답이 있다.
    head = "<tr><th>수온</th>" + "".join(
        f'<th>{esc(o["label"].replace(" — ", "<br>").replace("·U23·주니어·유스", ""))}</th>'
        for o in opts) + "</tr>"
    head = head.replace("&lt;br&gt;", "<br>")

    rows = []
    for t in WETSUIT_TEMPS:
        cells = []
        for o in opts:
            if t >= o["forbidden_at"]:
                cells.append('<td class="wt-no">금지</td>')
            elif t <= o["mandatory_at"]:
                cells.append('<td class="wt-must">의무</td>')
            else:
                cells.append('<td class="wt-ok">선택</td>')
        label = f"{t:g}℃"
        mark = ""
        if t == 15.9:
            mark = '<span class="wt-edge">이 아래는 전원 의무</span>'
        elif t == 24.6:
            mark = '<span class="wt-edge">동호인 상한</span>'
        rows.append(f'<tr><th>{esc(label)}{mark}</th>' + "".join(cells) + "</tr>")

    table = ('<div class="gt-wrap"><table class="gt wt-grid"><thead>' + head
             + "</thead><tbody>" + "".join(rows) + "</tbody></table></div>")

    # 효과 쪽. 규정이 이렇게 촘촘한데 효과 근거는 어떤지 바로 옆에 붙인다.
    eff = None
    for e in claim.get("effects", []):
        if e["id"] == "race_time":
            eff = e
            break
    ev_rows = ""
    if eff:
        for ev in eff.get("evidence", []):
            a = (ev.get("applies") or {}).get("swim_distance_km") or [None, None]
            scope = ("10km 이상" if a[0] else "10km 미만")
            pct = ev.get("effect_pct")
            val = (f'0 ~ {pct:.1f}% 빠름' if ev.get("significant") is False
                   else f'{pct:.1f}% 빠름')
            ev_rows += (f'<tr><th>{esc(scope)}</th><td>'
                        f'<span class="ge-grade ge-{esc(ev["grade"])}">{esc(ev["grade"])}</span> '
                        f'{esc(val)}'
                        + ('<span class="gt-ns">유의하지 않음</span>'
                           if ev.get("significant") is False else "")
                        + f'<span class="gm-note">참가자 {ev.get("n", 0)}명</span></td></tr>')

    body = (
        '<p class="gi-headline">규정은 수온을 세밀하게 나눠 두었지만, '
        '실제 대회 기록에서는 웻슈트 효과가 통계적으로 확인되지 않았습니다.</p>'
        '<h2>이 수온에서 입어도 되나 — World Triathlon 규정</h2>'
        + table
        + '<p class="gm-measure">같은 물에서 엘리트는 못 입고 동호인은 입을 수 있는 구간이 '
          '있습니다. 1500m 이하에서 엘리트는 20℃부터 금지이고 동호인은 22℃까지 입을 수 있으며, '
          '60세 이상은 거리와 상관없이 24.6℃까지 허용됩니다. 낮은 쪽은 모두 같아서 '
          '15.9℃ 이하에서는 전원이 착용해야 합니다. 기술대표가 대회 조건에 따라 따로 금지할 수도 있습니다.</p>'
        '<h2>입으면 빨라지나 — 실제 대회 기록</h2>'
        '<div class="gt-wrap"><table class="gt"><thead>'
        '<tr><th>수영 거리</th><th>웻슈트 쪽이</th></tr></thead><tbody>'
        + ev_rows + '</tbody></table></div>'
        '<p class="gm-measure">완주자 584명의 실제 대회 기록을 모아 견준 결과입니다. '
        '남녀 모두, 두 거리 모두에서 통계적으로 유의한 차이가 나오지 않았습니다. '
        '다만 같은 사람에게 둘 다 입혀 본 실험이 아니라 선수가 스스로 고른 결과를 나중에 '
        '모은 자료이고, 두 대회 모두 수온이 20℃를 넘었습니다. 웻슈트가 가장 크게 도움이 될 '
        '찬물 조건은 이 자료에 들어 있지 않습니다.</p>'
        '<h2>두 표를 함께 보면</h2>'
        '<p class="gm-measure">규정은 수온을 구간별로 나누어 금지·선택·의무를 정해 두었습니다. '
        '반면 기록이 얼마나 줄어드는지에 대한 근거는 이 규정만큼 세밀하지 않습니다. '
        '두 표는 서로 다른 질문에 답합니다. 규정은 입어도 되는지를, 연구는 입으면 빨라지는지를 다룹니다. '
        '효과 자료에 찬물 조건이 없으므로, 수온이 낮은 대회에서 웻슈트가 어떤 차이를 만드는지는 '
        '이 표만으로 판단하기 어렵습니다.</p>'
        f'<p class="gm-src">규정 원문과 효과 근거는 '
        f'<a href="{esc(slug_for("rule", rule["id"]))}">웻슈트 수온 기준</a>과 '
        f'<a href="{esc(slug_for("claim", claim["id"]))}">웻슈트 효과 판정</a>에 '
        f'자세히 적어 두었습니다.</p>')

    slug = "gear-wetsuit-by-temp.html"
    h1 = "수온별 웻슈트 — 입어도 되나, 빨라지나"
    title = "수온별 웻슈트 착용 기준과 효과 — 입어도 되나, 빨라지나 | 칼랭크"
    desc = ("수온별로 웻슈트가 금지·선택·의무 중 무엇인지 참가 구분까지 나눠 정리하고, "
            "실제 대회 기록에서 웻슈트가 얼마나 빨랐는지 함께 봅니다.")[:155]
    return slug, PAGE.format(
        title=esc(title), desc=esc(desc), base=BASE, slug=slug,
        jsonld=jsonld_for({"question": "이 수온에서 웻슈트를 입어도 되나?",
                           "headline": desc}, slug, h1, desc, "철인3종"),
        nav=nav_html(active_for("gear.html")), sport="철인3종",
        h1=esc(h1), question=esc("내 대회 수온에서는 어떻게 되나?"),
        body=body + pair_html("wetsuit-by-temp"), related="", bodyattr="")


# ── 경사표: 한 장비의 효과가 서로 반대로 간다 ────────────────────

def pole_gradient_page(claims):
    claim = findc(claims, "trail-poles")
    if not claim:
        return None
    reqs = [{"claim": "trail-poles", "input": {"gradient_pct": g}}
            for g in POLE_GRADIENTS]
    res = run_model(reqs)

    rows = ""
    for g, r in zip(POLE_GRADIENTS, res):
        if not r:
            continue
        cells = ""
        for e in r["effects"]:
            if not e["hasEvidence"]:
                cells += '<td><em>근거 없음</em></td>'
                continue
            rg = e["range"]
            ns = e.get("significant") is False
            lo = 0.0 if ns else rg["lo"]
            word = "늘어남" if e["direction"] == "worse" else "줄어듦"
            if abs(rg["hi"]) < 0.05:
                txt = "차이 없음"
            elif abs(rg["hi"] - lo) < 0.05:
                txt = f'{rg["hi"]:.0f}% {word}'
            else:
                txt = f'{lo:.0f} ~ {rg["hi"]:.0f}% {word}'
            cells += (f'<td><span class="ge-grade ge-{esc(e["grade"])}">{esc(e["grade"])}</span> '
                      f'{esc(txt)}'
                      + ('<span class="gt-ns">유의하지 않음</span>' if ns else "")
                      + "</td>")
        rows += f'<tr><th>{g}%</th>{cells}</tr>'

    labels = [e["label"] for e in res[0]["effects"]] if res and res[0] else []
    head = "<tr><th>경사</th>" + "".join(f"<th>{esc(l)}</th>" for l in labels) + "</tr>"
    table = (f'<div class="gt-wrap"><table class="gt"><thead>{head}</thead>'
             f"<tbody>{rows}</tbody></table></div>")

    body = (
        '<p class="gi-headline">트레일 폴은 에너지 소모를 늘리는 대신 '
        '다리에 걸리는 부담을 줄여 줍니다.</p>'
        + table
        + '<h2>표를 읽을 때</h2>'
          '<p class="gm-measure">산소 소모는 평지에서 가장 불리하고, 경사가 가팔라질수록 '
          '불리함이 줄어듭니다. 25도가 넘는 구간에서는 수직 이동 비용이 낮아졌다는 '
          '보고도 있지만 근거가 많지 않습니다. 다리에 걸리는 힘은 경사와 상관없이 '
          '줄어드는 쪽으로 보고됐습니다. 다만 측정 방식이 연구마다 달라 하나로 묶기 어렵고, '
          '러닝 쪽 근거에는 참가자 한 명짜리 연구도 포함돼 있습니다.</p>'
          '<p class="gm-measure">정리하면 폴은 기록을 줄이는 장비라기보다, 에너지를 조금 더 쓰는 대신 '
          '다리 부담을 덜어 주는 장비입니다. 긴 대회에서 다리가 먼저 지치는 경우에 '
          '도움이 될 수 있습니다. UTMB에서는 폴이 선택 장비이지만, 한번 들면 전 구간 '
          '들고 가야 합니다.</p>'
        + f'<p class="gm-src">근거와 출처는 '
          f'<a href="{esc(slug_for("claim", claim["id"]))}">트레일 폴 판정</a>에 '
          f'자세히 적어 두었습니다. 필수 장비 기준은 '
          f'<a href="gear-utmb-kit.html">UTMB 필수 장비</a>에서 볼 수 있습니다.</p>')

    slug = "gear-trail-poles-by-gradient.html"
    h1 = "경사별 트레일 폴 효과"
    title = "경사별 트레일 폴 효과 — 산소 소모와 다리 부담 | 칼랭크"
    desc = ("경사에 따라 트레일 폴의 효과가 어떻게 달라지는지 연구 근거 등급과 함께 "
            "정리했습니다. 산소 소모는 늘고 다리 부담은 줄어드는 양쪽을 함께 봅니다.")[:155]
    return slug, PAGE.format(
        title=esc(title), desc=esc(desc), base=BASE, slug=slug,
        jsonld=jsonld_for({"question": "폴을 쓰면 정말 덜 힘들까?", "headline": desc},
                          slug, h1, desc, "트레일러닝"),
        nav=nav_html(active_for("gear.html")), sport="트레일러닝",
        h1=esc(h1), question=esc("경사에 따라 얼마나 달라지나?"),
        body=body + pair_html("trail-poles-by-gradient"), related="", bodyattr="")


def update_sitemap(slugs):
    path = ROOT / "sitemap.xml"
    if not path.exists():
        return 0
    xml = path.read_text(encoding="utf-8")
    added, n = "", 0
    for slug in slugs:
        loc = f"{BASE}/{slug}"
        if f"<loc>{loc}</loc>" in xml:
            continue
        added += ("  <url>\n"
                  f"    <loc>{loc}</loc>\n"
                  f"    <lastmod>{TODAY}</lastmod>\n"
                  "    <changefreq>monthly</changefreq>\n"
                  "    <priority>0.8</priority>\n"
                  "  </url>\n")
        n += 1
    if added:
        xml = xml.replace("</urlset>", added + "</urlset>")
        path.write_text(xml, encoding="utf-8")
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    rules = json.loads((ROOT / "data" / "gear_rules.json").read_text(encoding="utf-8"))
    claims = json.loads((ROOT / "data" / "gear_claims.json").read_text(encoding="utf-8"))
    bodies = rules.get("bodies", {})

    items = [("rule", r) for r in rules.get("rules", [])] + \
            [("claim", c) for c in claims.get("claims", [])]

    by_sport = {}
    for kind, it in items:
        by_sport.setdefault(it.get("sport"), []).append((kind, it["id"], it["label"]))

    tidx = table_index(claims)
    pages = [build_page(kind, it, bodies, by_sport.get(it.get("sport"), []),
                        tidx.get(it["id"]) if kind == "claim" else None)
             for kind, it in items]
    pages += build_tables(claims, bodies)
    for fn in (lambda: wetsuit_temp_page(rules, claims), lambda: pole_gradient_page(claims)):
        r = fn()
        if r:
            pages.append(r)

    written, same, slugs = 0, 0, []
    from gear_images import add_image
    for slug, content in pages:
        content = add_image(slug, content)
        slugs.append(slug)
        p = ROOT / slug
        if p.exists() and p.read_text(encoding="utf-8") == content:
            same += 1
            continue
        if not args.check:
            p.write_text(content, encoding="utf-8")
        written += 1

    hub_changed = update_hub(rules, claims, check=args.check)

    if args.check:
        if written or hub_changed:
            print(f"기어 페이지 {written}장이 자료와 어긋납니다"
                  + (", 허브 목록도 오래됐습니다" if hub_changed else "")
                  + " — 생성기를 돌리세요.")
            return 1
        print(f"기어 페이지 {same}장 모두 최신입니다.")
        return 0

    n = update_sitemap(["gear.html"] + slugs)
    print(f"기어 페이지 {written}장 새로 쓰고 {same}장은 그대로. "
          f"sitemap 에 {n}개 추가." + (" 허브 목록도 갱신." if hub_changed else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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

            if ev.get("no_data"):
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
    faq = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{
            "@type": "Question", "name": item.get("question") or title,
            "acceptedAnswer": {"@type": "Answer",
                               "text": item.get("headline") or desc},
        }],
    }
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
    return dump(faq) + "\n" + dump(crumb)


def build_page(kind, item, bodies, siblings):
    slug = slug_for(kind, item["id"])
    sport = SPORT_LABEL.get(item.get("sport"), "")
    q = item.get("question") or item["label"]
    title = f"{item['label']} — {q} | 칼랭크 기어 판정"
    desc = (item.get("headline") or q)[:155]
    body = rule_body(item, bodies) if kind == "rule" else claim_body(item)
    attr = f' data-gear-{kind}="{esc(item["id"])}"'
    return slug, PAGE.format(
        title=esc(title), desc=esc(desc), base=BASE, slug=slug,
        jsonld=jsonld_for(item, slug, item["label"], desc, sport),
        nav=nav_html(active_for("gear.html")), sport=esc(sport),
        h1=esc(item["label"]), question=esc(q), body=body,
        related=related_block(item.get("sport"), siblings, slug),
        bodyattr=attr)


def build_hub(rules, claims):
    """허브(gear.html)의 목록을 정적으로 박는다.

    JS 가 그리면 사람에게는 보이지만 크롤러에게는 17장으로 가는 길이
    없다. 내부 링크가 없는 페이지는 색인에서 밀린다. 그래서 목록만은
    서버에서 찍어 둔다 — JS 쪽은 이미 들어 있으면 손대지 않는다.
    """
    bodies = rules.get("bodies", {})
    out = []
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
                           else "연구 자료를 모으는 중입니다. 숫자가 설 때까지 비워 둡니다.")
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
    new = re.sub(r'(<div id="gearHub" class="gi-hub">).*?(</div>)',
                 lambda m: m.group(1) + "\n" + block + "\n" + m.group(2),
                 src, count=1, flags=re.S)
    if new == src:
        return False
    if not check:
        path.write_text(new, encoding="utf-8")
    return True


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

    written, same, slugs = 0, 0, []
    for kind, it in items:
        slug, content = build_page(kind, it, bodies, by_sport.get(it.get("sport"), []))
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

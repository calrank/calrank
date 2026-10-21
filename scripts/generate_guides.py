"""
calrank 대회 가이드 칼럼 생성기.

구조
----
각 글은 (종목 sport) × (시기 stage) 좌표를 갖습니다. 이 좌표가 글끼리
서로 이어지는 LOOP 의 뼈대입니다.

  시기 축 : prep → gear → d1 → raceday → finish → recovery → (다시 prep)
  종목 축 : marathon / trail / triathlon / cycling / inline / gear

  ① 같은 종목 안에서 시기 순서대로 이전 글 ↔ 다음 글 (마지막 → 처음으로 순환)
  ② 같은 시기의 다른 종목으로 건너뛰기
  ③ 태그 페이지로 모이고, 태그 페이지에서 다시 각 글로 흩어짐
  ④ 허브(guides.html)에서 전체 조망

그래서 독자가 어느 글로 들어와도 막다른 길이 없습니다.

근거 검증
--------
본문에 {{키}} 를 쓰면 각주로 바뀝니다. 키는 scripts/references.py 에
등록된 것만 허용하며, 등록되지 않은 키가 하나라도 있으면 생성을 중단합니다.
또 각 글이 선언한 refs 목록과 본문에서 실제로 쓴 키가 다르면 역시 중단합니다.
근거 없는 주장이 조용히 올라가는 일을 막기 위한 장치입니다.

사용법:
  python3 scripts/generate_guides.py          # 생성
  python3 scripts/generate_guides.py --check  # 검증만 (파일 안 씀)
"""
import html
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import references as R
from guides_data import GUIDES, SPORTS, STAGES, TAG_INFO

ROOT = Path(__file__).resolve().parent.parent
KST = timezone(timedelta(hours=9))
BASE = "https://calrank.vercel.app"

CITE_RE = re.compile(r"\{\{([a-zA-Z0-9_]+)\}\}")

# 본문 안에서 다른 글로 거는 링크. [[글id|앵커 텍스트]] 로 적습니다.
# 앵커 텍스트가 검색어 역할을 하므로 "여기"나 "이 글" 같은 말 대신
# 실제로 검색되는 표현을 씁니다. 대상 id 가 없으면 생성을 중단합니다.
LINK_RE = re.compile(r"\[\[([a-z0-9-]+)\|([^\]]+)\]\]")


def render_links(text):
    def sub(m):
        gid, label = m.group(1), m.group(2)
        if gid not in _GUIDE_IDS:
            raise ValueError(
                f"본문 링크가 가리키는 글이 없습니다: [[{gid}|{label}]]. "
                f"있는 id: {sorted(_GUIDE_IDS)}")
        return f'<a class="g-ilink" href="guide-{gid}.html">{label}</a>'
    return LINK_RE.sub(sub, text)


_GUIDE_IDS = set()


def h(s):
    return html.escape(str(s), quote=True)


# ---------------------------------------------------------------- 인용

def collect_cites(guide):
    """글 전체에서 쓰인 출처 키를 등장 순서대로 모은다."""
    found = []
    def scan(text):
        for k in CITE_RE.findall(str(text)):
            if k not in found:
                found.append(k)
    for b in guide["blocks"]:
        scan(b.get("h2", ""))
        for p in b.get("p", []):
            scan(p)
        for item in b.get("list", []):
            scan(item)
        for row in b.get("rows", []):
            for cell in row:
                scan(cell)
        scan(b.get("note", ""))
        scan(b.get("callout", ""))
    for q, a in guide.get("faq", []):
        scan(q); scan(a)
    scan(guide.get("answer", ""))
    return found


def validate(guide):
    """등록되지 않은 출처, 선언과 실제 사용의 불일치를 잡는다."""
    used = collect_cites(guide)
    R.check_keys(used)
    declared = guide.get("refs", [])
    R.check_keys(declared)
    missing = [k for k in used if k not in declared]
    unused = [k for k in declared if k not in used]
    if missing:
        raise ValueError(
            f"[{guide['id']}] 본문에서 썼지만 refs 에 선언하지 않은 출처: {missing}")
    if unused:
        raise ValueError(
            f"[{guide['id']}] refs 에 선언했지만 본문에서 쓰지 않은 출처: {unused}")
    return used


def render_cites(text, order):
    """{{키}} → 위첨자 각주 링크."""
    def sub(m):
        k = m.group(1)
        n = order.index(k) + 1
        ref = R.cite(k)
        return (f'<sup class="g-cite"><a href="#ref-{n}" '
                f'title="{h(ref["label"])} — {h(ref["title"])}">[{n}]</a></sup>')
    return render_links(CITE_RE.sub(sub, text))


# ---------------------------------------------------------------- 본문 블록

def render_block(b, order, toc_ids=None):
    out = []
    if b.get("h2"):
        hid = (toc_ids or {}).get(b["h2"])
        attr = f' id="{hid}"' if hid else ""
        out.append(f'<h2 class="g-h2"{attr}>{render_cites(b["h2"], order)}</h2>')
    if b.get("h3"):
        out.append(f'<h3 class="g-h3">{render_cites(b["h3"], order)}</h3>')
    if b.get("warn"):
        out.append(f'<div class="g-warn">{render_cites(b["warn"], order)}</div>')
    for p in b.get("p", []):
        out.append(f'<p class="g-p">{render_cites(p, order)}</p>')
    if b.get("list"):
        tag = "ol" if b.get("ordered") else "ul"
        items = "".join(
            f'<li>{render_cites(i, order)}</li>' for i in b["list"])
        out.append(f'<{tag} class="g-list">{items}</{tag}>')
    if b.get("rows"):
        cap = (f'<caption class="g-tcap">{render_cites(b["caption"], order)}</caption>'
               if b.get("caption") else "")
        head = "".join(f"<th>{render_cites(c, order)}</th>" for c in b["head"])
        body = "".join(
            "<tr>" + "".join(f"<td>{render_cites(c, order)}</td>" for c in row) + "</tr>"
            for row in b["rows"])
        out.append(
            f'<div class="g-tablewrap"><table class="g-table">{cap}'
            f'<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')
    if b.get("callout"):
        out.append(f'<div class="g-callout">{render_cites(b["callout"], order)}</div>')
    if b.get("note"):
        out.append(f'<p class="g-note">{render_cites(b["note"], order)}</p>')
    return "\n".join(out)


def render_refs(order):
    items = []
    for n, k in enumerate(order, 1):
        r = R.cite(k)
        items.append(
            f'<li id="ref-{n}" class="g-ref">'
            f'<span class="g-ref-n">{n}</span>'
            f'<span class="g-ref-body">'
            f'<strong>{h(r["label"])}</strong>. {h(r["title"])}. '
            f'<em>{h(r["venue"])}</em><br>'
            f'<span class="g-ref-org">{h(r["org"])}</span> · '
            f'<a href="{h(r["url"])}" target="_blank" rel="noopener nofollow">원문 보기 ↗</a> · '
            f'<span class="g-ref-ver">{h(r["verified"])} 원문 확인</span>'
            f'</span></li>')
    return "\n".join(items)


# ---------------------------------------------------------------- LOOP

def build_loops(guides):
    """각 글에 prev/next(같은 종목)와 sibling(같은 시기)을 달아준다."""
    by_sport = {}
    for g in guides:
        by_sport.setdefault(g["sport"], []).append(g)
    order = {s: i for i, s in enumerate(STAGES)}
    loops = {}
    for sport, items in by_sport.items():
        items.sort(key=lambda g: order[g["stage"]])
        n = len(items)
        for i, g in enumerate(items):
            loops[g["id"]] = {
                "prev": items[(i - 1) % n] if n > 1 else None,
                "next": items[(i + 1) % n] if n > 1 else None,
                "series": items,
                "pos": i + 1,
                "total": n,
            }
    by_stage = {}
    for g in guides:
        by_stage.setdefault(g["stage"], []).append(g)
    for g in guides:
        loops[g["id"]]["siblings"] = [
            x for x in by_stage[g["stage"]] if x["sport"] != g["sport"]]
    return loops


def slug_of(g):
    return f"guide-{g['id']}.html"


def tag_slug(tag):
    return "guide-tag-" + TAG_INFO[tag]["slug"] + ".html"


MIN_TAG_ITEMS = 2

# 글이 이만큼 쌓이기 전까지 태그 페이지는 noindex 로 둔다.
#
# 이 사이트는 이미 수집은 됐지만 색인되지 않은 페이지가 많다. 항목이 몇 개뿐인
# 목록 페이지를 색인에 밀어 넣으면 그 숫자만 키우고 정작 본문 글의 평가에는
# 도움이 되지 않는다. noindex,follow 이므로 독자에게는 그대로 보이고
# 링크도 그대로 따라가며, 글이 INDEX_TAG_ITEMS 편을 넘으면 자동으로 풀린다.
INDEX_TAG_ITEMS = 6


def tag_count(tag, guides):
    return sum(1 for g in guides if tag in g["tags"])


def tag_indexable(tag, guides):
    return tag_count(tag, guides) >= INDEX_TAG_ITEMS


def live_tags(guides):
    """글이 MIN_TAG_ITEMS 편 이상인 태그만 돌려준다.

    내용이 거의 없는 목록 페이지를 만들면 검색엔진이 수집만 하고 색인하지
    않는 페이지가 늘어난다. 그래서 글이 쌓이기 전까지는 태그 페이지를
    만들지 않는다. 종목이 추가되면 자동으로 생긴다."""
    n = {t: 0 for t in TAG_INFO}
    for g in guides:
        for t in g["tags"]:
            n[t] += 1
    return [t for t in TAG_INFO if n[t] >= MIN_TAG_ITEMS]


# ---------------------------------------------------------------- 페이지

NAV = """<header class="site-header">
<div class="wrap header-inner">
<a href="index.html" class="wordmark">CALRANK</a>
<nav class="main-nav">
<a href="index.html" class="nav-link">캘린더</a>
<a href="regions.html" class="nav-link">지역별</a>
<a href="ranking.html" class="nav-link">대회랭킹</a>
<a href="guides.html" class="nav-link active">대회가이드</a>
<a href="column.html" class="nav-link">칼럼</a>
<a href="grade.html" class="nav-link">등급표</a>
<a href="myrank.html" class="nav-link">내 랭크</a>
<a href="contact.html" class="nav-contact-link">제휴문의</a>
</nav>
</div>
</header>"""

FOOT = """<footer class="site-footer">
<div class="wrap">
<p class="g-disclaimer">이 글은 국제 스포츠의학·영양학 공식 입장문과 체계적 문헌고찰을 근거로 정리했습니다.
글에 적힌 수치는 일반적인 성인 운동인을 기준으로 한 것이며, 개인의 건강 상태·복용 중인 약·기저질환에 따라
적절한 값이 달라집니다. 진단이나 처방을 대신하지 않습니다.
운동 중 또는 운동 후 흉통, 실신, 심한 호흡곤란, 지속되는 두근거림이 있으면 즉시 운동을 멈추고 진료를 받으세요.</p>
<p class="g-footlinks"><a href="guides.html">대회 가이드 전체</a> · <a href="grade-method.html">등급 산출 근거</a> · <a href="index.html">대회 캘린더</a></p>
</div>
</footer>"""


def head(title, desc, keywords, canonical, ld_blocks, robots=None):
    kw = ", ".join(keywords)
    robots_tag = f'\n<meta name="robots" content="{robots}">' if robots else ""
    lds = "\n".join(
        f'<script type="application/ld+json">{json.dumps(b, ensure_ascii=False)}</script>'
        for b in ld_blocks)
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{h(title)}</title>
<meta name="description" content="{h(desc)}">
<meta name="keywords" content="{h(kw)}">
<meta name="author" content="calrank">{robots_tag}
<meta property="og:type" content="article">
<meta property="og:site_name" content="칼랭크(CALRANK)">
<meta property="og:title" content="{h(title)}">
<meta property="og:description" content="{h(desc)}">
<meta property="og:image" content="{BASE}/og-image.png">
<meta property="og:url" content="{h(canonical)}">
<meta property="og:locale" content="ko_KR">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{h(title)}">
<meta name="twitter:description" content="{h(desc)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap" rel="stylesheet">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#0B0B0B">
<link rel="canonical" href="{h(canonical)}">
<link rel="stylesheet" href="style.css">
<link rel="stylesheet" href="guide.css">
{lds}
</head>
<body>
{NAV}"""


SHARE_JS = """<script>
(function(){
  var K="cfdf627cdfe54e49450a13c8ca8109aa";
  var SDK="https://t1.kakaocdn.net/kakao_js_sdk/2.8.3/kakao.min.js";
  var SRI="sha384-oroumrnFVE0xtgqyDZJARgERibXg2C28380uaUZz2kHDS5CR7tu20eGiOU6GkTpy";
  var url=location.href.split('#')[0];
  function tell(b,t){var o=b.textContent;b.textContent=t;setTimeout(function(){b.textContent=o;},1800);}
  var copy=document.querySelector('.g-sh-copy');
  if(copy)copy.addEventListener('click',function(){
    (navigator.clipboard?navigator.clipboard.writeText(url):Promise.reject())
      .then(function(){tell(copy,'주소를 복사했어요');})
      .catch(function(){tell(copy,'복사하지 못했어요');});
  });
  var nat=document.querySelector('.g-sh-native');
  if(nat){ if(!navigator.share){nat.style.display='none';}
    else nat.addEventListener('click',function(){
      navigator.share({title:document.title,url:url}).catch(function(){});
    });
  }
  var ka=document.querySelector('.g-sh-kakao');
  if(ka)ka.addEventListener('click',function(){
    function go(){
      try{
        if(!window.Kakao.isInitialized())window.Kakao.init(K);
        var link={webUrl:url,mobileWebUrl:url};
        window.Kakao.Share.sendDefault({objectType:'feed',
          content:{title:document.title,
            description:(document.querySelector('meta[name=description]')||{}).content||'',
            imageUrl:'https://calrank.vercel.app/og-image.png',link:link},
          buttons:[{title:'가이드 보기',link:link}]});
      }catch(e){tell(ka,'보내지 못했어요');}
    }
    if(window.Kakao)return go();
    var sc=document.createElement('script');
    sc.src=SDK;sc.integrity=SRI;sc.crossOrigin='anonymous';
    sc.onload=go;sc.onerror=function(){tell(ka,'보내지 못했어요');};
    document.head.appendChild(sc);
  });
})();
</script>"""


def build_toc(g):
    """소제목 목차. 긴 글에서 독자가 필요한 데로 바로 갈 수 있게."""
    items = [b["h2"] for b in g["blocks"] if b.get("h2")]
    if len(items) < 4:
        return "", {}
    ids = {}
    out = []
    for i, h in enumerate(items, 1):
        hid = f"s{i}"
        ids[h] = hid
        plain = re.sub(r"\{\{[^}]+\}\}", "", h)
        out.append(f'<li><a href="#{hid}">{h_esc(plain)}</a></li>')
    return (f'<nav class="g-toc"><p class="g-toc-t">이 글에서 다루는 것</p>'
            f'<ol class="g-toc-l">{"".join(out)}</ol></nav>'), ids


def h_esc(x):
    return html.escape(str(x), quote=True)


def build_share(g):
    return (
        '<section class="g-share">'
        '<p class="g-share-t">도움이 되었다면 같이 뛰는 분께도</p>'
        '<div class="g-share-row">'
        '<button type="button" class="g-sh-btn g-sh-kakao">카카오톡으로 보내기</button>'
        '<button type="button" class="g-sh-btn g-sh-copy">링크 복사</button>'
        '<button type="button" class="g-sh-btn g-sh-native">다른 앱으로 공유</button>'
        '</div></section>')


def build_related(g, guides, loops, limit=4):
    """태그가 겹치는 글을 관련 글로. 이전/다음에 이미 나온 글은 뺀다.

    앵커 텍스트에 글 제목을 그대로 써서 검색어가 링크에 실리게 한다.
    """
    lp = loops[g["id"]]
    shown = {g["id"]}
    for x in (lp["prev"], lp["next"]):
        if x:
            shown.add(x["id"])
    mine = set(g["tags"])
    scored = []
    for x in guides:
        if x["id"] in shown:
            continue
        overlap = len(mine & set(x["tags"]))
        if not overlap:
            continue
        scored.append((overlap, x["sport"] == g["sport"], x))
    scored.sort(key=lambda t: (-t[0], not t[1]))
    picks = [x for _, _, x in scored[:limit]]
    if not picks:
        return ""
    cards = "".join(
        f'<a class="g-rel" href="{slug_of(x)}">'
        f'<span class="g-rel-k" style="--c:{SPORTS[x["sport"]]["color"]}">'
        f'{h_esc(SPORTS[x["sport"]]["label"])} · {h_esc(STAGES[x["stage"]]["label"])}</span>'
        f'<span class="g-rel-t">{h_esc(x["title"])}</span></a>'
        for x in picks)
    return (f'<section class="g-rels"><h2 class="g-h2">이어서 읽으면 좋은 글</h2>'
            f'<div class="g-relgrid">{cards}</div></section>')


def build_guide_page(g, loops, today):
    order = validate(g)
    sp = SPORTS[g["sport"]]
    st = STAGES[g["stage"]]
    url = f"{BASE}/{slug_of(g)}"
    lp = loops[g["id"]]

    toc_html, toc_ids = build_toc(g)
    body = "\n".join(render_block(b, order, toc_ids) for b in g["blocks"])

    faq_html = ""
    if g.get("faq"):
        rows = "".join(
            f'<details class="g-faq"><summary>{render_cites(q, order)}</summary>'
            f'<div class="g-faq-a">{render_cites(a, order)}</div></details>'
            for q, a in g["faq"])
        faq_html = f'<h2 class="g-h2">자주 묻는 질문</h2>{rows}'

    who = ""
    if g.get("reader"):
        lis = "".join(f"<li>{h(x)}</li>" for x in g["reader"])
        who = (f'<div class="g-who"><p class="g-who-t">이런 분께 맞는 글입니다</p>'
               f'<ul>{lis}</ul></div>')

    live = live_tags(GUIDES)
    tags = "".join(
        f'<a class="g-tag" href="{tag_slug(t)}">#{h(t)}</a>'
        for t in g["tags"] if t in live)

    # ---- LOOP: 같은 종목 시리즈
    ser = "".join(
        f'<a class="g-serie{" is-now" if x["id"]==g["id"] else ""}" '
        f'href="{slug_of(x)}">'
        f'<span class="g-serie-n">{STAGES[x["stage"]]["short"]}</span>'
        f'<span class="g-serie-t">{h(x["short"])}</span></a>'
        for x in lp["series"])
    series_box = (
        f'<nav class="g-series" aria-label="{h(sp["label"])} 시리즈">'
        f'<p class="g-series-t">{h(sp["label"])} 가이드 · {lp["pos"]}/{lp["total"]}</p>'
        f'<div class="g-series-row">{ser}</div></nav>')

    # ---- LOOP: 같은 시기 다른 종목
    sib = ""
    if lp["siblings"]:
        cards = "".join(
            f'<a class="g-sib" href="{slug_of(x)}">'
            f'<span class="g-sib-sport" style="--c:{SPORTS[x["sport"]]["color"]}">'
            f'{h(SPORTS[x["sport"]]["label"])}</span>'
            f'<span class="g-sib-t">{h(x["short"])}</span></a>'
            for x in lp["siblings"])
        sib = (f'<section class="g-sibs"><h2 class="g-h2">같은 시기, 다른 종목</h2>'
               f'<p class="g-p">{h(st["label"])}에 챙길 것은 종목마다 다릅니다.</p>'
               f'<div class="g-sibgrid">{cards}</div></section>')

    # ---- LOOP: 이전/다음
    pn = ""
    if lp["prev"] and lp["next"]:
        pn = (f'<nav class="g-pn">'
              f'<a class="g-pn-a" href="{slug_of(lp["prev"])}">'
              f'<span class="g-pn-l">← 이전</span>'
              f'<span class="g-pn-t">{h(lp["prev"]["short"])}</span></a>'
              f'<a class="g-pn-a g-pn-next" href="{slug_of(lp["next"])}">'
              f'<span class="g-pn-l">다음 →</span>'
              f'<span class="g-pn-t">{h(lp["next"]["short"])}</span></a></nav>')

    refs_section = ("" if not order else
        '<section class="g-refs">\n<h2 class="g-h2">근거</h2>\n'
        '<p class="g-p">이 글에 적힌 수치는 아래 자료에서 그대로 가져온 것입니다. '
        '각 항목의 원문을 직접 열어 확인한 날짜를 함께 적어 두었습니다.</p>\n'
        '<ol class="g-reflist">\n' + render_refs(order) + '\n</ol>\n</section>')
    related = build_related(g, GUIDES, loops)
    share = build_share(g)
    _txt = re.sub(r"<[^>]+>", "", body)
    read_min = max(2, round(len(_txt) / 500))
    cta = (f'<div class="g-cta"><p class="g-cta-t">{h(g["cta"]["text"])}</p>'
           f'<a class="g-cta-b" href="{h(g["cta"]["href"])}">{h(g["cta"]["label"])} →</a></div>')

    ld = [
        {"@context": "https://schema.org", "@type": "Article",
         "headline": g["title"], "description": g["desc"],
         "datePublished": today, "dateModified": today,
         "inLanguage": "ko-KR",
         "keywords": ", ".join(g["keywords"]),
         "articleSection": sp["label"],
         "author": {"@type": "Organization", "name": "calrank", "url": BASE},
         "publisher": {"@type": "Organization", "name": "calrank",
                       "logo": {"@type": "ImageObject", "url": f"{BASE}/og-image.png"}},
         "mainEntityOfPage": {"@type": "WebPage", "@id": url},
         "citation": [
             {"@type": "CreativeWork", "name": R.cite(k)["title"],
              "url": R.cite(k)["url"]} for k in order]},
        {"@context": "https://schema.org", "@type": "BreadcrumbList",
         "itemListElement": [
             {"@type": "ListItem", "position": 1, "name": "calrank", "item": BASE},
             {"@type": "ListItem", "position": 2, "name": "대회 가이드",
              "item": f"{BASE}/guides.html"},
             {"@type": "ListItem", "position": 3, "name": sp["label"],
              "item": (f"{BASE}/{tag_slug(sp['tag'])}" if sp["tag"] in live
                       else f"{BASE}/guides.html#{g['sport']}")},
             {"@type": "ListItem", "position": 4, "name": g["title"], "item": url}]},
    ]
    if g.get("faq"):
        ld.append({
            "@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": CITE_RE.sub("", q),
                 "acceptedAnswer": {"@type": "Answer",
                                    "text": re.sub(r"<[^>]+>", "", CITE_RE.sub("", a))}}
                for q, a in g["faq"]]})

    return f"""{head(g['title'], g['desc'], g['keywords'], url, ld)}
<main class="g-wrap">
<nav class="g-crumb"><a href="index.html">calrank</a> › <a href="guides.html">대회 가이드</a> › <a href="{tag_slug(sp['tag']) if sp['tag'] in live else 'guides.html#' + g['sport']}">{h(sp['label'])}</a></nav>
<p class="g-kicker" style="--c:{sp['color']}">{h(sp['label'])} · {h(st['label'])}</p>
<h1 class="g-title">{h(g['title'])}</h1>
<p class="g-sub">{h(g['desc'])}</p>
<div class="g-tags">{tags}</div>
<div class="g-answer"><p class="g-answer-l">먼저 결론부터</p>{render_cites(g['answer'], order)}</div>
{who}
{toc_html}
{series_box}
<article class="g-body">
{body}
</article>
{faq_html}
{refs_section}
{related}
{share}
{sib}
{cta}
{pn}
<p class="g-updated">{today} 기준 · 읽는 데 약 {read_min}분</p>
</main>
{FOOT}
{SHARE_JS}
</body>
</html>"""


def build_tag_page(tag, guides, today):
    info = TAG_INFO[tag]
    url = f"{BASE}/{tag_slug(tag)}"
    items = [g for g in guides if tag in g["tags"]]
    order_idx = {s: i for i, s in enumerate(STAGES)}
    items.sort(key=lambda g: (g["sport"], order_idx[g["stage"]]))
    cards = "".join(
        f'<a class="g-card" href="{slug_of(g)}">'
        f'<span class="g-card-k" style="--c:{SPORTS[g["sport"]]["color"]}">'
        f'{h(SPORTS[g["sport"]]["label"])} · {h(STAGES[g["stage"]]["label"])}</span>'
        f'<span class="g-card-t">{h(g["title"])}</span>'
        f'<span class="g-card-d">{h(g["desc"])}</span></a>'
        for g in items)
    others = "".join(
        f'<a class="g-tag" href="{tag_slug(t)}">#{h(t)}</a>'
        for t in live_tags(guides) if t != tag)
    ld = [
        {"@context": "https://schema.org", "@type": "CollectionPage",
         "name": info["title"], "description": info["desc"],
         "inLanguage": "ko-KR", "url": url,
         "mainEntity": {"@type": "ItemList", "numberOfItems": len(items),
                        "itemListElement": [
                            {"@type": "ListItem", "position": i,
                             "url": f"{BASE}/{slug_of(g)}", "name": g["title"]}
                            for i, g in enumerate(items, 1)]}},
        {"@context": "https://schema.org", "@type": "BreadcrumbList",
         "itemListElement": [
             {"@type": "ListItem", "position": 1, "name": "calrank", "item": BASE},
             {"@type": "ListItem", "position": 2, "name": "대회 가이드",
              "item": f"{BASE}/guides.html"},
             {"@type": "ListItem", "position": 3, "name": info["title"], "item": url}]},
    ]
    robots = None if tag_indexable(tag, guides) else "noindex,follow"
    return f"""{head(info['title'], info['desc'], info['keywords'], url, ld, robots)}
<main class="g-wrap">
<nav class="g-crumb"><a href="index.html">calrank</a> › <a href="guides.html">대회 가이드</a> › #{h(tag)}</nav>
<h1 class="g-title">{h(info['title'])}</h1>
<p class="g-sub">{h(info['desc'])}</p>
<p class="g-count">{len(items)}편</p>
<div class="g-cards">{cards}</div>
<section class="g-othertags">
<h2 class="g-h2">다른 주제도 보기</h2>
<div class="g-tags">{others}</div>
</section>
<div class="g-cta"><p class="g-cta-t">기록을 가지고 계신가요? 어느 수준인지 먼저 확인해 보세요.</p>
<a class="g-cta-b" href="level.html">내 기록 등급 확인하기 →</a></div>
</main>
{FOOT}
</body>
</html>"""


def build_hub(guides, today):
    url = f"{BASE}/guides.html"
    order_idx = {s: i for i, s in enumerate(STAGES)}
    secs = []
    for sport, sp in SPORTS.items():
        items = sorted([g for g in guides if g["sport"] == sport],
                       key=lambda g: order_idx[g["stage"]])
        if not items:
            continue
        cards = "".join(
            f'<a class="g-card" href="{slug_of(g)}">'
            f'<span class="g-card-k" style="--c:{sp["color"]}">{h(STAGES[g["stage"]]["label"])}</span>'
            f'<span class="g-card-t">{h(g["title"])}</span>'
            f'<span class="g-card-d">{h(g["desc"])}</span></a>'
            for g in items)
        secs.append(
            f'<section class="g-hubsec" id="{sport}">'
            f'<h2 class="g-h2" style="--c:{sp["color"]}">{h(sp["label"])}</h2>'
            f'<p class="g-p">{h(sp["blurb"])}</p>'
            f'<div class="g-cards">{cards}</div></section>')

    # 시기 축 안내 — 독자 여정
    journey = "".join(
        f'<div class="g-journey-i"><span class="g-journey-n">{h(st["short"])}</span>'
        f'<span class="g-journey-t">{h(st["label"])}</span>'
        f'<span class="g-journey-d">{h(st["blurb"])}</span></div>'
        for st in STAGES.values())

    tags = "".join(f'<a class="g-tag" href="{tag_slug(t)}">#{h(t)}</a>'
                   for t in live_tags(guides))

    ld = [{"@context": "https://schema.org", "@type": "CollectionPage",
           "name": "대회 가이드 — 준비부터 완주·회복까지", "url": url, "inLanguage": "ko-KR",
           "description": "마라톤·트레일러닝·철인3종·자전거·인라인 대회를 "
                          "준비하고 완주하고 회복하기까지, 국제 스포츠의학 근거로 정리한 가이드.",
           "mainEntity": {"@type": "ItemList", "numberOfItems": len(guides),
                          "itemListElement": [
                              {"@type": "ListItem", "position": i,
                               "url": f"{BASE}/{slug_of(g)}", "name": g["title"]}
                              for i, g in enumerate(guides, 1)]}}]
    return f"""{head('대회 가이드 — 준비부터 완주·회복까지 | calrank',
                     '마라톤·트레일러닝·철인3종·자전거·인라인 대회 준비물, 대회 전날과 당일 식사, '
                     '수분 보충, 완주 후 근육통 회복까지. 국제 스포츠의학·영양학 공식 입장문을 근거로 정리했습니다.',
                     ['대회 준비','마라톤 준비','마라톤 준비물','대회 당일 식사','마라톤 회복',
                      '트레일러닝 준비물','철인3종 준비','자전거대회 준비','인라인대회 준비'],
                     url, ld)}
<main class="g-wrap">
<nav class="g-crumb"><a href="index.html">calrank</a> › 대회 가이드</nav>
<h1 class="g-title">대회 가이드</h1>
<p class="g-sub">신청해 놓고 나면 그때부터 찾아볼 게 많아집니다. 뭘 먹어야 하는지, 뭘 챙겨야 하는지,
끝나고 나서 다리가 왜 이렇게 아픈지. 그때그때 검색하지 않아도 되도록 시기별로 정리해 두었습니다.</p>
<div class="g-evidence-badge">이 가이드의 수치는 미국스포츠의학회(ACSM) 공식 입장문,
국제 저나트륨혈증 합의문, 코크란 문헌고찰 등 국제 학술자료에서 직접 가져왔습니다.
각 글 아래에 원문 링크와 확인 날짜를 적어 두었습니다.</div>
<section class="g-journey">
<h2 class="g-h2">대회까지 남은 시간에 따라</h2>
<div class="g-journey-row">{journey}</div>
</section>
{''.join(secs)}
<section class="g-othertags">
<h2 class="g-h2">주제로 찾기</h2>
<div class="g-tags">{tags}</div>
</section>
<div class="g-cta"><p class="g-cta-t">대회부터 고르시겠어요?</p>
<a class="g-cta-b" href="index.html">전국 대회 캘린더 보기 →</a></div>
</main>
{FOOT}
</body>
</html>"""


def update_sitemap(slugs, dropped, today):
    """새 글을 sitemap 에 넣고, 내려간 페이지는 뺀다."""
    path = ROOT / "sitemap.xml"
    if not path.exists():
        print("  sitemap.xml 없음 — 건너뜁니다.")
        return 0, 0
    xml = path.read_text(encoding="utf-8")

    removed = 0
    for slug in dropped:
        pat = re.compile(
            r"\s*<url>\s*<loc>" + re.escape(f"{BASE}/{slug}") + r"</loc>.*?</url>", re.S)
        xml, n = pat.subn("", xml)
        removed += n

    added = ""
    count = 0
    for slug in slugs:
        loc = f"{BASE}/{slug}"
        if f"<loc>{loc}</loc>" in xml:
            continue
        prio = "0.8" if slug.startswith("guide-") and "-tag-" not in slug else "0.7"
        added += ("  <url>\n"
                  f"    <loc>{loc}</loc>\n"
                  f"    <lastmod>{today}</lastmod>\n"
                  "    <changefreq>monthly</changefreq>\n"
                  f"    <priority>{prio}</priority>\n"
                  "  </url>\n")
        count += 1
    if (added or removed) and "</urlset>" in xml:
        path.write_text(xml.replace("</urlset>", added + "</urlset>"), encoding="utf-8")
    return count, removed


def main():
    check_only = "--check" in sys.argv
    today = datetime.now(KST).strftime("%Y-%m-%d")

    ids = [g["id"] for g in GUIDES]
    if len(ids) != len(set(ids)):
        raise ValueError(f"중복된 id 가 있습니다: {[i for i in ids if ids.count(i)>1]}")
    for g in GUIDES:
        if g["sport"] not in SPORTS:
            raise ValueError(f"[{g['id']}] 알 수 없는 종목: {g['sport']}")
        if g["stage"] not in STAGES:
            raise ValueError(f"[{g['id']}] 알 수 없는 시기: {g['stage']}")
        for t in g["tags"]:
            if t not in TAG_INFO:
                raise ValueError(f"[{g['id']}] 등록되지 않은 태그: {t}")

    _GUIDE_IDS.update(g["id"] for g in GUIDES)
    loops = build_loops(GUIDES)
    written = []

    for g in GUIDES:
        used = validate(g)
        page = build_guide_page(g, loops, today)
        if not check_only:
            (ROOT / slug_of(g)).write_text(page, encoding="utf-8")
        written.append((slug_of(g), len(page), len(used)))

    for tag in live_tags(GUIDES):
        page = build_tag_page(tag, GUIDES, today)
        if not check_only:
            (ROOT / tag_slug(tag)).write_text(page, encoding="utf-8")
        written.append((tag_slug(tag), len(page), 0))

    # 더 이상 유효하지 않은 태그 페이지는 지운다 (예전 실행에서 남은 빈 페이지)
    keep = {tag_slug(t) for t in live_tags(GUIDES)}
    removed = []
    for old in ROOT.glob("guide-tag-*.html"):
        if old.name not in keep:
            removed.append(old.name)
            if not check_only:
                old.unlink()
    if removed:
        print(f"  (정리) 글이 부족해 내린 태그 페이지: {', '.join(sorted(removed))}")

    hub = build_hub(GUIDES, today)
    if not check_only:
        (ROOT / "guides.html").write_text(hub, encoding="utf-8")
    written.append(("guides.html", len(hub), 0))

    # ---- LOOP 검사: 모든 글이 들어오는 링크와 나가는 링크를 갖는가
    inbound = {g["id"]: 0 for g in GUIDES}
    for g in GUIDES:
        lp = loops[g["id"]]
        for x in [lp["prev"], lp["next"]] + lp["siblings"]:
            if x:
                inbound[x["id"]] += 1
    orphan = [k for k, v in inbound.items() if v == 0]
    if orphan:
        raise ValueError(f"들어오는 링크가 없는 글: {orphan}")

    if not check_only:
        noindexed = {tag_slug(t) for t in live_tags(GUIDES)
                     if not tag_indexable(t, GUIDES)}
        slugs = [n for n, _, _ in written if n not in noindexed]
        removed = list(removed) + sorted(noindexed)
        if noindexed:
            print(f"  (색인 보류) 글이 {INDEX_TAG_ITEMS}편 미만인 태그 페이지 "
                  f"{len(noindexed)}개는 noindex 로 두고 sitemap 에서 뺐습니다.")
        n_add, n_del = update_sitemap(slugs, removed, today)
        print(f"  sitemap.xml — {n_add}개 추가, {n_del}개 제거")

    print(f"{'생성' if not check_only else '검증'} 완료 — {len(written)}개 파일")
    for name, size, nref in sorted(written):
        print(f"  {name:46} {size:7,}B  근거 {nref}건")
    print(f"\n글 {len(GUIDES)}편 · 태그 {len(TAG_INFO)}개 · 모든 글에 들어오는 링크 확인됨")
    return 0


if __name__ == "__main__":
    sys.exit(main())

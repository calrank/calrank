#!/usr/bin/env python3
"""근거 기반 러닝 칼럼을 하나씩 발행한다.

scripts/science_columns.json 에 쌓아 둔 글을 한 번 실행에 한 편씩 꺼내 쓴다.
한꺼번에 올리면 그날 하루 반짝하고 끝나지만, 하나씩 내보내면 색인이 꾸준히
늘고 칼럼 목록도 계속 갱신된다.

이 칼럼들의 전제는 하나다 — 몸에 관한 주장은 전부 PubMed 에서 확인 가능한
논문에 붙어 있어야 한다. 그래서 본문의 각 주장에 참고문헌 번호를 달고,
글 끝에 PMID 링크를 그대로 노출한다. 출처 없이 쓸 수 있는 문장은
"연구에서 확인된 것"이 아니라 "일반적으로 그렇게 이해한다" 정도로만 쓴다.
"""

import json
import re
import html as html_mod
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KST = timezone(timedelta(hours=9))

BANK_PATH = "scripts/science_columns.json"
STATE_PATH = "scripts/science_column_state.json"
SITE = "https://calrank.vercel.app"


def esc(t):
    return html_mod.escape(str(t if t is not None else ""), quote=True)


def load_json(path, default):
    p = ROOT / path
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(path, data):
    (ROOT / path).write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


# ── 본문 조립 ────────────────────────────────────────────────────────────
def render_refs(ref_ids, refs):
    """참고문헌. PMID 를 그대로 링크해 독자가 직접 원문을 확인할 수 있게 한다."""
    items = []
    for i, rid in enumerate(ref_ids, 1):
        r = refs.get(rid)
        if not r:
            continue
        items.append(
            f'<li id="ref{i}"><span class="ref-n">[{i}]</span> '
            f'{esc(r["authors"])} ({esc(r["year"])}). {esc(r["title"])} '
            f'<em>{esc(r["journal"])}</em>. '
            f'<a href="https://pubmed.ncbi.nlm.nih.gov/{esc(r["pmid"])}/" '
            f'target="_blank" rel="noopener nofollow">PMID {esc(r["pmid"])}</a></li>'
        )
    if not items:
        return ""
    return (
        '<h2 id="refs">참고문헌</h2>\n'
        '<p class="ref-note">아래 논문은 모두 PubMed 에서 원문 정보를 확인할 수 있습니다. '
        '번호를 본문의 <sup>[n]</sup> 표시와 맞춰 두었습니다.</p>\n'
        '<ol class="ref-list">\n' + "\n".join(items) + "\n</ol>"
    )


def render_body(article, refs):
    out = []
    out.append(f'<p class="col-lead">{article["lead"]}</p>')

    for sec in article.get("sections", []):
        out.append(f'<h2>{esc(sec["h2"])}</h2>')
        for para in sec.get("paras", []):
            out.append(f"<p>{para}</p>")
        if sec.get("list"):
            out.append("<ul class='col-ul'>")
            for li in sec["list"]:
                out.append(f"<li>{li}</li>")
            out.append("</ul>")
        if sec.get("table"):
            t = sec["table"]
            out.append('<div class="col-table-wrap"><table class="col-table">')
            out.append("<tr>" + "".join(f"<th>{esc(h)}</th>" for h in t["head"]) + "</tr>")
            for row in t["rows"]:
                out.append("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>")
            out.append("</table></div>")
        if sec.get("note"):
            out.append(f'<p class="col-note">{sec["note"]}</p>')

    if article.get("faq"):
        out.append("<h2>자주 묻는 질문</h2>")
        for f in article["faq"]:
            out.append(f'<p class="col-q">{esc(f["q"])}</p>')
            out.append(f'<p class="col-a">{f["a"]}</p>')

    out.append(render_refs(article.get("refs", []), refs))
    return "\n".join(x for x in out if x)


def render_jsonld(article, today_iso):
    url = f'{SITE}/{article["slug"]}'
    blocks = [{
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": article["title"],
        "description": article["description"],
        "inLanguage": "ko-KR",
        "datePublished": today_iso,
        "dateModified": today_iso,
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "author": {"@type": "Organization", "name": "calrank"},
        "publisher": {"@type": "Organization", "name": "calrank",
                      "url": SITE + "/"},
        "keywords": ", ".join(article.get("keywords", [])),
    }]
    if article.get("faq"):
        blocks.append({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": f["q"],
                 "acceptedAnswer": {"@type": "Answer",
                                    "text": re.sub(r"<[^>]+>", "", f["a"])}}
                for f in article["faq"]
            ],
        })
    return "\n".join(
        '<script type="application/ld+json">' +
        json.dumps(b, ensure_ascii=False, separators=(",", ":")) + "</script>"
        for b in blocks
    )


PAGE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — calrank</title>
<meta name="description" content="{desc}">
<meta name="keywords" content="{keywords}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{site}/og-image.png">
<meta property="og:locale" content="ko_KR">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap" rel="stylesheet">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="stylesheet" href="style.css">
{jsonld}
<style>
  .column-wrap {{ max-width: 720px; margin: 0 auto; padding: 44px 20px 80px; }}
  .column-meta {{ font-size: 13px; color: var(--ink-faint, #6A6A6A); margin-bottom: 12px; }}
  .column-title {{ font-family: var(--font-display); font-size: clamp(25px, 4vw, 36px); line-height: 1.32; margin-bottom: 20px; }}
  .column-body {{ font-size: 16px; line-height: 1.95; color: #E8E4E1; }}
  .column-body h2 {{ font-size: 21px; margin: 44px 0 14px; color: #fff; line-height: 1.4; }}
  .column-body p {{ margin-bottom: 18px; }}
  .column-body strong {{ color: #fff; }}
  .col-lead {{ font-size: 17px; line-height: 1.9; color: #C9C3BF; padding: 18px 20px; background: var(--surface,#141414); border-left: 3px solid var(--accent); border-radius: 2px; }}
  .col-ul {{ padding-left: 20px; margin: 0 0 18px; }}
  .col-ul li {{ margin-bottom: 9px; }}
  .col-note {{ font-size: 13.5px; line-height: 1.8; color: #9A9A9A; padding: 13px 15px; background: rgba(255,255,255,.03); border: 1px solid var(--border,#2A2A2A); border-radius: 2px; }}
  .col-q {{ font-weight: 700; color: #fff; margin-bottom: 7px; }}
  .col-a {{ color: #C9C3BF; }}
  .col-table-wrap {{ overflow-x: auto; margin-bottom: 20px; }}
  .col-table {{ width: 100%; border-collapse: collapse; font-size: 14px; min-width: 460px; }}
  .col-table th, .col-table td {{ padding: 10px 12px; border-bottom: 1px solid var(--border,#2A2A2A); text-align: left; vertical-align: top; }}
  .col-table th {{ color: #fff; background: rgba(255,255,255,.03); white-space: nowrap; }}
  .ref-note {{ font-size: 13px; color: #8E8884; }}
  .ref-list {{ padding-left: 20px; font-size: 13.5px; line-height: 1.85; color: #A9A29E; }}
  .ref-list li {{ margin-bottom: 11px; }}
  .ref-list a {{ color: #C9C3BF; }}
  .ref-n {{ color: var(--accent); font-weight: 700; margin-right: 4px; }}
  .col-evidence {{ margin: 26px 0 0; padding: 14px 16px; border: 1px solid var(--border,#2A2A2A); border-radius: 2px; font-size: 13px; line-height: 1.8; color: #9A9A9A; }}
  sup a {{ color: var(--accent); text-decoration: none; }}
  @media (max-width:600px) {{
    .column-wrap {{ padding: 32px 16px 64px; }}
    .column-body {{ font-size: 15.5px; }}
    .col-lead {{ font-size: 15.5px; padding: 15px 16px; }}
  }}
</style>
</head>
<body>

<header class="site-header">
<div class="wrap header-inner">
<a href="index.html" class="wordmark">CALRANK</a>
<nav class="main-nav">
<a href="index.html" class="nav-link">캘린더</a>
<a href="ranking.html" class="nav-link">대회랭킹</a>
<a href="news.html" class="nav-link">종목뉴스</a>
<a href="column.html" class="nav-link active">칼럼</a>
<a href="grade.html" class="nav-link">등급표</a>
<a href="myrank.html" class="nav-link">내 랭크</a>
<a href="contact.html" class="nav-contact-link">제휴문의</a>
</nav>
</div>
</header>

<main class="column-wrap">
<p class="column-meta">🔬 근거 기반 칼럼 · {date_ko}</p>
<h1 class="column-title">{title}</h1>

<div class="column-body">
{body}

<p class="col-evidence">이 글의 신체 변화에 관한 서술은 위 참고문헌의 체계적 문헌고찰·메타분석에 근거합니다.
다만 운동에 대한 몸의 반응은 주행거리·강도·나이·성별·기존 체력·식사·수면·유전에 따라 크게 다르며,
특정 거리나 기간이 특정 변화를 보장하지 않습니다. 이 글은 의학적 진단이나 처방이 아니며,
통증이나 지병이 있다면 전문의와 상의하세요.</p>

<div style="margin-top:30px;">
<a href="cert.html" class="cert-cta" style="margin-top:0;">
<span class="cc-ico">📷</span>
<span class="cc-txt"><b>기록증 사진 한 장으로 내 러닝 등급 확인</b><span>완주 시간을 읽어 나이·성별을 보정한 등급과 다음 목표까지 남은 시간을 알려드립니다. 로그인도 타이핑도 필요 없습니다.</span></span>
<span class="cc-go">바로 확인 →</span>
</a>
<a href="grade.html" class="cert-cta">
<span class="cc-ico">📊</span>
<span class="cc-txt"><b>거리별 러닝 등급표 — 5km · 10km · 하프 · 풀</b><span>나이별·성별로 내 기록이 어느 칸인지 표에서 바로 찾을 수 있습니다.</span></span>
<span class="cc-go">등급표 →</span>
</a>
</div>

<div class="column-tags">
{tags}
</div>
</div>
</main>

<footer class="site-footer">
<div class="wrap">
<p>calrank는 대회 주최측이 공개한 일정 정보를 정리해 제공합니다. 이 칼럼은 공개된 학술 문헌을 바탕으로 작성했으며 의학적 조언이 아닙니다.</p>
<p class="footer-links"><a href="terms.html">이용약관</a> · <a href="privacy.html">개인정보처리방침</a> · <a href="contact.html">제휴·광고 문의</a></p>
</div>
</footer>

<script defer src="/_vercel/insights/script.js"></script>
</body>
</html>
"""


def build_page(article, refs, now_kst):
    tags = "\n".join(
        f'<a href="column.html" class="column-tag">#{esc(k.replace(" ", ""))}</a>'
        for k in article.get("keywords", [])[:6]
    )
    return PAGE.format(
        title=esc(article["title"]),
        desc=esc(article["description"]),
        keywords=esc(", ".join(article.get("keywords", []))),
        url=f'{SITE}/{article["slug"]}',
        site=SITE,
        jsonld=render_jsonld(article, now_kst.strftime("%Y-%m-%d")),
        date_ko=now_kst.strftime("%Y년 %-m월 %-d일"),
        body=render_body(article, refs),
        tags=tags,
    )


# ── 목록·사이트맵 갱신 (generate_column.py 와 같은 자리에 끼워 넣는다) ──
def update_column_list(article, date_ko):
    path = ROOT / "column.html"
    if not path.exists():
        return False
    html = path.read_text(encoding="utf-8")
    card = (
        f'<a href="{article["slug"]}" class="column-card">\n'
        f'<p class="column-card-meta">🔬 근거 기반 · {date_ko}</p>\n'
        f'<p class="column-card-title">{esc(article["title"])}</p>\n'
        f'<p class="column-card-desc">{esc(article["description"])}</p>\n'
        f'</a>\n\n'
    )
    marker = '<div style="margin-top:24px;" id="columnCardsContainer">\n\n'
    if marker not in html or article["slug"] in html:
        return False
    path.write_text(html.replace(marker, marker + card), encoding="utf-8")
    return True


def update_sitemap(slug):
    path = ROOT / "sitemap.xml"
    if not path.exists():
        return False
    xml = path.read_text(encoding="utf-8")
    entry = (
        f"  <url>\n"
        f"    <loc>{SITE}/{slug}</loc>\n"
        f"    <changefreq>monthly</changefreq>\n"
        f"    <priority>0.7</priority>\n"
        f"  </url>\n"
    )
    if "</urlset>" not in xml or slug in xml:
        return False
    path.write_text(xml.replace("</urlset>", entry + "</urlset>"), encoding="utf-8")
    return True


def main():
    bank = load_json(BANK_PATH, {})
    refs = bank.get("references", {})
    articles = bank.get("articles", [])
    state = load_json(STATE_PATH, {"published": []})
    published = set(state.get("published", []))

    pending = [a for a in articles if a["slug"] not in published]
    if not pending:
        print("[science-column] 대기 중인 글이 없습니다. science_columns.json 에 추가하세요.")
        return

    article = pending[0]
    now_kst = datetime.now(KST)
    date_ko = now_kst.strftime("%Y년 %-m월 %-d일")

    missing = [r for r in article.get("refs", []) if r not in refs]
    if missing:
        raise SystemExit(f"[science-column] 참고문헌 정의 없음: {missing}")

    (ROOT / article["slug"]).write_text(
        build_page(article, refs, now_kst), encoding="utf-8"
    )
    listed = update_column_list(article, date_ko)
    mapped = update_sitemap(article["slug"])

    state.setdefault("published", []).append(article["slug"])
    save_json(STATE_PATH, state)

    print(f"[science-column] {article['slug']} 발행 "
          f"(목록 {'o' if listed else 'x'} / 사이트맵 {'o' if mapped else 'x'}) "
          f"· 남은 글 {len(pending) - 1}편")


if __name__ == "__main__":
    main()

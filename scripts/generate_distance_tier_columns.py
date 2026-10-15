"""거리별 '내 기록은 어느 수준일까' 칼럼을 만든다.

column-10km-age-gender-tier.html 한 장이 네이버 노출의 약 75%를 만들고 있다
(162클릭 / 4,176노출). 같은 질문을 5km·하프·풀코스로도 던지는 사람이 있는데
그 페이지가 없었다. 10km 페이지와 같은 출처(Running Level)·같은 구조로
세 거리를 추가한다.

10km 페이지는 이미 잘 돌고 있으므로 다시 만들지 않는다. 다른 거리로 가는
링크만 끼워 넣는다.

표의 숫자는 지어내지 않는다. Running Level 공개 데이터를 그대로 옮겼고,
10km 값을 이미 올라가 있는 페이지와 대조해 일치를 확인했다.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from site_nav import site_header  # noqa: E402
from distance_tier_data import DECADES, TIER_TABLES, DIST_COPY  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://calrank.vercel.app"
TIER_NAMES = ["비기너", "노비스", "인터미디엇", "어드밴스드", "엘리트"]

# 10km 은 이미 있는 페이지를 쓴다. 링크 묶음에는 함께 넣는다.
SERIES = [
    ("5km", "5km", "column-5km-age-gender-tier.html"),
    ("10km", "10km", "column-10km-age-gender-tier.html"),
    ("half", "하프마라톤", "column-half-age-gender-tier.html"),
    ("full", "풀코스", "column-full-age-gender-tier.html"),
]


def esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def tier_table(dist: str, gender: str) -> str:
    head = ("<tr><th>나이대</th>"
            + "".join(f'<th{" class=\"tc-elite\"" if n == "엘리트" else ""}>{n}</th>'
                      for n in TIER_NAMES)
            + "</tr>")
    rows = []
    for i, dec in enumerate(DECADES):
        vals = TIER_TABLES[(dist, gender)][i]
        cells = "".join(
            f'<td{" class=\"tc-elite\"" if k == 4 else ""}>{v}</td>'
            for k, v in enumerate(vals))
        rows.append(f"<tr><td>{dec}</td>{cells}</tr>")
    return ('<div class="table-scroll">\n<table class="tier-data-table">\n'
            + head + "\n" + "\n".join(rows) + "\n</table>\n</div>")


def series_links(current: str) -> str:
    """거리끼리 서로 닿게 한다. 같은 질문을 다른 거리로 하는 사람이 많다."""
    items = []
    for key, name, slug in SERIES:
        if key == current:
            items.append(f'<strong style="color:var(--ink,#fff);">{name}</strong>')
        else:
            items.append(f'<a href="{slug}" style="color:var(--accent,#FF3D1A);">{name}</a>')
    return ('<p style="font-size:13.5px;line-height:1.9;color:var(--ink-soft,#9A9A9A);'
            'margin:28px 0 0;padding-top:18px;border-top:1px solid var(--border,#2A2A2A);">'
            '다른 거리의 등급표 · ' + " · ".join(items) + "</p>")


def build(dist: str) -> tuple[str, str, str, str]:
    c = DIST_COPY[dist]
    slug = f"column-{c['slug']}-age-gender-tier.html"
    title = f"{c['title']} | calrank"
    desc = c["desc"]
    tags = "".join(
        f'<a href="{href}" class="column-tag">{t}</a>\n'
        for href, t in [
            ("index.html?sport=marathon", f"#{c['nav_name'].replace(' ', '')}"),
            ("column.html", "#러닝등급표"), ("column.html", "#나이별기록"),
            ("column.html", "#20대러닝"), ("column.html", "#30대러닝"),
            ("column.html", "#40대러닝"), ("column.html", "#50대러닝"),
            ("column.html", "#60대러닝"),
            ("column.html", f"#남자{c['label']}기록"),
            ("column.html", f"#여자{c['label']}기록"),
            ("myrank.html", "#내랭크"),
        ])
    why = "\n".join(f"<p>{esc(p)}</p>" for p in c["why"])

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta property="og:type" content="article">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{SITE}/og-image.png">
<meta property="og:url" content="{SITE}/{slug}">
<meta property="og:locale" content="ko_KR">
<link rel="canonical" href="{SITE}/{slug}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Black+Han+Sans&family=Noto+Sans+KR:wght@400;500;700;900&display=swap" rel="stylesheet">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="stylesheet" href="style.css">
<style>
  .column-wrap {{ max-width: 760px; margin: 0 auto; padding: 48px 20px 80px; }}
  .column-meta {{ font-size: 13px; color: var(--ink-faint, #6A6A6A); margin-bottom: 12px; }}
  .column-title {{ font-family: var(--font-display); font-size: clamp(24px, 3.8vw, 36px); line-height: 1.3; margin-bottom: 20px; }}
  .column-body {{ font-size: 16px; line-height: 1.9; color: #E8E4E1; }}
  .column-body h2 {{ font-size: 20px; margin: 36px 0 12px; color: #fff; }}
  .column-body p {{ margin-bottom: 16px; }}
  .column-tags {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 16px 0 24px; }}
  .column-tag {{ font-size: 12px; padding: 5px 12px; border: 1px solid var(--border, #2A2A2A); border-radius: 999px; color: #B8B0AC; text-decoration: none; }}
  .column-tag:hover {{ border-color: var(--accent); color: #fff; }}
  .source-box {{ background: var(--surface, #141414); border: 1px solid var(--border, #2A2A2A); border-radius: 10px; padding: 18px 20px; margin: 20px 0 28px; font-size: 13px; line-height: 1.8; color: #B8B0AC; }}
  .source-box strong {{ color: #fff; }}
  .tier-data-table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin: 16px 0 28px; }}
  .tier-data-table th, .tier-data-table td {{ padding: 8px 6px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.08); }}
  .tier-data-table th {{ color: #fff; font-weight: 700; background: rgba(255,255,255,0.03); }}
  .tier-data-table td:first-child, .tier-data-table th:first-child {{ text-align: left; color: #fff; font-weight: 600; }}
  .tier-data-table .tc-elite {{ color: #c9a6ff; font-weight: 700; }}
  .table-scroll {{ overflow-x: auto; }}
  .column-cta {{ margin-top: 32px; padding: 22px; background: var(--surface, #141414); border-radius: 10px; text-align: center; }}
  .column-cta a {{ display: inline-block; margin-top: 10px; background: var(--accent); color: #fff; font-weight: 700; padding: 12px 26px; border-radius: 6px; text-decoration: none; }}
</style>
</head>
<body>

{site_header("column")}

<main class="column-wrap">
<p class="column-meta">📊 데이터 분석 · 러닝 가이드</p>
<h1 class="column-title">{esc(c['h1'])}</h1>

<div class="column-tags">
{tags}</div>

<div class="column-body">
<p>{esc(c['lead'])}</p>

<a href="level.html" class="cert-cta" style="margin:18px 0 22px;">
<span class="cc-ico">🧮</span>
<span class="cc-txt"><b>표에서 찾기 전에 — 기록을 넣으면 바로 알려드립니다</b><span>완주 시간과 나이만 넣으면 내 등급, 다음 등급까지 남은 시간, 다른 거리 환산 기록까지 나옵니다. 결과는 이미지로 저장해 공유할 수 있습니다. 로그인 없이 바로.</span></span>
<span class="cc-go">계산하기 →</span>
</a>

<div class="source-box">
<strong>📌 이 칼럼의 출처</strong><br>
· <strong>누가</strong>: Running Level(Strength Level 산하 러닝 데이터 분석 플랫폼)<br>
· <strong>언제</strong>: 2024년 집계 데이터<br>
· <strong>어디서</strong>: runninglevel.com 공개 데이터베이스<br>
· <strong>무엇을</strong>: 대규모 실제 {esc(c['label'])} 레이스 완주기록을 나이·성별로 나눈 5단계(비기너~엘리트) 백분위 등급 기준<br>
· <strong>어떻게</strong>: 상위 5%/20%/50%/80%/95% 컷오프 라인을 나이·성별 구간별로 산출<br>
· <strong>왜</strong>: 개인이 절대 기록이 아닌 나이·성별 대비 상대적 위치를 객관적으로 확인할 수 있도록<br><br>
· 보강 자료: Lepers, R., Bagley, A. &amp; Stapley, P. (2021). <em>Sub 3-Hour Marathon Runners for Five Consecutive Decades Demonstrate a Reduced Age-Related Decline in Performance</em>. Frontiers in Physiology. (지구력 러닝 능력은 25~35세에 정점을 찍고, 50대 후반까지 10년마다 약 6~7% 감소한다는 연구)
</div>

<h2>등급은 이렇게 나뉩니다</h2>
<p>Running Level의 5단계 정의는 다음과 같습니다. 각 등급 "시간"은 그 등급에 속하기 위한 최소 기준선(컷오프)입니다.</p>
<div class="table-scroll">
<table class="tier-data-table">
<tr><th>등급</th><th>정의</th></tr>
<tr><td>비기너</td><td>전체 러너 중 상위 95%(하위권) — 러닝을 시작한 지 1개월 이상</td></tr>
<tr><td>노비스</td><td>상위 80% — 6개월 이상 꾸준히 러닝</td></tr>
<tr><td>인터미디엇</td><td>상위 50%(중앙값) — 2년 이상 꾸준히 러닝</td></tr>
<tr><td>어드밴스드</td><td>상위 20% — 5년 이상 러닝</td></tr>
<tr><td class="tc-elite">엘리트</td><td class="tc-elite">상위 5% — 5년 이상 경쟁력 있는 수준을 목표로 훈련</td></tr>
</table>
</div>

<h2>남성 {esc(c['label'])} 기록 등급표 (나이대별)</h2>
{tier_table(dist, "male")}

<h2>여성 {esc(c['label'])} 기록 등급표 (나이대별)</h2>
{tier_table(dist, "female")}
<p style="font-size:13px; color:var(--ink-faint,#6A6A6A);">※ 10대는 아직 성장기라 성인 기준 등급을 그대로 적용하기는 조심스럽습니다. 참고용으로만 봐주세요. 데이터는 5세 단위로 제공되어, 각 나이대의 대표 구간 값을 사용했습니다.</p>
<p style="font-size:13px; color:var(--ink-faint,#6A6A6A);">※ {esc(c['note'])}</p>

<div style="margin:30px 0 34px;">
<p style="font-size:13.5px; line-height:1.8; color:var(--ink-soft,#9A9A9A); margin:0 0 14px;">
위 표는 <strong style="color:var(--ink,#fff);">Running Level</strong>(해외 공개 데이터) 기준 5단계입니다.
calrank는 나이·성별 보정 방식이 다른 <strong style="color:var(--ink,#fff);">자체 7단계 등급</strong>도 함께 제공합니다 —
같은 기록이라도 두 기준의 결과가 다를 수 있으니, 둘 다 보시는 편이 정확합니다.
</p>

<a href="level.html" class="cert-cta" style="margin-top:0;">
<span class="cc-ico">🧮</span>
<span class="cc-txt"><b>기록을 직접 넣어 계산하기</b><span>WMA 연령 기준표로 5km·하프·풀코스까지 같은 잣대로 비교합니다.</span></span>
<span class="cc-go">계산하기 →</span>
</a>

<a href="cert.html" class="cert-cta">
<span class="cc-ico">📷</span>
<span class="cc-txt"><b>기록증 사진 한 장으로 바로 확인</b><span>완주 시간을 읽어 내 등급과 다음 목표까지 남은 시간을 알려드립니다. 로그인도 타이핑도 필요 없습니다.</span></span>
<span class="cc-go">바로 확인 →</span>
</a>

<a href="grade.html" class="cert-cta">
<span class="cc-ico">📊</span>
<span class="cc-txt"><b>calrank 자체 등급표 — 5km · 10km · 하프 · 풀</b><span>거리별·나이별·성별로 내 기록이 어느 칸인지 표에서 바로 찾을 수 있습니다.</span></span>
<span class="cc-go">등급표 →</span>
</a>
</div>

<h2>{esc(c['why_h2'])}</h2>
{why}

{series_links(dist)}

<div class="column-cta">
<p>기록증 사진 한 장이면 등급이 바로 나옵니다. 가입도, 타이핑도 필요 없습니다.</p>
<a href="cert.html">사진으로 내 등급 확인하기 →</a>
</div>
</div>
</main>

<footer class="site-footer">
<div class="wrap">
<p>calrank는 대회 주최측이 공개한 일정 정보를 정리해 제공합니다. 이 칼럼의 등급표는 외부 공개 데이터(Running Level, 2024)를 바탕으로 하며, 실제 신체 조건·훈련 상태에 따라 개인차가 있을 수 있습니다.</p>
<p class="footer-links"><a href="terms.html">이용약관</a> · <a href="privacy.html">개인정보처리방침</a> · <a href="contact.html">제휴·광고 문의</a></p>
</div>
</footer>

</body>
</html>
"""
    return slug, html, c["h1"], desc


def link_10km_page() -> bool:
    """이미 있는 10km 페이지에 다른 거리로 가는 링크를 끼운다.

    이 페이지는 유입이 가장 많으므로 통째로 다시 만들지 않는다.
    링크 묶음만 넣고, 이미 있으면 최신 내용으로 갈아 끼운다.
    """
    path = ROOT / "column-10km-age-gender-tier.html"
    if not path.exists():
        print("[tier columns] 10km 페이지 없음 — 링크 건너뜀")
        return False
    html = path.read_text(encoding="utf-8")
    block = series_links("10km")
    marker = '<div class="column-cta">'
    existing = re.search(r'<p style="font-size:13\.5px;line-height:1\.9;[^>]*>다른 거리의 등급표.*?</p>\n', html, re.S)
    if existing:
        new = html[:existing.start()] + block + "\n\n" + html[existing.end():]
    elif marker in html:
        new = html.replace(marker, block + "\n\n" + marker, 1)
    else:
        print("[tier columns] 10km 페이지에 넣을 자리를 못 찾음")
        return False
    if new != html:
        path.write_text(new, encoding="utf-8")
        print("[tier columns] 10km 페이지에 거리 링크 반영")
        return True
    return False


def update_column_list(cards) -> int:
    path = ROOT / "column.html"
    if not path.exists():
        return 0
    html = path.read_text(encoding="utf-8")
    marker = '<div style="margin-top:24px;" id="columnCardsContainer">\n\n'
    if marker not in html:
        print("[tier columns] column.html 에 카드 자리를 못 찾음")
        return 0
    added = 0
    for slug, title, desc in cards:
        if f'href="{slug}"' in html:
            continue
        card = (f'<a href="{slug}" class="column-card">\n'
                f'<p class="column-card-meta">📊 데이터 분석 · 러닝 가이드</p>\n'
                f'<p class="column-card-title">{esc(title)}</p>\n'
                f'<p class="column-card-desc">{esc(desc)}</p>\n'
                f'</a>\n\n')
        html = html.replace(marker, marker + card, 1)
        added += 1
    if added:
        path.write_text(html, encoding="utf-8")
    return added


def update_sitemap(slugs) -> int:
    path = ROOT / "sitemap.xml"
    if not path.exists():
        return 0
    xml = path.read_text(encoding="utf-8")
    marker = "</urlset>"
    added, count = "", 0
    for slug in slugs:
        loc = f"{SITE}/{slug}"
        if f"<loc>{loc}</loc>" in xml:
            continue
        added += ("  <url>\n"
                  f"    <loc>{loc}</loc>\n"
                  "    <changefreq>monthly</changefreq>\n"
                  "    <priority>0.8</priority>\n"
                  "  </url>\n")
        count += 1
    if added and marker in xml:
        path.write_text(xml.replace(marker, added + marker), encoding="utf-8")
    return count


def main() -> None:
    slugs, cards = [], []
    for dist in ("5km", "half", "full"):
        slug, html, title, desc = build(dist)
        path = ROOT / slug
        if not path.exists() or path.read_text(encoding="utf-8") != html:
            path.write_text(html, encoding="utf-8")
        slugs.append(slug)
        cards.append((slug, title, desc))
        print(f"[tier columns] {slug} ({len(html) // 1024}KB)")
    link_10km_page()
    n_card = update_column_list(cards)
    n_map = update_sitemap(slugs)
    print(f"[tier columns] 칼럼 목록 카드 {n_card}개 · sitemap {n_map}개 추가")


if __name__ == "__main__":
    main()

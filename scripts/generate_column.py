"""
calrank 칼럼 자동 생성 스크립트 (순수 통계 기반, AI 미사용)

events.json에서 실제 대회 통계를 계산한 뒤, 여러 문장 템플릿 중 하나를
무작위로 골라 숫자를 끼워 넣습니다. 새로운 사실을 지어내지 않으므로
할루시네이션 위험이 없습니다.

사용 예시:
  python scripts/generate_column.py
"""
import json
import random
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KST = timezone(timedelta(hours=9))

SPORT_LABEL = {
    "marathon": "마라톤",
    "cycling": "자전거",
    "trail": "트레일러닝",
    "triathlon": "철인3종",
    "inline": "인라인",
}
SPORT_ROTATION = ["marathon", "cycling", "trail", "triathlon", "inline"]

# 실제 검색 트렌드 조사(대회 브랜드명, 이벤트 형식, 관련 커뮤니티 용어) 기반 키워드 풀.
# 종목당 20개 이상, 총 100개 이상을 확보해 매번 다르게 순환 사용한다.
SPORT_KEYWORD_POOL = {
    "marathon": [
        "마라톤대회", "마라톤일정", "마라톤접수", "하프마라톤", "풀코스마라톤",
        "10km마라톤", "5km마라톤", "울트라마라톤", "나이트런", "컬러런",
        "애니멀런", "버츄얼레이스", "런트립", "국제마라톤", "가을마라톤",
        "봄마라톤", "초보마라톤", "마라톤완주", "마라톤기록증", "마라톤PB",
        "마라톤서브3", "마라톤서브4", "러닝크루", "마스터즈마라톤", "마라톤코스",
    ],
    "cycling": [
        "그란폰도", "메디오폰도", "자전거대회", "라이딩대회", "자전거대회일정",
        "MTB대회", "로드바이크대회", "자전거동호인", "자전거완주", "힐클라임",
        "자전거투어", "사이클대회", "센추리라이드", "자전거접수", "그란폰도일정",
        "장거리라이딩", "자전거코스", "자전거동호회대회", "라이딩코스", "자전거대회추천",
    ],
    "trail": [
        "트레일러닝대회", "울트라트레일", "산악마라톤", "트레일런", "100K대회",
        "트레일러닝입문", "가을트레일", "봄트레일", "산길달리기", "등산마라톤",
        "스카이러닝", "트레일러닝코스", "트레일러닝일정", "트레일러닝접수", "산악레이스",
        "트레일완주", "국내트레일대회", "숲길마라톤", "트레일러닝추천", "트레일러닝초보",
    ],
    "triathlon": [
        "철인3종대회", "트라이애슬론", "듀애슬론", "아쿠아슬론", "올림픽코스철인",
        "스프린트철인3종", "스탠다드철인3종", "철인3종입문", "철인3종완주", "바다수영대회",
        "철인3종일정", "전국철인3종", "철인3종접수", "철인3종코스", "철인3종추천",
        "아이언맨코스", "철인3종훈련", "3종경기대회", "트라이애슬론일정", "철인3종동호인",
    ],
    "inline": [
        "인라인스케이트대회", "인라인스피드", "인라인마라톤", "인라인프리스타일", "인라인하키",
        "롤러스포츠대회", "인라인대회일정", "인라인스케이팅", "인라인완주", "전국인라인대회",
        "인라인동호인", "스피드스케이팅대회", "인라인레이스", "인라인입문", "인라인스케이트동호회",
    ],
}
MIN_EVENTS_FOR_TOPIC = 3


def load_json(path, default):
    p = ROOT / path
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(path, data):
    p = ROOT / path
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def slugify(sport, month_label):
    return f"column-{month_label}-{sport}-auto.html"


def compute_stats(events, sport, month_label, now_kst):
    # 1차: 해당 월(calendar month) 기준으로 시도
    subset = [e for e in events if e.get("sport") == sport and (e.get("date") or "").startswith(month_label)]
    window_label = month_label

    # 데이터가 적은 종목(자전거·인라인 등)은 이번 달만으로는 기사 분량이 안 나올 수 있어,
    # 오늘부터 45일 이내로 창을 넓혀 재시도한다. 로테이션이 계속 막히는 것을 방지한다.
    if len(subset) < MIN_EVENTS_FOR_TOPIC:
        today = now_kst.date()
        end = today + timedelta(days=45)
        subset = [
            e for e in events
            if e.get("sport") == sport and e.get("date")
            and today.isoformat() <= e["date"][:10] <= end.isoformat()
        ]
        window_label = f'{today.strftime("%m.%d")}~{end.strftime("%m.%d")}'

    if len(subset) < MIN_EVENTS_FOR_TOPIC:
        return None

    by_region = {}
    for e in subset:
        r = e.get("region") or "미표기"
        by_region[r] = by_region.get(r, 0) + 1
    top_regions = sorted(by_region.items(), key=lambda x: -x[1])[:5]

    by_distance = {}
    for e in subset:
        for d in (e.get("distances") or []):
            by_distance[d] = by_distance.get(d, 0) + 1
    top_distances = sorted(by_distance.items(), key=lambda x: -x[1])[:6]

    sample_names = [e.get("name") for e in subset[:6] if e.get("name")]

    if window_label == month_label:
        y, m = month_label.split("-")
        month_kr = f"{y}년 {int(m)}월"
    else:
        month_kr = f"{window_label} 사이"

    return {
        "sport": sport,
        "sport_label": SPORT_LABEL[sport],
        "month_label": month_label,
        "month_kr": month_kr,
        "total": len(subset),
        "top_regions": top_regions,
        "top_distances": top_distances,
        "sample_names": sample_names,
        "events": sorted(subset, key=lambda e: e.get("date") or ""),
    }


ADJ_REF_C, ADJ_PER_C, ADJ_MAX_DELTA = 15.0, 0.008, 8.0
MIN_CLIMATE_ROWS = 5  # 이 수 이상 기온 자료가 붙어야 색인 대상으로 둔다


def climate_rows(stats):
    rows = []
    for e in stats.get("events", []):
        c = e.get("climate")
        if not c or "minAvg" not in c or "maxAvg" not in c:
            continue
        mean = (c["minAvg"] + c["maxAvg"]) / 2
        over = mean - ADJ_REF_C
        pct = ADJ_PER_C * min(over, ADJ_MAX_DELTA) * 100 if over > 0 else 0.0
        rows.append((e, c, mean, pct))
    return rows


def climate_html(stats):
    """대회 당일 기온 평년값과 칼랭크의 더위 보정 폭. 대회마다 값이 달라 월마다 내용이 바뀐다."""
    from html import escape as esc
    rows = climate_rows(stats)
    if len(rows) < 3:
        return ""
    cap = 12
    body = ""
    for e, c, mean, pct in rows[:cap]:
        d = (e.get("date") or "")[5:10].replace("-", ".")
        adj = f"+{pct:.1f}%" if pct > 0 else "보정 없음"
        body += (f'<tr><td><a href="e/{esc(str(e["id"]))}.html">{esc(e.get("name") or "")}</a></td><td>{d}</td>'
                 f'<td>{c["minAvg"]:.0f}~{c["maxAvg"]:.0f}℃</td><td>{adj}</td></tr>')
    hot = [r for r in rows if r[3] > 0]
    inrng = [r for r in rows if 3.8 <= r[2] <= 9.9]
    txt = (f'기온 자료가 붙은 {len(rows)}개 대회 가운데 일평균기온이 보정 기준(15℃)을 넘는 대회는 {len(hot)}개입니다. ')
    if hot:
        h = max(hot, key=lambda r: r[3])
        txt += f'가장 더운 날은 {h[0].get("name")}로 일평균 {h[2]:.1f}℃, 같은 실력이라도 기록이 약 {h[3]:.1f}% 느려지는 것으로 계산됩니다. '
    if stats.get("sport") == "marathon":
      txt += (f'마라톤 기록이 가장 좋았던 기온대로 보고된 3.8~9.9℃(El Helou 외, 2012, 완주자 1,791,972명 분석)에 일평균이 드는 대회는 {len(inrng)}개입니다. ')
    return (
        '<h2>대회 당일 기온과 기록 보정</h2>'
        f'<p>{txt}</p>'
        '<div style="overflow-x:auto"><table class="cv-table" style="font-size:14.5px"><colgroup><col><col style="width:3.6em"><col style="width:6em"><col style="width:4.4em"></colgroup>'
        '<thead><tr><th>대회</th><th>날짜</th><th>평년 최저~최고</th><th>더위 보정</th></tr></thead><tbody>'
        + body + '</tbody></table></div>'
        + (f'<p style="font-size:13.5px">날짜순 {cap}개만 실었습니다.</p>' if len(rows) > cap else '')
        + '<p style="font-size:13.5px;line-height:1.7">기온은 기상청 종관기상관측(ASOS) 최근 10년 같은 날짜 평균이고, 가장 가까운 관측소 값입니다. '
        '더위 보정은 일평균기온이 15℃를 넘는 만큼 1℃당 0.8%(최대 8℃까지)를 적용한 칼랭크 모델 값이며, '
        '근거는 Nikolaidis 외(Int J Environ Res Public Health 2019;16:614)와 Knechtle 외(PLoS ONE 2019;14:e0212797)입니다. '
        '짧은 거리에서는 이 폭이 상한에 가깝습니다. '
        '<a href="level.html">내 기록의 칼랭크 등급 계산하기</a> · <a href="grade-method.html">등급 산정 방식</a></p>'
    )


def pick_topic(events, state):
    idx = state.get("last_sport_index", -1)
    now_kst = datetime.now(KST)
    month_label = now_kst.strftime("%Y-%m")
    published = set(state.get("published", []))

    for attempt in range(len(SPORT_ROTATION)):
        idx = (idx + 1) % len(SPORT_ROTATION)
        sport = SPORT_ROTATION[idx]
        topic_key = f"{sport}-{month_label}"
        if topic_key in published:
            continue
        stats = compute_stats(events, sport, month_label, now_kst)
        if stats is None:
            continue
        return idx, sport, month_label, topic_key, stats

    return None, None, None, None, None


def build_content(stats, rng):
    s = stats
    region_lines = ", ".join(f"{r}({c}개)" for r, c in s["top_regions"][:4])
    distance_lines = ", ".join(f"{d}({c}개)" for d, c in s["top_distances"][:5])
    sample_lines = ", ".join(s["sample_names"][:5])
    top_region_name, top_region_count = s["top_regions"][0]

    title_options = [
        f'{s["month_kr"]}, 전국 {s["sport_label"]} 대회 {s["total"]}개 — 지역별 정리',
        f'{s["month_kr"]} {s["sport_label"]} 대회 {s["total"]}개 — 지역·거리별 현황',
        f'{s["month_kr"]}에 열리는 {s["sport_label"]} 대회 {s["total"]}곳',
    ]
    title = rng.choice(title_options)

    from column_text import build as build_text
    tx = build_text(s["sport_label"], s["month_kr"], s["total"], s["sample_names"],
                    s["top_regions"], s["top_distances"], s["sport"])
    intro = tx["intro"]
    sections = [
        {"heading": "이번 달 대회 현황", "body": tx["sec1"]},
        {"heading": "지역별 분포", "body": tx["sec2"]},
    ]
    if tx["sec3"]:
        sections.append({"heading": "거리별 분포", "body": tx["sec3"]})
    if tx["gear"]:
        sections.append({"heading": "장비도 함께 보려면", "body": tx["gear"]})
    cta_text = tx["cta"]

    return {"title": title, "intro": intro, "sections": sections, "cta_text": cta_text}


def build_tags(stats, rng):
    sport = stats["sport"]
    tags = [
        (f"index.html?sport={sport}", f"#{stats['sport_label']}"),
    ]
    # 실제 조사한 종목별 키워드 풀에서 매번 다른 조합을 무작위로 골라 사용한다.
    pool = SPORT_KEYWORD_POOL.get(sport, [])
    picked = rng.sample(pool, k=min(7, len(pool)))
    for kw in picked:
        tags.append((f"index.html?sport={sport}", f"#{kw}"))
    for r, _ in stats["top_regions"][:3]:
        if r and r not in ("미표기", "전국"):
            tags.append((f"index.html?region={r}", f"#{r}{stats['sport_label']}"))
    tags.append(("column.html", "#대회분석"))
    seen = set()
    uniq = []
    for href, label in tags:
        if label in seen:
            continue
        seen.add(label)
        uniq.append((href, label))
    return uniq[:14]


def build_html(stats, content, slug, rng):
    tags_html = "\n".join(
        f'<a href="{href}" class="column-tag">{label}</a>' for href, label in build_tags(stats, rng)
    )
    sections_html = "\n".join(
        f'<h2>{sec["heading"]}</h2>\n<p>{sec["body"]}</p>' for sec in content["sections"]
    ) + "\n" + climate_html(stats)
    robots = "" if len(climate_rows(stats)) >= MIN_CLIMATE_ROWS else '<meta name="robots" content="noindex,follow">\n'
    stats["_indexed"] = not robots
    region_boxes = "".join(
        f'<div class="stat-box"><b>{r}</b><span>{c}개</span></div>' for r, c in [x for x in stats["top_regions"] if x[0] not in ("전국", "미표기", "")][:3]
    )
    stat_boxes = f'<div class="stat-grid"><div class="stat-box"><b>{stats["total"]}개</b><span>{stats["month_label"]} {stats["sport_label"]} 대회</span></div>{region_boxes}</div>'

    title = content["title"]
    desc = content["intro"][:120]
    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
{robots}<title>{title} — calrank</title>
<meta name="description" content="{desc}">
<meta property="og:type" content="article">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="https://calrank.vercel.app/og-image.png">
<meta property="og:url" content="https://calrank.vercel.app/{slug}">
<meta property="og:locale" content="ko_KR">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Black+Han+Sans&family=Noto+Sans+KR:wght@400;500;700;900&display=swap" rel="stylesheet">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="stylesheet" href="style.css">
<style>
  .column-wrap {{ max-width: 720px; margin: 0 auto; padding: 48px 20px 80px; }}
  .column-meta {{ font-size: 14.5px; color: var(--ink-faint, #8E8E8E); margin-bottom: 12px; }}
  .column-title {{ font-family: var(--font-display); font-size: clamp(26px, 4vw, 38px); line-height: 1.3; margin-bottom: 24px; }}
  .column-body {{ font-size: 16px; line-height: 1.9; color: var(--ink); }}
  .column-body h2 {{ font-size: 21px; margin: 40px 0 14px; color: var(--ink); }}
  .column-body p {{ margin-bottom: 18px; }}
  .stat-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 12px; margin: 24px 0 32px; }}
  .stat-box {{ background: var(--surface, #141414); border: 1px solid var(--border, #2A2A2A); border-radius: 8px; padding: 16px; text-align: center; }}
  .stat-box b {{ display: block; font-size: 22px; color: var(--accent-ink); font-family: var(--font-display); margin-bottom: 4px; }}
  .stat-box span {{ font-size: 13.5px; color: var(--ink-faint, #8E8E8E); }}
  .cv-table {{ width: 100%; border-collapse: collapse; }}
  .cv-table th, .cv-table td {{ padding: 8px 6px; border-top: 1px solid var(--line); text-align: left; font-weight: 400; }}
  .cv-table th {{ color: var(--ink-soft); }}
  .column-cta {{ margin-top: 40px; padding: 24px; background: var(--surface, #141414); border-radius: 10px; text-align: center; }}
  .column-cta a {{ display: inline-block; margin-top: 12px; background: var(--accent); color: var(--on-accent); background: var(--accent-fill); font-weight: 700; padding: 12px 28px; border-radius: 6px; text-decoration: none; }}
  .column-tags {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 20px 0 8px; }}
  .column-tag {{ font-size: 13.5px; padding: 5px 12px; border: 1px solid var(--border, #2A2A2A); border-radius: 999px; color: var(--ink-soft); text-decoration: none; }}
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
<a href="myrank.html" class="nav-link">내 랭크</a>
<a href="contact.html" class="nav-contact-link">제휴문의</a>
</nav>
</div>
</header>
<main class="column-wrap">
<p class="column-meta">📊 데이터 분석 · {stats["month_label"]}</p>
<h1 class="column-title">{title}</h1>
<div class="column-tags">
{tags_html}
</div>
<div class="column-body">
<p>{content["intro"]}</p>
{stat_boxes}
{sections_html}
<div class="column-cta">
<p>{content["cta_text"]}</p>
<a href="index.html?sport={stats["sport"]}">{stats["sport_label"]} 대회 전체 보기 →</a>
</div>
</div>
</main>
<footer class="site-footer">
<div class="wrap">
<p>칼랭크(CALRANK)는 대회 일정을 모으고, 기록에는 칼랭크 등급을, 코스에는 칼랭크 난이도를 매기는 곳입니다. 대회 일정은 주최측이 공개한 내용을 정리한 것입니다. 접수 조건 등 정확한 내용은 신청 페이지에서 다시 확인해주세요.</p>
<p class="footer-links"><a href="terms.html">이용약관</a> · <a href="privacy.html">개인정보처리방침</a> · <a href="contact.html">문의·제휴</a></p>
</div>
</footer>
</body>
</html>
''', title, desc


def update_column_list(title, desc, slug, month_label):
    path = ROOT / "column.html"
    html = path.read_text(encoding="utf-8")
    card = (
        f'<a href="{slug}" class="column-card">\n'
        f'<p class="column-card-meta">📊 데이터 분석 · {month_label}</p>\n'
        f'<p class="column-card-title">{title}</p>\n'
        f'<p class="column-card-desc">{desc}</p>\n'
        f'</a>\n\n'
    )
    marker = '<div style="margin-top:24px;" id="columnCardsContainer">\n\n'
    if marker in html:
        html = html.replace(marker, marker + card)
        path.write_text(html, encoding="utf-8")


def update_sitemap(slug):
    path = ROOT / "sitemap.xml"
    xml = path.read_text(encoding="utf-8")
    entry = (
        f"  <url>\n"
        f"    <loc>https://calrank.vercel.app/{slug}</loc>\n"
        f"    <changefreq>monthly</changefreq>\n"
        f"    <priority>0.6</priority>\n"
        f"  </url>\n"
    )
    marker = "</urlset>"
    if marker in xml and entry not in xml:
        xml = xml.replace(marker, entry + marker)
        path.write_text(xml, encoding="utf-8")


def main():
    events = load_json("events.json", [])
    sys.path.insert(0, str(ROOT / "scripts"))
    import generate_event_pages as gep
    gep.attach_climate(events)
    state = load_json("scripts/column_state.json", {"last_sport_index": -1, "published": []})

    idx, sport, month_label, topic_key, stats = pick_topic(events, state)
    if stats is None:
        print("No suitable topic found (insufficient data or all covered).")
        return

    rng = random.Random(topic_key)
    content = build_content(stats, rng)
    slug = slugify(sport, month_label)
    html, title, desc = build_html(stats, content, slug, rng)

    (ROOT / slug).write_text(html, encoding="utf-8")
    update_column_list(title, desc, slug, month_label)
    # 대회 당일 기온·보정 표가 5개 이상 붙은 글만 색인 대상으로 두고 사이트맵에 넣는다.
    # 나머지는 noindex 로 남긴다(숫자만 바뀌는 얇은 글이 되기 때문).
    if stats.get("_indexed"):
        update_sitemap(slug)

    state["last_sport_index"] = idx
    state.setdefault("published", []).append(topic_key)
    save_json("scripts/column_state.json", state)

    print(f"Generated: {slug}")


if __name__ == "__main__":
    main()

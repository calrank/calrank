"""
calrank 아쿠아슬론 페이지(aquathlon.html) 정적 생성 스크립트

배경: 검색에서 가장 반응이 좋은 키워드("아쿠아슬론 대회 일정")의 도착 페이지가
JS로 목록을 그리는 구조라, 예정 대회가 없으면 검색엔진에도 사람에게도 빈 페이지였다.
이 스크립트는 서버 단계에서 내용이 채워진 정적 페이지를 만든다.

데이터 출처 (모두 실제 값, 없는 정보는 만들지 않는다)
- events.json: 크롤러가 수집한 아쿠아슬론 대회 (예정 대회 목록 + 지난 대회 자동 누적)
- scripts/aquathlon_archive.json: 공식 페이지·언론 보도로 확인한 시즌 기록(출처 링크 포함)

새 시즌 대회가 events.json에 들어오면 "예정 대회"에 자동으로 나타나고,
지난 뒤에는 연도별 시즌 표에 자동으로 쌓인다.
"""
import html
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://calrank.vercel.app"
PAGE = "aquathlon.html"
KST = timezone(timedelta(hours=9))
AQ_RE = re.compile(r"아쿠아슬론|aquathlon", re.I)
WEEKDAY = ["월", "화", "수", "목", "금", "토", "일"]
FEDERATION_URL = "https://triathlon.or.kr/events/tour/"


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


def parse_d(s):
    try:
        return datetime.strptime((s or "")[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def fmt_day(d) -> str:
    return f"{d.month}월 {d.day}일({WEEKDAY[d.weekday()]})"


def fmt_range(start, end) -> str:
    if start == end:
        return fmt_day(start)
    if start.month == end.month:
        return f"{start.month}월 {start.day}일({WEEKDAY[start.weekday()]})~{end.day}일({WEEKDAY[end.weekday()]})"
    return f"{fmt_day(start)}~{fmt_day(end)}"


def event_page_for(events, start, end):
    """해당 날짜 범위의 아쿠아슬론 대회 중, 정적 상세페이지(e/<id>.html)가 실제로 있는 것의 경로."""
    for e in events:
        d = parse_d(e.get("date"))
        if d and start <= d <= end and AQ_RE.search(e.get("name", "")):
            if (ROOT / "e" / f"{e['id']}.html").exists():
                return f"e/{quote(e['id'])}.html"
    return None


def load_archive():
    path = ROOT / "scripts" / "aquathlon_archive.json"
    items = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for it in items:
        s, e = parse_d(it["start"]), parse_d(it["end"])
        if not s or not e:
            continue
        out.append({**it, "start": s, "end": e})
    return out


def build_entries(events, today):
    archive = load_archive()
    crawled = [e for e in events if AQ_RE.search(e.get("name", "")) and parse_d(e.get("date"))]

    upcoming = sorted(
        [e for e in crawled if parse_d(e["date"]) >= today],
        key=lambda e: e["date"],
    )

    entries = list(archive)
    for e in crawled:
        d = parse_d(e["date"])
        if d >= today:
            continue
        if any(a["start"] <= d <= a["end"] for a in archive):
            continue  # 아카이브가 이미 다루는 날짜
        entries.append({
            "start": d, "end": d, "name": e["name"],
            "place": e.get("location") or "",
            "note": "",
            "source_name": "대한철인3종협회",
            "source_url": e.get("sourceUrl") or FEDERATION_URL,
        })
    # 지난 대회만 시즌 표에 둔다(예정 대회는 위쪽 별도 표)
    entries = [x for x in entries if x["end"] < today or x in archive]
    return upcoming, entries


def season_table(entries_for_year, events) -> str:
    rows = []
    for x in sorted(entries_for_year, key=lambda x: x["start"]):
        link = event_page_for(events, x["start"], x["end"])
        name_html = f'<a href="{esc(link)}">{esc(x["name"])}</a>' if link else esc(x["name"])
        src = f'<a href="{esc(x["source_url"])}" target="_blank" rel="noopener">{esc(x["source_name"])}</a>'
        note = f'{esc(x["note"])}<br>' if x.get("note") else ""
        rows.append(
            f'<tr><td class="aq-date">{esc(fmt_range(x["start"], x["end"]))}</td>'
            f'<td>{name_html}</td><td>{esc(x["place"])}</td>'
            f'<td class="aq-note">{note}출처: {src}</td></tr>'
        )
    return (
        '<div class="aq-scroll"><table class="aq-table"><thead><tr>'
        '<th>일정</th><th>대회</th><th>장소</th><th>비고·출처</th></tr></thead><tbody>'
        + "".join(rows) + "</tbody></table></div>"
    )


def upcoming_table(upcoming) -> str:
    rows = []
    for e in upcoming:
        d = parse_d(e["date"])
        link = f"e/{quote(e['id'])}.html"
        apply_url = e.get("applyUrl") or e.get("sourceUrl") or FEDERATION_URL
        rows.append(
            f'<tr><td class="aq-date">{esc(d.year)}년 {esc(fmt_day(d))}</td>'
            f'<td><a href="{esc(link)}">{esc(e["name"])}</a></td>'
            f'<td>{esc(e.get("location") or "")}</td>'
            f'<td><a href="{esc(apply_url)}" target="_blank" rel="noopener">접수·공식 안내 ↗</a></td></tr>'
        )
    return (
        '<div class="aq-scroll"><table class="aq-table"><thead><tr>'
        '<th>일정</th><th>대회</th><th>장소</th><th>접수</th></tr></thead><tbody>'
        + "".join(rows) + "</tbody></table></div>"
    )


FAQ = [
    ("아쿠아슬론이란 무엇인가요?",
     "수영과 달리기를 연이어 치르는 복합 종목입니다. 철인3종(수영·사이클·달리기)에서 사이클을 뺀 형태로, "
     "지구력과 페이스 조절 능력이 고루 요구됩니다."),
    ("국내 아쿠아슬론 대회는 언제 열리나요?",
     "해마다 시기가 달라서 공지를 확인해야 합니다. 예를 들어 익산 챌린지 시리즈는 2025년에 5월 17일·7월 26일 대회가 확인되고, "
     "2026년에는 4월·5월·9월 일정으로 공지됐습니다."),
    ("참가 신청은 어디서 하나요?",
     "대한철인3종협회 대회일정/참가신청 페이지에서 대회별 접수 상태를 확인할 수 있습니다. "
     "접수 기간과 참가 자격은 대회마다 다르니 신청 전에 공지를 꼭 확인하세요."),
]


def ld(data) -> str:
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + "</script>"


def render(upcoming, entries, events, today) -> str:
    url = f"{SITE}/{PAGE}"
    title = "아쿠아슬론 대회 일정 총정리 — 익산 챌린지·롯데 아쿠아슬론 | calrank"
    if upcoming:
        desc = (f"국내 아쿠아슬론(수영+달리기) 대회 일정을 대한철인3종협회 공식 정보 기준으로 정리했습니다. "
                f"앞으로 예정된 대회 {len(upcoming)}개와 익산 챌린지·롯데 아쿠아슬론 등 시즌 기록을 확인하세요.")
    else:
        desc = ("국내 아쿠아슬론(수영+달리기) 대회 일정을 대한철인3종협회 공식 정보 기준으로 정리했습니다. "
                "2026 시즌 익산 챌린지·롯데 아쿠아슬론 날짜와 장소, 다음 대회 확인 방법까지.")
    today_ko = f"{today.year}년 {today.month}월 {today.day}일"

    if upcoming:
        status = (f'<p class="aq-status aq-open">앞으로 예정된 아쿠아슬론 대회가 {len(upcoming)}개 있습니다.</p>'
                  + upcoming_table(upcoming))
    else:
        status = (f'<p class="aq-status">{esc(today_ko)} 기준, 대한철인3종협회 일정에 등록된 예정 대회는 없습니다. '
                  "새 대회가 등록되면 이 페이지가 자동으로 갱신됩니다.</p>")

    years = sorted({x["start"].year for x in entries}, reverse=True)
    seasons = ""
    for y in years:
        seasons += (f'<h2>{y}년 시즌 국내 아쿠아슬론 대회</h2>'
                    + season_table([x for x in entries if x["start"].year == y], events))

    faq_html = "".join(f"<h3>{esc(q)}</h3><p>{esc(a)}</p>" for q, a in FAQ)

    ld_blocks = "\n".join([
        ld({"@context": "https://schema.org", "@type": "CollectionPage", "name": title,
            "description": desc, "url": url, "dateModified": today.isoformat(), "inLanguage": "ko"}),
        ld({"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q,
                            "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ]}),
        ld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "calrank", "item": f"{SITE}/index.html"},
            {"@type": "ListItem", "position": 2, "name": "아쿠아슬론 대회 일정"}]}),
    ])

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{SITE}/og-image.png">
<meta property="og:url" content="{url}">
<meta property="og:locale" content="ko_KR">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap" rel="stylesheet">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="apple-touch-icon" href="/favicon.svg">
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#0B0B0B">
<link rel="canonical" href="{url}">
<link rel="stylesheet" href="style.css">
{ld_blocks}
<style>
  .aq-wrap {{ max-width: 860px; margin: 0 auto; padding: 48px 20px 80px; }}
  .aq-wrap h1 {{ font-family: var(--font-display); font-size: clamp(24px, 3.6vw, 34px); line-height: 1.3; margin-bottom: 12px; }}
  .aq-wrap h2 {{ font-size: 19px; margin: 36px 0 12px; }}
  .aq-wrap h3 {{ font-size: 16px; margin: 20px 0 6px; }}
  .aq-wrap p {{ font-size: 15px; line-height: 1.8; color: #D6D0CC; }}
  .aq-sub {{ color: #B8B0AC; margin-bottom: 20px; }}
  .aq-status {{ padding: 14px 16px; background: var(--surface, #141414); border: 1px solid var(--border, #2A2A2A); border-radius: 8px; margin: 18px 0; }}
  .aq-open {{ border-color: var(--accent); }}
  .aq-scroll {{ overflow-x: auto; }}
  .aq-table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  .aq-table th, .aq-table td {{ padding: 10px 8px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.08); vertical-align: top; }}
  .aq-table th {{ color: #fff; background: rgba(255,255,255,0.03); white-space: nowrap; }}
  .aq-date {{ color: var(--accent); font-weight: 700; white-space: nowrap; }}
  .aq-note {{ color: #B8B0AC; font-size: 13px; }}
  .aq-table a {{ color: #E8E4E1; }}
  .aq-next {{ padding: 16px 18px; background: var(--surface, #141414); border-radius: 10px; margin-top: 12px; line-height: 1.9; font-size: 14.5px; }}
  .aq-next a {{ color: var(--accent); font-weight: 700; }}
  .aq-disclaimer {{ font-size: 12.5px !important; color: #8E8884 !important; margin-top: 32px; }}
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
<a href="column.html" class="nav-link">칼럼</a>
<a href="myrank.html" class="nav-link">내 랭크</a>
<a href="contact.html" class="nav-contact-link">제휴문의</a>
</nav>
</div>
</header>
<main class="aq-wrap">
<h1>아쿠아슬론 대회 일정 총정리</h1>
<p class="aq-sub">수영과 달리기를 연이어 치르는 국내 아쿠아슬론 대회를 대한철인3종협회 공식 정보 기준으로 정리했습니다. 익산 챌린지 시리즈와 롯데 아쿠아슬론 등 시즌 일정과 다음 대회를 놓치지 않는 방법을 함께 담았습니다.</p>
{status}
{seasons}
<h2>다음 대회를 놓치지 않는 방법</h2>
<div class="aq-next">
· <a href="feed.ics">캘린더 구독(feed.ics)</a> — 새 대회가 등록되면 내 캘린더에 자동으로 추가됩니다. 전 종목 일정이 함께 들어옵니다.<br>
· <a href="news.html">종목뉴스</a> — 대한철인3종협회 공식 소식을 매일 자동으로 모아 보여줍니다.<br>
· <a href="{FEDERATION_URL}" target="_blank" rel="noopener">대한철인3종협회 대회일정/참가신청 ↗</a> — 접수 상태의 원본 페이지입니다.<br>
· <a href="index.html?sport=triathlon">철인3종 전체 대회 캘린더</a> — 아쿠아슬론 외 철인3종 대회까지 한눈에 볼 수 있습니다.
</div>
<h2>자주 묻는 질문</h2>
{faq_html}
<p class="aq-disclaimer">이 페이지는 대한철인3종협회 공개 일정과 언론 보도를 바탕으로 정리했으며, 일정과 접수 조건은 변경될 수 있습니다. 참가 전 반드시 공식 안내를 다시 확인해주세요. 마지막 갱신 기준일: {esc(today_ko)}</p>
</main>
<footer class="site-footer">
<div class="wrap">
<p>calrank는 대회 주최측이 공개한 일정 정보를 정리해 제공합니다. 접수 조건 등 정확한 내용은 신청 페이지에서 다시 확인해주세요.</p>
<p class="footer-links"><a href="terms.html">이용약관</a> · <a href="privacy.html">개인정보처리방침</a> · <a href="contact.html">제휴·광고 문의</a></p>
</div>
</footer>
<script defer src="/_vercel/insights/script.js"></script>
</body>
</html>
"""


def main():
    events = json.loads((ROOT / "events.json").read_text(encoding="utf-8"))
    today = datetime.now(KST).date()
    upcoming, entries = build_entries(events, today)
    page = render(upcoming, entries, events, today)
    out = ROOT / PAGE
    if not out.exists() or out.read_text(encoding="utf-8") != page:
        out.write_text(page, encoding="utf-8")
    print(f"[aquathlon] 예정 {len(upcoming)}개, 시즌 표 {len(entries)}개 항목")


if __name__ == "__main__":
    main()

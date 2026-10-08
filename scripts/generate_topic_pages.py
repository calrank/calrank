"""
calrank 틈새 주제 페이지 생성 스크립트

배경: aquathlon.html 이 예정 대회 0개인데도 검색 노출 대비 클릭률 18.9%로
사이트에서 가장 높다. 경쟁자가 거의 없는 말이기 때문이다. 같은 방식으로
"울트라마라톤 대회", "야간 마라톤", "걷기 대회", "어린이 마라톤"처럼
사람들이 실제로 검색하지만 전용 페이지가 드문 주제를 각각 한 장으로 만든다.

데이터는 events.json 하나뿐이다. 없는 대회를 지어내지 않는다.
예정 대회가 적은 주제는 지난 대회를 연도별 표로 함께 보여 준다
(대회가 끝난 뒤에 "○○ 기록"으로 검색하는 사람에게 그쪽이 더 쓸모 있다).
"""
import html
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://calrank.vercel.app"
KST = timezone(timedelta(hours=9))
WEEKDAY = ["월", "화", "수", "목", "금", "토", "일"]

# 각 주제는 events.json 의 대회 이름·거리에서 정규식으로 골라낸다.
TOPICS = [
    {
        "page": "open-registration.html",
        "select": "open",          # 이름이 아니라 접수 마감일로 고른다
        "h1": "지금 접수 중인 마라톤 대회",
        "title": "지금 접수 중인 마라톤 대회 | 접수·신청 마감일 모음 - calrank",
        "desc_head": "지금 접수가 열려 있는 전국 마라톤·트레일러닝·자전거 대회를 마감일이 가까운 순서로 모았습니다.",
        "lead": ("지금 신청할 수 있는 전국 대회를 접수 마감일이 가까운 순서로 모았습니다. "
                 "마라톤·트레일러닝·자전거·철인3종·인라인을 가리지 않고, "
                 "5km·10km·하프마라톤·풀코스 거리와 접수 마감일, 신청 링크를 함께 담았습니다."),
        "related": "events-index.html",
        "related_label": "전국 대회 일정 전체 목록",
        "faq": [
            ("이 목록은 얼마나 자주 갱신되나요?",
             "대회 수집이 도는 매일 아침에 다시 만들어집니다. 접수가 마감된 대회는 목록에서 빠지고, "
             "새로 접수를 시작한 대회가 들어옵니다."),
            ("접수 마감일이 지났는데 아직 신청이 되는 경우도 있나요?",
             "현장 접수를 받거나 정원이 남아 기간을 연장하는 대회가 있습니다. "
             "반대로 정원이 차면 마감일 전에 닫히기도 하므로, 신청 링크에서 실제 상태를 확인하세요."),
            ("마감 전에 알림을 받을 수 있나요?",
             "캘린더 구독(feed.ics)을 추가해 두면 접수 마감 3일 전과 하루 전에 휴대폰 캘린더가 알려줍니다. "
             "가입도 앱 설치도 필요 없습니다."),
        ],
    },
    {
        "page": "ultra-marathon.html",
        "desc_head": "풀코스보다 긴 거리를 달리는 국내 울트라마라톤 대회를 모았습니다. 50km·100km 로드 울트라와 산악 울트라 트레일을 함께 담았습니다.",
        "match": r"울트라|100\s?km|100K|50\s?km|60\s?km|80\s?km|200\s?km",
        "h1": "울트라마라톤 대회 일정",
        "title": "울트라마라톤 대회 일정 | 50km·100km 국내 울트라 레이스 - calrank",
        "lead": ("풀코스(42.195km)보다 긴 거리를 달리는 국내 울트라마라톤 대회를 모았습니다. "
                 "50km·100km 로드 울트라와 산악 울트라 트레일을 함께 담았고, "
                 "대회마다 코스 거리와 접수 마감일, 신청 링크를 확인할 수 있습니다."),
        "related": "index.html?sport=marathon",
        "related_label": "마라톤 전체 대회 캘린더",
        "faq": [
            ("울트라마라톤은 몇 km부터인가요?",
             "풀코스 42.195km보다 긴 모든 거리를 울트라마라톤이라고 부릅니다. 국내에서는 50km와 100km가 가장 흔하고, "
             "산악 코스에서는 트레일 울트라로 나뉘기도 합니다."),
            ("울트라마라톤 대회는 1년에 몇 번 열리나요?",
             "일반 마라톤보다 훨씬 적습니다. 이 페이지는 calrank가 수집한 대회만 보여 주므로, "
             "표에 있는 수가 곧 지금 확인된 대회 수입니다. 새 대회가 등록되면 자동으로 올라옵니다."),
            ("처음 도전하는데 어느 거리부터 시작해야 하나요?",
             "풀코스 완주 경험을 먼저 쌓은 뒤 50km로 넘어가는 것이 일반적입니다. "
             "제한 시간과 관문 통과 규정이 대회마다 다르므로 신청 전에 공식 안내를 확인하세요."),
        ],
    },
    {
        "page": "night-run.html",
        "desc_head": "해가 진 뒤에 달리는 국내 야간 마라톤·나이트런 대회를 모았습니다. 여름철 더위를 피해 저녁이나 밤에 출발하는 대회가 많습니다.",
        "match": r"야간|나이트|[Nn]ight|심야|달밤|노을|선셋|[Ss]unset",
        "h1": "야간 마라톤·나이트런 대회 일정",
        "title": "야간 마라톤 대회 일정 | 나이트런·심야 러닝 대회 - calrank",
        "lead": ("해가 진 뒤에 달리는 국내 야간 마라톤·나이트런 대회를 모았습니다. "
                 "여름철 더위를 피해 저녁이나 밤에 출발하는 대회가 많고, "
                 "대회마다 출발 시각과 코스 거리, 접수 마감일을 확인할 수 있습니다."),
        "related": "index.html?sport=marathon",
        "related_label": "마라톤 전체 대회 캘린더",
        "faq": [
            ("야간 마라톤은 보통 몇 시에 출발하나요?",
             "대회마다 다릅니다. 저녁 무렵 출발하는 대회부터 자정 가까이 출발하는 대회까지 있으므로, "
             "표의 대회 이름을 눌러 상세 페이지에서 출발 시각을 확인하세요."),
            ("야간 대회에 필요한 준비물이 있나요?",
             "코스에 따라 헤드랜턴이나 반사 밴드를 의무로 요구하는 대회가 있습니다. "
             "특히 산악 구간이 포함된 대회는 장비 규정이 까다로우니 공식 안내를 반드시 확인하세요."),
            ("야간 대회 기록도 등급으로 확인할 수 있나요?",
             "네. 기록증 사진을 올리면 완주 시간을 읽어 나이·성별을 보정한 등급을 알려드립니다. "
             "주간·야간 구분 없이 같은 기준으로 계산합니다."),
        ],
    },
    {
        "page": "walking-events.html",
        "desc_head": "기록 경쟁 없이 완주가 목표인 국내 걷기 대회와 워킹 행사를 모았습니다. 마라톤 대회의 걷기 부문까지 함께 담았습니다.",
        "match": r"걷기|워킹|[Ww]alk|도보|둘레길|올레",
        "h1": "걷기 대회 일정",
        "title": "걷기 대회 일정 | 전국 워킹·둘레길 걷기 행사 - calrank",
        "lead": ("기록 경쟁 없이 완주 자체가 목표인 국내 걷기 대회와 워킹 행사를 모았습니다. "
                 "마라톤 대회에 걷기 부문이 함께 열리는 경우도 많아 그런 대회까지 포함했습니다. "
                 "대회마다 코스 거리와 접수 마감일, 신청 링크를 확인할 수 있습니다."),
        "related": "index.html",
        "related_label": "전체 대회 캘린더",
        "faq": [
            ("걷기 대회는 마라톤 대회와 어떻게 다른가요?",
             "순위를 가리지 않고 제한 시간 안에 완주하는 데 초점을 둡니다. "
             "다만 국내에서는 마라톤 대회가 5km 안팎의 걷기 부문을 함께 여는 경우가 많아, "
             "이 목록에는 그런 대회도 들어 있습니다."),
            ("달리기를 못 해도 참가할 수 있나요?",
             "걷기 부문은 보통 연령 제한 없이 누구나 신청할 수 있습니다. "
             "다만 제한 시간이 있는 대회가 있으므로 신청 전에 공식 안내를 확인하세요."),
            ("가족이 함께 참가할 수 있나요?",
             "걷기 부문은 가족 단위 참가를 받는 대회가 많습니다. "
             "어린이 참가 가능 여부와 보호자 동반 규정은 대회마다 다릅니다."),
        ],
    },
    {
        "page": "kids-marathon.html",
        "desc_head": "어린이와 가족이 함께 참가할 수 있는 전국 마라톤·달리기 대회를 모았습니다. 유아부·초등부 부문이 있거나 가족 단위 참가를 받는 대회입니다.",
        "match": r"어린이|키즈|[Kk]ids|가족|유아|꿈나무|초등|패밀리|[Ff]amily",
        "h1": "어린이 마라톤·가족 달리기 대회 일정",
        "title": "어린이 마라톤 대회 일정 | 키즈런·가족 달리기 - calrank",
        "lead": ("어린이와 가족이 함께 참가할 수 있는 국내 마라톤·달리기 대회를 모았습니다. "
                 "어린이부·꿈나무부가 따로 있는 대회와 가족 단위로 신청하는 대회를 함께 담았고, "
                 "대회마다 코스 거리와 접수 마감일, 신청 링크를 확인할 수 있습니다."),
        "related": "index.html?sport=marathon",
        "related_label": "마라톤 전체 대회 캘린더",
        "faq": [
            ("어린이는 몇 살부터 참가할 수 있나요?",
             "대회마다 다릅니다. 유아부를 두는 대회도 있고 초등학생 이상만 받는 대회도 있으므로, "
             "표의 대회 이름을 눌러 상세 페이지에서 참가 자격을 확인하세요."),
            ("어린이 부문은 거리가 얼마나 되나요?",
             "보통 1km에서 3km 사이입니다. 5km 부문에 어린이가 보호자와 함께 참가하도록 하는 대회도 있습니다."),
            ("보호자가 함께 뛰어야 하나요?",
             "유아부나 저학년 부문은 보호자 동반을 의무로 하는 대회가 많습니다. "
             "동반 보호자도 따로 접수해야 하는 경우가 있으니 공식 안내를 확인하세요."),
        ],
    },
]


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


def parse_d(s):
    try:
        return datetime.strptime((s or "")[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def fmt_day(d) -> str:
    return f"{d.month}월 {d.day}일({WEEKDAY[d.weekday()]})"


def blob(e) -> str:
    return str(e.get("name") or "") + " " + " ".join(str(x) for x in (e.get("distances") or []))


def has_page(ev) -> bool:
    return (ROOT / "e" / f"{ev.get('id')}.html").exists()


def link_for(ev) -> str:
    return f"e/{quote(str(ev['id']))}.html"


def row(ev, show_year: bool, with_apply: bool, deadline: bool = False) -> str:
    d = parse_d(ev["date"])
    when = (f"{d.year}년 " if show_year else "") + fmt_day(d)
    if deadline:
        dl = parse_d(ev.get("regDeadline"))
        left = (dl - datetime.now(KST).date()).days if dl else None
        when = (f"{fmt_day(dl)} 마감" if dl else "마감일 미정")
        if left is not None and left <= 7:
            when = ("오늘 마감" if left == 0 else f"D-{left} · {when}")
    name = esc(ev.get("name") or "대회")
    name_html = f'<a href="{esc(link_for(ev))}">{name}</a>' if has_page(ev) else name
    place = esc(ev.get("location") or ev.get("region") or "")
    dists = " · ".join(esc(x) for x in (ev.get("distances") or [])[:4] if x and str(x) != "미정")
    if with_apply:
        url = ev.get("applyUrl") or ev.get("sourceUrl") or ""
        last = (f'<a href="{esc(url)}" target="_blank" rel="noopener">접수·공식 안내 ↗</a>'
                if url else "—")
    else:
        last = dists or "—"
    return (f'<tr><td class="tp-date">{esc(when)}</td><td>{name_html}</td>'
            f'<td>{place}</td><td class="tp-note">{last}</td></tr>')


def table(rows_html: str, last_head: str) -> str:
    return ('<div class="tp-scroll"><table class="tp-table"><thead><tr>'
            f'<th>일정</th><th>대회</th><th>장소</th><th>{last_head}</th>'
            "</tr></thead><tbody>" + rows_html + "</tbody></table></div>")


def ld(data) -> str:
    return ('<script type="application/ld+json">'
            + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + "</script>")


STYLE = """
  .tp-wrap{max-width:860px;margin:0 auto;padding:48px 20px 80px;}
  .tp-wrap h1{font-family:var(--font-display);font-size:clamp(24px,3.6vw,34px);line-height:1.3;margin-bottom:12px;}
  .tp-wrap h2{font-size:19px;margin:36px 0 12px;}
  .tp-wrap h3{font-size:16px;margin:20px 0 6px;}
  .tp-wrap p{font-size:15px;line-height:1.8;color:#D6D0CC;}
  .tp-sub{color:#B8B0AC;margin-bottom:20px;}
  .tp-status{padding:14px 16px;background:var(--surface,#141414);
    border:1px solid var(--border,#2A2A2A);border-radius:8px;margin:18px 0;}
  .tp-open{border-color:var(--accent);}
  .tp-scroll{overflow-x:auto;}
  .tp-table{width:100%;border-collapse:collapse;font-size:14px;}
  .tp-table th,.tp-table td{padding:10px 8px;text-align:left;
    border-bottom:1px solid rgba(255,255,255,.08);vertical-align:top;}
  .tp-table th{color:#fff;background:rgba(255,255,255,.03);white-space:nowrap;}
  .tp-date{color:var(--accent);font-weight:700;white-space:nowrap;}
  .tp-note{color:#B8B0AC;font-size:13px;}
  .tp-table a{color:#E8E4E1;}
  .tp-next{padding:16px 18px;background:var(--surface,#141414);border-radius:10px;
    margin-top:12px;line-height:1.9;font-size:14.5px;}
  .tp-next a{color:var(--accent);font-weight:700;}
  .tp-disclaimer{font-size:12.5px !important;color:#8E8884 !important;margin-top:32px;}
"""


def render(topic, upcoming, past, today) -> str:
    url = f"{SITE}/{topic['page']}"
    title = topic["title"]
    head = topic["desc_head"]
    if topic.get("select") == "open":
        desc = (f"{head} 지금 신청할 수 있는 대회 {len(upcoming)}개의 마감일과 "
                "거리, 신청 링크를 확인하세요. 매일 아침 자동으로 갱신됩니다.")
    elif upcoming:
        desc = (f"{head} 앞으로 예정된 대회 {len(upcoming)}개와 "
                f"지난 대회 {len(past)}개의 일정, 장소, 코스 거리를 확인하세요.")
    else:
        desc = (f"{head} 지난 대회 {len(past)}개의 일정과 장소를 정리했습니다. "
                "새 대회가 등록되면 이 페이지가 자동으로 갱신됩니다.")
    today_ko = f"{today.year}년 {today.month}월 {today.day}일"

    if upcoming:
        is_open = topic.get("select") == "open"
        lead_line = (f"지금 접수가 열려 있는 대회가 {len(upcoming)}개 있습니다. 마감일이 가까운 순서입니다."
                     if is_open else f"앞으로 예정된 대회가 {len(upcoming)}개 있습니다.")
        status = (f'<p class="tp-status tp-open">{lead_line}</p>'
                  + table("".join(row(e, True, True, deadline=is_open) for e in upcoming),
                          "접수"))
    else:
        status = (f'<p class="tp-status">{esc(today_ko)} 기준, calrank가 수집한 예정 대회는 없습니다. '
                  "새 대회가 등록되면 이 페이지가 자동으로 갱신됩니다.</p>")

    seasons = ""
    for year in sorted({parse_d(e["date"]).year for e in past}, reverse=True):
        rows = [e for e in past if parse_d(e["date"]).year == year]
        rows.sort(key=lambda e: e["date"], reverse=True)
        seasons += (f'<h2>{year}년에 열린 대회 ({len(rows)}개)</h2>'
                    + table("".join(row(e, False, False) for e in rows), "거리"))

    faq_html = "".join(f"<h3>{esc(q)}</h3><p>{esc(a)}</p>" for q, a in topic["faq"])
    ld_blocks = "\n".join([
        ld({"@context": "https://schema.org", "@type": "CollectionPage", "name": title,
            "description": desc, "url": url, "dateModified": today.isoformat(), "inLanguage": "ko"}),
        ld({"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q,
                            "acceptedAnswer": {"@type": "Answer", "text": a}}
                           for q, a in topic["faq"]]}),
        ld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "calrank", "item": f"{SITE}/index.html"},
            {"@type": "ListItem", "position": 2, "name": topic["h1"]}]}),
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
<style>{STYLE}</style>
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
<main class="tp-wrap">
<h1>{esc(topic['h1'])}</h1>
<p class="tp-sub">{esc(topic['lead'])}</p>
{status}
{seasons}
<h2>다음 대회를 놓치지 않는 방법</h2>
<div class="tp-next">
· <a href="feed.ics">캘린더 구독(feed.ics)</a> — 새 대회가 등록되면 내 캘린더에 자동으로 들어옵니다. 접수 마감 3일 전·하루 전에 알림이 옵니다.<br>
· <a href="events-index.html">전국 대회 일정 전체 목록</a> — 종목 구분 없이 월별로 모아 둔 목록입니다.<br>
· <a href="{esc(topic['related'])}">{esc(topic['related_label'])}</a> — 종목·지역·거리로 걸러 볼 수 있습니다.
</div>
<h2>자주 묻는 질문</h2>
{faq_html}
<a href="cert.html" class="cert-cta" style="margin-top:34px;">
<span class="cc-ico">📷</span>
<span class="cc-txt"><b>기록증 사진 한 장으로 내 러닝 등급 확인</b><span>완주 시간을 읽어 나이·성별을 보정한 등급과 다음 목표까지 남은 시간을 알려드립니다. 로그인도 타이핑도 필요 없습니다.</span></span>
<span class="cc-go">바로 확인 →</span>
</a>
<p class="tp-disclaimer">이 페이지는 대회 주최측이 공개한 일정을 모아 자동으로 만들어집니다. 일정과 접수 조건은 변경될 수 있으니 참가 전 공식 안내를 다시 확인해 주세요. 마지막 갱신 기준일: {esc(today_ko)}</p>
</main>
<footer class="site-footer">
<div class="wrap">
<p>calrank는 대회 주최측이 공개한 일정 정보를 정리해 제공합니다. 접수 조건 등 정확한 내용은 신청 페이지에서 다시 확인해주세요.</p>
<p class="footer-links"><a href="events-index.html">전국 대회 일정 전체 목록</a> · <a href="terms.html">이용약관</a> · <a href="privacy.html">개인정보처리방침</a> · <a href="contact.html">제휴·광고 문의</a></p>
</div>
</footer>
<script defer src="/_vercel/insights/script.js"></script>
</body>
</html>
"""


def main():
    events = json.loads((ROOT / "events.json").read_text(encoding="utf-8"))
    today = datetime.now(KST).date()
    made = []
    for topic in TOPICS:
        if topic.get("select") == "open":
            # 접수가 열려 있는 대회: 대회일도 마감일도 아직 안 지난 것
            upcoming = sorted(
                (e for e in events
                 if e.get("id") and parse_d(e.get("date")) and parse_d(e.get("date")) >= today
                 and parse_d(e.get("regDeadline")) and parse_d(e["regDeadline"]) >= today),
                key=lambda e: (e["regDeadline"], e["date"]))
            past = []
        else:
            rx = re.compile(topic["match"])
            hits = [e for e in events if e.get("id") and parse_d(e.get("date")) and rx.search(blob(e))]
            upcoming = sorted((e for e in hits if parse_d(e["date"]) >= today), key=lambda e: e["date"])
            past = [e for e in hits if parse_d(e["date"]) < today]

        # 내용이 너무 없는 페이지는 만들지 않는다. 표가 몇 줄뿐인 페이지는
        # 검색에서 "알맹이 없는 페이지"로 분류돼 오히려 사이트 전체에 해롭다.
        if len(upcoming) + len(past) < 5:
            print(f"[{topic['page']}] 대회 {len(upcoming)+len(past)}개뿐 — 만들지 않음")
            continue

        page = render(topic, upcoming, past, today)
        out = ROOT / topic["page"]
        if not out.exists() or out.read_text(encoding="utf-8") != page:
            out.write_text(page, encoding="utf-8")
        made.append(topic["page"])
        print(f"[{topic['page']}] 예정 {len(upcoming)}개 / 지난 {len(past)}개")
    print(f"[topic pages] {len(made)}개 생성: {', '.join(made)}")


if __name__ == "__main__":
    main()

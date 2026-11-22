"""대회 일정 변경 소식(schedule-changes.html) 생성 스크립트

배경: track_event_changes.py 가 매일 events.json 을 지난번 상태와 비교해 바뀐 것
(접수 마감일·대회일·장소·거리·접수 링크, 새로 확인된 대회, 목록에서 사라진 대회)을
data/event_history.json 에 날짜와 함께 쌓는다. 소스 사이트는 지난 모습을 남기지 않아서,
이 기록은 칼랭크에만 있는 자료다. 쌓아만 두면 이용자에게는 보이지 않으므로, 가장 최근 변경을
한 장으로 공개한다. 접수 마감일이 바뀌었는지 확인하려는 참가자가 이 기록을 찾아 올 수 있다.

원칙
- 문장과 숫자는 event_history.json 에 실제로 적힌 값으로만 조립한다. 없는 변경을 지어내지 않는다.
- "처음 확인한 날"은 칼랭크가 처음 본 날이지 소스에 올라온 날이 아니다. 그렇게 쓴다.
- "목록에서 보이지 않음"은 취소가 아니다. 취소로 읽히는 표현은 쓰지 않는다.
- 아직 열리지 않은 대회(대회일이 오늘 이후)만 보여 준다. 지난 대회의 변경은 쓸모가 없다.
- 표가 몇 줄뿐이면 만들지 않는다(알맹이 없는 페이지는 사이트 전체에 해롭다).
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import generate_topic_pages as tp

ROOT = tp.ROOT
SITE = tp.SITE
KST = tp.KST
OUT = ROOT / "schedule-changes.html"
WINDOW_DAYS = 60
MIN_ROWS = 5
SHOW_ADDED = 20


def esc(s):
    return tp.esc(s)


def md(s):
    d = tp.parse_d(s)
    return f"{d.month}/{d.day}" if d else "미정"


def mdy(s):
    d = tp.parse_d(s)
    return f"{d.year}.{d.month}.{d.day}" if d else "미정"


def name_cell(ev_id, name):
    nm = esc(name or "대회")
    if ev_id and (ROOT / "e" / f"{ev_id}.html").exists():
        return f'<a href="e/{esc(quote(str(ev_id)))}.html">{nm}</a>'
    return nm


def short_list(v):
    if isinstance(v, list):
        return ", ".join(str(x) for x in v) or "없음"
    return str(v) if v not in (None, "") else "없음"


def collect(log, events, today):
    """최근 WINDOW_DAYS 일 안의 기록 중 아직 열리지 않은 대회만, 종류별로 묶는다."""
    cutoff = today - timedelta(days=WINDOW_DAYS)
    live = {e["id"]: e for e in events if e.get("id")}
    groups = {"deadline": [], "date": [], "other": [], "added": [], "dropped": []}
    restored = {x["id"] for x in log if x.get("type") == "restored"}
    for x in sorted(log, key=lambda r: (r.get("day") or "", r.get("id") or ""), reverse=True):
        day = tp.parse_d(x.get("day"))
        if not day or day < cutoff:
            continue
        ev_date = tp.parse_d(x.get("date")) or tp.parse_d((live.get(x.get("id")) or {}).get("date"))
        if x.get("type") == "moved":
            ev_date = tp.parse_d(x.get("new")) or ev_date
        if not ev_date or ev_date < today:
            continue
        t, f = x.get("type"), x.get("field")
        if t == "changed" and f == "regDeadline":
            groups["deadline"].append(x)
        elif t == "moved" or (t == "changed" and f == "date"):
            groups["date"].append(x)
        elif t == "changed":
            groups["other"].append(x)
        elif t == "added":
            groups["added"].append(x)
        elif t == "dropped" and x.get("id") not in restored and x.get("id") not in live:
            groups["dropped"].append(x)
    groups["added"] = groups["added"][:SHOW_ADDED]
    return groups


def change_text(x):
    t, f = x.get("type"), x.get("field")
    if t == "moved":
        return f"대회일 {mdy(x.get('old'))} → {mdy(x.get('new'))}"
    if f == "date":
        return f"대회일 {mdy(x.get('old'))} → {mdy(x.get('new'))}"
    if f == "regDeadline":
        return f"접수 마감 {mdy(x.get('old'))} → {mdy(x.get('new'))}"
    if f == "distances":
        return f"거리 {short_list(x.get('old'))} → {short_list(x.get('new'))}"
    if f == "location":
        return f"장소 {x.get('old') or '미정'} → {x.get('new') or '미정'}"
    if f == "applyUrl":
        return "접수 링크 바뀜"
    if f == "time":
        return f"시간 {x.get('old') or '미정'} → {x.get('new') or '미정'}"
    if f == "regClosed":
        return "접수 마감됨으로 바뀜" if x.get("new") else "접수가 다시 열림"
    return "내용 바뀜"


def table(rows, head3):
    body = "".join(rows)
    return ('<div class="tp-scroll"><table class="tp-table"><thead><tr>'
            f'<th>확인한 날</th><th>대회</th><th>{head3}</th></tr></thead><tbody>{body}</tbody></table></div>')


def render(g, today, total):
    url = f"{SITE}/schedule-changes.html"
    title = "대회 일정 변경 소식 | 접수 마감일·대회일 변경 모음 - calrank"
    n = len(g["deadline"]) + len(g["date"]) + len(g["other"])
    desc = (f"칼랭크가 매일 확인해 기록한 전국 대회 일정 변경입니다. 최근 {WINDOW_DAYS}일 동안 접수 마감일·대회일·"
            f"거리·접수 링크가 바뀐 대회 {n}곳과 새로 확인된 대회를 날짜와 함께 보여 줍니다.")
    today_ko = f"{today.year}년 {today.month}월 {today.day}일"

    def rows_for(items, with_text=True):
        out = []
        for x in items:
            third = esc(change_text(x)) if with_text else esc(f"대회일 {mdy(x.get('date'))}")
            out.append(f'<tr><td class="tp-date">{esc(md(x.get("day")))}</td>'
                       f'<td>{name_cell(x.get("id"), x.get("name"))}</td><td class="tp-note">{third}</td></tr>')
        return out

    sections = ""
    if g["deadline"]:
        sections += (f'<h2>접수 마감일이 바뀐 대회 ({len(g["deadline"])}건)</h2>'
                     + table(rows_for(g["deadline"]), "바뀐 내용"))
    if g["date"]:
        sections += (f'<h2>대회일이 바뀐 대회 ({len(g["date"])}건)</h2>'
                     + table(rows_for(g["date"]), "바뀐 내용"))
    if g["other"]:
        sections += (f'<h2>거리·장소·접수 링크가 바뀐 대회 ({len(g["other"])}건)</h2>'
                     + table(rows_for(g["other"]), "바뀐 내용"))
    if g["added"]:
        sections += (f'<h2>새로 확인된 대회 (최근 {len(g["added"])}곳)</h2>'
                     + table(rows_for(g["added"], False), "대회일"))
    if g["dropped"]:
        sections += (f'<h2>목록에서 보이지 않게 된 대회 ({len(g["dropped"])}곳)</h2>'
                     '<p>수집처 목록에서 사흘 넘게 보이지 않은 대회입니다. 취소를 뜻하지는 않으며, 수집처에서 내렸을 수도 있습니다. '
                     '참가를 준비하셨다면 주최측 공식 안내를 확인하세요.</p>'
                     + table(rows_for(g["dropped"], False), "대회일"))

    faq = [
        ("접수 마감일이 바뀌면 어디서 알 수 있나요?",
         "이 페이지에 바뀐 날짜와 함께 올라옵니다. 칼랭크는 매일 아침 대회 일정을 확인해 바뀐 값을 기록합니다. "
         "캘린더 구독(feed.ics)을 쓰시면 최신 마감일이 내 캘린더에 반영됩니다."),
        ("‘확인한 날’은 대회 일정이 바뀐 날인가요?",
         "아닙니다. 칼랭크가 바뀐 값을 처음 본 날입니다. 주최측이 실제로 바꾼 날은 이보다 앞설 수 있습니다."),
        ("여기 없는 대회는 변경이 없는 건가요?",
         "칼랭크가 수집하는 범위에서 바뀐 값이 없었다는 뜻입니다. 접수 조건 등 정확한 내용은 주최측 공식 안내에서 다시 확인해 주세요."),
    ]
    ld_blocks = "\n".join([
        tp.ld({"@context": "https://schema.org", "@type": "CollectionPage", "name": title,
               "description": desc, "url": url, "dateModified": today.isoformat(), "inLanguage": "ko"}),
        tp.ld({"@context": "https://schema.org", "@type": "FAQPage",
               "mainEntity": [{"@type": "Question", "name": q,
                               "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}),
        tp.ld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "calrank", "item": f"{SITE}/index.html"},
            {"@type": "ListItem", "position": 2, "name": "대회 일정 변경 소식"}]}),
    ])
    faq_html = "".join(f"<h3>{esc(q)}</h3><p>{esc(a)}</p>" for q, a in faq)
    page = tp.render({
        "page": "schedule-changes.html", "title": title, "h1": "대회 일정 변경 소식",
        "lead": ("칼랭크는 매일 아침 전국 대회 일정을 확인하고, 접수 마감일·대회일·거리·접수 링크가 바뀌면 날짜와 함께 기록합니다. "
                 f"그중 아직 열리지 않은 대회의 최근 {WINDOW_DAYS}일 변경만 모았습니다."),
        "desc_head": desc, "faq": faq, "related": "events-index.html", "related_label": "전국 대회 일정 전체 목록",
        "select": "changes",
    }, [], [], today)
    # 공통 생성기의 본문(표·FAQ 자리)을 이 페이지 내용으로 바꿔 끼운다.
    start = page.index('<main class="tp-wrap">')
    end = page.index("</main>")
    head_part = page[:start]
    foot_part = page[end:]
    # head 의 메타·구조화 데이터는 이 페이지용으로 다시 쓴다.
    head_part = rewrite_head(head_part, title, desc, url, ld_blocks)
    main = (f'<main class="tp-wrap">\n<h1>대회 일정 변경 소식</h1>\n'
            f'<p class="tp-sub">{esc("칼랭크는 매일 아침 전국 대회 일정을 확인하고, 접수 마감일·대회일·거리·접수 링크가 바뀌면 날짜와 함께 기록합니다. 그중 아직 열리지 않은 대회의 최근 " + str(WINDOW_DAYS) + "일 변경만 모았습니다.")}</p>\n'
            f'<p class="tp-status tp-open">{esc(today_ko)} 기준, 최근 {WINDOW_DAYS}일 동안 변경이 확인된 대회는 {n}곳입니다. '
            f'‘확인한 날’은 칼랭크가 바뀐 값을 처음 본 날입니다.</p>\n'
            f'{sections}\n'
            '<h2>다음 대회를 놓치지 않는 방법</h2>\n<div class="tp-next">\n'
            '· <a href="feed.ics">캘린더 구독(feed.ics)</a> — 새 대회와 바뀐 마감일이 내 캘린더에 자동으로 반영됩니다.<br>\n'
            '· <a href="open-registration.html">지금 접수 중인 대회</a> — 마감일이 가까운 순서로 모았습니다.<br>\n'
            '· <a href="events-index.html">전국 대회 일정 전체 목록</a> — 종목 구분 없이 월별로 모아 둔 목록입니다.\n</div>\n'
            f'<h2>자주 묻는 질문</h2>\n{faq_html}\n'
            f'<p class="tp-disclaimer">이 페이지는 칼랭크가 매일 확인한 대회 일정의 변경 기록으로 자동으로 만들어집니다. '
            f'일정과 접수 조건은 다시 바뀔 수 있으니 참가 전 공식 안내를 확인해 주세요. 마지막 갱신 기준일: {esc(today_ko)}</p>\n')
    return head_part + main + foot_part


def rewrite_head(head, title, desc, url, ld_blocks):
    """tp.render 가 만든 head 에서 제목·설명·주소·구조화 데이터를 이 페이지 값으로 바꾼다."""
    import re
    head = re.sub(r"<title>.*?</title>", f"<title>{esc(title)}</title>", head, flags=re.S)
    head = re.sub(r'(<meta name="description" content=")[^"]*(")', lambda m: m.group(1) + esc(desc) + m.group(2), head)
    for p in ('og:title', 'og:description', 'og:url'):
        val = {"og:title": esc(title), "og:description": esc(desc), "og:url": url}[p]
        head = re.sub(rf'(<meta property="{p}" content=")[^"]*(")', lambda m, v=val: m.group(1) + v + m.group(2), head)
    for p in ('twitter:title', 'twitter:description'):
        val = {"twitter:title": esc(title), "twitter:description": esc(desc)}[p]
        head = re.sub(rf'(<meta name="{p}" content=")[^"]*(")', lambda m, v=val: m.group(1) + v + m.group(2), head)
    head = re.sub(r'(<link rel="canonical" href=")[^"]*(")', lambda m: m.group(1) + url + m.group(2), head)
    head = re.sub(r'<script type="application/ld\+json">.*?</script>\s*', "", head, flags=re.S)
    head = head.replace('<link rel="stylesheet" href="style.css">', '<link rel="stylesheet" href="style.css">\n' + ld_blocks)
    return head


def main():
    events = json.loads((ROOT / "events.json").read_text(encoding="utf-8"))
    p = ROOT / "data" / "event_history.json"
    if not p.exists():
        print("[changes] event_history.json 없음 — 만들지 않음")
        return
    log = json.loads(p.read_text(encoding="utf-8")).get("log", [])
    today = datetime.now(KST).date()
    g = collect(log, events, today)
    total = sum(len(v) for v in g.values())
    if total < MIN_ROWS:
        print(f"[changes] 보여 줄 변경이 {total}건뿐 — 만들지 않음")
        return
    page = render(g, today, total)
    if not OUT.exists() or OUT.read_text(encoding="utf-8") != page:
        OUT.write_text(page, encoding="utf-8")
    print("[changes] " + ", ".join(f"{k} {len(v)}" for k, v in g.items()))


if __name__ == "__main__":
    main()

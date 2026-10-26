"""monthly 계열 네 페이지의 본문을 정적으로 채운다.

이 페이지들은 대회 목록을 monthly.js 가 실행 시점에 불러왔다. 그래서 검색엔진이
보는 본문이 "대회를 불러오는 중…" 에서 끝났고, 실제 글자수가 305~442자였다.
네이버 서치어드바이저에서 cycling-monthly 가 957노출에 27클릭, trail-monthly 는
490노출에 CTR 1.0% 였다 — 노출은 제목으로 받는데 들어오면 줄 게 없는 상태였다.

한 가지 더. "이번 달 주말" 만 싣는 설계는 종목에 따라 빈 페이지가 된다
(자전거 11월 2개, 12월 0개). 그래서 다음 달 미리보기와 연간 흐름을 같이 싣는다.

숫자는 전부 events.json 에서 센다. 지어내지 않는다.
"""
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
WDAY = ["월", "화", "수", "목", "금", "토", "일"]

PAGES = {
    "monthly.html": ("marathon", "마라톤"),
    "cycling-monthly.html": ("cycling", "자전거"),
    "trail-monthly.html": ("trail", "트레일러닝"),
    "triathlon-monthly.html": ("triathlon", "철인3종"),
}


def esc(s) -> str:
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def parse(s):
    try:
        return date.fromisoformat(str(s)[:10])
    except Exception:
        return None


def card(ev) -> str:
    d = parse(ev.get("date"))
    when = f"{d.month}.{d.day}({WDAY[d.weekday()]})" if d else ""
    dists = " · ".join(dict.fromkeys(ev.get("distances") or []))
    loc = ev.get("location") or ""
    return (f'<a class="mo-row" href="e/{quote(ev.get("id",""))}.html">'
            f'<span class="mo-date">{esc(when)}</span>'
            f'<span class="mo-name">{esc(ev.get("name"))}</span>'
            f'<span class="mo-meta">{esc(loc)}{" · " + esc(dists) if dists else ""}</span>'
            f"</a>")


def build_body(sport: str, label: str, events) -> str:
    today = date.today()
    y, m = today.year, today.month
    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)

    mine = [e for e in events if e.get("sport") == sport and parse(e.get("date"))]
    mine.sort(key=lambda e: e["date"])

    def inmonth(yy, mm, weekend_only=True):
        out = [e for e in mine if (d := parse(e["date"])).year == yy and d.month == mm]
        wk = [e for e in out if parse(e["date"]).weekday() >= 5]
        # 주말만 걸러 너무 적어지면 평일도 함께 싣는다. 빈 페이지보다 낫다.
        return wk if len(wk) >= 3 else out

    cur_all = inmonth(y, m)
    nxt_all = inmonth(ny, nm)
    # 마라톤은 한 달에 150개가 넘는다. 전부 박으면 페이지가 80KB 가 되고 읽히지도 않는다.
    CAP = 40
    cur, nxt = cur_all[:CAP], nxt_all[:CAP]
    todo = [e for e in mine if (d := parse(e["date"])) and d >= today]
    opens = [e for e in todo if e.get("regDeadline") and str(e["regDeadline"])[:10] >= today.isoformat()]

    out = []
    # 이 묶음은 monthly.js 가 같은 목록을 그린 뒤 치운다(중복 방지).
    # 자바스크립트를 실행하지 않는 크롤러에게는 그대로 남는다.
    out.append('<div id="moDupe">')
    out.append(f'<h2 class="mo-h2">{y}년 {m}월 {label} 대회 {len(cur_all)}개</h2>')
    if cur:
        out.append('<div class="mo-list">' + "\n".join(card(e) for e in cur) + "</div>")
        if len(cur_all) > CAP:
            out.append(f'<p class="mo-note">날짜순 {CAP}개만 보여 드립니다. 나머지 '
                       f'{len(cur_all) - CAP}개는 <a href="index.html?sport={sport}">전체 캘린더</a>에서 '
                       f'지역·거리로 걸러 보세요.</p>')
    else:
        out.append(f'<p class="mo-note">{m}월에 열리는 {label} 대회는 아직 등록된 것이 없습니다. '
                   f'아래 {nm}월 일정을 먼저 보시거나, '
                   f'<a href="index.html?sport={sport}">전체 캘린더</a>에서 확인하세요.</p>')

    out.append('</div>')
    out.append(f'<h2 class="mo-h2">{nm}월 미리보기 — {len(nxt_all)}개</h2>')
    if nxt:
        out.append(f'<p class="mo-note">{nm}월 대회는 지금부터 접수가 열리는 곳이 많습니다. '
                   f'마감일을 미리 확인해 두세요.</p>')
        out.append('<div class="mo-list">' + "\n".join(card(e) for e in nxt) + "</div>")
        if len(nxt_all) > CAP:
            out.append(f'<p class="mo-note">{CAP}개만 보여 드립니다. 나머지 '
                       f'{len(nxt_all) - CAP}개는 <a href="index.html?sport={sport}">전체 캘린더</a>에 있습니다.</p>')
    else:
        out.append(f'<p class="mo-note">{nm}월에는 아직 등록된 {label} 대회가 없습니다.</p>')

    # 연간 흐름 — "몇 월에 대회가 많나" 는 실제로 찾는 질문이고, 우리 자료로만 답할 수 있다.
    months = [0] * 13
    for e in mine:
        d = parse(e["date"])
        if d and d.year == y:
            months[d.month] += 1
    if sum(months) >= 6:
        peak = sorted(range(1, 13), key=lambda i: -months[i])[:3]
        peak = [i for i in peak if months[i]]
        bars = "".join(
            f'<div class="mo-bar"><span class="mo-bar-m">{i}월</span>'
            # 0 인 달은 막대를 아예 그리지 않는다. 짧은 조각이 남으면 오류처럼 보인다.
            + (f'<span class="mo-bar-f" style="width:{months[i] / max(months) * 100:.1f}%"></span>'
               if months[i] else '')
            + f'<span class="mo-bar-n">{months[i]}</span></div>'
            for i in range(1, 13))
        out.append(f'<h2 class="mo-h2">{y}년 {label} 대회는 언제 많을까</h2>')
        out.append(f'<p class="mo-note">저희가 모은 {y}년 {label} 대회 {sum(months)}개를 달별로 센 것입니다. '
                   f'가장 많은 달은 ' + " · ".join(f"{i}월 {months[i]}개" for i in peak) + ' 입니다. '
                   f'주최측이 공개하지 않은 대회는 빠져 있을 수 있습니다.</p>')
        out.append(f'<div class="mo-chart">{bars}</div>')

    if opens:
        out.append(f'<p class="mo-note" style="margin-top:22px;">지금 접수 마감일이 공개된 '
                   f'{label} 대회가 <b>{len(opens)}개</b> 있습니다. 마감일은 대회마다 다르니 '
                   f'각 대회 쪽에서 확인하세요.</p>')
    return "\n".join(out), len(cur_all)


CSS = """
<style id="moStatic">
  .mo-h2{font-size:17px;margin:30px 0 10px;}
  .mo-note{font-size:13px;line-height:1.8;color:var(--ink-faint);margin:0 0 12px;}
  .mo-list{display:flex;flex-direction:column;gap:1px;background:var(--border);
           border:1px solid var(--border);border-radius:8px;overflow:hidden;}
  .mo-row{display:block;padding:11px 13px;background:var(--surface);text-decoration:none;}
  .mo-row:hover{background:var(--tint-1);}
  .mo-date{display:inline-block;min-width:62px;font-size:12.5px;font-weight:700;
           color:var(--accent-ink);}
  .mo-name{font-size:13.5px;font-weight:700;color:var(--ink);}
  .mo-meta{display:block;margin-top:3px;font-size:12px;color:var(--ink-faint);}
  .mo-chart{display:flex;flex-direction:column;gap:4px;margin:0 0 10px;}
  .mo-bar{display:flex;align-items:center;gap:8px;font-size:12px;}
  .mo-bar-m{width:30px;color:var(--ink-faint);text-align:right;flex:none;}
  .mo-bar-f{height:12px;background:var(--accent);border-radius:2px;}
  .mo-bar-n{color:var(--ink-soft);}
  @media (max-width:680px){ .mo-date{min-width:56px;} }
</style>
"""

START = "<!-- static-monthly:start -->"
END = "<!-- static-monthly:end -->"
BLOCK = re.compile(re.escape(START) + ".*?" + re.escape(END), re.S)
# 자리표시자. monthly.js 가 나중에 덮어쓰더라도 크롤러는 정적 본문을 본다.
ANCHOR = '<section class="event-list" id="eventGrid" aria-live="polite"></section>'


def main() -> None:
    events = json.loads((ROOT / "events.json").read_text(encoding="utf-8"))
    if isinstance(events, dict):
        events = events.get("events", [])
    n = 0
    _counts = {}
    for fname, (sport, label) in PAGES.items():
        path = ROOT / fname
        if not path.exists():
            print(f"[monthly] {fname} 없음 — 건너뜀")
            continue
        html = path.read_text(encoding="utf-8")
        body, cur_n = build_body(sport, label, events)
        _counts[fname] = cur_n
        body = START + CSS + body + END
        if BLOCK.search(html):
            new = BLOCK.sub(lambda _m: body, html, count=1)
        elif ANCHOR in html:
            new = html.replace(ANCHOR, ANCHOR + "\n" + body, 1)
        else:
            print(f"[monthly] {fname} 에 넣을 자리를 못 찾음")
            continue
        # 자리표시자도 크롤러가 읽는다. 실제 개수로 바꿔 둔다(JS 가 다시 쓴다).
        new = re.sub(r'(<p class="result-count" id="resultCount">).*?(</p>)',
                     lambda mm: mm.group(1) + f"{_counts[fname]}개 대회" + mm.group(2),
                     new, count=1)
        if new != html:
            path.write_text(new, encoding="utf-8")
            n += 1
        print(f"[monthly] {fname} ({len(body)}자)")
    print(f"[monthly] {n}개 갱신")


if __name__ == "__main__":
    main()

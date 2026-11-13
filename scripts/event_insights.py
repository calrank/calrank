#!/usr/bin/env python3
"""대회 상세 페이지마다 다른 내용을 붙이는 조각들.

왜 만드나
---------
대회 상세 825장은 같은 틀에서 나온다. 틀 바깥의 글이 짧으면 "같은 틀에서 찍어 낸 얇은
페이지"로 읽힌다. 그래서 이 대회 하나의 날짜·장소·거리·주최·기온에서만 나오는 값을
계산해서 쓴다. 지어낸 값은 없고, 근거가 필요한 값은 출처를 함께 적는다.

각 함수는 값이 없으면 빈 문자열을 돌려준다. 근거 없이 문단을 채우지 않는다.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from datetime import date, timedelta
from html import escape
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
WEEKDAY = "월화수목금토일"
SPORT_LABEL = {"marathon": "마라톤", "trail": "트레일러닝", "cycling": "사이클", "triathlon": "철인3종", "inline": "인라인"}

# 2026년 공휴일. 한국천문연구원 월력요항(https://astro.kasi.re.kr/life/post/calendarData?year=2026) 기준.
# 제헌절(7/17)은 국경일 표시만 있어 공휴일로 넣지 않았다.
HOLIDAYS_2026 = {
    date(2026, 1, 1): "신정", date(2026, 2, 16): "설날 연휴", date(2026, 2, 17): "설날", date(2026, 2, 18): "설날 연휴",
    date(2026, 3, 1): "3·1절", date(2026, 3, 2): "3·1절 대체공휴일", date(2026, 5, 5): "어린이날",
    date(2026, 5, 24): "부처님오신날", date(2026, 5, 25): "부처님오신날 대체공휴일", date(2026, 6, 3): "전국동시지방선거일",
    date(2026, 6, 6): "현충일", date(2026, 8, 15): "광복절", date(2026, 8, 17): "광복절 대체공휴일",
    date(2026, 9, 24): "추석 연휴", date(2026, 9, 25): "추석", date(2026, 9, 26): "추석 연휴",
    date(2026, 10, 3): "개천절", date(2026, 10, 5): "개천절 대체공휴일", date(2026, 10, 9): "한글날",
    date(2026, 12, 25): "성탄절",
}


def esc(s) -> str:
    return escape(str(s if s is not None else ""), quote=True)


def _d(s):
    try:
        return date.fromisoformat((s or "")[:10])
    except ValueError:
        return None


def _wd(d: date) -> str:
    return WEEKDAY[d.weekday()]


def _md(d: date) -> str:
    return f"{d.month}월 {d.day}일({_wd(d)})"


def _hav(a, b, c, d):
    p = math.pi / 180
    x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))


def _ord(n: int) -> str:
    return f"{n}번째"


# ── 걷기 코스·산 (대회장 근처 찾기용) ─────────────────────────────────
_PLACES = None


def _places():
    global _PLACES
    if _PLACES is not None:
        return _PLACES
    out = {"course": [], "mountain": []}
    try:
        cs = json.loads((ROOT / "data/courses.json").read_text(encoding="utf-8")).get("courses", [])
        cs += json.loads((ROOT / "data/forest_trails.json").read_text(encoding="utf-8")).get("courses", [])
        for c in cs:
            p = c.get("path") or []
            if p:
                out["course"].append({"id": c["id"], "name": c["name"], "pts": p[::max(1, len(p) // 40)]})
    except (OSError, ValueError):
        pass
    try:
        for m in json.loads((ROOT / "data/mountains.json").read_text(encoding="utf-8")).get("mountains", []):
            pts = []
            for s in m.get("sections", []):
                pts += (s.get("path") or [])[::5]
            if not pts:
                continue
            S = m["sections"]
            hi = max(max(x.get("startM", 0), x.get("endM", 0)) for x in S)
            tot = sum(x.get("lenM", 0) for x in S) / 1000
            r = (m.get("region") or "").split()
            out["mountain"].append({"id": m["id"], "name": m["name"], "pts": pts, "hi": hi, "km": tot, "n": len(S),
                                    "where": " ".join(r[:2])})
    except (OSError, ValueError):
        pass
    _PLACES = out
    return out


def _nearest(items, lat, lng, limit_km, take):
    hits = []
    for it in items:
        d = min(_hav(lat, lng, a, b) for a, b in it["pts"])
        if d <= limit_km:
            hits.append((d, it))
    hits.sort(key=lambda t: (t[0], t[1]["id"]))
    return hits[:take]


# ── 전체 통계 (한 번만 센다) ──────────────────────────────────────────
class Stats:
    def __init__(self, events):
        self.events = [e for e in events if _d(e.get("date"))]
        self.by_sport_year = {}
        for e in self.events:
            self.by_sport_year.setdefault((e.get("sport"), _d(e["date"]).year), []).append(e)
        for v in self.by_sport_year.values():
            v.sort(key=lambda e: (e["date"], str(e.get("id"))))
        self.gaps = {}
        for e in self.events:
            dl, dt = _d(e.get("regDeadline")), _d(e["date"])
            if dl and 0 <= (dt - dl).days <= 200:
                self.gaps.setdefault(e.get("sport"), []).append((dt - dl).days)
        self.org = {}
        for e in self.events:
            o = (e.get("organizer") or "").strip()
            if o:
                self.org.setdefault(o, []).append(e)


def make_stats(events):
    return Stats(events)


# ── 1. 올해 달력에서의 자리 ───────────────────────────────────────────
def calendar_position(ev, st: Stats) -> str:
    d = _d(ev.get("date"))
    sport = ev.get("sport")
    pool = st.by_sport_year.get((sport, d.year if d else None))
    if not d or not pool or len(pool) < 5:
        return ""
    label = SPORT_LABEL.get(sport, "대회")
    n = len(pool)
    idx = next((i for i, e in enumerate(pool) if e.get("id") == ev.get("id")), None)
    if idx is None:
        return ""
    bits = []
    first = f"칼랭크에 일정이 실린 {d.year}년 {label} 대회는 {n}개입니다. 이 대회는 날짜순으로 {_ord(idx + 1)}"
    if idx == 0:
        first += "로, 그해 가장 먼저 열리는 대회입니다."
    elif idx == n - 1:
        first += "로, 그해 가장 마지막에 열리는 대회입니다."
    else:
        first += "입니다."
    bits.append(first)

    months = Counter(_d(e["date"]).month for e in pool)
    m_cnt = months[d.month]
    top = max(months.values())
    tops = [m for m, c in months.items() if c == top]
    rank = 1 + sum(1 for m, c in months.items() if c > m_cnt)
    if n >= 10:
        if m_cnt == top and len(tops) == 1 and m_cnt >= 4:
            bits.append(f"{d.month}월에는 {m_cnt}개가 몰려 있어 한 해 중 대회가 가장 많은 달입니다."
                        + ("" if d < date.today() else " 같은 날 겹치는 일정을 미리 보는 편이 좋습니다."))
        elif m_cnt <= 3:
            bits.append(f"{d.month}월에 열리는 {label} 대회는 {m_cnt}개뿐이라 비교적 조용한 달입니다.")
        else:
            bits.append(f"{d.month}월에는 {m_cnt}개가 열리고, 대회가 많은 달 순서로 {rank}위입니다.")

    wd = Counter(_d(e["date"]).weekday() for e in pool)
    share = wd[d.weekday()] * 100 / n
    if n < 10:
        pass
    elif share >= 30:
        bits.append(f"{_wd(d)}요일 대회가 전체의 {share:.0f}%라 흔한 편입니다.")
    elif share < 15:
        bits.append(f"{_wd(d)}요일에 열리는 대회는 전체의 {share:.0f}%라 드문 편입니다.")

    region = ev.get("region")
    if region and region != "전국":
        same = [e for e in pool if e.get("region") == region]
        if len(same) >= 2:
            j = next((i for i, e in enumerate(same) if e.get("id") == ev.get("id")), 0)
            bits.append(f"{region}에서는 올해 {len(same)}개 가운데 {_ord(j + 1)}로 열립니다.")

    wk_start = d - timedelta(days=d.weekday())
    wk = [e for e in pool if wk_start <= _d(e["date"]) <= wk_start + timedelta(days=6) and e.get("id") != ev.get("id")]
    if wk:
        bits.append(f"같은 주({wk_start.month}/{wk_start.day}~{(wk_start + timedelta(days=6)).month}/{(wk_start + timedelta(days=6)).day})에 전국에서 {len(wk)}개가 더 열립니다.")

    return ('<h2 class="ev-h2">올해 달력에서 이 대회의 자리</h2>'
            f'<p class="ev-p">{esc(" ".join(bits))}</p>'
            '<p class="ev-src">칼랭크가 모은 일정만 센 값이라 열리는 모든 대회를 뜻하지는 않습니다.</p>')


# ── 2. 날짜 읽기: 연휴, 접수 마감 간격, 지난 회차와의 차이 ───────────────
def _off_day(d: date) -> bool:
    return d.weekday() >= 5 or d in HOLIDAYS_2026


def _holiday_text(d: date) -> str:
    if d.year != 2026:
        return ""
    name = HOLIDAYS_2026.get(d)
    # 쉬는 날이 이어지는 길이
    lo = d
    while _off_day(lo - timedelta(days=1)):
        lo -= timedelta(days=1)
    hi = d
    while _off_day(hi + timedelta(days=1)):
        hi += timedelta(days=1)
    span = (hi - lo).days + 1
    if name and span >= 3:
        return f"이 날은 {name}이고 {_md(lo)}부터 {span}일 동안 이어지는 연휴 안에 있습니다."
    if name:
        return f"이 날은 {name}입니다."
    if span >= 3 and d.weekday() < 5:
        return f"평일이지만 {_md(lo)}부터 {span}일 쉬는 날이 이어지는 구간 안에 있습니다."
    if span >= 3:
        return f"{_md(lo)}부터 {span}일 이어지는 연휴 가운데 있어 이동·숙박이 몰릴 수 있습니다."
    nxt, prv = d + timedelta(days=1), d - timedelta(days=1)
    if d.weekday() == 5 and nxt in HOLIDAYS_2026:
        return f"다음 날이 {HOLIDAYS_2026[nxt]}이라 쉬는 날이 이틀 이어집니다."
    return ""


def date_reading(ev, st: Stats, by_norm) -> str:
    d = _d(ev.get("date"))
    if not d:
        return ""
    bits = []
    h = _holiday_text(d)
    if h:
        bits.append(h)

    dl = _d(ev.get("regDeadline"))
    if dl and 0 <= (d - dl).days <= 200:
        gap = (d - dl).days
        gaps = sorted(st.gaps.get(ev.get("sport"), []))
        label = SPORT_LABEL.get(ev.get("sport"), "대회")
        if gap == 0:
            txt = f"접수는 대회 당일인 {_md(dl)}까지 열려 있도록 적혀 있습니다."
        else:
            txt = f"접수 마감은 {_md(dl)}로 대회 {gap}일 전입니다."
        if len(gaps) >= 10:
            med = gaps[len(gaps) // 2]
            if gap + 3 < med:
                txt += f" 칼랭크에 실린 {label} 대회의 마감~대회 간격 중앙값은 {med}일이라, 이 대회는 마감이 더 늦은 편입니다."
            elif gap > med + 3:
                txt += f" {label} 대회의 중앙값은 {med}일이라 이 대회는 일찍 마감합니다."
            else:
                txt += f" {label} 대회의 중앙값 {med}일과 비슷합니다."
        bits.append(txt)

    key = ev.get("_norm")
    others = [o for o in by_norm.get(key, []) if o.get("id") != ev.get("id") and _d(o.get("date"))] if key else []
    prev = [o for o in others if _d(o["date"]) < d]
    if prev:
        p = max(prev, key=lambda o: o["date"])
        pd = _d(p["date"])
        same_year_day = date(d.year, pd.month, min(pd.day, 28))
        shift = (d - same_year_day).days
        if abs(shift) <= 1 and pd.year != d.year:
            bits.append(f"{pd.year}년 회차({_md(pd)})와 거의 같은 시기에 열립니다.")
        elif pd.year != d.year:
            bits.append(f"{pd.year}년 회차는 {pd.month}월 {pd.day}일이었고, 올해는 {abs(shift)}일 {'늦게' if shift > 0 else '일찍'} 열립니다.")
    if not bits:
        return ""
    return ('<h2 class="ev-h2">날짜로 읽는 이 대회</h2>' + "".join(f'<p class="ev-p">{esc(b)}</p>' for b in bits)
            + ('<p class="ev-src">공휴일은 한국천문연구원 월력요항 2026년 기준입니다.</p>' if h else ""))


# ── 3. 기온을 기록으로 바꾸면 ─────────────────────────────────────────
ADJ_PER_C, ADJ_REF_C, ADJ_MAX_DELTA = 0.008, 15.0, 8.0
HEAT_SRC = ("보스턴마라톤 완주 기록 분석: Nikolaidis 외, <i>Int J Environ Res Public Health</i> 2019;16:614 · "
            "Knechtle 외, <i>PLoS ONE</i> 2019;14(3):e0212797")
_EXAMPLE = {5.0: 30 * 60, 10.0: 60 * 60, 21.0975: 130 * 60, 42.195: 270 * 60}


def _hms(sec: int) -> str:
    h, r = divmod(int(round(sec)), 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _lab(km):
    return "하프" if abs(km - 21.0975) < 0.01 else "풀코스" if abs(km - 42.195) < 0.01 else f"{km:g}km"


def heat_translation(ev, kms) -> str:
    c = ev.get("climate") or {}
    if not all(k in c for k in ("minAvg", "maxAvg")) or not kms:
        return ""
    avg = (c["minAvg"] + c["maxAvg"]) / 2
    over = avg - ADJ_REF_C
    kms = [k for k in kms if k in _EXAMPLE]
    if not kms:
        return ""
    head = (f"최근 {c.get('years', 10)}년 이 날의 아침 최저와 낮 최고를 평균하면 약 {avg:.1f}도입니다(일평균을 이 두 값의 가운데로 어림한 값).")
    if over <= 0:
        body = (f"기준으로 삼는 15도보다 낮아서 더위로 기록이 깎이는 계산은 붙이지 않았습니다. 15도보다 추운 쪽은 1도당 얼마나 느려지는지 "
                "발표된 계수가 없어 숫자를 만들지 않았습니다.")
        return ('<h2 class="ev-h2">이 날 기온을 기록으로 바꾸면</h2>'
                f'<p class="ev-p">{esc(head)} {esc(body)}</p>'
                f'<p class="ev-src">{HEAT_SRC}</p>')
    delta = min(over, ADJ_MAX_DELTA)
    pct = ADJ_PER_C * delta * 100
    capped = over > ADJ_MAX_DELTA
    rows = ""
    for km in kms:
        base = _EXAMPLE[km]
        slow = base * (1 + ADJ_PER_C * delta)
        mark = "최대 " if km < 21 else ""
        rows += (f"<tr><td>{esc(_lab(km))}</td><td>{_hms(base)}</td><td>{_hms(slow)}</td><td>{mark}+{pct:.1f}%</td></tr>")
    note = ("기온 보정은 풀코스 자료에서 나온 계수(1도당 약 0.8%)이고, 짧은 거리는 더위에 노출되는 시간이 짧아 영향이 더 작을 수 있어 '최대'로 적었습니다."
            + (" 23도를 넘는 날은 관측이 적어 23도까지만 계산합니다." if capped else ""))
    return ('<h2 class="ev-h2">이 날 기온을 기록으로 바꾸면</h2>'
            f'<p class="ev-p">{esc(head)} 기준 15도보다 {over:.1f}도 높아서, 같은 몸 상태라면 시원한 날보다 {pct:.1f}% 안팎 느려질 수 있습니다.</p>'
            '<table class="ev-pace"><thead><tr><th>거리</th><th>평소 기록 예시</th><th>이 날 기온에서</th><th>차이</th></tr></thead>'
            f"<tbody>{rows}</tbody></table>"
            f'<p class="ev-src">{esc(note)} 예시 기록은 설명용 값입니다. 내 기록으로 계산하려면 등급 계산기에 넣어 보세요. · {HEAT_SRC}</p>')


# ── 4. 대회장 가까이의 산과 걷기 코스 ─────────────────────────────────
def _far(d):
    return "직선 1km 안" if d < 1 else f"직선 약 {d:.0f}km"


def around_venue(ev) -> str:
    lat, lng = ev.get("lat"), ev.get("lng")
    if not (isinstance(lat, (int, float)) and isinstance(lng, (int, float))):
        return ""
    pl = _places()
    ms = _nearest(pl["mountain"], lat, lng, 15, 3)
    cs = _nearest(pl["course"], lat, lng, 20, 3)
    if not ms and not cs:
        return ""
    out = ['<h2 class="ev-h2">대회장 가까이의 산과 걷기 코스</h2>']
    approx = " 이 대회의 좌표는 시·군 중심 기준의 어림값입니다." if ev.get("geoApprox") else ""
    out.append(f'<p class="ev-p">대회장에서 직선으로 가까운 곳입니다. 전날 몸을 풀거나 대회 뒤에 걸을 곳을 찾을 때 참고해 주세요. 도로 거리와는 다릅니다.{esc(approx)}</p>')
    if ms:
        li = "".join(
            f'<li><a href="mountain-{esc(m["id"])}.html"><b>{esc(m["name"])}</b></a> '
            f'<span>{_far(d)}{" · " + esc(m["where"]) if m["where"] else ""} · 등산로 구간 {m["n"]}개, 합계 {m["km"]:.1f}km, 구간 최고 해발 약 {m["hi"]:.0f}m</span></li>'
            for d, m in ms)
        out.append(f'<ul class="ev-list">{li}</ul>')
    if cs:
        li = "".join(
            f'<li><a href="course-{esc(c["id"])}.html"><b>{esc(c["name"])}</b></a> <span>{_far(d)}</span></li>' for d, c in cs)
        out.append(f'<ul class="ev-list">{li}</ul>')
    out.append('<p class="ev-src">자료: 산림청 등산로 구간, 한국관광공사 두루누비, 한국등산트레킹지원센터 숲길. 거리는 칼랭크가 좌표로 어림한 값입니다.</p>')
    return "".join(out)


# ── 5. 같은 주최가 여는 다른 대회 ─────────────────────────────────────
def same_organizer(ev, st: Stats) -> str:
    o = (ev.get("organizer") or "").strip()
    if not o:
        return ""
    key = ev.get("_norm")
    others = [e for e in st.org.get(o, []) if e.get("id") != ev.get("id") and e.get("_norm") != key]
    if not others:
        return ""
    others.sort(key=lambda e: e["date"])
    shown = others[:5]
    li = "".join(
        f'<li><a href="e/{esc(quote(str(e["id"])))}.html"><b>{esc(e.get("name"))}</b></a> '
        f'<span>{_d(e["date"]).year}.{_d(e["date"]).month:02d}.{_d(e["date"]).day:02d}'
        f'{" · " + esc(e["region"]) if e.get("region") else ""} · {esc(SPORT_LABEL.get(e.get("sport"), ""))}</span></li>'
        for e in shown)
    more = f" 이 밖에 {len(others) - 5}개가 더 있습니다." if len(others) > 5 else ""
    return (f'<h2 class="ev-h2">{esc(o)}의 다른 대회</h2>'
            f'<p class="ev-p">같은 주최로 적힌 대회가 {len(others)}개 더 있습니다.{esc(more)}</p>'
            f'<ul class="ev-list">{li}</ul>')


# ── 6. 종목 구성과 완주 시각 ──────────────────────────────────────────
_REG = [(42.195, "풀코스"), (21.0975, "하프"), (10.0, "10km"), (5.0, "5km")]


def _tokens(ev):
    out = []
    for item in ev.get("distances") or []:
        for part in re.split(r"[·,/]| 및 ", str(item)):
            t = part.strip()
            if t and t not in out:
                out.append(t)
    return out


def _classify(tok):
    t = tok.lower().replace(" ", "")
    if "풀" in t or "42.195" in t:
        return "reg", 42.195
    if "하프" in t or "21.0975" in t or "21.1km" in t:
        return "reg", 21.0975
    m = re.fullmatch(r"(\d+(?:\.\d+)?)(?:km|k)", t)
    if m:
        v = float(m.group(1))
        for rv, _ in _REG:
            if abs(v - rv) < 0.05:
                return "reg", rv
        return ("ultra" if v > 43 else "other"), v
    return "word", None


def distance_mix(ev, st: Stats) -> str:
    if ev.get("sport") not in ("marathon", "trail"):
        return ""      # 사이클·철인·인라인은 거리 체계가 달라 같은 말을 쓸 수 없다
    toks = _tokens(ev)
    if len(toks) < 1:
        return ""
    reg, other, ultra, word = [], [], [], []
    for t in toks:
        k, v = _classify(t)
        {"reg": reg, "other": other, "ultra": ultra, "word": word}[k].append((t, v))
    regs = sorted({v for _, v in reg}, reverse=True)
    if not (regs or other or ultra):
        return ""
    names = {42.195: "풀코스", 21.0975: "하프", 10.0: "10km", 5.0: "5km"}
    bits = [f"종목은 {len(toks)}가지로 적혀 있습니다."]
    if regs:
        key = tuple(regs)
        same = [e for e in st.events if e is not ev and tuple(sorted({v for _, v in (_classify(t) for t in _tokens(e)) if v and _classify(t)[0] == "reg"}, reverse=True)) == key
                and e.get("sport") == ev.get("sport")]
        mix = "·".join(names[v] for v in regs)
        bits.append(f"{mix}처럼 정규 거리는 같은 기준표로 칼랭크 등급을 매길 수 있습니다.")
        if len(same) >= 3:
            bits.append(f"같은 구성({mix})으로 열리는 {SPORT_LABEL.get(ev.get('sport'), '')} 대회는 이 대회 말고도 {len(same)}개입니다.")
        elif len(same) == 0:
            bits.append("이 거리 구성을 똑같이 갖춘 다른 대회는 칼랭크 일정에서 찾지 못했습니다.")
    if other and ev.get("sport") == "trail":
        bits.append("트레일러닝은 같은 거리라도 오르막에 따라 걸리는 시간이 크게 달라서, 거리만으로 기록을 견주지 않고 위의 난이도 판정을 함께 봅니다.")
    elif other:
        o = ", ".join(t for t, _ in other[:4])
        bits.append(f"{o}는 정규 거리가 아니어서 같은 거리끼리 기록을 견주기 어렵습니다. 대회가 쓰는 코스 길이를 요강에서 확인해 주세요.")
    if ultra:
        bits.append(f"{', '.join(t for t, _ in ultra[:3])}는 울트라 거리입니다. 칼랭크 등급은 마라톤(42.195km)까지만 매기고, 이 거리는 완주 중심으로 봅니다.")
    if word:
        bits.append(f"'{', '.join(t for t, _ in word[:3])}' 종목은 기록보다 참여가 중심이라 등급 기준 거리가 없습니다.")
    return ('<h2 class="ev-h2">종목 구성 읽기</h2>' f'<p class="ev-p">{esc(" ".join(bits))}</p>')


def _start_min(ev):
    t = str(ev.get("time") or "")
    if "집결" in t or "입장" in t or "접수" in t:
        return None
    m = re.search(r"(\d{1,2}):(\d{2})", t)
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    return h * 60 + mi if 0 <= h < 24 else None


_GOALS = {5.0: (25, 35), 10.0: (50, 70), 21.0975: (110, 150), 42.195: (225, 300)}


def finish_clock(ev, kms) -> str:
    st = _start_min(ev)
    kms = [k for k in kms if k in _GOALS]
    if st is None or not kms:
        return ""
    def clock(mins):
        mins = int(mins)
        h, m = divmod(mins, 60)
        return f"{h % 24}:{m:02d}" + (" (다음 날)" if h >= 24 else "")
    rows = ""
    for km in kms:
        a, b = _GOALS[km]
        rows += f"<tr><td>{esc(_lab(km))}</td><td>{a // 60 and str(a // 60) + '시간 ' or ''}{a % 60}분 → {clock(st + a)}</td><td>{b // 60 and str(b // 60) + '시간 ' or ''}{b % 60}분 → {clock(st + b)}</td></tr>"
    lat, lng, d = ev.get("lat"), ev.get("lng"), _d(ev.get("date"))
    tail = ""
    if isinstance(lat, (int, float)) and isinstance(lng, (int, float)) and d:
        try:
            import sun_times
            rise, set_ = sun_times.sun_times(float(lat), float(lng), d)
            if set_:
                last = max(_GOALS[k][1] for k in kms)
                tail = f" 그날 일몰은 {int(set_) // 60}:{int(set_) % 60:02d}라서, 가장 느린 칸도 해가 지기 {'전' if st + last < set_ else '후'}에 들어옵니다."
                if st + last >= set_:
                    tail = f" 그날 일몰은 {int(set_) // 60}:{int(set_) % 60:02d}이고, 가장 느린 칸은 일몰 뒤에 들어옵니다. 어두워질 때를 대비한 조명을 챙겨 주세요."
        except Exception:  # noqa: BLE001
            pass
    return ('<h2 class="ev-h2">출발 시각으로 본 완주 시각</h2>'
            f'<p class="ev-p">{_md_t(st)} 출발 기준으로, 빠른 쪽과 느린 쪽 완주 시간을 넣어 도착 시각을 계산했습니다. 마중 나오는 분이나 이동 계획을 세울 때 참고해 주세요.{esc(tail)}</p>'
            '<table class="ev-pace"><thead><tr><th>거리</th><th>빠른 쪽</th><th>느린 쪽</th></tr></thead>'
            f"<tbody>{rows}</tbody></table>"
            '<p class="ev-src">완주 시간은 설명용 예시이고 대회의 제한 시간과는 다릅니다.</p>')


def _md_t(m):
    return f"{m // 60}:{m % 60:02d}"


def build_all(ev, st: Stats, by_norm, kms) -> list:
    """붙일 조각들을 순서대로 돌려준다."""
    return [
        heat_translation(ev, kms),
        distance_mix(ev, st),
        finish_clock(ev, kms),
        calendar_position(ev, st),
        date_reading(ev, st, by_norm),
        around_venue(ev),
        same_organizer(ev, st),
    ]

#!/usr/bin/env python3
"""코스 페이지마다 다른 해설을 붙이는 조각들.

코스 218장은 같은 틀에서 나온다. 틀의 문장은 같아도 이 코스의 고도 단면에서만 나오는
값(정점의 위치, 가장 긴 오르막, 1km 구간별 오르막·내리막, 해 지기 전에 끝내려면 몇 시에
출발해야 하는지, 같은 길 안에서의 순위, 근처에서 열리는 대회)은 코스마다 다르다. 그런 값만
계산해서 쓴다. 근거가 없는 말은 쓰지 않는다.
"""
from __future__ import annotations

import json
import math
import re
from datetime import date
from html import escape
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent


def esc(s) -> str:
    return escape(str(s if s is not None else ""), quote=True)


def _grades(prof):
    """(시작 m, 끝 m, 시작 고도, 끝 고도, 경사 %) 조각 목록."""
    out = []
    for a, b in zip(prof, prof[1:]):
        run = b[0] - a[0]
        if run > 0:
            out.append((a[0], b[0], a[1], b[1], (b[1] - a[1]) / run * 100))
    return out


def _longest_climb(prof, slack=4.0):
    """중간에 slack(m) 이하로 내려가는 것은 한 오르막으로 본다."""
    best = None
    i = 0
    n = len(prof)
    while i < n - 1:
        j, peak_j, peak = i, i, prof[i][1]
        low_since = prof[i][1]
        k = i
        while k < n - 1:
            k += 1
            if prof[k][1] > peak:
                peak, peak_j = prof[k][1], k
                low_since = peak
            else:
                low_since = min(low_since, prof[k][1])
                if peak - low_since > slack:
                    break
        gain = peak - prof[i][1]
        length = prof[peak_j][0] - prof[i][0]
        if gain >= 15 and length > 0 and (best is None or gain > best[0]):
            best = (gain, length, prof[i][0], prof[peak_j][0])
        i = max(peak_j, i + 1)
    return best


def _window(prof, width_m, sign):
    """가장 가파른 width_m 구간. sign=+1 오르막, -1 내리막."""
    best = None
    for i in range(len(prof)):
        for j in range(i + 1, len(prof)):
            run = prof[j][0] - prof[i][0]
            if run >= width_m:
                g = (prof[j][1] - prof[i][1]) / run * 100 * sign
                if best is None or g > best[0]:
                    best = (g, prof[i][0], prof[j][0])
                break
    return best


def reading(c, stats) -> str:
    prof = c["profile"]
    if len(prof) < 8:
        return ""
    km, gain, loss, steep = stats
    el = [p[1] for p in prof]
    hi_i = max(range(len(el)), key=lambda i: el[i])
    lo_i = min(range(len(el)), key=lambda i: el[i])
    bits = []
    start, end = el[0], el[-1]
    bits.append(f"출발점은 해발 약 {start:.0f}m, 도착점은 약 {end:.0f}m입니다.")
    diff = end - start
    if abs(diff) < max(8, km * 1.5):
        bits.append("출발과 도착의 높이가 비슷해서 오르막과 내리막이 서로 상쇄되는 코스입니다.")
    elif diff > 0:
        bits.append(f"도착이 출발보다 {diff:.0f}m 높아서 전체적으로 올라가는 쪽입니다.")
    else:
        bits.append(f"도착이 출발보다 {-diff:.0f}m 낮아서 전체적으로 내려가는 쪽입니다.")
    span = el[hi_i] - el[lo_i]
    if span >= 20:
        bits.append(f"가장 높은 곳은 {prof[hi_i][0] / 1000:.1f}km 지점의 약 {el[hi_i]:.0f}m, 가장 낮은 곳은 {prof[lo_i][0] / 1000:.1f}km 지점의 약 {el[lo_i]:.0f}m로, 높이 차는 {span:.0f}m입니다.")
    else:
        bits.append(f"코스 전체의 높이 차가 {span:.0f}m에 그쳐 거의 평지로 걷게 됩니다.")
    lc = _longest_climb(prof)
    if lc:
        g, ln, a, b = lc
        bits.append(f"이어지는 가장 긴 오르막은 {a / 1000:.1f}km에서 {b / 1000:.1f}km까지 {ln / 1000:.1f}km, 약 {g:.0f}m를 올라가는 구간으로 평균 경사는 {g / ln * 100:.1f}%입니다.")
    sw = _window(prof, 300, +1)
    if sw and sw[0] >= 4:
        bits.append(f"300m 단위로 가장 가파른 곳은 {sw[1] / 1000:.1f}km 부근으로 평균 {sw[0]:.0f}%입니다.")
    dw = _window(prof, 300, -1)
    if dw and dw[0] >= 8:
        bits.append(f"내리막은 {dw[1] / 1000:.1f}km 부근 300m가 평균 {dw[0]:.0f}%로 가장 급합니다.")
    # 전반·후반
    mid = prof[-1][0] / 2
    g1 = sum(max(0, b[1] - a[1]) for a, b in zip(prof, prof[1:]) if b[0] <= mid)
    tot = sum(max(0, b[1] - a[1]) for a, b in zip(prof, prof[1:]))
    if tot >= 30:
        share2 = (tot - g1) / tot * 100
        if share2 >= 62:
            bits.append(f"오르막의 {share2:.0f}%가 후반에 몰려 있어 지친 뒤에 오르게 됩니다. 앞에서 힘을 아끼는 편이 낫습니다.")
        elif share2 <= 38:
            bits.append(f"오르막의 {100 - share2:.0f}%가 전반에 있어 몸이 풀리기 전에 올라야 합니다. 후반은 상대적으로 편합니다.")
        else:
            bits.append("오르막이 전반과 후반에 비슷하게 나뉘어 있습니다.")
    return ('<section class="tp-sec"><h2 class="tp-h2">이 코스를 고도 단면으로 읽으면</h2>'
            f'<p class="tp-p">{esc(" ".join(bits))}</p>'
            '<p class="tp-small">경로 파일의 고도를 약 50m 간격으로 다듬은 값이라 실제 현장의 작은 오르내림과는 다를 수 있습니다.</p></section>')


def per_km_table(c) -> str:
    prof = c["profile"]
    total = prof[-1][0]
    if total < 1500 or len(prof) < 8:
        return ""
    step = 1000 if total <= 21000 else 2000
    rows = ""
    k = 0
    while k * step < total:
        a, b = k * step, min((k + 1) * step, total)
        if b - a < 300:
            break
        seg = [p for p in prof if a <= p[0] <= b]
        if len(seg) < 2:
            k += 1
            continue
        up = sum(max(0, y[1] - x[1]) for x, y in zip(seg, seg[1:]))
        dn = sum(max(0, x[1] - y[1]) for x, y in zip(seg, seg[1:]))
        gr = (seg[-1][1] - seg[0][1]) / (seg[-1][0] - seg[0][0]) * 100
        lab = f"{a / 1000:.0f}~{b / 1000:.0f}km" if abs(b / 1000 - round(b / 1000)) < 0.05 else f"{a / 1000:.0f}~{b / 1000:.1f}km"
        rows += (f"<tr><td>{lab}</td><td>+{up:.0f}m</td><td>-{dn:.0f}m</td>"
                 f"<td>{gr:+.1f}%</td><td>{seg[-1][1]:.0f}m</td></tr>")
        k += 1
    if not rows:
        return ""
    unit = "1km" if step == 1000 else "2km"
    return ('<section class="tp-sec"><h2 class="tp-h2">' + unit + ' 구간별 오르막과 내리막</h2>'
            '<div class="cv-scroll"><table class="cv-table"><thead><tr><th>구간</th><th>오르막</th><th>내리막</th><th>평균 경사</th><th>끝 해발</th></tr></thead>'
            f"<tbody>{rows}</tbody></table></div>"
            '<p class="tp-small">오르막과 내리막은 구간 안에서 오른 높이와 내린 높이를 따로 더한 값이고, 평균 경사는 구간 처음과 끝의 높이 차로 계산했습니다.</p></section>')


def daylight_table(c, walk_min) -> str:
    """해 지기 전에 끝내려면 늦어도 몇 시에 출발해야 하는지."""
    if not walk_min or not c.get("path"):
        return ""
    try:
        import sun_times
    except ImportError:
        return ""
    lat, lng = c["path"][0]
    rows = ""
    for (m, d, label) in ((3, 21, "봄(3/21)"), (6, 21, "여름(6/21)"), (9, 23, "가을(9/23)"), (12, 21, "겨울(12/21)")):
        try:
            rise, st = sun_times.sun_times(float(lat), float(lng), date(2026, m, d))
        except Exception:                                        # noqa: BLE001
            return ""
        if rise is None or st is None:
            return ""
        latest = st - walk_min - 30
        rows += (f"<tr><td>{label}</td><td>{int(rise) // 60}:{int(rise) % 60:02d}</td><td>{int(st) // 60}:{int(st) % 60:02d}</td>"
                 f"<td>{int(latest) // 60}:{int(latest) % 60:02d}</td></tr>")
    h, mm = divmod(int(round(walk_min)), 60)
    t = f"{h}시간 {mm}분" if h and mm else (f"{h}시간" if h else f"{mm}분")
    return ('<section class="tp-sec"><h2 class="tp-h2">해 지기 전에 끝내려면</h2>'
            f'<p class="tp-p">이 코스를 {t} 걷는다고 보고, 일몰 30분 전에 도착하려면 늦어도 몇 시에 출발해야 하는지 계산했습니다. {esc(c.get("region") or "이 코스가 있는 곳")}에서는 계절마다 이렇게 다릅니다.</p>'
            '<table class="cv-table"><thead><tr><th>계절</th><th>일출</th><th>일몰</th><th>늦어도 출발</th></tr></thead>'
            f"<tbody>{rows}</tbody></table>"
            '<p class="tp-small">NOAA 태양 위치 계산식으로 구한 시각이고, 표준시(UTC+9) 기준입니다. 숲길은 평지보다 해가 일찍 어두워지니 여유를 더 두는 편이 안전합니다.</p></section>')


def _num(name):
    m = re.search(r"(\d+)(?:-(\d+))?\s*코스", name)
    if m:
        return (int(m.group(1)), int(m.group(2) or 0))
    return (10 ** 6, 0)


def in_the_route(c, group, label, gstats, href_for) -> str:
    """같은 길 안에서 이 코스가 어디쯤인지와 이웃 코스."""
    if not group or len(group) < 3:
        return ""
    me = c["id"]
    rows = []
    for g in group:
        k, up, dn, st = gstats(g)
        rows.append((g["id"], k, up, up / max(k, 0.1), st))
    n = len(rows)
    mine = next(r for r in rows if r[0] == me)

    def rank(idx, rev=True):
        s = sorted(rows, key=lambda r: r[idx], reverse=rev)
        return [r[0] for r in s].index(me) + 1

    bits = []
    rk, ru, rd = rank(1), rank(2), rank(3)
    bits.append(f"{label} 코스 {n}개 가운데 거리는 {rk}번째로 길고, 누적 오르막은 {ru}번째로 많고, 1km당 오르막은 {rd}번째로 가파릅니다.")
    ordered = sorted(group, key=lambda g: _num(g["name"]))
    ids = [g["id"] for g in ordered]
    i = ids.index(me)
    nav = ""
    if i > 0 or i < n - 1:
        pv, nx = (ordered[i - 1] if i > 0 else None), (ordered[i + 1] if i < n - 1 else None)
        links = []
        for lab, g in (("앞 코스", pv), ("다음 코스", nx)):
            if g:
                k, up, _, _ = gstats(g)
                links.append(f'<li><a href="{esc(href_for(g))}"><b>{esc(g["name"])}</b></a> <span class="tp-small">{lab} · {k:.1f}km · 오르막 {up:.0f}m</span></li>')
        if links:
            nav = '<ul class="cp-list">' + "".join(links) + "</ul>"
        if pv and nx:
            a = gstats(pv)[1]
            b = gstats(nx)[1]
            bits.append(f"이어서 걷는다면 앞 코스는 오르막 {a:.0f}m, 다음 코스는 {b:.0f}m입니다.")
    return (f'<section class="tp-sec"><h2 class="tp-h2">{esc(label)} 안에서 이 코스의 자리</h2>'
            f'<p class="tp-p">{esc(" ".join(bits))}</p>{nav}</section>')


_EVENTS = None


def _events():
    global _EVENTS
    if _EVENTS is None:
        try:
            _EVENTS = [e for e in json.loads((ROOT / "events.json").read_text(encoding="utf-8"))
                       if isinstance(e.get("lat"), (int, float)) and isinstance(e.get("lng"), (int, float)) and e.get("date")]
        except (OSError, ValueError):
            _EVENTS = []
    return _EVENTS


def _hav(a, b, c, d):
    p = math.pi / 180
    x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))


def nearby_events(c, limit_km=25) -> str:
    path = c.get("path") or []
    if not path:
        return ""
    pts = path[::max(1, len(path) // 20)]
    hits = []
    for e in _events():
        d = min(_hav(e["lat"], e["lng"], a, b) for a, b in pts)
        if d <= limit_km:
            hits.append((d, e))
    if not hits:
        return ""
    hits.sort(key=lambda t: (t[0], t[1]["date"]))
    chosen = sorted(hits[:5], key=lambda t: t[1]["date"])
    li = "".join(
        f'<li><a href="e/{esc(quote(str(e["id"])))}.html"><b>{esc(e.get("name"))}</b></a> '
        f'<span class="tp-small">{e["date"].replace("-", ".")} · {esc(e.get("sportLabel") or "")} · 코스에서 직선 {"1km 안" if d < 1 else f"약 {d:.0f}km"}</span></li>'
        for d, e in chosen)
    return ('<section class="tp-sec"><h2 class="tp-h2">이 코스 가까이에서 열리는 대회</h2>'
            '<p class="tp-p">코스 경로에서 직선으로 가까운 대회입니다. 대회 날짜에 맞춰 이 길을 미리 걸어 보는 분들이 있어서 모았습니다.</p>'
            f'<ul class="cp-list">{li}</ul></section>')


def build(c, stats, walk_min, group, label, gstats, href_for) -> str:
    return "\n".join(filter(None, [
        reading(c, stats),
        per_km_table(c),
        daylight_table(c, walk_min),
        in_the_route(c, group, label, gstats, href_for),
        nearby_events(c),
    ]))

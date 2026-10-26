"""도시별 '오늘 언제 뛰면 좋은가' 를 기상청 단기예보로 만든다.

왜 기온만 보나. El Helou 외(2012)가 6개 메이저 마라톤 10년치 완주자 179만 명을
분석했을 때, 습도·기압·대부분의 대기오염 물질은 유의한 영향이 없었고 기온만
뚜렷하게 남았다. 기록이 가장 잘 나오는 기온은 수준에 따라 3.8~9.9℃ 사이다.
그래서 시간대별 기온이 그 구간에 얼마나 가까운지만 보면 된다.

WBGT(습구흑구온도)는 쓰지 않는다. 기온·습도만으로 근사하는 공식은 여럿 돌아다니지만
출처를 확인하지 못했다. 안전 기준(ACSM WBGT 28℃/32.3℃)은 글로만 안내한다.

출처
  El Helou N 외 (2012) PLoS ONE 7(5):e37407
  Ely MR, Cheuvront SN, Roberts WO, Montain SJ (2007)
    Med Sci Sports Exerc 39(3):487-493
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_race_forecast import base_time, call_fcst, to_grid  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
KST = timezone(timedelta(hours=9))
OUT = ROOT / "running-weather.json"

# 기록이 가장 잘 나오는 기온대(El Helou 2012). 수준에 따라 이 범위 안에서 갈린다.
OPT_LO, OPT_HI = 3.8, 9.9

CITIES = [
    ("서울", 37.5665, 126.9780), ("부산", 35.1796, 129.0756),
    ("대구", 35.8714, 128.6014), ("인천", 37.4563, 126.7052),
    ("광주", 35.1595, 126.8526), ("대전", 36.3504, 127.3845),
    ("울산", 35.5384, 129.3114), ("수원", 37.2636, 127.0286),
    ("춘천", 37.8813, 127.7300), ("전주", 35.8242, 127.1480),
    ("포항", 36.0190, 129.3435), ("제주", 33.4996, 126.5312),
]


def gap(t):
    """최적 구간에서 몇 도 벗어났나. 구간 안이면 0."""
    if t < OPT_LO:
        return round(OPT_LO - t, 1)
    if t > OPT_HI:
        return round(t - OPT_HI, 1)
    return 0.0


def verdict(t):
    g = gap(t)
    if g == 0:
        return "최적", "기록이 가장 잘 나오는 기온대입니다."
    if t > OPT_HI:
        if g <= 5:
            return "조금 더움", "최적보다 조금 높습니다. 목표 페이스를 약간 여유 있게 잡으세요."
        if g <= 12:
            return "더움", "더위로 기록이 눈에 띄게 느려지는 구간입니다. 기록보다 완주를 기준으로."
        return "매우 더움", "기록을 노릴 조건이 아닙니다. 수분과 그늘을 먼저 챙기세요."
    if g <= 6:
        return "조금 추움", "최적보다 조금 낮습니다. 준비운동을 길게 하세요."
    return "추움", "근육이 굳기 쉽습니다. 준비운동과 보온을 신경 쓰세요."


def hourly(items, ymd):
    """그 날짜의 시간별 기온. {시: 기온}"""
    out = {}
    for it in items or []:
        if it.get("fcstDate") != ymd or it.get("category") != "TMP":
            continue
        try:
            out[int(it["fcstTime"][:2])] = float(it["fcstValue"])
        except (ValueError, KeyError, TypeError):
            continue
    return out


def main() -> None:
    key = os.environ.get("DATA_GO_KR_KEY", "").strip()
    if not key:
        print("[running-weather] DATA_GO_KR_KEY 없음 — 중단")
        sys.exit(1)

    now = datetime.now(KST)
    bd, bt = base_time(now)
    ymd = now.strftime("%Y%m%d")

    cities, fails = [], []
    for name, lat, lon in CITIES:
        nx, ny = to_grid(lat, lon)
        items, err = call_fcst(key, nx, ny, bd, bt)
        if err:
            fails.append(f"{name}: {err}")
            continue
        temps = hourly(items, ymd)
        # 아직 지나지 않은 시간만. 새벽에 돌면 하루가 다 남는다.
        rest = {h: t for h, t in temps.items() if h >= now.hour}
        if not rest:
            rest = temps
        if not rest:
            fails.append(f"{name}: 시간별 기온 없음")
            continue
        best = min(rest, key=lambda h: gap(rest[h]))
        label, note = verdict(rest[best])
        cities.append({
            "name": name,
            "hours": [{"h": h, "t": rest[h], "gap": gap(rest[h])} for h in sorted(rest)],
            "best": {"h": best, "t": rest[best], "gap": gap(rest[best]),
                     "label": label, "note": note},
        })

    data = {
        "updated": now.isoformat(timespec="seconds"),
        "base": f"{bd} {bt}",
        "optimal": [OPT_LO, OPT_HI],
        "cities": cities,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    write_page(data)
    print(f"[running-weather] 도시 {len(cities)}곳 · 실패 {len(fails)}곳")
    for f in fails[:6]:
        print("   ", f)
    if not cities:
        sys.exit(1)


def write_page(data) -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from site_nav import site_header
    html = build_page(data).replace("{header}", site_header("")) \
                           .replace("{footer}", FOOTER)
    (ROOT / SLUG).write_text(html, encoding="utf-8")
    print(f"[running-weather] {SLUG} ({len(html) // 1024}KB)")
    add_to_sitemap()


def add_to_sitemap() -> None:
    """사이트맵에 한 번만 넣는다. 매일 다시 구워도 항목이 늘지 않게."""
    sm = ROOT / "sitemap.xml"
    if not sm.exists():
        return
    xml = sm.read_text(encoding="utf-8")
    loc = f"{SITE}/{SLUG}"
    if loc in xml:
        return
    entry = (f"  <url>\n    <loc>{loc}</loc>\n"
             f"    <changefreq>daily</changefreq>\n"
             f"    <priority>0.7</priority>\n  </url>\n")
    if "</urlset>" in xml:
        sm.write_text(xml.replace("</urlset>", entry + "</urlset>"), encoding="utf-8")
        print("[running-weather] 사이트맵에 추가")


FOOTER = """<footer class="site-footer">
<div class="wrap">
<p>칼랭크(CALRANK)는 대회 주최측이 공개한 일정 정보를 정리해 제공합니다. 접수 조건 등 정확한 내용은 신청 페이지에서 다시 확인해 주세요.</p>
<p class="footer-links"><a href="terms.html">이용약관</a> · <a href="privacy.html">개인정보처리방침</a> · <a href="contact.html">제휴·광고 문의</a></p>
</div>
</footer>"""


# ── 페이지 ────────────────────────────────────────────────
# monthly 계열에서 배운 것: 자바스크립트로 그리면 크롤러가 본문을 못 본다.
# 여기서 HTML 까지 구워 둔다.
SITE = "https://calrank.vercel.app"
SLUG = "running-weather.html"


def esc(x) -> str:
    return (str(x or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def city_block(c) -> str:
    b = c["best"]
    cls = {"최적": "rw-ok", "조금 더움": "rw-warm", "더움": "rw-hot",
           "매우 더움": "rw-vhot", "조금 추움": "rw-cool", "추움": "rw-cold"}.get(b["label"], "")
    hours = "".join(
        f'<span class="rw-h {"rw-pick" if h["h"] == b["h"] else ""}">'
        f'<i>{h["h"]}시</i><b>{h["t"]:g}°</b></span>'
        for h in c["hours"])
    return (f'<div class="rw-city">'
            f'<div class="rw-head"><h3>{esc(c["name"])}</h3>'
            f'<span class="rw-badge {cls}">{esc(b["label"])}</span></div>'
            f'<p class="rw-best">가장 좋은 시간 <b>{b["h"]}시</b> · <b>{b["t"]:g}℃</b>'
            + (f' · 최적 구간에서 {b["gap"]:g}℃ 벗어남' if b["gap"] else " · 최적 구간 안") + "</p>"
            f'<p class="rw-note">{esc(b["note"])}</p>'
            f'<div class="rw-hours">{hours}</div></div>')


def build_page(data) -> str:
    when = data["updated"][:16].replace("T", " ")
    lo, hi = data["optimal"]
    cities = "\n".join(city_block(c) for c in data["cities"])
    title = "오늘 달리기 좋은 시간 — 도시별 기온으로 보는 러닝 지수 | 칼랭크 CALRANK"
    desc = (f"기록이 가장 잘 나오는 기온은 {lo}~{hi}℃입니다(완주자 179만 명 분석). "
            f"오늘 도시별 시간대 기온을 그 기준에 맞춰 정리했습니다. {when} 기준.")
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
<meta property="og:url" content="{SITE}/{SLUG}">
<meta property="og:locale" content="ko_KR">
<link rel="canonical" href="{SITE}/{SLUG}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap" rel="stylesheet">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#0B0B0B">
<link rel="stylesheet" href="style.css">
<style>
  .rw-wrap{{max-width:760px;margin:0 auto;padding:44px 20px 80px;}}
  .rw-title{{font-family:var(--font-display);font-size:clamp(23px,3.4vw,32px);line-height:1.3;margin-bottom:12px;}}
  .rw-lead{{font-size:14.5px;line-height:1.85;color:var(--ink-soft);margin:0 0 6px;}}
  .rw-when{{font-size:12.5px;color:var(--ink-faint);margin:0 0 26px;}}
  .rw-city{{border:1px solid var(--border);border-radius:10px;padding:14px 15px;margin:0 0 10px;background:var(--surface);}}
  .rw-head{{display:flex;align-items:center;gap:9px;margin:0 0 6px;}}
  .rw-head h3{{font-size:15.5px;margin:0;}}
  .rw-badge{{font-size:11.5px;font-weight:700;padding:2px 9px;border-radius:999px;border:1px solid var(--border);color:var(--ink-soft);}}
  .rw-ok{{border-color:var(--accent);color:var(--accent-ink);}}
  .rw-hot,.rw-vhot{{border-color:var(--accent);background:rgba(255,61,26,.10);color:var(--accent-ink);}}
  .rw-best{{font-size:13.5px;margin:0 0 4px;color:var(--ink);}}
  .rw-note{{font-size:12.5px;line-height:1.7;color:var(--ink-faint);margin:0 0 10px;}}
  .rw-hours{{display:flex;gap:5px;overflow-x:auto;padding-bottom:2px;}}
  .rw-h{{flex:none;display:flex;flex-direction:column;align-items:center;gap:2px;
         min-width:40px;padding:6px 4px;border-radius:7px;background:var(--tint-1);}}
  .rw-h i{{font-style:normal;font-size:11px;color:var(--ink-faint);}}
  .rw-h b{{font-size:13px;color:var(--ink);}}
  .rw-pick{{background:var(--accent);}}
  .rw-pick i,.rw-pick b{{color:var(--on-accent);}}
  .rw-src{{margin-top:30px;padding:16px 18px;border:1px solid var(--border);border-radius:10px;
           font-size:12.5px;line-height:1.85;color:var(--ink-faint);background:var(--surface);}}
  .rw-src b{{color:var(--ink);}}
  @media(max-width:680px){{.rw-wrap{{padding:30px 14px 70px;}}}}
</style>
</head>
<body>
{{header}}
<main class="rw-wrap">
<h1 class="rw-title">오늘 달리기 좋은 시간</h1>
<p class="rw-lead">기록이 가장 잘 나오는 기온은 <b>{lo}~{hi}℃</b>입니다. 6개 메이저 마라톤
10년치 완주자 179만 명을 분석한 연구에서 나온 값이고, 빠른 러너일수록 더 낮은 쪽입니다.
아래는 오늘 남은 시간대의 기온을 그 기준에 맞춰 본 것입니다.</p>
<p class="rw-when">기상청 단기예보 {esc(data["base"])} 발표 기준 · {esc(when)} 갱신</p>

{cities}

<div class="rw-src">
<b>이 페이지의 근거</b><br>
· 기온과 기록: El Helou N, Tafflet M, Berthelot G 외 (2012).
<em>Impact of Environmental Parameters on Marathon Running Performance.</em>
PLoS ONE 7(5):e37407. 파리·런던·베를린·보스턴·시카고·뉴욕 6개 대회 10년치,
완주자 179만 1,972명. 습도·기압·대부분의 대기오염 물질은 유의한 영향이 없었고
기온만 뚜렷했습니다.<br>
· 더울 때 얼마나 느려지나: Ely MR 외 (2007). <em>Impact of weather on marathon-running
performance.</em> Medicine &amp; Science in Sports &amp; Exercise 39(3):487-493.
습구흑구온도(WBGT) 20.1~25℃ 구간에서 남자 상위권이 코스 기록 대비 4.5%,
여자 상위권이 5.4% 느렸습니다. <b>느린 러너일수록 더 많이 느려진다</b>고 밝히고 있어,
동호인에게는 이 수치가 하한입니다.<br>
· 안전: 미국스포츠의학회 열질환 입장문은 WBGT 28℃를 넘으면 대회 취소·일정 변경을,
32.3℃ 이상이면 취소를 권고합니다. WBGT는 햇볕과 습도까지 반영하므로 같은 날
기온보다 높게 나옵니다. 이 페이지는 기온만 다루니, 한여름에는 기온이 낮아 보여도
안전 기준은 따로 보셔야 합니다.<br>
· 기온 자료: 기상청 단기예보 (공공데이터포털)<br><br>
시간대별 기온은 예보값이라 실제와 다를 수 있습니다. 기록 목표는 참고용이고,
몸 상태와 안전이 먼저입니다.
</div>

<p style="margin-top:26px;font-size:13.5px;">
<a href="level.html" style="color:var(--accent-ink);">내 기록이 어느 등급인지 확인하기 →</a><br>
<a href="index.html" style="color:var(--accent-ink);">다가오는 대회 일정 보기 →</a></p>
</main>
{{footer}}
</body>
</html>
"""


if __name__ == "__main__":
    main()

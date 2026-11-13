#!/usr/bin/env python3
"""대회 심화 가이드 칼럼 4개를 '확인된 사실 + 칼랭크가 계산한 값'으로 다시 쓴다.

예전 글은 러닝위키·나무위키 같은 커뮤니티 글을 옮겨 적은 것이라 새로운 정보가 없었고,
고도·난이도 문장은 근거를 확인할 수 없었다. 이번 글은 아래 원칙으로 쓴다.

- 근거를 확인한 사실만 쓴다. 출처는 문장마다 표에 적는다.
- 칼랭크가 가진 자료로 직접 계산한 값을 넣는다: 대회일 기온(기상청 ASOS 10년),
  기온 보정(level.js 와 같은 계수), 목표 기록별 칼랭크 등급(WMA), 카본화 단축(기어 판정 모델).
- 확인하지 못한 것(코스 고도 등)은 그렇다고 적고, 추측으로 채우지 않는다.

쓰임: python3 scripts/rewrite_course_guides.py
(본문 <main> 과 제목·설명만 바꾼다. 머리글·바닥글·목록 카드는 건드리지 않는다.)
"""
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_event_pages as gep  # noqa: E402
import wma_standards as wma  # noqa: E402
from gear_table_data import RUN_GOALS, tier_bounds, tier_of, run_model  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ADJ_PER_C, ADJ_REF_C, ADJ_MAX_DELTA = 0.008, 15.0, 8.0     # level.js 와 같은 값
BOUNDS = tier_bounds()


def esc(s):
    return html.escape(str(s), quote=True)


def clock(sec):
    sec = int(round(sec))
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def gap(sec):
    sec = int(round(sec))
    m, s = divmod(sec, 60)
    return f"{m}분 {s}초" if m and s else (f"{m}분" if m else f"{s}초")


def load_events():
    ev = json.loads((ROOT / "events.json").read_text(encoding="utf-8"))
    gep.attach_climate(ev)
    return {e["id"]: e for e in ev}


def mean_temp(c):
    return (c["minAvg"] + c["maxAvg"]) / 2


def heat_adjust(c):
    """level.js climateAdjust 와 같은 식. 일평균기온이 15℃ 를 넘을 때만 보정."""
    over = mean_temp(c) - ADJ_REF_C
    if over <= 0:
        return None
    delta = min(over, ADJ_MAX_DELTA)
    return {"over": over, "delta": delta, "pct": ADJ_PER_C * delta * 100, "capped": over > ADJ_MAX_DELTA}


SRC = {
    "asos": '기상청 종관기상관측(ASOS) 일자료, 최근 10년 같은 날짜 평균 — <a href="https://data.kma.go.kr" rel="noopener">data.kma.go.kr</a>',
    "elhelou": 'El Helou N 외, Impact of environmental parameters on marathon running performance. <i>PLoS ONE</i> 2012;7(5):e37407 — <a href="https://doi.org/10.1371/journal.pone.0037407" rel="noopener">doi</a>',
    "nikol": 'Nikolaidis PT 외, <i>Int J Environ Res Public Health</i> 2019;16(4):614 · Knechtle B 외, <i>PLoS ONE</i> 2019;14(3):e0212797',
    "haney": 'Haney DE Jr, Mercer JA. A description of variability of pacing in marathon distance running. <i>Int J Exerc Sci</i> 2011;4(2):133-140 — <a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC4738997" rel="noopener">PMC4738997</a>',
    "ely": 'Ely MR 외, Impact of weather on marathon-running performance. <i>Med Sci Sports Exerc</i> 2007;39(3):487-493',
    "wa": 'World Athletics, Label Road Races (2026 캘린더 목록) — <a href="https://www.worldathletics.org/competitions/world-athletics-label-road-races" rel="noopener">worldathletics.org</a>, 2026-11-13 확인',
    "wa_reg": 'World Athletics, C1.6 Label Road Race Regulations 2026, 10.2 (코스 계측)',
    "wma": '세계마스터즈육상연맹(WMA) 연령 기준표 — 칼랭크 등급 계산 방식은 <a href="grade-method.html">칼랭크 등급은 어떻게 매기나</a>',
    "gear": '기어 판정 모델 — <a href="gear-carbon-plate-full.html">풀코스 카본화 효과</a>, 근거 등급과 원 논문은 해당 페이지에 있음',
}


def fact_table(rows):
    body = "".join(f"<tr><th>{esc(k)}</th><td>{v}</td><td>{s}</td></tr>" for k, v, s in rows)
    return ('<div class="table-scroll"><table class="segment-table"><thead><tr><th>항목</th><th>내용</th><th>출처</th></tr></thead>'
            f"<tbody>{body}</tbody></table></div>")


def goals_table(dist_key, km, dist_label, adj=None):
    """목표 기록별 페이스·칼랭크 등급(40대 남녀)·카본화 단축. adj 가 있으면 15℃ 환산 칸을 더한다."""
    goals = RUN_GOALS[dist_key]
    res = run_model([{"claim": "carbon-plate", "input": {"finishSec": s, "distanceKm": km}} for s, _ in goals])
    head = "<tr><th>목표</th><th>km당</th><th>40대 남성</th><th>40대 여성</th><th>카본화 평균 단축</th>"
    head += ("<th>15℃ 환산</th>" if adj else "") + "</tr>"
    rows = ""
    for (sec, label), r in zip(goals, res):
        e = r["effects"][0] if r and r.get("effects") else None
        cut = "—"
        if e and e.get("cutSec"):
            pt = abs(e["cutSec"]["point"])
            cut = "유의하지 않음" if e.get("significant") is False else f'{gap(pt)} (근거 {e["grade"]})'
        tm = tier_of(wma.age_grade(sec, "male", dist_key, 40), BOUNDS)
        tf = tier_of(wma.age_grade(sec, "female", dist_key, 40), BOUNDS)
        pace = sec / km
        cell = ""
        if adj:
            cell = f"<td>{clock(sec / (1 + ADJ_PER_C * adj['delta']))}</td>"
        rows += (f"<tr><th>{esc(label)}</th><td>{int(pace) // 60}:{int(pace) % 60:02d}</td>"
                 f"<td>{esc(tm)}</td><td>{esc(tf)}</td><td>{cut}</td>{cell}</tr>")
    return f'<div class="table-scroll"><table class="segment-table"><thead>{head}</thead><tbody>{rows}</tbody></table></div>'


def weather_block(ev, title_when):
    c = ev["climate"]
    m = mean_temp(c)
    adj = heat_adjust(c)
    lines = [
        f'{title_when} 최근 {c["years"]}년 기록으로 아침 최저 평균 {c["minAvg"]:.1f}℃, 낮 최고 평균 {c["maxAvg"]:.1f}℃였고, '
        f'가장 더웠던 {c["hottestYear"]}년에는 {c["hottestMax"]:.1f}℃까지 올랐음. '
        f'비가 온 해는 {c["years"]}년 중 {c["rainYears"]}번. {c["station"]} 관측소 기준이며 대회장과 {c["stationKm"]}km 떨어져 있음.'
    ]
    if adj is None:
        lines.append(f'일평균기온은 약 {m:.1f}℃로 보정 기준인 {ADJ_REF_C:g}℃ 이하임. 칼랭크 기준으로는 더위 보정이 붙지 않는 날씨임.')
    else:
        cap = " (보정 상한 8℃에서 자름)" if adj["capped"] else ""
        lines.append(f'일평균기온은 약 {m:.1f}℃로 보정 기준 {ADJ_REF_C:g}℃보다 {adj["over"]:.1f}℃ 높음{cap}. '
                     f'풀코스 기준 계수 {ADJ_PER_C * 100:.1f}%/℃를 적용하면 같은 몸으로 {ADJ_REF_C:g}℃에서 뛴 기록보다 약 {adj["pct"]:.1f}% 느린 날씨임.')
    return lines, adj


def page(title, desc, meta, body_html):
    return title, desc, meta, body_html


# ── 춘천마라톤 ─────────────────────────────────────────────────────────
def build_chuncheon(E):
    ev = E["rr-2026-춘천마라톤-2026-10-25"]
    lines, adj = weather_block(ev, "10월 25일 춘천의")
    c = ev["climate"]
    swing = c["maxAvg"] - c["minAvg"]
    body = f"""
<p>춘천마라톤 2026년 대회는 {esc(ev['date'])} 열리는 풀코스·10km 대회임. 이 글은 대회일 날씨와 목표 기록별 기준을 칼랭크가 가진 자료로 계산해 정리한 것임. 코스 고도는 공식 자료를 확인하지 못해 수치를 싣지 않았음.</p>
<h2>확인된 대회 정보</h2>
{fact_table([
    ("일시", esc(ev["date"]), "칼랭크 대회 일정(주최측 공개 내용 정리)"),
    ("장소", esc(ev.get("location") or "미확인"), "칼랭크 대회 일정"),
    ("종목", esc(" · ".join(gep.dedupe_distances(ev["distances"]))), "칼랭크 대회 일정"),
])}
<h2>대회일 날씨</h2>
<p>{lines[0]}</p>
<p>{lines[1]}</p>
<p>하루 기온 폭은 {swing:.1f}℃임. El Helou 등(2012)은 완주자 1,791,972명의 기록에서 기온이 3.8~9.9℃일 때 기록이 가장 좋았다고 분석했음. 아침 최저 평균은 이 구간보다 낮고 낮 최고 평균은 이 구간보다 높아서, 출발 때는 겉옷을 입고 뛰는 동안 벗을 수 있는 차림이 필요한 날씨임.</p>
<p>Ely 등(2007)은 7개 마라톤 대회 자료에서 습구흑구온도(WBGT)가 5℃에서 25℃로 오르는 동안 기록이 단계적으로 느려졌고, 느린 주자일수록 영향이 컸다고 보고했음. 같은 논문에서 상위 남성 선수의 코스 기록 대비 느려진 폭은 WBGT 5.1~10℃ 구간 1.7%, 20.1~25℃ 구간 4.5%였음.</p>
<h2>목표 기록별 기준</h2>
<p>풀코스 목표 기록별 km당 페이스와 칼랭크 등급임. 등급은 40대 기준이고, 나이와 성별을 바꿔 보려면 <a href="level.html?d=42.195">등급 계산기</a>를 쓰면 됨. 카본화 단축은 기어 판정 모델의 평균 효과이며, 통계적으로 유의하지 않은 속도 구간은 그렇게 표시했음.</p>
{goals_table("full", 42.195, "풀코스")}
<h2>페이스 배분</h2>
<p>Haney와 Mercer(2011)는 마라톤 2개 대회의 GPS 기록 285건에서 속도 변동계수(CV)를 계산했음. 완주 3.9시간 미만은 12.3~13.2%, 3.9~4.6시간은 15.1~15.9%, 4.6시간 초과는 21.5~22.2%였음. 완주 시간이 느릴수록 속도 변동이 컸고, 완주 시간과 변동계수의 회귀 설명력(R²)은 0.46이었음. 이 결과는 상관 관계이며, 변동을 줄이면 기록이 빨라진다는 인과를 보인 것은 아님.</p>
<p>이 자료로 말할 수 있는 것은, 목표 기록이 같은 주자 사이에서도 구간마다 속도를 크게 흔드는 쪽이 느린 기록과 함께 나타났다는 점임. 목표 페이스를 표의 km당 값 안팎에서 일정하게 유지하는 계획이 이 자료와 맞음.</p>
<h2>코스 고도</h2>
<p>주최측이 공개한 공식 고저차·누적 오르막 자료를 확인하지 못했음. 제3자가 올린 GPX 분석 글은 있으나 공식 파일인지 확인되지 않고 글 안의 합계 수치도 서로 맞지 않아 인용하지 않았음. 공식 GPX가 공개되면 <a href="yardage.html">대회 코스 야디지북</a>에 올려 구간별 경사와 목표 기록별 통과 시간을 볼 수 있음. 파일은 이 기기 밖으로 나가지 않음.</p>
<div class="source-box"><strong>📌 이 글의 출처</strong><br>
· {SRC['asos']}<br>· {SRC['elhelou']}<br>· {SRC['ely']}<br>· {SRC['haney']}<br>· {SRC['wma']}<br>· {SRC['gear']}</div>
<div class="column-cta"><p>춘천마라톤 접수 일정과 상세 정보는 칼랭크 대회 페이지에서 확인할 수 있음.</p>
<a href="e/{esc(quote_id(ev['id']))}.html">춘천마라톤 대회 상세보기 →</a></div>
"""
    return ("춘천마라톤 대회일 날씨와 목표 기록별 기준 — 기온 10년 평균과 칼랭크 등급",
            "춘천마라톤 대회일의 최근 10년 기온, 풀코스 목표 기록별 페이스와 칼랭크 등급, 카본화 평균 단축을 기상청 자료와 논문 근거로 계산했습니다.",
            "🏔️ 대회 심화 가이드 · 마라톤", body)


def quote_id(i):
    from urllib.parse import quote
    return quote(i)


# ── 서울마라톤 vs JTBC ─────────────────────────────────────────────────
def build_seoul_jtbc(E):
    a = E["rm-2026-서울마라톤-2026-03-15"]
    b = E["ro-서울국제마라톤-2026-11-01"]
    ca, cb = a["climate"], b["climate"]
    ra, rb = heat_adjust(ca), heat_adjust(cb)

    def row(label, f):
        return f"<tr><th>{label}</th><td>{f(ca)}</td><td>{f(cb)}</td></tr>"

    table = ('<div class="table-scroll"><table class="segment-table"><thead><tr><th>서울 · 최근 10년 평균</th><th>3월 15일 (서울마라톤)</th><th>11월 1일 (JTBC 서울마라톤)</th></tr></thead><tbody>'
             + row("아침 최저 평균", lambda c: f"{c['minAvg']:.1f}℃")
             + row("낮 최고 평균", lambda c: f"{c['maxAvg']:.1f}℃")
             + row("일평균(최저·최고의 중간)", lambda c: f"{mean_temp(c):.1f}℃")
             + row("가장 더웠던 해", lambda c: f"{c['hottestYear']}년 {c['hottestMax']:.1f}℃")
             + row("비가 온 해", lambda c: f"{c['years']}년 중 {c['rainYears']}번")
             + row("15℃ 기준 더위 보정", lambda c: "없음" if heat_adjust(c) is None else f"{heat_adjust(c)['pct']:.1f}%")
             + "</tbody></table></div>")
    diff = mean_temp(cb) - mean_temp(ca)
    body = f"""
<p>같은 서울에서 열리는 두 풀코스 대회의 대회일 날씨를 같은 방식으로 비교함. 기온은 기상청 서울 관측소의 최근 10년 같은 날짜 평균이고, 칼랭크 대회 일정 기준 날짜는 서울마라톤 {esc(a['date'])}, 11월 대회 {esc(b['date'])}임.</p>
<h2>대회일 날씨 비교</h2>
{table}
<p>일평균기온은 11월 1일이 3월 15일보다 {diff:.1f}℃ 높음. 두 날 모두 15℃ 이하여서 칼랭크 기준의 더위 보정은 붙지 않음. 가장 더웠던 해의 낮 최고기온은 3월 15일이 {ca['hottestMax']:.1f}℃({ca['hottestYear']}년), 11월 1일이 {cb['hottestMax']:.1f}℃({cb['hottestYear']}년)로, 11월 쪽에서 더 높은 값이 나왔음.</p>
<p>아침 최저 평균은 3월 15일이 {ca['minAvg']:.1f}℃로 영하에 가깝고 11월 1일은 {cb['minAvg']:.1f}℃임. El Helou 등(2012)의 최적 구간(3.8~9.9℃)을 기준으로 보면 두 날 모두 아침 최저 평균이 구간보다 낮고(3월 15일 {ca['minAvg']:.1f}℃, 11월 1일 {cb['minAvg']:.1f}℃), 낮 최고 평균은 구간을 넘음. 11월 1일의 아침 최저 평균은 구간 하단 3.8℃에 {3.8 - cb['minAvg']:.1f}℃ 못 미치는 값임.</p>
<h2>확인된 대회 정보</h2>
{fact_table([
    ("세계육상연맹 라벨 로드레이스 2026 목록", "한국 대회로 확인된 것은 대구(2/22), 서울(3/15), 군산 새만금(4/5), 경주(10/17) 마라톤 4개. 서울마라톤은 포함, JTBC 서울마라톤은 이 목록에서 확인되지 않음", SRC['wa']),
    ("라벨 대회의 코스 요건", "World Athletics 국제 계측 증명서가 대회 당일 유효해야 함", SRC['wa_reg']),
    ("목록의 라벨 등급", "해당 페이지에 등급(골드·실버 등) 표기가 없어 이 글에서도 등급은 적지 않음", SRC['wa']),
])}
<h2>코스 비교는 싣지 않은 이유</h2>
<p>두 대회의 고저차·누적 오르막을 주최측 공식 자료로 확인하지 못했음. 커뮤니티 글에는 구간별 난이도 서술이 있으나 계측 근거를 확인할 수 없어 인용하지 않았음. 공식 GPX를 구하면 <a href="yardage.html">대회 코스 야디지북</a>에서 같은 기준으로 두 코스를 구간별로 비교할 수 있음.</p>
<h2>어느 쪽이 기록에 유리한가</h2>
<p>날씨만으로 보면 3월 15일은 아침 기온이 영하에 가까워 방한 준비가 필요하고, 11월 1일은 아침 기온이 최적 구간 하단 근처임. 두 날 모두 평년 일평균이 15℃ 이하라서, 같은 능력의 주자가 날씨 때문에 잃는 기록은 칼랭크 기준으로 0임. 날씨 외 변수(코스 고도, 출발 인원, 접수 방식)는 이 글에서 다루지 않았음.</p>
<div class="source-box"><strong>📌 이 글의 출처</strong><br>
· {SRC['asos']}<br>· {SRC['elhelou']}<br>· {SRC['nikol']}<br>· {SRC['wa']}<br>· {SRC['wa_reg']}</div>
<div class="column-cta"><p>두 대회의 접수 일정과 상세 정보는 칼랭크 대회 페이지에서 확인할 수 있음.</p>
<a href="e/{esc(quote_id(a['id']))}.html">서울마라톤 상세보기 →</a>
<a href="e/{esc(quote_id(b['id']))}.html" style="margin-left:8px;">11월 서울 대회 상세보기 →</a></div>
"""
    return ("서울마라톤 3월과 JTBC 서울마라톤 11월 — 대회일 날씨 10년 비교",
            "서울에서 열리는 두 풀코스 대회의 대회일 평균 기온, 최고 기온, 강수일을 기상청 10년 자료로 비교하고 세계육상연맹 라벨 목록 포함 여부를 확인했습니다.",
            "🏔️ 대회 심화 가이드 · 마라톤", body)


# ── 대구마라톤 ─────────────────────────────────────────────────────────
def build_daegu(E):
    km109 = 10.9
    rows = ""
    for mins in (50, 55, 60, 65, 70):
        sec = mins * 60
        pace = sec / km109
        rows += (f"<tr><th>{mins}분</th><td>{int(pace) // 60}:{int(pace) % 60:02d}</td>"
                 f"<td>{clock(pace * 10)}</td></tr>")
    t109 = ('<div class="table-scroll"><table class="segment-table"><thead><tr><th>10.9km 목표</th><th>km당</th><th>같은 페이스의 10km 기록</th></tr></thead>'
            f"<tbody>{rows}</tbody></table></div>")
    body = f"""
<p>2026 대구마라톤은 2월 22일 오전 9시 대구스타디움에서 열린 25회 대회임. 이 글은 대구시 발표를 보도한 기사 두 건에서 확인한 사실과, 10.9km 종목의 목표 기록 계산을 정리한 것임.</p>
<h2>확인된 대회 정보</h2>
{fact_table([
    ("일시·장소", "2026년 2월 22일(일) 09:00, 대구스타디움", '시사뉴스 2026-02-12, 전국매일신문 2026-02-12'),
    ("라벨", "세계육상연맹(WA) 골드라벨, 4년 연속", '대구시 발표 보도(위 두 기사), 대회 공식 사이트 영문 안내의 "WA Gold Label" 표기'),
    ("참가", "엘리트 약 150명(15개국), 마스터즈 41,104명(34개국)", '시사뉴스, 전국매일신문'),
    ("종목", "엘리트 풀코스, 마스터즈 풀코스, 10.9km, 건강달리기", '시사뉴스, 전국매일신문'),
    ("코스 변경", "35km 이후 구간의 고저차 약 10m 완화, 반환점을 2개소에서 1개소로 축소", '시사뉴스(2→1 명시), 전국매일신문(복수→1)'),
    ("우승 상금", "16만 달러에서 20만 달러로 인상", '시사뉴스, 전국매일신문'),
])}
<p>코스 변경은 시사뉴스가 세계 기록 도전을 지원하기 위한 조치라고 전했음. 두 기사 모두 완화된 고저차의 절대 높이나 코스 전체의 누적 오르막 수치는 밝히지 않았고, 이 글도 그 수치를 만들어 싣지 않음.</p>
<h2>10.9km 종목의 목표 기록</h2>
<p>마스터즈 10km 종목의 실제 거리는 10.9km임(시사뉴스, 전국매일신문). 10km 표의 페이스(기록÷10)를 그대로 쓰면 같은 기록에 필요한 페이스보다 약 9% 느려서 목표에 닿지 못하므로, 거리에 맞춰 계산해야 함. 아래는 10.9km 목표 기록별 km당 페이스와, 같은 페이스로 10km를 뛰었을 때의 기록임. 세계마스터즈육상연맹은 10.9km 기준기록을 내지 않아서 이 종목에는 칼랭크 등급을 매기지 않음. 같은 페이스의 10km 기록을 <a href="level.html?d=10">10km 등급 계산기</a>에 넣어 대략의 수준을 볼 수는 있음.</p>
{t109}
<h2>풀코스 목표 기록별 기준</h2>
<p>풀코스 목표 기록별 km당 페이스와 칼랭크 등급(40대 기준), 카본화 평균 단축임. 마스터즈 풀코스 참가자가 자기 목표를 가늠하는 용도임.</p>
{goals_table("full", 42.195, "풀코스")}
<h2>코스 고도</h2>
<p>대구마라톤 공식 사이트와 위 기사에서 코스 전체의 고저차나 누적 오르막 자료를 확인하지 못했음. 대구 2월 22일의 평년 기온은 칼랭크 대회 일정의 해당 일자 자료가 없어 계산하지 못했음. 공식 GPX가 공개되면 <a href="yardage.html">대회 코스 야디지북</a>에서 구간별로 확인할 수 있음.</p>
<div class="source-box"><strong>📌 이 글의 출처</strong><br>
· 시사뉴스, 하정수 기자, '완벽한 안전, 품격 있는 레이스, 최정상의 선수! 대구 시민과 함께하는 「2026대구마라톤」' (2026-02-12) — <a href="https://www.sisa-news.com/news/article.html?no=266219" rel="noopener">원문</a><br>
· 전국매일신문, 신용대 기자, '대구시, 2026대구마라톤 열어' (2026-02-12) — <a href="https://www.jeonmae.co.kr/news/articleView.html?idxno=1230904" rel="noopener">원문</a><br>
· 대구마라톤 공식 사이트(영문), 대회명 표기 — <a href="https://daegumarathon.daegu.go.kr/englishpage.php" rel="noopener">daegumarathon.daegu.go.kr</a><br>
· {SRC['wma']}<br>· {SRC['gear']}</div>
<div class="column-cta"><p>대구마라톤 일정과 접수 정보는 칼랭크 대회 페이지에서 확인할 수 있음.</p>
<a href="events-index.html">전체 대회 일정 보기 →</a></div>
"""
    return ("대구마라톤 2026 확인된 사실과 10.9km 종목 목표 기록표 — 골드라벨·코스 변경",
            "2026 대구마라톤의 일시, 골드라벨, 참가 규모, 코스 변경을 대구시 발표 보도로 확인하고, 실제 거리 10.9km 종목의 목표 기록별 페이스를 계산했습니다.",
            "🏔️ 대회 심화 가이드 · 마라톤", body)


# ── 밤섬마라톤 ─────────────────────────────────────────────────────────
def build_bamseom(E):
    may = E["rm-제4회-밤섬-마라톤-2026-05-31"]
    dec = E["rr-제5회-밤섬-마라톤-2026-12-13"]
    jun = E["rm-2026-람사르습지-밤섬런-2026-06-21"]
    items = [("제4회 밤섬마라톤", may), ("람사르습지 밤섬런", jun), ("제5회 밤섬마라톤", dec)]
    head = "<tr><th>서울 · 최근 10년 평균</th>" + "".join(f"<th>{esc(n)}<br>{esc(e['date'][5:].replace('-', '월 '))}일</th>" for n, e in items) + "</tr>"

    def r(label, f):
        return f"<tr><th>{label}</th>" + "".join(f"<td>{f(e['climate'])}</td>" for _, e in items) + "</tr>"

    tbl = ('<div class="table-scroll"><table class="segment-table"><thead>' + head + "</thead><tbody>"
           + r("아침 최저 평균", lambda c: f"{c['minAvg']:.1f}℃")
           + r("낮 최고 평균", lambda c: f"{c['maxAvg']:.1f}℃")
           + r("일평균(최저·최고의 중간)", lambda c: f"{mean_temp(c):.1f}℃")
           + r("가장 더웠던 해", lambda c: f"{c['hottestYear']}년 {c['hottestMax']:.1f}℃")
           + r("15℃ 대비 더위 보정(풀코스 계수)", lambda c: "없음" if heat_adjust(c) is None else f"최대 {heat_adjust(c)['pct']:.1f}%")
           + "</tbody></table></div>")
    ad = heat_adjust(may["climate"])
    half_rows = ""
    for sec, label in RUN_GOALS["half"][1:4]:
        half_rows += (f"<tr><th>{esc(label)}</th><td>{clock(sec)}</td><td>{clock(sec / (1 + ADJ_PER_C * ad['delta']))}</td>"
                      f"<td>{gap(sec - sec / (1 + ADJ_PER_C * ad['delta']))}</td></tr>")
    half_t = ('<div class="table-scroll"><table class="segment-table"><thead><tr><th>하프 목표</th><th>5월 31일 기록</th><th>15℃ 환산 하한</th><th>차이(최대)</th></tr></thead>'
              f"<tbody>{half_rows}</tbody></table></div>")
    body = f"""
<p>밤섬마라톤은 같은 서울 여의도 일대에서 계절을 달리해 열림. 2026년에는 5월 31일(제4회)과 12월 13일(제5회) 대회가 있고, 6월 21일에는 람사르습지 밤섬런이 열림. 세 대회의 대회일 날씨를 같은 기준으로 계산하면 같은 코스라도 기록에 미치는 영향이 크게 다름. 코스 고도는 공식 자료를 확인하지 못해 싣지 않았음.</p>
<h2>세 대회일의 날씨</h2>
{tbl}
<p>5월 31일의 일평균기온은 {mean_temp(may['climate']):.1f}℃로 보정 기준 15℃보다 {ad['over']:.1f}℃ 높음. 12월 13일은 {mean_temp(dec['climate']):.1f}℃로 {ADJ_REF_C:g}℃ 아래이고 낮 최고 평균도 {dec['climate']['maxAvg']:.1f}℃에 그침. 같은 코스에서 두 대회의 평년 일평균기온 차이는 {mean_temp(may['climate']) - mean_temp(dec['climate']):.1f}℃임.</p>
<p>Ely 등(2007)은 WBGT가 5℃에서 25℃로 오르는 동안 마라톤 기록이 단계적으로 느려졌고 느린 주자일수록 영향이 컸다고 보고했음. 칼랭크의 보정 계수 0.8%/℃는 보스턴마라톤 완주 기록 분석(Nikolaidis 등 2019: 1℃당 0.854%, Knechtle 등 2019: 1℃당 0.81%) 중 작은 쪽 아래로 잡은 값임.</p>
<h2>5월 31일 하프의 15℃ 환산</h2>
<p>보정 계수는 풀코스 자료에서 나왔고 하프 이하는 노출 시간이 짧아 영향이 더 작을 가능성이 높음. 그래서 하프의 환산은 &quot;최대 이 정도&quot;로만 읽어야 함. 아래는 평년 기온 기준으로 5월 31일에 낸 기록이 15℃에서 같은 몸으로 뛴 기록이었다면 이르렀을 하한임.</p>
{half_t}
<p>이 표는 평년값 계산이며 그날의 실제 기온이 아님. 실제 대회 당일의 기상청 실측 일평균기온이 있으면 <a href="level.html?d=21.0975">하프 등급 계산기</a>가 그 값으로 보정함.</p>
<h2>목표 기록별 기준</h2>
{goals_table("half", 21.0975, "하프")}
<h2>코스 고도</h2>
<p>밤섬마라톤 주최측의 공식 고저차 자료를 확인하지 못했음. 커뮤니티 글에 있는 &quot;전 구간 평탄&quot; 서술은 계측 근거를 확인할 수 없어 인용하지 않았음. 공식 GPX가 공개되면 <a href="yardage.html">대회 코스 야디지북</a>에서 구간별 경사를 확인할 수 있음.</p>
<div class="source-box"><strong>📌 이 글의 출처</strong><br>
· {SRC['asos']}<br>· {SRC['elhelou']}<br>· {SRC['ely']}<br>· {SRC['nikol']}<br>· {SRC['wma']}</div>
<div class="column-cta"><p>밤섬마라톤 접수 일정과 상세 정보는 칼랭크 대회 페이지에서 확인할 수 있음.</p>
<a href="e/{esc(quote_id(may['id']))}.html">제4회 밤섬마라톤 →</a>
<a href="e/{esc(quote_id(dec['id']))}.html" style="margin-left:8px;">제5회 밤섬마라톤 →</a></div>
"""
    return ("밤섬마라톤 5월과 12월 대회일 날씨 비교 — 15℃ 환산 기록과 목표 기준",
            "밤섬마라톤 5월 31일, 6월 21일, 12월 13일 대회일의 서울 10년 평균 기온을 비교하고, 더운 날의 하프 기록을 15℃ 기준으로 환산했습니다.",
            "🏔️ 대회 심화 가이드 · 마라톤", body)


GUIDES = {
    "column-chuncheon-marathon-course-guide.html": build_chuncheon,
    "column-seoul-vs-jtbc-marathon-comparison.html": build_seoul_jtbc,
    "column-daegu-marathon-course-guide.html": build_daegu,
    "column-bamseom-marathon-course-guide.html": build_bamseom,
}


def main():
    E = load_events()
    for fname, fn in GUIDES.items():
        title, desc, meta, body = fn(E)
        p = ROOT / fname
        s = p.read_text(encoding="utf-8")
        s = re.sub(r"<title>.*?</title>", f"<title>{esc(title)} — calrank</title>", s, count=1, flags=re.S)
        s = re.sub(r'(<meta name="description" content=")[^"]*(")', lambda m: m.group(1) + esc(desc) + m.group(2), s, count=1)
        s = re.sub(r'(<meta property="og:title" content=")[^"]*(")', lambda m: m.group(1) + esc(title) + m.group(2), s, count=1)
        s = re.sub(r'(<meta property="og:description" content=")[^"]*(")', lambda m: m.group(1) + esc(desc) + m.group(2), s, count=1)
        new_main = ('<main class="column-wrap">\n'
                    f'<p class="column-meta">{meta}</p>\n'
                    f'<h1 class="column-title"><img class="emo" src="/emoji/memo.svg" alt="" width="24" height="24" decoding="async" aria-hidden="true">{esc(title)}</h1>\n'
                    f'<div class="column-body">{body}</div>\n</main>')
        s, n = re.subn(r"<main class=\"column-wrap\">.*?</main>", lambda m: new_main, s, count=1, flags=re.S)
        assert n == 1, fname
        p.write_text(s, encoding="utf-8")
        text = re.sub(r"<[^>]+>", " ", body)
        print(fname, "본문", len(re.sub(r"\s+", " ", html.unescape(text))), "자")


if __name__ == "__main__":
    main()

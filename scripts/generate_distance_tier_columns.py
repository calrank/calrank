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


DIST_KM = {"5km": 5.0, "10km": 10.0, "half": 21.0975, "full": 42.195}
GRADE_SLUG = {"5km": "5km", "10km": "10km", "half": "half", "full": "full"}


def _sec(t: str) -> int:
    """'1:23:45' 또는 '48:15' 를 초로."""
    p = [int(x) for x in t.split(":")]
    return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]


def _mmss(sec: float) -> str:
    sec = int(round(sec))
    return f"{sec // 60}:{sec % 60:02d}"


def _hms(sec: float) -> str:
    sec = int(round(sec))
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


# 거리마다 "그 거리에서만 겪는 것"을 적는다. 숫자와 거리 이름만 바꾼 글은
# 길어도 얇은 페이지다 — 대회 상세 822장이 1,180자인데도 유입이 0인 이유가 그것이다.
# 여기 적는 문장은 전부 아래 출처에서 확인한 것이다. 확인 못 한 것은 쓰지 않는다.
DIST_EXTRA = {
    "half": """
<h2>하프는 거의 모두가 후반에 느려집니다</h2>
<p>하프마라톤은 풀코스처럼 연료가 바닥나는 거리는 아닙니다. 그런데도 후반에 느려지는 사람이
압도적으로 많습니다. Johansson 등이 예테보리 하프마라톤 10년치(2010~2019)
<strong>완주 기록 42만 3,496건</strong>을 분석한 연구가 그 비율을 보여 줍니다.</p>
<ul class="fact-list">
<li>전·후반을 같거나 더 빠르게 뛴 사람은 <strong>9.8%</strong>뿐입니다. 열에 아홉은 후반에
느려진다는 뜻입니다.</li>
<li>한 구간에서 25% 넘게 무너지는 <strong>심한 페이스 실패는 8.6%</strong>입니다. 풀코스의
28%(남성)·17%(여성)보다 한참 낮습니다. 하프는 실수를 덜 벌하는 거리입니다.</li>
<li>남성이 여성보다 <strong>두 배 더</strong> 자주 무너집니다(10.2% 대 5.4%).</li>
<li>가장 많이 무너지는 건 <strong>17~29세</strong>(남성 13.1%), 가장 적은 건
<strong>40대</strong>(남성 9.0%)입니다.</li>
</ul>
<p>남성이 더 자주, 젊을수록 더 자주, 40대가 가장 안정적이라는 세 가지는 풀코스 연구와
방향이 같습니다. 거리와 무관하게 <strong>페이스 판단이 체력만큼 중요하다</strong>는 쪽을
가리킵니다.</p>

<h2>하프에서 흔한 실수 — 10km 속도로 출발하기</h2>
<p>하프는 10km와 풀코스 사이에 끼어 있어서 감을 잡기 어려운 거리입니다. 10km를 뛰어 본
사람은 그 페이스가 몸에 남아 있고, 하프 초반 5km는 그 속도로도 힘들지 않게 느껴집니다.
문제는 15km 지점부터 드러납니다.</p>
<p>위의 <strong>다른 거리 가늠하기</strong> 표에서 간격이 보입니다. 하프를 1시간 50분에
뛰는 사람의 10km 환산은 <strong>49분 51초</strong>입니다. 페이스로 바꾸면 하프가 km당
5분 12초, 10km가 4분 59초 — <strong>km당 약 14초</strong> 차이입니다.</p>
<p>10km 페이스 그대로 하프를 시작하면 1km마다 14초씩 빚을 지는 셈입니다. 5km까지는
1분 9초, 10km면 2분 17초. 초반에는 몸이 받아 주니 티가 안 나다가 후반에 몇 배로
돌아옵니다.</p>
<p>반대로 하프에서 풀코스를 가늠할 때는 오차가 더 커집니다. Riegel 공식은 두 거리를
<strong>비슷하게 훈련했을 때</strong>를 전제하는데, 하프까지만 뛰던 사람이 풀코스를 처음
나가면 장거리 훈련량이 받쳐 주지 않아 예상보다 느린 것이 보통입니다. 공식이 틀린 게 아니라
전제가 다른 것입니다.</p>

<h2>그래서 하프는 이렇게</h2>
<p><strong>① 첫 5km를 목표 페이스보다 느리게.</strong> 위 구간 통과 시간표의 5km 값을
기준으로 삼되, 초반에는 그보다 조금 늦게 지나도 괜찮습니다. 열에 아홉이 후반에 느려지는
거리에서, 앞에서 벌어 두는 전략은 통계적으로 불리합니다.</p>
<p><strong>② 15km를 분기점으로 본다.</strong> 하프에서 무너지는 구간은 대개 후반 1/3입니다.
15km를 지날 때 아직 여유가 있다면 거기서부터 올리면 되고, 이미 힘들다면 그건 초반 페이스가
과했다는 신호입니다.</p>
<p><strong>③ 보급은 풀코스만큼 필요하지 않습니다.</strong> 2시간 안팎이면 저장된 글리코겐으로
대체로 감당됩니다. 다만 2시간 30분을 넘어가면 풀코스와 같은 기준(시간당 탄수화물 60g)이
의미를 갖기 시작합니다.</p>
<p><strong>④ 목표는 한 칸씩.</strong> 위 등급표에서 지금 자리를 확인하고 한 칸 위를
노리는 편이, 두 칸을 건너뛰려다 15km에서 무너지는 것보다 결국 빠릅니다.</p>

<div class="source-box" style="margin-top:28px;">
<strong>📚 이 절의 출처</strong><br>
· Johansson, M., Atterfors, J. &amp; Lamm, J. (2023). <em>Pacing Patterns of Half-Marathon
Runners: An analysis of ten years of results from Gothenburg Half Marathon.</em>
International Journal of Computer Science in Sport, 22(1), 124-138.
(2010~2019년 예테보리 하프마라톤 완주 기록 423,496건, 개인 184,890명)<br>
· Smyth, B. (2021). <em>How recreational marathon runners hit the wall.</em>
PLoS ONE 16(5): e0251513. (풀코스 비교 수치)<br>
· Riegel, P. S. (1981). <em>Athletic Records and Human Endurance.</em>
American Scientist 69(3), 285-290. (거리 환산 공식과 그 전제)
</div>
""",
    "full": """
<h2>30km에서 무너지는 건 당신만이 아닙니다</h2>
<p>마라톤에서 "벽"은 느낌이 아니라 통계로 잡히는 현상입니다. Smyth가 2005~2019년
38개 도시 270개 대회의 완주 기록 <strong>418만 건(러너 274만 명)</strong>을 분석한 연구가
있습니다. 20km 이후 5km 이상 구간에서 페이스가 25% 넘게 떨어진 경우를 벽으로 정의했더니,
이런 그림이 나왔습니다.</p>
<ul class="fact-list">
<li>무너지기 시작하는 지점은 <strong>남성 평균 29.6km, 여성 29.3km</strong>입니다.
"30km 벽"이라는 말은 경험칙이 아니라 실제 평균값과 거의 맞습니다.</li>
<li>겪는 비율은 <strong>남성 28%, 여성 17%</strong>입니다. 남성이 모든 연령대·모든 기록대에서
더 많이 겪습니다.</li>
<li>한 번 무너지면 완주 기록이 <strong>평균 31~33분</strong> 늦어집니다.</li>
<li>무너지는 구간 길이는 남성 평균 10.7km, 여성 9.6km입니다. 한 번 시작되면
남은 거리를 대부분 그 상태로 간다는 뜻입니다.</li>
</ul>
<p>뜻밖의 결과가 두 가지 있습니다. 하나는 <strong>개인 최고기록을 낸 전후 3년에 오히려 더
자주 겪는다</strong>는 것입니다(36% 대 23%). 잘 뛰려고 마음먹었을 때 무리하게 되기 때문으로
보입니다. 다른 하나는 <strong>젊을수록 더 많이 겪고, 45~49세 구간에서 가장 적다</strong>는
것입니다. 체력보다 페이스 판단이 더 크게 작용한다는 쪽을 시사합니다.</p>

<h2>왜 하필 30km인가 — 숫자로 보면</h2>
<p>이유는 연료입니다. Rapoport가 대사 모형으로 계산한 바로는, <strong>70kg 러너가 풀코스를
완주하는 데 약 2,950kcal</strong>이 듭니다. 그런데 몸에 저장해 둘 수 있는 탄수화물은
일반적으로 <strong>근육 글리코겐 약 310g, 간 글리코겐 약 88g</strong> 수준입니다.
합쳐서 400g 남짓, 열량으로 1,600kcal 정도입니다.</p>
<p>필요한 양의 절반 조금 넘는 수준입니다. 그래서 Rapoport는 "일반적인 저장량만으로는 부족하다"고
못 박습니다. 탄수화물 로딩을 제대로 하면 근육 쪽을 약 570g까지, 간은 160g까지 늘릴 수
있지만, 그래도 달리면서 보충하지 않으면 모자라는 경우가 많습니다.</p>
<p>저장량이 바닥나는 지점은 강도에 따라 달라집니다. 같은 연구에서 최대산소섭취량의
80~95%로 달린 경우 실패 지점이 <strong>21마일(약 34km) 부근에 몰렸습니다.</strong>
천천히 달리면 지방을 더 쓰기 때문에 더 멀리 갑니다 — 55% 아래로 달리면 벽을 거의
겪지 않는다고 적고 있습니다.</p>

<h2>그래서 무엇을 해야 하나</h2>
<p><strong>① 일정한 페이스로.</strong> 같은 연구가 연료 효율이 가장 좋은 전략으로
일정 페이스를 꼽습니다. 초반에 벌어 두겠다는 생각이 30km 이후에 몇 배로 돌아옵니다.
위의 구간 통과 시간표가 바로 그 일정 페이스를 목표별로 적어 둔 것입니다.</p>
<p><strong>② 배고프기 전에 먹기.</strong> Rapoport는 보충을 <strong>지칠 것으로 예상되는
시점보다 30분 먼저</strong> 하라고 권합니다. 몸이 신호를 보낼 때는 이미 늦습니다.</p>
<p><strong>③ 시간당 얼마나.</strong> 마라톤 러너의 영양 섭취를 정리한 2025년 종설은
미국스포츠의학회 기준을 인용해 <strong>2시간 30분까지는 시간당 탄수화물 60g,
그보다 길어지면 최대 90g</strong>까지를 제시합니다. 4시간 완주라면 240~300g 범위입니다.
다만 장이 적응돼 있지 않으면 그대로 넣었다가 탈이 나므로, 훈련 때 미리 시험해 보는 것이
전제입니다.</p>
<p><strong>④ 목표를 현실에 맞추기.</strong> 벽은 체력이 모자라서보다 페이스를 과하게 잡아서
오는 경우가 많습니다. 위 등급표에서 지금 내 자리를 확인하고, 거기서 한 칸 위를 목표로
잡는 편이 두 칸 위를 노리다 30km에서 무너지는 것보다 빠릅니다.</p>

<div class="source-box" style="margin-top:28px;">
<strong>📚 이 절의 출처</strong><br>
· Smyth, B. (2021). <em>How recreational marathon runners hit the wall: A large-scale data
analysis of late-race pacing collapse in the marathon.</em> PLoS ONE 16(5): e0251513.
(2005~2019년 38개 도시 270개 대회, 완주 기록 418만 건)<br>
· Rapoport, B. I. (2010). <em>Metabolic Factors Limiting Performance in Marathon Runners.</em>
PLoS Computational Biology 6(10): e1000960. (글리코겐 저장량과 완주 가능 거리의 대사 모형)<br>
· Jim&eacute;nez-Alfageme, R. 외 (2025). <em>Nutritional Intake and Timing of Marathon Runners.</em>
Sports Medicine - Open 11:26. (미국스포츠의학회 탄수화물 섭취 권고 인용)
</div>
""",
}


# 목표 기록별로 몇 분에 어느 지점을 지나야 하는지. 러너가 실제로 팔에 적어 가는 표다.
# 숫자는 전부 산수라 지어낼 여지가 없다.
SPLIT_TARGETS = {
    "5km":  [("20분", 1200), ("22분", 1320), ("25분", 1500), ("27분", 1620),
             ("30분", 1800), ("35분", 2100)],
    "10km": [("40분", 2400), ("45분", 2700), ("50분", 3000), ("55분", 3300),
             ("60분", 3600), ("70분", 4200)],
    "half": [("1시간 30분", 5400), ("1시간 40분", 6000), ("1시간 50분", 6600),
             ("2시간", 7200), ("2시간 15분", 8100), ("2시간 30분", 9000)],
    "full": [("서브3", 10800), ("3시간 30분", 12600), ("서브4", 14400),
             ("4시간 30분", 16200), ("5시간", 18000), ("5시간 30분", 19800)],
}
# 구간을 나누는 지점(km). 짧은 거리는 촘촘하게, 긴 거리는 5km 단위로.
SPLIT_MARKS = {
    "5km": [1, 2, 3, 4, 5],
    "10km": [2, 4, 6, 8, 10],
    "half": [5, 10, 15, 20, 21.0975],
    "full": [5, 10, 15, 20, 21.0975, 25, 30, 35, 40, 42.195],
}


def split_table(dist: str) -> str:
    km = DIST_KM[dist]
    marks = SPLIT_MARKS[dist]
    head = "<tr><th>목표</th>" + "".join(
        f"<th>{'하프' if abs(m-21.0975)<0.01 else ('완주' if abs(m-km)<0.01 else f'{m:g}km')}</th>"
        for m in marks) + "</tr>"
    rows = []
    for label, total in SPLIT_TARGETS[dist]:
        cells = "".join(f"<td>{_hms(total * m / km)}</td>" for m in marks)
        rows.append(f"<tr><td>{label}</td>{cells}</tr>")
    return ('<div class="table-scroll">\n<table class="tier-data-table">\n'
            + head + "\n" + "\n".join(rows) + "\n</table>\n</div>")


# Riegel(1981) 환산. T2 = T1 x (D2/D1)^1.06
RIEGEL_B = 1.06
# 이 거리 기록으로 나머지 세 거리를 가늠한다. 방향을 하나로 두는 쪽이 읽기 쉽다.
RIEGEL_SAMPLES = {
    "5km":  [1080, 1200, 1380, 1500, 1680, 1800],
    "10km": [2400, 2700, 3000, 3300, 3600, 4200],
    "half": [5400, 6000, 6600, 7200, 8100, 9000],
    "full": [10800, 12600, 14400, 16200, 18000, 19800],
}
RIEGEL_LIMIT = 230 * 60          # Riegel 이 밝힌 적용 상한(230분)
# 10km 페이지는 손으로 쓴 것이라 DIST_COPY 에 없다. 이름만 따로 둔다.
DIST_NAME = {"5km": "5km", "10km": "10km", "half": "하프마라톤", "full": "풀코스"}


def riegel_table(dist: str) -> str:
    from_km = DIST_KM[dist]
    others = [(k, DIST_NAME[k], DIST_KM[k]) for k in ("5km", "10km", "half", "full")
              if k != dist]
    head = (f"<tr><th>{DIST_NAME[dist]} 기록</th>"
            + "".join(f"<th>{lab}</th>" for _, lab, _ in others) + "</tr>")
    rows = []
    for t in RIEGEL_SAMPLES[dist]:
        cells = ""
        for _, _, to_km in others:
            pred = t * (to_km / from_km) ** RIEGEL_B
            # 범위를 넘은 값은 표시해 둔다. 숨기는 것보다 적어 두는 쪽이 정직하다.
            mark = "*" if pred > RIEGEL_LIMIT else ""
            cells += f"<td>{_hms(pred)}{mark}</td>"
        rows.append(f"<tr><td>{_hms(t)}</td>{cells}</tr>")
    return ('<div class="table-scroll">\n<table class="tier-data-table">\n'
            + head + "\n" + "\n".join(rows) + "\n</table>\n</div>")


def median_table(dist: str) -> str:
    """'평균 기록'을 찾는 사람이 가장 많다. 중앙값(인터미디엇 열)을 페이스와 함께 뽑는다.
    산술평균이 아니라 중앙값을 쓰는 이유는 러닝 기록이 느린 쪽으로 꼬리가 길어서다."""
    km = DIST_KM[dist]
    rows = []
    for i, dec in enumerate(DECADES):
        m = TIER_TABLES[(dist, "male")][i][2]      # 인터미디엇 = 상위 50%
        f = TIER_TABLES[(dist, "female")][i][2]
        rows.append(f"<tr><td>{dec}</td><td>{m}</td><td>{_mmss(_sec(m)/km)}</td>"
                    f"<td>{f}</td><td>{_mmss(_sec(f)/km)}</td></tr>")
    return ('<div class="table-scroll">\n<table class="tier-data-table">\n'
            "<tr><th>나이대</th><th>남성 중앙값</th><th>남성 페이스</th>"
            "<th>여성 중앙값</th><th>여성 페이스</th></tr>\n"
            + "\n".join(rows) + "\n</table>\n</div>")


def pace_table(dist: str) -> str:
    """시계에 페이스만 찍혀 있는 경우. 완주 시간으로 바꿔 줘야 표에서 찾을 수 있다."""
    km = DIST_KM[dist]
    step = 15 if dist in ("5km", "10km") else 15
    lo, hi = (240, 450) if dist in ("5km", "10km") else (270, 510)
    rows = []
    for p in range(lo, hi + 1, step):
        rows.append(f"<tr><td>{_mmss(p)}/km</td><td>{_hms(p*km)}</td></tr>")
    return ('<div class="table-scroll">\n<table class="tier-data-table">\n'
            f"<tr><th>평균 페이스</th><th>{DIST_COPY[dist]['label']} 완주 시간</th></tr>\n"
            + "\n".join(rows) + "\n</table>\n</div>")


def decade_links(dist: str) -> str:
    key = GRADE_SLUG[dist]
    items = " · ".join(
        f'<a href="grade-{key}-{d}s.html" style="color:var(--accent-ink);">{d}대</a>'
        for d in (20, 30, 40, 50, 60, 70))
    return f'<p style="font-size:14px;line-height:2;">{items}</p>'


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
  .column-meta {{ font-size: 13px; color: var(--ink-faint, #8E8E8E); margin-bottom: 12px; }}
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
  @media (max-width: 680px) {{
    .column-wrap {{ padding: 32px 14px 70px; }}
    .column-body {{ font-size: 15.5px; line-height: 1.85; }}
    .column-body h2 {{ font-size: 18px; margin: 30px 0 10px; }}
    .tier-data-table {{ font-size: 12.5px; }}
    .tier-data-table th, .tier-data-table td {{ padding: 7px 5px; }}
    /* 가로로 미는 표에서 나이대 칸은 붙잡아 둔다. 안 그러면 어느 줄인지 잃는다. */
    /* 고정 칸이 좁으면 "3시간 30분" 이 네 줄로 접혀 행이 길어진다. 줄바꿈을 막는다. */
    .tier-data-table td:first-child, .tier-data-table th:first-child {{
      position: sticky; left: 0; background: var(--surface); z-index: 2;
      white-space: nowrap; padding-right: 10px;
      box-shadow: 1px 0 0 var(--border); }}
    .table-scroll {{ margin: 0 -14px; padding: 0 14px; }}
  }}
  .fact-list {{ margin: 0 0 18px; padding-left: 20px; }}
  .fact-list li {{ margin-bottom: 10px; line-height: 1.85; }}
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
· 보강 자료: Lepers, R., Burfoot, A. &amp; Stapley, P. J. (2021). <em>Sub 3-Hour Marathon Runners for Five Consecutive Decades Demonstrate a Reduced Age-Related Decline in Performance</em>. Frontiers in Physiology, 12:649282. (서브3를 50년간 유지한 러너 40명을 추적한 연구다. 73%가 25~34세에 개인 최고기록을 냈고, 60세 전까지 10년당 7% 미만으로 감소를 묶었다. 대상이 특수하게 잘 훈련된 집단이라 일반 동호인에게 그대로 적용하기는 어렵다)
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
<p style="font-size:13px; color:var(--ink-faint,#8E8E8E);">※ 10대는 아직 성장기라 성인 기준 등급을 그대로 적용하기는 조심스럽습니다. 참고용으로만 봐주세요. 데이터는 5세 단위로 제공되어, 각 나이대의 대표 구간 값을 사용했습니다.</p>
<p style="font-size:13px; color:var(--ink-faint,#8E8E8E);">※ {esc(c['note'])}</p>

<h2>{esc(c['label'])} 평균 기록은 얼마일까 — 나이대별 중앙값</h2>
<p>"평균"을 찾는 분이 많은데, 러닝 기록은 느린 쪽 꼬리가 길어서 산술 평균이 실제 체감과 어긋납니다.
그래서 <strong>중앙값</strong>(딱 절반이 이 안에 들어오는 기록)을 씁니다. 위 표의 인터미디엇 열이
바로 상위 50% 지점이며, 아래는 그 값만 페이스와 함께 뽑은 것입니다.</p>
{median_table(dist)}

<h2>페이스만 알 때 — {esc(c['label'])} 완주 시간 환산</h2>
<p>시계에 찍힌 평균 페이스만 기억난다면, 먼저 완주 시간으로 바꾼 뒤 위 등급표에서 찾으세요.
{esc(c['label'])}는 페이스에 {DIST_KM[dist]:g}을 곱하면 완주 시간이 됩니다.</p>
{pace_table(dist)}

<h2>목표 기록별 구간 통과 시간 — {esc(c['label'])}</h2>
<p>등급을 확인했다면 다음은 "그 기록으로 달리려면 어느 지점을 몇 분에 지나야 하는가"입니다.
아래는 목표 기록을 일정한 페이스로 나눈 통과 시간입니다. 대회 당일 시계와 맞춰 보기 좋게
구간마다 적어 두었습니다.</p>
{split_table(dist)}
<p style="font-size:13px; color:var(--ink-faint);">※ 일정 페이스를 가정한 산술 값입니다.
실제로는 오르막·급수대·초반 혼잡 때문에 구간마다 달라집니다. 특히 초반 5km는 사람에 밀려
계획보다 느려지는 경우가 많으니, 그걸 만회하려고 무리하게 당기지 않는 편이 낫습니다.</p>

<h2>{esc(c['label'])} 기록으로 다른 거리 가늠하기</h2>
<p>"{esc(c['label'])}는 뛰어봤는데 다른 거리는 어느 정도 나올까" — 거리를 바꿔 예측할 때
가장 널리 쓰이는 것이 Riegel 공식입니다. Peter Riegel이
<em>American Scientist</em>(1981, 69권 3호 285-290쪽)에 실은 것으로,
<strong>예상 시간 = 기준 기록 × (거리비)<sup>1.06</sup></strong> 형태입니다.
지수가 1보다 큰 이유는 거리가 늘면 페이스가 떨어지기 때문이고, 단순히 거리를 곱하는 것보다
현실에 가깝습니다.</p>
{riegel_table(dist)}
<p style="font-size:13px; color:var(--ink-faint); line-height:1.8;">
※ 표에서 <strong>*</strong> 가 붙은 값은 Riegel 본인이 밝힌 적용 범위
(<strong>3분 30초~230분</strong>, 즉 3시간 50분)를 넘어선 예측입니다. 그 구간에서는 공식이
실제보다 빠른 값을 내놓는 것으로 알려져 있으니 참고만 하세요.<br>
※ 두 거리를 <strong>비슷한 정도로 훈련했을 때</strong>를 전제합니다. 하프까지만 뛰던 사람이
풀코스를 처음 나가면 예상보다 느린 것이 보통이고, 그건 공식이 틀린 게 아니라 전제가 다른 것입니다.</p>

<h2>내 연령대만 자세히 보기</h2>
<p>위 표는 10년 단위입니다. 한 살 단위로 경계가 어떻게 움직이는지 보려면 아래에서 연령대를 고르세요.
각 페이지에 남녀 기준이 한 살씩 나뉘어 있습니다.</p>
{decade_links(dist)}

{DIST_EXTRA.get(dist, '')}

<h2>기록은 왜 나이 들수록 떨어질까</h2>
<p>지구력은 나이가 들면서 실제로 떨어집니다. Tanaka와 Seals가 <em>Journal of Physiology</em>
(2008;586(1):55-63)에 정리한 바로는, 지구력 종목의 기량이 대체로 35세 전후까지 유지되다가
그 뒤 완만히, 60세를 넘기면서 뚜렷하게 떨어집니다. 최대산소섭취량과 심박출량이 줄기 때문입니다.</p>
<p>잘 훈련된 러너는 그 기울기를 늦출 수 있습니다. Lepers 등(2021)이 서브3 마라톤을 50년간
유지한 러너 40명을 추적했더니, 73%가 25~34세에 개인 최고기록을 냈고 60세 전까지 감소를
10년당 7% 미만으로 묶었습니다. 다만 이건 아주 특수하게 선별된 집단이라, 일반 동호인의
기울기는 이보다 가파를 수 있습니다.</p>
<p>위 표에서도 20~30대 기록이 거의 같고 40대부터 서서히 벌어지는 모습이 보입니다.
등급표가 나이마다 기준을 달리 두는 이유가 여기 있습니다.</p>

<h2>이 등급은 어떻게 나왔나 — 계산 과정</h2>
<p>러닝 등급표는 많지만, 숫자가 어디서 나왔는지 확인할 수 있는 곳은 드뭅니다. 체감이나
커뮤니티 의견으로 구간을 나누면 보여 줄 계산 과정이 없기 때문입니다. calrank는 두 기준을
나란히 두고 출처와 계산식을 전부 공개합니다.</p>
<p><strong>기준 ① 위 표 — Running Level 5단계.</strong> 해외 공개 데이터베이스의 실제 레이스
기록 백분위입니다. 상위 95%·80%·50%·20%·5% 지점을 그대로 가져왔고 가공하지 않았습니다.</p>
<p><strong>기준 ② calrank 7단계 — WMA 연령 기준표.</strong> 세계마스터즈육상연맹이 2025년에
낸 도로 종목 연령 기준표(퍼블릭 도메인, CC0)를 씁니다. 그 나이·성별의 기준기록을 내 기록으로
나눈 값이 연령등급 %이고, 그 %를 일곱 칸으로 나눈 자리만 calrank가 정했습니다.
계산식과 경계값은 <a href="grade-method.html" style="color:var(--accent-ink);">등급 기준과 근거</a>에
전부 적어 두었습니다.</p>
<p>두 기준은 출처가 달라 같은 기록이라도 결과가 다를 수 있습니다. 둘 다 보시는 편이 정확합니다.</p>

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
<p>칼랭크(CALRANK)는 달린 기록이 어느 등급인지 읽어 주고, 다음 출발선을 찾아 주는 곳입니다. 대회 일정은 주최측이 공개한 내용을 정리한 것입니다. 이 칼럼의 등급표는 외부 공개 데이터(Running Level, 2024)를 바탕으로 하며, 실제 신체 조건·훈련 상태에 따라 개인차가 있을 수 있습니다.</p>
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

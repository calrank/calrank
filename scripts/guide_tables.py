# -*- coding: utf-8 -*-
"""
가이드 본문에 들어가는 '계산된 표'.

왜 따로 두는가
--------------
목표 시간별 페이스, 구간 통과 시간, 연령등급은 손으로 적으면 반드시 틀립니다.
그리고 등급 기준이 바뀌면 글마다 숫자가 어긋나기 시작합니다.
그래서 전부 wma_standards.py(WMA 2025 연령 기준표)와 산술에서 뽑습니다.

여기서 나오는 숫자는 두 종류뿐입니다.
  1) 나눗셈 — 목표 시간 ÷ 거리 = 페이스. 추정이 아니라 정의입니다.
  2) 연령등급 — 그 나이·성별 기준기록 ÷ 내 기록 × 100. WMA 표가 근거입니다.

둘 다 출처가 분명해서 각주 없이 쓸 수 있습니다. 반대로 '이 페이스로 가면
완주한다' 같은 예측은 여기서 만들지 않습니다. 그건 근거가 필요한 주장입니다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wma_standards as wma

DIST_KM = {"5km": 5.0, "10km": 10.0, "half": 21.0975, "full": 42.195}
DIST_LABEL = {"5km": "5km", "10km": "10km", "half": "하프마라톤", "full": "풀코스"}

# calrank 등급 구간 — generate_grade_pages.py 의 TIER_BOUNDS 와 같은 값이어야 합니다.
TIER_BOUNDS = [
    (72, "상당한 러너"), (65, "러닝 상급자"), (59, "매우 좋은 편"),
    (51, "상당히 좋은 편"), (45, "꾸준한 러너"), (39, "보통"), (0, "이제 시작"),
]


def tier_of(pct):
    for bound, label in TIER_BOUNDS:
        if pct >= bound:
            return label
    return TIER_BOUNDS[-1][1]


# ------------------------------------------------------------------ 포맷

def hms(sec):
    """3661 → '1:01:01', 2400 → '40:00'"""
    sec = int(round(sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def pace(sec_per_km):
    m, s = divmod(int(round(sec_per_km)), 60)
    return f"{m}:{s:02d}"


# ------------------------------------------------------------------ 표

def pace_split_rows(dist_key, targets_sec, marks_km):
    """목표 시간별로 km당 페이스와 각 지점 통과 시간.

    일정한 페이스로 달린다고 보고 계산합니다. 실제로는 그렇게 안 되지만,
    '내가 지금 빠른가 느린가'를 판단할 기준선이 있어야 합니다.
    """
    full_km = DIST_KM[dist_key]
    rows = []
    for t in targets_sec:
        per_km = t / full_km
        cells = [hms(t), pace(per_km) + " /km"]
        cells += [hms(t * (m / full_km)) for m in marks_km]
        rows.append(cells)
    return rows


def pace_split_head(marks_km):
    def mk(m):
        return f"{m:g}km"
    return ["목표 기록", "평균 페이스"] + [mk(m) for m in marks_km]


def grade_rows(dist_key, targets_sec, ages, gender):
    """목표 시간 × 나이 → 연령등급 %와 calrank 등급."""
    rows = []
    for t in targets_sec:
        cells = [hms(t)]
        for a in ages:
            pct = wma.age_grade(t, gender, dist_key, a)
            # 퍼센트를 먼저 크게, 등급 이름은 그 아래 작게. 좁은 화면에서
            # 줄바꿈이 제멋대로 일어나지 않도록 마크업으로 자리를 정해 둡니다.
            cells.append(
                f'<span class="g-pct">{pct:.0f}%</span>'
                f'<span class="g-tier">{tier_of(pct)}</span>')
        rows.append(cells)
    return rows


def grade_head(ages):
    return ["기록"] + [f"{a}세" for a in ages]


def fuel_rows(dist_key, finish_sec, g_per_h, per_gel_g):
    """보급 지점 — 몇 분, 몇 km 에서 몇 개째인지.

    총 섭취량(g) = 완주 시간(h) × 시간당 g. 이걸 젤 하나 분량으로 나눠
    균등 간격으로 배치합니다. 첫 보급은 출발 직후가 아니라 한 간격 뒤입니다.
    """
    full_km = DIST_KM[dist_key]
    hours = finish_sec / 3600.0
    total_g = hours * g_per_h
    n = max(1, int(total_g // per_gel_g))
    gap = finish_sec / (n + 1)
    rows = []
    for i in range(1, n + 1):
        at = gap * i
        rows.append([f"{i}개째", hms(at), f"{at / finish_sec * full_km:.1f}km"])
    return rows, n, round(total_g)


def minutes(*mins):
    return [m * 60 for m in mins]


def hm(*pairs):
    return [h * 3600 + m * 60 for h, m in pairs]

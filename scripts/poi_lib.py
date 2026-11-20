"""
시설 지점(화장실·약수터·쉼터 등)을 코스 경로에 맞춰 '출발점에서 몇 m' 로 바꾸는 공용 계산.

점검(probe_poi.py)과 지점 자료 만들기(build_poi_layer.py)가 같은 계산을 쓰도록 한 곳에 둔다.
좌표는 [위도, 경도]. 경로는 점이 듬성듬성할 수 있어 25m 간격으로 채운 뒤 격자(약 100m 칸)로 찾는다.
"""
import collections
import math

NEAR_M = 80  # 경로에서 이 거리 안의 지점만 코스의 지점으로 본다
CELL = (0.0009, 0.0011)  # 위도·경도 한 칸 ≈ 100m


def hav(a, b):
    """두 [위도, 경도] 사이 거리(m). 코스 크기에서는 평면 근사로 충분하다."""
    x = math.radians(b[1] - a[1]) * math.cos(math.radians((a[0] + b[0]) / 2))
    y = math.radians(b[0] - a[0])
    return 6371000 * math.hypot(x, y)


def densify(pts, step=25):
    """경로를 step(m) 간격으로 채운다. [(위도, 경도, 출발점부터의 거리 m), ...]"""
    out, cum = [], 0.0
    for a, b in zip(pts, pts[1:]):
        d = hav(a, b)
        n = max(1, int(d // step))
        for i in range(n):
            t = i / n
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, cum + d * t))
        cum += d
    if pts:
        out.append((pts[-1][0], pts[-1][1], cum))
    return out


def build_grid(routes):
    """routes: {경로 이름: [[위도, 경도], ...]} → (격자, 경로별 전체 길이 m)"""
    grid = collections.defaultdict(list)
    length = {}
    for rid, pts in routes.items():
        dense = densify(pts)
        length[rid] = dense[-1][2] if dense else 0.0
        for p in dense:
            grid[(int(p[0] / CELL[0]), int(p[1] / CELL[1]))].append((rid, p))
    return grid, length


def snap(grid, lat, lon, near=NEAR_M):
    """지점 하나가 가까운 경로마다 (경로 이름 → (출발점부터 거리 m, 경로까지 거리 m)). 경로마다 가장 가까운 한 점만 쓴다."""
    ci, cj = int(lat / CELL[0]), int(lon / CELL[1])
    best = {}
    for i in (ci - 1, ci, ci + 1):
        for j in (cj - 1, cj, cj + 1):
            for rid, p in grid.get((i, j), ()):
                d = hav((lat, lon), p)
                if d <= near and (rid not in best or d < best[rid][1]):
                    best[rid] = (p[2], d)
    return best


def next_ahead(pois, here_m, kinds=None):
    """내 위치(출발점부터 here_m) 앞쪽에서 종류별로 가장 가까운 지점. pois: [(거리m, 종류, 이름), ...]
    돌아오는 값: {종류: (이름, 앞으로 남은 m)}. 앞쪽에 없는 종류는 빠진다(없다는 뜻이 아니라 자료에 없다는 뜻)."""
    out = {}
    for d, kind, name in sorted(pois):
        if d < here_m or (kinds and kind not in kinds):
            continue
        out.setdefault(kind, (name, d - here_m))
    return out

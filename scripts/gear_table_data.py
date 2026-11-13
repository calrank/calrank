"""기어 효과표가 쓰는 설정과 계산.

왜 이 표인가
------------
목표 시간 페이지("10km 50분", "서브4")가 먹힌 이유는 숫자 하나를 넣으면
네 가지 틀로 되돌려 주고, 그중 하나가 "또래에서 내 자리"이기 때문이다.
읽는 사람이 표에서 자기 줄을 찾는다.

장비도 같은 구조로 간다. 다만 쪼갤 가치가 있는 조합만 만든다 — 표의 줄이
서로 다른 답을 내지 않으면 페이지를 나눌 이유가 없다. 카본화는 한 표
안에서 근거 등급이 A 에서 C 로 뒤집히고, 타이어는 평속에 따라 단축이
3.5배까지 벌어진다. 반면 웻슈트는 철인 전 거리가 같은 근거 구간에
들어가서 줄마다 같은 숫자가 나온다 — 그래서 만들지 않는다.

등급 경계는 level.js 에서 읽어 온다. 양쪽에 따로 적어 두면 언젠가
어긋나고, 그때 사이트 안에서 같은 기록에 다른 등급이 나온다.
"""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (claim id, 맥락키, 슬러그조각, 제목에 쓸 말, 거리km 또는 None)
RUN_DISTS = [
    ("5km",  5.0,     "5km",  "5km"),
    ("10km", 10.0,    "10km", "10km"),
    ("half", 21.0975, "half", "하프마라톤"),
    ("full", 42.195,  "full", "풀코스 마라톤"),
]

# 목표 시간은 goal_data 의 것을 그대로 쓴다. 사이트 안에서 같은 말이
# 다른 숫자를 가리키면 안 된다.
RUN_GOALS = {
    "5km":  [(20 * 60, "20분"), (25 * 60, "25분"), (30 * 60, "30분")],
    "10km": [(40 * 60, "40분"), (45 * 60, "45분"), (50 * 60, "50분"),
             (55 * 60, "55분"), (60 * 60, "1시간")],
    "half": [(90 * 60, "1시간 30분"), (100 * 60, "1시간 40분"),
             (110 * 60, "1시간 50분"), (120 * 60, "2시간"), (150 * 60, "2시간 30분")],
    "full": [(180 * 60, "3시간"), (210 * 60, "3시간 30분"), (240 * 60, "4시간"),
             (270 * 60, "4시간 30분"), (300 * 60, "5시간")],
}

# 사이클은 완주 시간이 아니라 평속으로 묻는다. 동호인은 기록보다 평속을
# 외운다 — "나 평속 30 나와" 가 그 사람들이 쓰는 말이다.
BIKE_SPEEDS = [22, 25, 28, 32, 35, 38]
BIKE_DISTS = [(40, "40km"), (100, "100km")]

# 만들 조합. 줄이 갈리는 것만 넣었다.
RUN_TABLES = ["carbon-plate"]
BIKE_TABLES = ["tyre-rolling", "aero-wheel", "aero-helmet"]

# 표의 등급 칸이 기준으로 삼는 사람. 단축 '초'는 나이와 무관하지만
# 그 초가 등급을 바꾸는지는 나이에 달렸다. 가운데 나이를 쓰고 화면에 적는다.
REF_AGE = 40
REF_GENDER = "male"


def tier_bounds():
    """등급 경계를 level.js 에서 읽는다 — 한 곳에만 적어 두기 위해서다."""
    src = (ROOT / "level.js").read_text(encoding="utf-8")
    m = re.search(r"const TIER_BOUNDS = \[(.*?)\n\];", src, re.S)
    if not m:
        raise RuntimeError("level.js 에서 TIER_BOUNDS 를 찾지 못했습니다")
    out = []
    for line in m.group(1).splitlines():
        mm = re.match(r'\s*\[(\d+),\s*"([^"]+)"', line)
        if mm:
            out.append((int(mm.group(1)), mm.group(2)))
    if not out:
        raise RuntimeError("TIER_BOUNDS 를 읽지 못했습니다")
    return out


def tier_of(pct, bounds):
    for bound, label in bounds:
        if pct >= bound:
            return label
    return bounds[-1][1]


def run_model(requests):
    """gear-model.js 를 그대로 불러 계산한다.

    같은 식을 파이썬으로 또 쓰면 둘이 어긋날 때 어느 쪽이 맞는지 알 수 없다.
    화면이 쓰는 그 파일을 쓴다.
    """
    script = r"""
const fs = require("fs");
global.window = global;
require(process.argv[1]);
const claims = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const reqs = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const G = global.calrankGear;
const out = reqs.map(function (q) {
  const claim = G.findClaim(claims, q.claim);
  if (!claim) return null;
  const res = G.judge(Object.assign({ claim: claim }, q.input));
  if (!res) return null;
  return {
    speedKmh: res.speedKmh, paceSecPerKm: res.paceSecPerKm,
    effects: res.effects.map(function (e) {
      return {
        id: e.id, label: e.label, direction: e.direction,
        hasEvidence: e.hasEvidence, noData: !!e.noData, caveat: !!e.caveat,
        grade: e.evidence ? e.evidence.grade : null,
        significant: e.evidence ? e.evidence.significant !== false : null,
        studies: e.evidence ? e.evidence.studies : null,
        n: e.evidence ? e.evidence.n : null,
        range: e.range || null, cutSec: e.cutSec || null,
        adjustedSec: e.adjustedSec || null,
        aero: e.aero || null,
        watts: e.aero ? e.aero.watts : null,
        sharePct: e.aero ? e.aero.sharePct : null,
        rollSharePct: e.aero ? e.aero.rollSharePct : null
      };
    })
  };
});
process.stdout.write(JSON.stringify(out));
"""
    tmp = ROOT / ".gear_req.json"
    tmp.write_text(json.dumps(requests, ensure_ascii=False), encoding="utf-8")
    try:
        p = subprocess.run(
            ["node", "-e", script, str(ROOT / "gear-model.js"),
             str(ROOT / "data" / "gear_claims.json"), str(tmp)],
            capture_output=True, text=True, cwd=str(ROOT))
        if p.returncode != 0:
            raise RuntimeError("gear-model.js 실행 실패:\n" + p.stderr[:2000])
        return json.loads(p.stdout)
    finally:
        tmp.unlink(missing_ok=True)


# ── 두 축이 만나는 표 ────────────────────────────────────────────
#
# 웻슈트 수온표는 이 사이트에서 유일하게 규정과 효과가 한 화면에 서는
# 자리다. "이 수온에서 입어도 되나"는 연맹 규정이 답하고, "입으면
# 빨라지나"는 연구가 답한다. 둘을 떼어 놓으면 읽는 사람이 둘 다
# 찾아다녀야 한다.
WETSUIT_TEMPS = [13, 14, 15, 15.9, 17, 18, 19, 20, 21, 22, 23, 24, 24.6, 26]

# 트레일 폴은 경사에 따라 효과의 방향이 갈린다. 한 장비가 한 효과만
# 내지 않는다는 것을 가장 잘 보여 주는 자리라 표로 만들 가치가 있다.
POLE_GRADIENTS = [0, 3, 5, 8, 10, 15, 20, 25, 30]

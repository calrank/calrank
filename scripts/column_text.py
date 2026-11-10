"""월간 대회 칼럼의 문장. 생성기와 기존 페이지 정리 스크립트가 같이 쓴다.

원칙: 데이터에 없는 말은 쓰지 않는다. '전국', '미표기' 는 지역이 아니라 값이
비어 있다는 뜻이라 지역 순위에서 뺀다. 거리 칸에 들어온 '토요일: 스프린트' 같은
설명 글은 거리가 아니므로 숫자 거리와 하프·풀만 남긴다."""
import re

NOT_REGION = {"전국", "미표기", ""}
_DIST = re.compile(r"^(\d+(?:\.\d+)?)\s*(km|k)$", re.I)
_NAMED = {"하프", "풀", "마라톤"}

# 대회 장비가 궁금한 사람을 이어 줄 기어 판정 (종목 → 주소, 이름)
GEAR_LINK = {
    "marathon": ("gear-carbon-plate.html", "카본화 효과와 근거 등급"),
    "trail": ("gear-utmb-kit.html", "UTMB 필수 장비 규정"),
    "cycling": ("gear-aero-wheel.html", "에어로 휠 효과와 근거 등급"),
    "triathlon": ("gear-wetsuit.html", "웻슈트 효과와 근거 등급"),
    "inline": ("gear-ws-wheel-diameter.html", "인라인 바퀴 지름 규정"),
}


def josa(word, a, b):
    """받침이 있으면 a, 없으면 b. 숫자로 끝나면(철인3종) 발음 기준 '삼'."""
    ch = word[-1]
    if ch.isdigit():
        return a if ch in "013678" else b
    code = ord(ch) - 0xAC00
    if 0 <= code < 11172:
        return a if code % 28 else b
    return b


def topic(word):
    return word + josa(word, "은", "는")


def clean_regions(pairs):
    return [(r, c) for r, c in pairs if r not in NOT_REGION]


def clean_distances(pairs):
    out = []
    for d, c in pairs:
        d = d.strip()
        if _DIST.match(d) or d in _NAMED:
            out.append((d, c))
    return out


def _km(d):
    m = _DIST.match(d)
    return float(m.group(1)) if m else None


def region_sentence(pairs):
    p = clean_regions(pairs)
    if not p:
        return "이 기간 대회는 지역이 '전국'으로만 표기되어 있어 지역별로 나누지 않았습니다."
    top, n = p[0]
    rest = p[1:4]
    if n == 1 and len(p) == 1:
        return f"지역은 {top} 한 곳입니다."
    if n == 1:
        names = ", ".join(r for r, _ in p[:5])
        return f"특정 지역에 몰리지 않고 {names}에 한 곳씩 열립니다."
    s = f"지역별로는 {top}{josa(top, '이', '가')} {n}개로 가장 많습니다."
    if rest:
        s += " 이어서 " + ", ".join(f"{r}({c}개)" for r, c in rest) + " 순입니다."
    return s


def distance_sentence(pairs):
    p = clean_distances(pairs)
    if not p:
        return ""
    if len(p) >= 3 and all(c == 1 for _, c in p):
        kms = [k for k in (_km(d) for d, _ in p) if k is not None]
        if kms:
            return (f"거리는 {min(kms):g}km부터 {max(kms):g}km까지 다양하고, "
                    "같은 거리가 겹치는 대회는 많지 않습니다.")
    return "참가 거리로는 " + ", ".join(f"{d}({c}개)" for d, c in p[:5]) + " 순으로 많습니다."


def _uniq(names):
    seen, out = set(), []
    for n in names:
        key = re.sub(r"\s+|\(.*", "", n)
        if key and key not in seen:
            seen.add(key)
            out.append(re.sub(r"\s*\(.*", "", n).strip())
    return out


def build(sport_label, month_kr, total, samples, region_pairs, dist_pairs, sport):
    t = topic(sport_label)
    intro = (f"{month_kr}에 열리는 {sport_label} 대회를 칼랭크에 등록된 일정으로 정리했습니다. "
             "지역과 거리를 함께 보면 어디서 어떤 대회가 열리는지 알기 쉽습니다.")
    span = "" if month_kr.endswith("사이") else " 한 달간"
    sec1 = f"{month_kr}{span} 칼랭크에 등록된 {sport_label} 대회는 {total}개입니다."
    samples = _uniq(samples)
    if samples:
        sec1 += " 대회로는 " + ", ".join(samples[:5]) + " 등이 있습니다."
    sec2 = region_sentence(region_pairs)
    sec3 = distance_sentence(dist_pairs)
    cta = f"{sport_label} 대회는 캘린더에서 지역과 거리별로 걸러 볼 수 있습니다."
    gear = None
    if sport in GEAR_LINK:
        h, n = GEAR_LINK[sport]
        gear = (f'대회 장비가 궁금하다면 칼랭크 기어 판정의 <a href="{h}">{n}</a>을 함께 보세요. '
                "규정은 연맹 문서에서, 효과는 논문 근거에서 따로 정리했습니다.")
    return {"intro": intro, "sec1": sec1, "sec2": sec2, "sec3": sec3, "cta": cta, "gear": gear}

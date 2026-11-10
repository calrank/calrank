"""이미 만들어진 월간 대회 칼럼(column-YYYY-MM-종목-auto.html)을 새 문장으로 고친다.
각 페이지가 가진 숫자(총 개수, 지역·거리 표)를 읽어 column_text 로 다시 쓴다.
같은 입력이면 같은 결과라 여러 번 돌려도 된다."""
import re, sys, glob
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import column_text as ct

ROOT = Path(__file__).resolve().parent.parent
LABEL = {"marathon": "마라톤", "cycling": "자전거", "trail": "트레일러닝",
         "triathlon": "철인3종", "inline": "인라인"}
PAIR = re.compile(r"([^,()]+?)\((\d+)개\)")


def pairs(text):
    """'서울(36개), 경기(22개)' 꼴의 목록을 (이름, 개수) 로. 앞에 붙은 설명은 버린다."""
    out = []
    for item in text.split(", "):
        m = re.fullmatch(r"(.+?)\((\d+)개\)", item.strip().rstrip("."))
        if m:
            out.append((m.group(1).split(" ")[-1] if " · " not in m.group(1) else m.group(1), int(m.group(2))))
    return out


def region_pairs(reg):
    if "그 뒤를 " in reg:
        lst = reg.split("그 뒤를 ")[1].split(" 순으로")[0]
        return pairs(lst)
    if " 순으로 대회가 분포" in reg:
        return pairs(reg.split(" 순으로")[0])
    m = re.search(r"특히 (.+?)\((\d+)개\)", reg)
    return [(m.group(1), int(m.group(2)))] if m else []


def fix(path):
    t = path.read_text(encoding="utf-8")
    if 'class="column-body"' not in t:
        return False
    sport = re.search(r"column-\d{4}-\d{2}-(\w+)-auto", path.name).group(1)
    label = LABEL[sport]
    h1 = re.search(r'<h1 class="column-title">(.*?)</h1>', t).group(1)
    month_kr = re.match(r"(.+?)(?:, 전국| \S+ 대회|에 열리는)", h1).group(1)
    total = int(re.search(r"(\d+)(?:개|곳)", h1).group(1))
    body = re.search(r'<div class="column-body">(.*?)<div class="column-cta">', t, re.S).group(1)
    ps = re.findall(r"<p>(.*?)</p>", body, re.S)
    reg = next((p for p in ps if p.startswith("지역별로") or "순으로 대회가 분포" in p or "경향을" in p), "")
    dis = next((p for p in ps if p.startswith("거리별 분포") or p.startswith("참가 거리") or p.startswith("참가 거리 기준")), "")
    # 새 문장은 한 번 더 읽어도 같은 표를 돌려주도록 '지역(N개)' 꼴을 유지한다.
    if "칼랭크에 등록된 일정으로 정리" in t:
        return False
    names = re.search(r"(?:대표적으로|대회로는) (.*?) 등", ps[1] if len(ps) > 1 else "")
    samples = [s.strip() for s in names.group(1).split(", ")] if names else []
    rp = region_pairs(reg)
    tx = ct.build(label, month_kr, total, samples, rp, pairs(dis.split("는 ",1)[1] if dis.startswith(("거리별 분포는","참가 거리 기준으로는")) else dis), sport)
    old_intro, old_s1 = ps[0], ps[1]
    t = t.replace(old_intro, tx["intro"]).replace(old_s1, tx["sec1"])
    if reg:
        t = t.replace(reg, tx["sec2"])
    if dis:
        if tx["sec3"]:
            t = t.replace(dis, tx["sec3"])
        else:
            t = re.sub(r"<h2>[^<]*</h2>\n<p>" + re.escape(dis) + r"</p>\n", "", t)
    t = re.sub(r"<h2>총 몇 개나 열릴까</h2>|<h2>[^<]*대회 규모</h2>|<h2>이번 달 대회 현황</h2>", "<h2>이번 달 대회 현황</h2>", t)
    t = re.sub(r"<h2>(어느 지역에서 가장 많이 열릴까|[^<]*어디서 많이 열리나|지역별 분포)</h2>", "<h2>지역별 분포</h2>", t)
    t = re.sub(r"<h2>(거리별로는 어떨까|코스 거리 분포|어떤 거리의 대회가 많을까|거리별 분포)</h2>", "<h2>거리별 분포</h2>", t)
    t = re.sub(r'(<div class="column-cta">\n<p>)[^<]*(</p>)', lambda m: m.group(1) + tx["cta"] + m.group(2), t)
    if tx["gear"] and "장비도 함께 보려면" not in t:
        t = t.replace('<div class="column-cta">',
                      f'<h2>장비도 함께 보려면</h2>\n<p>{tx["gear"]}</p>\n<div class="column-cta">', 1)
    # 상단 숫자 칸에서 '전국' 제거
    t = re.sub(r'<div class="stat-box"><b>(전국|미표기)</b><span>\d+개</span></div>', "", t)
    t = t.replace("지역별 완전정리", "지역별 정리").replace("대회 총정리 —", "대회 현황 —")
    path.write_text(t, encoding="utf-8")
    return True


if __name__ == "__main__":
    n = sum(fix(Path(f)) for f in sorted(glob.glob(str(ROOT / "column-20*-auto.html"))))
    print(f"월간 칼럼 {n}장 고침")

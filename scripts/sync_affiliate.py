#!/usr/bin/env python3
"""칼럼 페이지(gear-*.html 이 아닌 곳)에 쿠팡 파트너스 제휴 블록을 그린다.

data/affiliate_links.json 의 항목 중 page 가 gear- 로 시작하지 않는 것만 다룬다(기어 페이지는 기어 생성기가 그린다).
생성기가 20여 개라 칼럼마다 고치지 않고, 마무리 단계에서 같은 표식 구간을 넣고 갱신한다.
대가성 문구는 링크 바로 위에 두고 링크에는 rel="sponsored nofollow" 를 단다. 항목이 없어지면 구간도 지운다.

  python3 scripts/sync_affiliate.py          # 적용
  python3 scripts/sync_affiliate.py --check  # 바뀔 게 있으면 1로 끝난다
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
BEGIN, END = "<!--sync-aff-->", "<!--/sync-aff-->"
import aff_render  # noqa: E402


def block(page, rows):
    return f'{BEGIN}\n' + aff_render.render(page, "") + f'\n{END}\n'


def strip(t):
    return re.sub(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", "", t, flags=re.S)


def main(check):
    data = json.loads((ROOT / "data" / "affiliate_links.json").read_text(encoding="utf-8"))
    by = {}
    for x in data.get("items", []):
        pg = str(x.get("page", ""))
        if pg.startswith("gear-") or not (x.get("widget") or str(x.get("url", "")).startswith("https://link.coupang.com/")):
            continue
        by.setdefault(pg, []).append(x)
    changed = {}
    # 표식이 남은 페이지(항목이 지워진 경우)도 훑어서 정리한다.
    for f in sorted(ROOT.glob("*.html")):
        if f.name.startswith("gear-"):
            continue
        t = f.read_text(encoding="utf-8")
        if f.name not in by and BEGIN not in t:
            continue
        base = strip(t)
        new = base
        if f.name in by:
            b = block(f.name, by[f.name])
            marker = '<div class="column-cta"'
            if marker in base:
                new = base.replace(marker, b + marker, 1)
            elif "</main>" in base:
                new = base.replace("</main>", b + "</main>", 1)
            else:
                print(f"제휴 블록: {f.name} 에 넣을 자리가 없습니다")
                continue
        if new != t:
            changed[f] = new
    if not changed:
        print("제휴 블록: 바뀔 것 없음")
        return 0
    if check:
        print(f"제휴 블록: {len(changed)}개가 아직 반영되지 않았습니다 — python3 scripts/sync_affiliate.py")
        return 1
    for f, t in changed.items():
        f.write_text(t, encoding="utf-8")
    print(f"제휴 블록: {len(changed)}개 갱신")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))

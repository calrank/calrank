#!/usr/bin/env python3
"""같은 종류의 페이지끼리 서로 이어 준다. (칼럼은 sync_columns.py 가 맡는다)

왜 필요한가
-----------
audit_pages.py 로 재 보니 사이트맵 페이지 40개가 다른 페이지에서 받는 링크가 3개 미만이었다.
지역 랜딩 24개는 regions.html 한 곳에서만, 거리 랜딩은 distances.html 한 곳에서만 걸려 있었다.
docs/new-page-criteria.md 의 "들어오는 링크 3개 이상" 기준을 맞추려고 같은 묶음 안에서
서로 3~4개씩 링크한다. 고르는 방식은 입력이 같으면 결과도 같고, 링크가 한쪽에 쏠리지 않는다.

  python3 scripts/sync_links.py          # 적용
  python3 scripts/sync_links.py --check  # 바뀔 게 있으면 1로 끝난다
"""
import html as htmllib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sync_columns import indexable, title_of  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BEGIN, END = "<!--sync-links-->", "<!--/sync-links-->"

# (이름, 제목, 파일 패턴 또는 목록, 페이지당 링크 수)
GROUPS = [
    ("지역-마라톤", "다른 지역 마라톤 대회", ["landing-*-marathon.html"], 4),
    ("지역-트레일", "다른 지역 트레일러닝 대회", ["landing-*-trail.html"], 3),
    ("지역-사이클", "다른 지역 사이클 대회", ["landing-*-cycling.html"], 3),
    ("지역-철인", "다른 지역 철인3종 대회", ["landing-*-triathlon.html"], 3),
    ("지역-인라인", "다른 지역 인라인 대회", ["landing-*-inline.html"], 3),
    ("거리-마라톤", "다른 거리의 마라톤 대회", ["landing-dist-marathon-*.html"], 4),
    ("거리-트레일", "다른 거리의 트레일러닝 대회", ["landing-dist-trail-*.html"], 3),
    ("기어-헬멧휠타이어", "함께 보는 기어 판정",
     ["gear-aero-helmet*.html", "gear-aero-wheel*.html", "gear-tyre-rolling*.html", "gear-drafting.html",
      "gear-aero-position.html", "gear-aero-clothing.html"], 4),
    ("기어-인라인", "함께 보는 기어 판정", ["gear-inline-bearings.html", "gear-ws-wheel-diameter.html", "gear-shoe-rotation.html"], 2),
    ("도구", "함께 쓰는 도구",
     ["age-curve.html", "zone2-heart-rate-calculator.html", "goals.html", "ledger.html", "standards-running.html",
      "standards-cycling.html", "standards-trail.html", "standards-triathlon.html", "race-finder-quiz.html",
      "race-checklist-tool.html", "record-issue-diagnosis-tool.html", "level.html"], 4),
    ("일정모음", "대회 일정 모아 보기",
     ["monthly.html", "trail-monthly.html", "cycling-monthly.html", "triathlon-monthly.html", "kids-marathon.html",
      "night-run.html", "ultra-marathon.html", "walking-events.html", "open-registration.html", "aquathlon.html"], 4),
    ("소개자료", "칼랭크 소개·자료", ["about.html", "editorial.html", "distribution.html", "guides.html"], 3),
    ("코스허브", "코스·산 찾아보기", ["course.html", "trailroot.html", "mountains.html"], 2),
    ("월별보관함", "다른 달의 대회 보관함", ["events-archive-2026-*.html"], 3),
]


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def strip_block(t: str) -> str:
    return re.sub(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", "", t, flags=re.S)


def expand(patterns):
    out = []
    for pat in patterns:
        for p in sorted(ROOT.glob(pat)):
            if p.name not in out:
                out.append(p.name)
    return out


def main(check: bool) -> int:
    pages = {p.name: read(p) for p in ROOT.glob("*.html")}
    changed = {}
    for gname, heading, pats, n_per in GROUPS:
        members = [n for n in expand(pats) if n in pages and indexable(pages[n])]
        if len(members) < 2:
            continue
        k = min(n_per, len(members) - 1)
        for i, n in enumerate(members):
            # 앞뒤로 번갈아 가며 k개: 모든 페이지가 같은 수만큼 링크를 받는다
            picks, step = [], 1
            while len(picks) < k:
                j = (i + (step + 1) // 2 * (1 if step % 2 else -1)) % len(members)
                if members[j] != n and members[j] not in picks:
                    picks.append(members[j])
                step += 1
                if step > 4 * len(members):
                    break
            items = "".join(f'<li><a href="{x}">{htmllib.escape(title_of(pages[x]))}</a></li>' for x in picks)
            block = (f'{BEGIN}\n<nav class="rel-cols" aria-label="{heading}" data-group="{gname}"><h2>{heading}</h2>'
                     f'<ul>{items}</ul></nav>\n{END}\n')
            t = strip_block(pages[n])
            marker = '<footer class="site-footer"'
            if marker in t:
                new = t.replace(marker, block + marker, 1)
            elif "</main>" in t:
                new = t.replace("</main>", block + "</main>", 1)
            else:
                continue
            if new != pages[n]:
                changed[n] = new
    if not changed:
        print("링크 묶음: 바뀔 것 없음")
        return 0
    if check:
        print(f"링크 묶음: {len(changed)}개가 아직 반영되지 않았습니다 — python3 scripts/sync_links.py")
        return 1
    for n, t in changed.items():
        (ROOT / n).write_text(t, encoding="utf-8")
    print(f"링크 묶음: {len(changed)}개 갱신")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))

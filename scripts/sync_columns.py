#!/usr/bin/env python3
"""칼럼·가이드가 서로, 그리고 칼럼 목록에서 이어지게 만든다.

왜 필요한가
-----------
서치 콘솔에서 칼럼 몇 개가 "발견됨 - 색인 안 됨"에 있었다. 확인해 보니 다른 페이지에서 걸리는
링크가 0~1개였고, 근거 기반 칼럼 4개는 column.html 목록에도 빠져 있었다.
검색엔진은 링크를 따라 중요한 페이지를 가려내므로, 본문이 충실해도 연결이 없으면 뒤로 밀린다.

하는 일
-------
1. 색인 대상 칼럼이 column.html 카드 목록에 없으면 카드를 채운다.
2. 색인 대상 칼럼·가이드마다 "함께 읽을 글" 3개를 본문 끝에 붙인다.
   같은 주제를 먼저 고르고, 들어오는 링크가 가장 적은 글을 우선해 링크가 고르게 퍼지게 한다.
   결과는 입력이 같으면 항상 같다(실행할 때마다 바뀌지 않는다).

  python3 scripts/sync_columns.py          # 적용
  python3 scripts/sync_columns.py --check  # 바뀔 게 있으면 1로 끝난다
"""
import html as htmllib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BEGIN, END = "<!--sync-related-->", "<!--/sync-related-->"
N_RELATED = 3


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def indexable(t: str) -> bool:
    return not re.search(r'<meta[^>]*noindex', t[:6000])


def group_of(name: str) -> str:
    n = name.replace(".html", "")
    if n.startswith("column-running-"):
        return "science"
    for key in ("marathon", "trail", "triathlon", "cycling"):
        if n.startswith(f"column-howto-{key}-") or n.startswith(f"guide-{key}-"):
            return key
    if n.endswith("age-gender-tier"):
        return "tier"
    if n.endswith("course-guide") or "marathon-comparison" in n:
        return "course"
    if n.startswith("guide-training") or n.startswith("guide-tag-"):
        return "guide"
    return "other"


def title_of(t: str) -> str:
    m = re.search(r"<h1[^>]*>(.*?)</h1>", t, re.S)
    s = re.sub(r"<[^>]+>", "", m.group(1)) if m else re.sub(r"\s*[—|-]\s*calrank\s*$", "", re.search(r"<title>(.*?)</title>", t, re.S).group(1))
    return htmllib.unescape(re.sub(r"\s+", " ", s)).strip()


def desc_of(t: str) -> str:
    m = re.search(r'<meta name="description" content="([^"]*)"', t)
    return htmllib.unescape(m.group(1)).strip() if m else ""


def date_of(t: str) -> str:
    m = re.search(r'"datePublished":"(\d{4})-(\d{2})-(\d{2})"', t)
    return f"{m.group(1)}년 {int(m.group(2))}월 {int(m.group(3))}일" if m else ""


def strip_block(t: str) -> str:
    return re.sub(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", "", t, flags=re.S)


def main(check: bool) -> int:
    pages = {}
    for f in sorted(ROOT.glob("*.html")):
        t = read(f)
        pages[f.name] = t
    targets = [n for n in pages
               if (n.startswith("column-") or (n.startswith("guide-") and not n.startswith("guide-tag-")))
               and indexable(pages[n])]

    # 들어오는 링크 수(이 스크립트가 붙인 블록은 빼고 센다)
    inl = {n: 0 for n in targets}
    for n, t in pages.items():
        s = strip_block(t)
        for h in set(re.findall(r'href="/?([a-z0-9\-]+\.html)', s)):
            if h in inl and h != n:
                inl[h] += 1

    changed = []

    # 1) column.html 카드 보충
    col = pages.get("column.html", "")
    marker = '<div style="margin-top:24px;" id="columnCardsContainer">\n\n'
    cards = ""
    for n in targets:
        if n.startswith("column-") and n not in col:
            t = pages[n]
            is_sci = group_of(n) == "science"
            meta = f"🔬 근거 기반 · {date_of(t)}".rstrip(" ·") if is_sci else f"📝 칼럼 · {date_of(t)}".rstrip(" ·")
            cards += (f'<a href="{n}" class="column-card">\n<p class="column-card-meta">{meta}</p>\n'
                      f'<p class="column-card-title">{htmllib.escape(title_of(t))}</p>\n'
                      f'<p class="column-card-desc">{htmllib.escape(desc_of(t))}</p>\n</a>\n\n')
    if cards and marker in col:
        pages["column.html"] = col.replace(marker, marker + cards, 1)
        changed.append("column.html (카드 보충)")

    # 2) 함께 읽을 글
    by_group = {}
    for n in targets:
        by_group.setdefault(group_of(n), []).append(n)
    run = dict(inl)   # 고르는 동안 늘어나는 링크 수. 어느 글도 소외되지 않게 퍼뜨린다.
    picks = {}
    for n in sorted(targets, key=lambda x: (inl[x], x)):
        g = group_of(n)
        order = lambda x: (run[x], x)
        same = sorted([x for x in by_group.get(g, []) if x != n], key=order)[:N_RELATED - 1]
        others = sorted([x for x in targets if x != n and x not in same], key=order)
        pick = same + others[:N_RELATED - len(same)]
        for x in pick:
            run[x] += 1
        picks[n] = pick
    for n in targets:
        pick = picks[n]
        items = "".join(
            f'<li><a href="{x}">{htmllib.escape(title_of(pages[x]))}</a></li>' for x in pick)
        block = (f'{BEGIN}\n<nav class="rel-cols" aria-label="함께 읽을 글"><h2>함께 읽을 글</h2>'
                 f'<ul>{items}</ul></nav>\n{END}\n')
        t = strip_block(pages[n])
        if "</main>" not in t:
            continue
        new = t.replace("</main>", block + "</main>", 1)
        if new != pages[n]:
            pages[n] = new
            if n not in changed:
                changed.append(n)

    if not changed:
        print("칼럼 연결: 바뀔 것 없음")
        return 0
    if check:
        print(f"칼럼 연결: {len(changed)}개가 아직 반영되지 않았습니다 — python3 scripts/sync_columns.py")
        return 1
    for n in changed:
        key = n.split(" ")[0]
        (ROOT / key).write_text(pages[key], encoding="utf-8")
    print(f"칼럼 연결: {len(changed)}개 갱신")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))

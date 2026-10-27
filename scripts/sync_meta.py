#!/usr/bin/env python3
"""색인되는 페이지에 canonical 과 og:title 이 빠진 곳을 채운다.

왜 필요한가
-----------
손으로 만든 페이지와 오래된 생성기 산출물에는 canonical 이 없다. 같은 글이
`/column.html` 과 `/column.html?x=1` 처럼 여러 주소로 걸리면 검색엔진이 어느
쪽을 대표로 둘지 스스로 고르고, 그 선택이 매번 같지도 않다. og:title 이 없으면
공유했을 때 카드에 주소만 남는다.

noindex 페이지(로그인 보조·위젯·웰컴)와 소유 확인 파일은 건드리지 않는다.
거기에 canonical 을 달면 색인하지 말라는 말과 대표 주소를 알리는 말을 동시에
하는 셈이 된다.

쓰임:
  python scripts/sync_meta.py            # 고치고 바뀐 장수를 알려준다
  python scripts/sync_meta.py --check    # 고치지 않고 빠진 곳만 센다
"""
import argparse
import html as html_mod
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://calrank.vercel.app/"

TITLE_RE = re.compile(r"<title\b[^>]*>(.*?)</title>", re.S | re.I)
HEAD_END = re.compile(r"</head>", re.I)
CANON_RE = re.compile(r'rel\s*=\s*"canonical"', re.I)
# 목차가 없는 게 맞는 페이지. sync_nav.py 의 SKIP 과 뜻이 다르다 — 여기서는
# "색인 대상이 아닌 페이지"를 뜻한다.
NOINDEX_EXTRA = {"greeting.html"}


def meta_of(doc: str, *, name: str = "", prop: str = "") -> str:
    """속성 순서에 상관없이 meta 를 찾는다.

    `<meta id="metaDesc" name="description" …>` 처럼 id 가 앞에 오는 페이지가
    있어서, name= 으로 시작하는 정규식만 쓰면 있는 걸 없다고 센다.
    """
    for m in re.finditer(r"<meta\b([^>]*)>", doc, re.I):
        attrs = m.group(1)
        k = re.search(r'\bname\s*=\s*"([^"]*)"', attrs, re.I)
        p = re.search(r'\bproperty\s*=\s*"([^"]*)"', attrs, re.I)
        c = re.search(r'\bcontent\s*=\s*"([^"]*)"', attrs, re.I)
        if not c:
            continue
        if name and k and k.group(1).lower() == name:
            return html_mod.unescape(c.group(1)).strip()
        if prop and p and p.group(1).lower() == prop:
            return html_mod.unescape(c.group(1)).strip()
    return ""


def canonical_url(rel: str) -> str:
    return SITE if rel == "index.html" else SITE + rel


def indexable(path: Path, doc: str) -> bool:
    if path.name.startswith(("naver", "google")):
        return False
    if path.name in NOINDEX_EXTRA:
        return False
    return "noindex" not in meta_of(doc, name="robots").lower()


def fix(path: Path, rel: str, check: bool) -> list[str]:
    doc = path.read_text(encoding="utf-8")
    if not indexable(path, doc):
        return []
    if not HEAD_END.search(doc):
        return []

    added, inserts = [], []
    if not CANON_RE.search(doc):
        inserts.append('<link rel="canonical" href="%s">' % canonical_url(rel))
        added.append("canonical")

    if not meta_of(doc, prop="og:title"):
        m = TITLE_RE.search(doc)
        title = (m.group(1).strip() if m else "")
        if title:
            # 제목은 이미 escape 된 상태로 들어 있으니 그대로 옮긴다.
            inserts.append('<meta property="og:title" content="%s">' % title)
            added.append("og:title")

    if added and not check:
        block = "".join("  %s\n" % line for line in inserts)
        doc = HEAD_END.sub(lambda _m: block + "</head>", doc, count=1)
        path.write_text(doc, encoding="utf-8")
    return added


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    tally: dict[str, int] = {}
    touched = 0
    paths = [(p, p.name) for p in sorted(ROOT.glob("*.html"))]
    paths += [(p, "e/" + p.name) for p in sorted((ROOT / "e").glob("*.html"))]
    for path, rel in paths:
        added = fix(path, rel, args.check)
        if added:
            touched += 1
            for a in added:
                tally[a] = tally.get(a, 0) + 1

    word = "빠진 곳" if args.check else "채움"
    if not tally:
        print("[meta] 빠진 곳 없습니다 (%d장 확인)" % len(paths))
    else:
        print("[meta] %s — %s · 페이지 %d장 / 전체 %d장"
              % (word, " · ".join("%s %d" % kv for kv in sorted(tally.items())),
                 touched, len(paths)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

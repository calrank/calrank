#!/usr/bin/env python3
"""구조화 데이터(JSON-LD)가 하나도 없는 페이지에 기본형을 채운다.

검색엔진과 AI 검색은 페이지가 무엇인지(글, 안내, 목록)와 어디에 속하는지(빵부스러기)를
JSON-LD 로 읽는다. 생성기가 만드는 페이지(코스·산·등급·장비·대회)는 이미 갖고 있고,
손으로 만든 페이지와 오래된 생성기 산출물만 비어 있다.

날짜는 넣지 않는다. 이 단계는 파일만 보고 돌아서 "언제 고쳤는지"를 알 수 없고,
틀린 날짜는 없는 것보다 나쁘다.

  python scripts/sync_seo.py           # 채운다
  python scripts/sync_seo.py --check   # 빠진 곳만 센다
"""
import argparse
import html as html_mod
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://calrank.vercel.app/"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sync_meta import meta_of, indexable, TITLE_RE, HEAD_END  # noqa: E402

ORG = {"@type": "Organization", "name": "칼랭크", "url": SITE,
       "logo": SITE + "favicon-512.png"}


def kind_of(name: str):
    """(스키마 유형, 상위 목록 페이지, 상위 이름)"""
    n = name[:-5]
    if n.startswith("column-"):
        return "Article", "column.html", "칼럼"
    if n.startswith("goal-"):
        return "WebPage", "goals.html", "목표 기록"
    if n.startswith("events-archive"):
        return "CollectionPage", "events-index.html" if n != "events-archive" else None, "대회 보관함"
    if n in ("about",):
        return "AboutPage", None, None
    if n in ("contact",):
        return "ContactPage", None, None
    if n.endswith("-monthly") or n == "monthly":
        return "CollectionPage", None, None
    return "WebPage", None, None


def build(name: str, doc: str):
    m = TITLE_RE.search(doc)
    title = html_mod.unescape(m.group(1)).strip() if m else ""
    desc = meta_of(doc, name="description")
    h1m = re.search(r"<h1\b[^>]*>(.*?)</h1>", doc, re.S)
    h1 = html_mod.unescape(re.sub(r"<[^>]+>", "", h1m.group(1))).strip() if h1m else title
    if not title:
        return None
    typ, parent, parent_name = kind_of(name)
    url = SITE + name
    main = {"@context": "https://schema.org", "@type": typ, "name": h1 or title,
            "url": url, "inLanguage": "ko",
            "isPartOf": {"@type": "WebSite", "name": "calrank", "url": SITE}}
    if desc:
        main["description"] = desc
    if typ == "Article":
        main["headline"] = (h1 or title)[:110]
        main["mainEntityOfPage"] = url
        main["author"] = ORG
        main["publisher"] = ORG
    crumbs = [{"@type": "ListItem", "position": 1, "name": "calrank", "item": SITE + "index.html"}]
    if parent and (ROOT / parent).exists():
        crumbs.append({"@type": "ListItem", "position": 2, "name": parent_name, "item": SITE + parent})
    crumbs.append({"@type": "ListItem", "position": len(crumbs) + 1, "name": h1 or title})
    bc = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": crumbs}
    return [main, bc]


def fix(path: Path, check: bool) -> bool:
    doc = path.read_text(encoding="utf-8")
    if not indexable(path, doc) or not HEAD_END.search(doc):
        return False
    if "application/ld+json" in doc:
        return False
    blocks = build(path.name, doc)
    if not blocks:
        return False
    if not check:
        tags = "".join('<script type="application/ld+json">%s</script>\n'
                       % json.dumps(b, ensure_ascii=False) for b in blocks)
        doc = HEAD_END.sub(lambda _m: tags + "</head>", doc, count=1)
        path.write_text(doc, encoding="utf-8")
    return True


def org_home(check: bool) -> bool:
    """홈에 Organization 이 없으면 둔다. 어디서나 같은 이름·로고로 불리게 한다."""
    p = ROOT / "index.html"
    doc = p.read_text(encoding="utf-8")
    if '"@type": "Organization"' in doc or '"@type":"Organization"' in doc:
        return False
    if not check:
        tag = ('<script type="application/ld+json">%s</script>\n'
               % json.dumps(dict(ORG, **{"@context": "https://schema.org"}), ensure_ascii=False))
        doc = HEAD_END.sub(lambda _m: tag + "</head>", doc, count=1)
        p.write_text(doc, encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    n = sum(fix(p, a.check) for p in sorted(ROOT.glob("*.html")))
    n += org_home(a.check)
    word = "빠진 곳" if a.check else "채움"
    print("[seo] 구조화 데이터 %s %d장" % (word, n) if n else "[seo] 구조화 데이터 빠진 곳 없습니다")
    return 0


if __name__ == "__main__":
    sys.exit(main())

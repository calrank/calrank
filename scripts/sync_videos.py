#!/usr/bin/env python3
"""참고 영상 카드를 페이지에 꽂는다.

자료: data/videos.json
  items[] = { id, pages[] 또는 title_in[]+only, title, channel, kind, published, checked, status? }
  - id        YouTube 영상 ID
  - pages     카드를 달 페이지. 파일 이름 또는 * 가 든 패턴 (예: course-dr-*.html)
  - kind      '공식 기관', '연맹 공식', '지자체 공식' 처럼 누가 올렸는지
  - checked   사람이 채널과 내용을 확인한 날
  - official  false 면 '비공식 해설 영상'으로 표시 (기본 true = 공식 채널)
  - published YYYY-MM-DD (3년 넘으면 카드에 오래됐다는 안내가 붙는다)
  - status    'dead' 면 그리지 않는다 (점검 스크립트가 바꾼다)

대표 이미지는 YouTube 가 영상마다 내려 주는 주소(i.ytimg.com)를 그대로 불러온다.
파일을 내려받아 두지 않고, 영상 화면을 따로 캡처하지도 않는다.
카드는 영상을 불러오지 않는 링크라서 페이지 속도에 영향이 거의 없다.
재생 아이콘은 Material Icons(Apache 2.0)의 play_circle 이다.

판정의 근거가 아니라 이해를 돕는 자료라는 점을 카드에 적는다.

  python scripts/sync_videos.py          # 반영
  python scripts/sync_videos.py --check  # 어긋난 곳만 센다
"""
import argparse
import fnmatch
import html as html_mod
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "videos.json"
START, END = "<!--vid-->", "<!--/vid-->"
BLOCK = re.compile(re.escape(START) + r".*?" + re.escape(END) + r"\n?", re.S)
LINK = '<link rel="stylesheet" href="video.css">\n'
PLAY = ('<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 '
        '10-4.48 10-10S17.52 2 12 2zm-2 14.5v-9l6 4.5-6 4.5z"/></svg>')
MAX_PER_PAGE = 2


def esc(s):
    return html_mod.escape(s or "", quote=True)


THIS_YEAR = 2026


def note_of(v):
    parts = []
    if v.get("official", True):
        parts.append("이해를 돕는 참고 영상이며 판정의 근거가 아닙니다.")
    else:
        parts.append("공식 자료가 아닌 비공식 해설 영상입니다. 판정의 근거가 아니며, 내용은 올린 곳의 책임입니다.")
    y = int((v.get("published") or "0")[:4] or 0)
    if y and THIS_YEAR - y >= 3:
        parts.append("%d년에 올라온 영상이라 지금의 규정·제품과 다를 수 있으니 본문의 판정을 기준으로 봅니다." % y)
    parts.append("YouTube로 연결됩니다.")
    return " ".join(parts)


_GEO = None
_MT = None


def _load_geo():
    global _GEO, _MT
    if _GEO is not None:
        return
    _GEO, _MT = [], {}
    try:
        g = json.loads((ROOT / "data" / "mountain_geocache.json").read_text(encoding="utf-8"))
        for k, arr in g.items():
            for e in arr or []:
                try:
                    _GEO.append((k.split(" ")[0], float(e["lat"]), float(e["lon"]), e.get("display_name", "")))
                except (KeyError, ValueError):
                    pass
        d = json.loads((ROOT / "data" / "mountains.json").read_text(encoding="utf-8"))
        L = d if isinstance(d, list) else (d.get("items") or d.get("mountains") or [])
        for m in L:
            if m.get("sections"):
                _MT[m["id"]] = tuple(m["sections"][0]["path"][0])
    except Exception:
        pass


def mountain_subject(name):
    """mountain-<id>.html 의 산 이름과 지역. 제목의 괄호 주소를 먼저 쓰고, 없으면 좌표가 가장 가까운 지명 자료로 채운다."""
    mm = re.match(r"mountain-(\d+)\.html$", name)
    if not mm:
        return None, None
    t = title_of(name)
    m = re.match(r"(.+?)\s*(?:\((.*?)\))?\s*등산로", t)
    if not m:
        return None, None
    base, region = m.group(1).strip(), (m.group(2) or "").strip()
    if region and not re.search(r"(도|시|군|구)", region):
        region = ""
    if not region:
        _load_geo()
        pt = _MT.get(mm.group(1))
        best = None
        if pt:
            for nm, la, lo, dn in _GEO:
                if nm != base:
                    continue
                dist = abs(la - pt[0]) + abs(lo - pt[1])
                if dist < 0.1 and (best is None or dist < best[0]):
                    best = (dist, dn)
        if best:
            parts = [x.strip() for x in best[1].split(",")][1:]
            parts = [x for x in parts if x and not x.isdigit() and x != "대한민국"]
            region = " ".join(reversed(parts))
    return base, region


def card(v, subject=None, region=None):
    vid = v["id"]
    url = f"https://www.youtube.com/watch?v={vid}"
    kind = v.get("kind") or ("공식" if v.get("official", True) else "")
    meta = " · ".join(x for x in [region, v.get("channel"), kind,
                                    (v.get("published") or "")[:7].replace("-", ".") or None] if x)
    return (
        '<section class="vid-card"><h2>' + esc((subject + " " if subject else "") + ("참고 영상" if v.get("official", True) else "비공식 해설 영상")) + '</h2>'
        f'<a class="vid-link" href="{url}" target="_blank" rel="noopener" '
        f'aria-label="{esc(v["title"])} — YouTube에서 보기">'
        f'<img class="vid-thumb" src="https://i.ytimg.com/vi/{vid}/hqdefault.jpg" '
        f'alt="" width="480" height="360" loading="lazy" decoding="async">'
        f'<span class="vid-play">{PLAY}</span>'
        f'<span class="vid-cap"><b>{esc(v["title"])}</b><span>{esc(meta)}</span></span></a>'
        f'<p class="vid-note">{esc(note_of(v))}</p></section>')


def load():
    if not DATA.exists():
        return []
    items = json.loads(DATA.read_text(encoding="utf-8")).get("items", [])
    return [v for v in items if v.get("status") != "dead" and v.get("id") and v.get("checked")]


TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)


def title_of(name):
    m = TITLE_RE.search((ROOT / name).read_text(encoding="utf-8"))
    return m.group(1) if m else ""


def hit(v, name, title):
    if any(fnmatch.fnmatch(name, p) for p in v.get("pages", [])):
        return True
    # title_in: 페이지 <title> 에 이 낱말이 있으면 단다 (course-dr-* 처럼 경로 이름이 제목에 있는 쪽)
    pats = v.get("title_in", [])
    if pats and fnmatch.fnmatch(name, v.get("only", "*")):
        return any(w in title for w in pats)
    return False


def want_for(name, items):
    title = title_of(name)
    return [v for v in items if hit(v, name, title)][:MAX_PER_PAGE]


def sync(path, items, check):
    doc = path.read_text(encoding="utf-8")
    vids = want_for(path.name, items)
    base = BLOCK.sub("", doc)
    if vids and "</main>" in base:
        subj, reg = mountain_subject(path.name)
        block = START + "".join(card(v, subj, reg) for v in vids) + END + "\n"
        new = base.replace("</main>", block + "</main>", 1)
        if LINK not in new and "</head>" in new:
            new = new.replace("</head>", LINK + "</head>", 1)
    else:
        new = base.replace(LINK, "") if START not in base else base
    if new == doc:
        return False
    if not check:
        path.write_text(new, encoding="utf-8")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    items = load()
    # 카드가 이미 달린 페이지도 다시 봐야 영상이 빠졌을 때 걷어낸다.
    names = set()
    for p in ROOT.glob("*.html"):
        if want_for(p.name, items):
            names.add(p.name)
            continue
        if START in p.read_text(encoding="utf-8"):
            names.add(p.name)
    n = sum(sync(ROOT / nm, items, a.check) for nm in sorted(names))
    cards = sum(1 for nm in names if want_for(nm, items))
    print("[videos] 영상 카드 %d장 · %s %d장" % (cards, "어긋난 곳" if a.check else "고친 페이지", n))
    return 0


if __name__ == "__main__":
    sys.exit(main())

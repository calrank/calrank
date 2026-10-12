"""모든 페이지의 목차를 site_nav.py 의 정의와 맞춘다.

손으로 만든 페이지는 생성기를 거치지 않아 목차가 옛날 그대로 남는다.
이 스크립트가 <nav class="main-nav"> … </nav> 부분만 갈아 끼운다.
머리말·꼬리말의 다른 부분은 건드리지 않는다.

워크플로에서 매일 돌아서, 생성기를 고쳐도 손으로 만든 페이지가
뒤처지는 일이 없게 한다.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from site_nav import active_for, nav_html  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NAV_RE = re.compile(r'<nav class="main-nav">.*?</nav>', re.S)

# 목차가 없는 게 맞는 페이지들
SKIP = {"widget.html", "greeting.html"}


def sync(path: Path) -> bool:
    if path.name in SKIP or path.name.startswith("naver"):
        return False
    html = path.read_text(encoding="utf-8")
    if not NAV_RE.search(html):
        return False
    # 대회 상세 페이지(e/…)는 파일 이름이 대회 id 라 접두사로 못 찾는다. 캘린더로 둔다.
    active = "calendar" if path.parent.name == "e" else active_for(path.name)
    want = nav_html(active)
    new = NAV_RE.sub(lambda _m: want, html, count=1)
    if new == html:
        return False
    path.write_text(new, encoding="utf-8")
    return True


def main() -> None:
    changed = []
    for path in sorted(ROOT.glob("*.html")):
        if sync(path):
            changed.append(path.name)
    for path in sorted((ROOT / "e").glob("*.html")):
        if sync(path):
            changed.append("e/" + path.name)
    print(f"[nav] 목차를 맞춘 페이지 {len(changed)}개")
    if changed:
        head = [c for c in changed if not c.startswith("e/")]
        print("      " + ", ".join(head[:10]) + (" …" if len(head) > 10 else ""))


if __name__ == "__main__":
    main()

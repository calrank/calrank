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
from site_nav import WORDMARK, active_for, nav_html  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NAV_RE = re.compile(r'<nav class="main-nav">.*?</nav>', re.S)
# 로고도 같이 맞춘다. 손으로 만든 페이지에 옛 글자 로고가 남으면 머리줄만 다른 사이트가 된다.
MARK_RE = re.compile(r'<a href="index\.html" class="wordmark"[^>]*>.*?</a>', re.S)

# 꼬리말 한 줄은 모든 페이지에 깔린다. 이름을 한글로도 적어 둬야 사람들이
# "칼랭크"로 기억하고 그렇게 검색도 한다. 영문만 쓰면 읽는 법이 안 남는다.
#
# 이 한 줄이 사이트를 정의하는 유일한 문장이라, 전에 쓰던 "공개한 일정 정보를
# 정리해 제공합니다"는 스스로를 수집기로 소개하는 셈이었다. 하는 일(등급 판정)을
# 앞에 두고, 면책은 뒤 문장으로 떼어 놓는다. 페이지마다 붙는 그 뒤의 면책
# 문구는 그대로 남는다.
BRAND_SUBS = [
    ("calrank는 대회 주최측이", "칼랭크(CALRANK)는 대회 주최측이"),
    ("대회 주최측이 공개한 일정 정보를 정리해 제공합니다.",
     "달린 기록이 어느 등급인지 읽어 주고, 다음 출발선을 찾아 주는 곳입니다. "
     "대회 일정은 주최측이 공개한 내용을 정리한 것입니다."),
]

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
    new = MARK_RE.sub(lambda _m: WORDMARK, new, count=1)
    for _o, _n in BRAND_SUBS:
        new = new.replace(_o, _n)
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
    print(f"[nav] 목차·로고를 맞춘 페이지 {len(changed)}개")
    if changed:
        head = [c for c in changed if not c.startswith("e/")]
        print("      " + ", ".join(head[:10]) + (" …" if len(head) > 10 else ""))


if __name__ == "__main__":
    main()

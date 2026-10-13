"""모든 페이지의 파비콘 선언을 한 벌로 맞춘다.

네이버 검색 결과에 기본 지구본이 떴다. 원인은 /favicon.ico 가 없고
favicon.svg 하나만 있었던 것이다. 구글이 파비콘으로 지원하는 형식에는
SVG 가 없다(BMP·GIF·ICO·PNG·JPEG·PPM·TIFF). 크롤러는 링크 태그가 없어도
/favicon.ico 를 관례적으로 찾으므로 그 파일이 가장 중요하고,
선언은 페이지마다 같아야 한다.

sync_nav.py 와 같은 방식으로 워크플로에서 매번 돌려, 생성기가 옛 선언을
다시 써 넣어도 커밋 전에 교정되게 한다.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BLOCK = ('<link rel="icon" href="/favicon.ico" sizes="any">\n'
         '<link rel="icon" type="image/svg+xml" href="/favicon.svg">\n'
         '<link rel="icon" type="image/png" sizes="96x96" href="/favicon-96.png">\n'
         '<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">')

# 기존 아이콘 선언을 통째로 집어낸다. manifest 줄은 건드리지 않는다.
ICON_RE = re.compile(
    r'(?:[ \t]*<link[^>]*rel="(?:shortcut )?icon"[^>]*>\s*'
    r'|[ \t]*<link[^>]*rel="apple-touch-icon(?:-precomposed)?"[^>]*>\s*)+')

SKIP = {"widget.html", "greeting.html"}


def main() -> None:
    changed = []
    for f in sorted(list(ROOT.glob("*.html")) + list(ROOT.glob("e/*.html"))):
        if f.name in SKIP or f.name.startswith("naver"):
            continue
        s = f.read_text(encoding="utf-8")
        m = ICON_RE.search(s)
        if m:
            new = s[:m.start()] + BLOCK + "\n" + s[m.end():]
        elif "</head>" in s:
            # 선언이 아예 없는 페이지도 있다(ranking.html 등). 머리말 끝에 넣는다.
            i = s.index("</head>")
            new = s[:i] + BLOCK + "\n" + s[i:]
        else:
            continue
        if new != s:
            f.write_text(new, encoding="utf-8")
            changed.append(f.name)
    print(f"[icons] 파비콘 선언을 맞춘 페이지 {len(changed)}개")
    if changed:
        print("      " + ", ".join(changed[:10]) + (" …" if len(changed) > 10 else ""))


if __name__ == "__main__":
    main()

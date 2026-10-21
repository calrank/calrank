"""하드코딩된 색을 style.css 의 토큰으로 바꾼다.

사이트가 밝은 바탕/어두운 바탕 두 벌을 쓰게 되면서, 색은 :root 변수 한 곳에서만
정해져야 한다. 그런데 페이지마다 <style> 안에 #fff, #141414 같은 값이 박혀 있어서
바탕만 바꾸면 글자가 안 보이게 된다. 이 스크립트가 그 값들을 var(--…) 로 갈아 끼운다.

sync_nav.py 와 같은 자리에서 매일 돌아, 생성기가 새로 찍어낸 페이지도 하루 안에
토큰으로 맞춰진다. 이미 var(--…) 인 자리는 건드리지 않으므로 여러 번 돌려도 안전하다.

#fff 만 맥락을 본다. 주황(accent) 배경 위에 얹힌 흰 글자는 두 벌 모두에서 흰색이라야
하므로 --on-accent 로, 그냥 강조 글자면 --ink 로 보낸다.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 밝기대로 묶었다. 어두운 바탕에서 쓰던 값 → 뜻이 같은 토큰.
PLAIN = {
    # 바탕
    "#0b0b0b": "var(--bg)", "#0d0d0d": "var(--bg)",
    # 카드/패널
    "#141414": "var(--surface)", "#171514": "var(--surface)",
    "#121010": "var(--surface)", "#161311": "var(--surface)",
    "#222": "var(--surface)",
    # 선
    "#2e2e2e": "var(--line)",
    "#2a2a2a": "var(--border)",
    # 글자 — 흰색에 가까운 강조
    "#e8e4e1": "var(--ink)", "#d8d4d2": "var(--ink)",
    "#d6d1cd": "var(--ink)", "#d6d0cc": "var(--ink)",
    # 글자 — 본문
    "#c8c4c2": "var(--ink-soft)", "#c9c3bf": "var(--ink-soft)",
    "#c3bdb9": "var(--ink-soft)", "#b5afab": "var(--ink-soft)",
    "#b8b0ac": "var(--ink-soft)", "#a9a29e": "var(--ink-soft)",
    # 글자 — 흐린
    "#9a9a9a": "var(--ink-faint)", "#8e8884": "var(--ink-faint)",
    "#6a6a6a": "var(--ink-faint)",  # 예전 흐린 회색 — 대비가 3.6:1 뿐이라 쓰면 안 된다
    "#8e8e8e": "var(--ink-faint)", "#5e5a57": "var(--ink-faint)",
    # 그 밖
    "#d4af37": "var(--gold)",
    "#c9a6ff": "var(--elite-line)", "#b892ff": "var(--elite-line)",
    "#9ea6ad": "var(--silver-line)",
    "#ff6b4a": "var(--accent)",
}

# 어두운 바탕 전용으로 깔던 살짝 밝은 막. 밝은 바탕에선 반대로 어두워야 한다.
# 투명도를 숫자로 읽어서 단계를 고른다 — 정규식으로 자릿수를 세면 0.1 이 0.03 쪽으로 샌다.
WHITE_FILM = re.compile(r"rgba\(\s*255\s*,\s*255\s*,\s*255\s*,\s*([0-9.]+)\s*\)")


def _film(m: "re.Match") -> str:
    a = float(m.group(1))
    if a >= 0.5:          # 사실상 흰색
        return "var(--ink)"
    if a <= 0.045:
        return "var(--tint-1)"
    if a <= 0.08:
        return "var(--tint-2)"
    return "var(--tint-3)"


WHITE = re.compile(r"#(?:fff|ffffff)\b", re.I)
# 주황을 "글자색"으로 쓰면 밝은 바탕에서 3.2:1 밖에 안 나온다. 글자일 때만 어두운 주황으로.
# 배경이나 테두리로 쓰는 주황은 그대로 둔다.
ACCENT_TEXT = re.compile(r"(?<![-\w])color:\s*(?:var\(--accent(?:,\s*#[0-9A-Fa-f]{3,6})?\)|#[fF][fF]3[dD]1[aA])")
RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")
# 이 규칙의 배경이 주황이면, 그 위 흰 글자는 두 벌 모두에서 흰색이어야 한다.
ON_ACCENT = re.compile(r"background[^;]*(?:var\(--accent\)|#[fF][fF]3[dD]1[aA]|linear-gradient)")


def _decl(body: str) -> str:
    """규칙 하나의 속성 묶음을 고친다."""
    on_accent = bool(ON_ACCENT.search(body))
    out = []
    for decl in body.split(";"):
        low = decl.lower()
        if WHITE.search(decl):
            prop = low.split(":")[0].strip()
            if prop.startswith("color") and not on_accent:
                decl = WHITE.sub("var(--ink)", decl)
            elif prop.startswith("color"):
                decl = WHITE.sub("var(--on-accent)", decl)
            elif prop.startswith("background"):
                decl = WHITE.sub("var(--surface)", decl)
        out.append(decl)
    return ";".join(out)


def convert(css: str) -> str:
    css = RULE.sub(lambda m: m.group(1) + "{" + _decl(m.group(2)) + "}", css)
    css = WHITE_FILM.sub(_film, css)
    css = ACCENT_TEXT.sub("color:var(--accent-ink)", css)
    # 긴 것부터 바꿔야 #222 가 #2222… 를 먹지 않는다.
    for hx in sorted(PLAIN, key=len, reverse=True):
        css = re.sub(re.escape(hx) + r"\b", PLAIN[hx], css, flags=re.I)
    return css


# style="…" 속성 안에도 색이 박혀 있다. <style> 블록만 고치면 이 자리가 남아서
# 밝은 바탕에 흰 글자 같은 안 보이는 조합이 생긴다.
ATTR = re.compile(r'style="([^"]*)"')
# 종목색은 뜻이 분명하니 종목 토큰으로 보낸다. 밝은 바탕에서는 어두운 쪽으로 바뀐다.
SPORT = {
    "#ff3d1a": "var(--marathon)", "#4caf7d": "var(--trail)",
    "#5b8def": "var(--cycling)", "#b37fea": "var(--triathlon)",
    "#00c2a8": "var(--inline)", "#f2c230": "var(--hyrox)",
}
# var(--x, #fallback) 안의 값은 실제로 쓰이지 않으니 건드리지 않는다.
VARFALL = re.compile(r"var\(--[\w-]+\s*,\s*#[0-9A-Fa-f]{3,6}\s*\)")


def convert_attr(body: str) -> str:
    keep = []
    body = VARFALL.sub(lambda m: (keep.append(m.group(0)), f"\x00{len(keep)-1}\x00")[1], body)
    for hx, tok in SPORT.items():
        body = re.sub(re.escape(hx) + r"\b", tok, body, flags=re.I)
    body = _decl(body)
    for hx in sorted(PLAIN, key=len, reverse=True):
        body = re.sub(re.escape(hx) + r"\b", PLAIN[hx], body, flags=re.I)
    body = WHITE_FILM.sub(_film, body)
    return re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], body)


STYLE = re.compile(r"(<style>)(.*?)(</style>)", re.S)

# 로고에 쓰는 Archivo Black 을 이미 있는 폰트 주소에 얹는다. @import 로 따로 받으면
# style.css 를 받은 다음에야 폰트를 부르러 가서 로고가 한 박자 늦게 뜬다.
# 공유될 때 뜨는 사이트 이름. 한글 이름을 같이 적어 둬야 "칼랭크"로 기억에 남는다.
# 제목(title)은 검색 순위가 걸려 있어 건드리지 않는다.
SITE_NAME_OLD = 'og:site_name" content="calrank"'
SITE_NAME_NEW = 'og:site_name" content="\uce7c\ub7ad\ud06c(CALRANK)"'

FONT_OLD = "css2?family=Noto+Sans+KR:wght@400;700;900&display=swap"
FONT_NEW = "css2?family=Archivo+Black&family=Noto+Sans+KR:wght@400;700;900&display=swap"

# 주소창 색. 한 줄짜리 고정값이면 바탕 두 벌에 맞춰 두 줄로 바꾼다.
TC_OLD = re.compile(r'[ \t]*<meta name="theme-color" content="#0B0B0B"\s*/?>\n?', re.I)
TC_NEW = ('<meta name="theme-color" content="#F5F2EF" media="(prefers-color-scheme: light)">\n'
          '<meta name="theme-color" content="#0B0B0B" media="(prefers-color-scheme: dark)">\n')


def do_html(path: Path) -> bool:
    h = path.read_text(encoding="utf-8")
    new = STYLE.sub(lambda m: m.group(1) + convert(m.group(2)) + m.group(3), h)
    new = ATTR.sub(lambda m: 'style="' + convert_attr(m.group(1)) + '"', new)
    new = TC_OLD.sub(TC_NEW, new, count=1)
    new = new.replace(FONT_OLD, FONT_NEW)
    new = new.replace(SITE_NAME_OLD, SITE_NAME_NEW)
    if new == h:
        return False
    path.write_text(new, encoding="utf-8")
    return True


def do_css(path: Path) -> bool:
    c = path.read_text(encoding="utf-8")
    # style.css 의 :root 와 어두운 모드 블록은 색을 "정의"하는 자리라 건드리면 안 된다.
    if path.name == "style.css":
        cut = c.index("*{box-sizing:border-box;}")
        head, body = c[:cut], c[cut:]
        new = head + convert(body)
    else:
        new = convert(c)
    if new == c:
        return False
    path.write_text(new, encoding="utf-8")
    return True


def main() -> None:
    n = 0
    for path in sorted(ROOT.glob("*.css")):
        if do_css(path):
            n += 1
            print(f"      {path.name}")
    css_n = n
    pages = []
    for pat in ("*.html", "e/*.html"):
        for path in sorted(ROOT.glob(pat)):
            if do_html(path):
                pages.append(path.name)
    print(f"[theme] 스타일시트 {css_n}개 · 페이지 {len(pages)}개를 토큰으로 맞췄다")
    if "--check" in sys.argv and (css_n or pages):
        sys.exit(1)


if __name__ == "__main__":
    main()

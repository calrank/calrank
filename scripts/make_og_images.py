"""종목별 공유 카드(OG 이미지) 생성.

카카오톡·페이스북에 링크를 붙였을 때 뜨는 그림이다. 지금은 모든 페이지가
og-image.png 하나를 쓴다. 지역·종목 랜딩 페이지가 수십 개인데 그림이 다 같으면
어떤 링크인지 구분이 안 된다.

엠블럼(sport_emblems.py)과 같은 조형을 써서 종목마다 한 장씩 만든다.
SVG 로 조판하고 PNG 로 굽는다 — 글꼴에 의존하지 않도록 글자는 쓰지 않고
엠블럼과 굵은 선으로만 구성한다... 가 아니라, 한글이 필요하므로
시스템에 설치된 글꼴을 찾아 쓰고 없으면 만들지 않는다(빈 네모가 찍히는 것보다 낫다).
"""
import subprocess
import sys
from pathlib import Path

import cairosvg

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sport_emblems import SPORTS, _ART  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
W, H = 1200, 630
BG = "#0B0B0B"


def pick_font() -> str | None:
    """한글이 그려지는 글꼴 이름을 찾는다."""
    try:
        out = subprocess.run(["fc-list", ":lang=ko", "family"],
                             capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    names = {line.split(",")[0].strip() for line in out.splitlines() if line.strip()}
    # 한국어 자형이 든 글꼴을 먼저 쓴다. "Noto Sans CJK TC"(번체) 같은 걸
    # 집으면 한글이 빈 네모로 찍힌다.
    for want in ("Noto Sans KR", "Noto Sans CJK KR", "NanumGothic", "Malgun Gothic"):
        if want in names:
            return want
    for name in sorted(names):
        if name.endswith("KR") or "Nanum" in name or "Gothic" in name:
            return name
    return next(iter(sorted(names)), None)


def card_svg(sport: str, font: str) -> str:
    meta = SPORTS[sport]
    color = meta["color"]
    art = _ART[sport].strip()
    # 엠블럼을 220px 로 키워 왼쪽에, 오른쪽에 글자
    scale = 220 / 64
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">
  <rect width="{W}" height="{H}" fill="{BG}"/>
  <rect x="0" y="0" width="{W}" height="6" fill="{color}"/>
  <g transform="translate(120,205) scale({scale})" style="color:{color}">
    <circle cx="32" cy="32" r="29" fill="none" stroke="{color}"
            stroke-opacity=".32" stroke-width="1.6"/>
    <g fill="none" stroke="currentColor" stroke-width="3.5"
       stroke-linecap="round" stroke-linejoin="round">{art}</g>
  </g>
  <text x="400" y="268" font-family="{font}" font-size="86" font-weight="900"
        fill="#FFFFFF">{meta['label']} 대회 일정</text>
  <text x="400" y="340" font-family="{font}" font-size="36" font-weight="400"
        fill="#B8B0AC">전국 대회를 한곳에 · 접수 마감일까지</text>
  <text x="400" y="430" font-family="{font}" font-size="34" font-weight="900"
        fill="{color}" letter-spacing="3">CALRANK</text>
</svg>"""


def main() -> None:
    font = pick_font()
    if not font:
        print("[og] 한글 글꼴을 찾지 못해 만들지 않습니다")
        return
    print(f"[og] 글꼴: {font}")
    for sport in SPORTS:
        out = ROOT / f"og-{sport}.png"
        cairosvg.svg2png(bytestring=card_svg(sport, font).encode("utf-8"),
                         write_to=str(out), output_width=W, output_height=H)
        print(f"[og] {out.name} ({out.stat().st_size // 1024}KB)")


if __name__ == "__main__":
    main()

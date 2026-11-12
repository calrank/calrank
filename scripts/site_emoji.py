"""칼랭크 이모지 — Microsoft Fluent Emoji (Color), MIT 라이선스.
파일은 /emoji/*.svg, 라이선스 전문은 /emoji/LICENSE.txt.
한 세트만 쓰고 글자 이모지(❤️ 등)는 쓰지 않는다. 기기마다 모양이 달라져 일관성이 깨지기 때문이다.

쓰는 법: emo("mountain") → <img class="emo" ...>
크기와 정렬은 style.css 의 .emo 한 곳에서만 정한다(글자 크기에 비례).
"""
from pathlib import Path

_DIR = Path(__file__).resolve().parent.parent / "emoji"


def emo(name: str, cls: str = "") -> str:
    if not (_DIR / f"{name}.svg").exists():
        raise ValueError(f"이모지 파일이 없습니다: {name}")
    c = "emo" + (f" {cls}" if cls else "")
    return (f'<img class="{c}" src="/emoji/{name}.svg" alt="" width="24" height="24" '
            f'decoding="async" aria-hidden="true">')

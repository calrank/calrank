"""제휴 블록 그리기(기어 생성기와 칼럼용 sync_affiliate 가 함께 쓴다).

원칙(Kevin, 2026-11-22):
  1. 대가성 문구는 위에 크게 두지 않는다. 배너 아래에 작고 옅게 둔다(공정위 심사지침이 말하는 "링크 인근 명확 표시"는 지킨다).
  2. 글자 링크가 아니라 상품 이미지가 보이는 쿠팡 공식 배너(다이나믹 배너, 상품 직접 선택)를 보여 준다.
     눌러 볼 만한 이름 있는 인기 상품을 담는다. 가격·재고는 쿠팡이 직접 갱신한다.
data/affiliate_links.json 의 항목: {page, label, url, widget(배너 id), w, h}. 최상위 tracking 은 파트너스 트래킹 코드.
widget 이 없는 항목은 배너가 만들어질 때까지 작은 글자 링크로 보인다(임시).
"""
import html as htmllib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AFF_FILE = ROOT / "data" / "affiliate_links.json"
# 대가성 문구. "쿠팡 파트너스 활동의 일환으로" 는 site_health 가 찾는 문구이므로 바꾸지 않는다.
NOTICE = "이 배너·링크는 쿠팡 파트너스 활동의 일환으로 일정액의 수수료를 받으며, 구매 가격은 달라지지 않습니다."


def load():
    try:
        return json.loads(AFF_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"items": []}


def rows_for(data, page):
    return [x for x in data.get("items", []) if x.get("page") == page
            and (x.get("widget") or str(x.get("url", "")).startswith("https://link.coupang.com/"))]


def render(page, cls_sec, data=None):
    """배너 블록 HTML. 항목이 없으면 빈 문자열. cls_sec 는 바깥 section 의 추가 클래스."""
    data = data or load()
    rows = rows_for(data, page)
    if not rows:
        return ""
    tc = str(data.get("tracking", ""))
    bk = next((k for k, v in (data.get("banners") or {}).items() if page in v.get("pages", [])), "")
    esc = htmllib.escape
    body = ""
    for x in rows:
        if x.get("widget") and tc:
            w, h = int(x.get("w", 340)), int(x.get("h", 90))
            src = (f"https://ads-partners.coupang.com/widgets.html?id={int(x['widget'])}&template=carousel"
                   f"&trackingCode={esc(tc)}&subId=&width={w}&height={h}&tsource=")
            body += (f'<div class="aff-ban" style="max-width:{w}px"><iframe src="{src}" width="{w}" height="{h}" loading="lazy" '
                     f'frameborder="0" scrolling="no" referrerpolicy="unsafe-url" title="{esc(x.get("label", "쿠팡 인기 상품"))} (광고)"></iframe></div>')
        else:
            body += (f'<p class="aff-lk"><a href="{esc(x["url"])}" rel="sponsored nofollow noopener" target="_blank" '
                     f'data-aff="{esc(page)}">{esc(x.get("label", "쿠팡에서 보기"))}</a></p>')
    return (f'<section class="aff-box {cls_sec}" aria-label="관련 제품(광고)" data-bk="{esc(bk)}">{body}'
            f'<p class="aff-note">{NOTICE}</p></section>'
            '<script defer src="funnel.js"></script><script defer src="aff.js"></script>')

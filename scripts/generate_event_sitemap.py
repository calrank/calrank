"""
calrank 개별 대회 페이지 사이트맵 자동 등록 스크립트

"대회리뷰/대회평/대회후기/대회총평/대회별점/대회평점" 같은 검색어로 각 대회의
event.html 페이지가 검색엔진에 노출되려면, 먼저 그 페이지가 사이트맵에 있어야
발견·색인 확률이 크게 오른다. events.json에 있는 모든 대회(현재 776개+)에 대해
event.html?id=... URL을 sitemap.xml에 자동으로 넣고, events.json이 매일 바뀔
때마다 다시 실행되어 최신 상태로 갱신한다.

사용 예시:
  python scripts/generate_event_sitemap.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE_URL = "https://calrank.vercel.app"


def load_json(path, default):
    p = ROOT / path
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    events = load_json("events.json", [])
    sitemap_path = ROOT / "sitemap.xml"
    xml = sitemap_path.read_text(encoding="utf-8")

    # 기존에 들어있던 event.html 항목들을 전부 제거한다(사라진 대회 정리 + 중복 방지).
    xml = re.sub(
        r"\s*<url>\s*<loc>[^<]*event\.html\?id=[^<]*</loc>.*?</url>",
        "",
        xml,
        flags=re.DOTALL,
    )

    entries = []
    for e in events:
        eid = e.get("id")
        if not eid:
            continue
        loc = f"{BASE_URL}/event.html?id={eid}"
        entries.append(
            f"  <url>\n"
            f"    <loc>{loc}</loc>\n"
            f"    <changefreq>weekly</changefreq>\n"
            f"    <priority>0.5</priority>\n"
            f"  </url>\n"
        )

    marker = "</urlset>"
    if marker in xml:
        xml = xml.replace(marker, "".join(entries) + marker)
        sitemap_path.write_text(xml, encoding="utf-8")

    print(f"Registered {len(entries)} event pages in sitemap.xml")


if __name__ == "__main__":
    main()

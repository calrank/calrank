"""사이트 자가점검. 배포 전에 깨질 수 있는 것을 숫자로 잡는다.

점검 항목
 치명(실패 처리): 사이트맵에 있는데 파일이 없는 주소 · 사이트맵 페이지의 noindex · 깨진 내부 링크 ·
                  홈의 봇 판별이 알려진 구글·네이버·빙 크롤러를 놓치는 경우 · canonical 불일치
 경고(보고만):   사이트맵 페이지 중 다른 페이지가 한 번도 링크하지 않는 고아 페이지 · 제목/설명 중복

이름에 bot 이 없는 크롤러(Google-InspectionTool 등)가 안내 페이지(noindex)로 보내져 색인 요청이
거부된 일이 있었다(2026-11-22). 같은 종류의 회귀를 매일 잡으려는 것이다.
사용: python3 scripts/site_health.py [--json]
"""
import json, re, sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse, unquote

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://calrank.kr"

CRAWLER_UAS = {
    "Googlebot-smartphone": "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Google-InspectionTool": "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36 (compatible; Google-InspectionTool/1.0)",
    "GoogleOther": "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36 (compatible; GoogleOther)",
    "AdsBot-Google": "Mozilla/5.0 (compatible; AdsBot-Google; +http://www.google.com/adsbot.html)",
    "Yeti(네이버)": "Mozilla/5.0 (compatible; Yeti/1.1; +https://naver.me/spd)",
    "Bingbot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm) Chrome/116.0.1938.76 Safari/537.36",
    "Daumoa(다음)": "Mozilla/5.0 (compatible; Daum/4.1; +http://cs.daum.net/faq/15/4118.html?faqId=28966)",
    "facebookexternalhit": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
}


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def sitemap_urls() -> list[str]:
    urls = []
    for name in ("sitemap.xml", "sitemap-events.xml"):
        t = read(ROOT / name)
        urls += re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", t)
    return urls


def to_file(url: str) -> Path | None:
    path = unquote(urlparse(url).path)
    if path in ("", "/"):
        path = "/index.html"
    f = ROOT / path.lstrip("/")
    return f if f.is_file() else None


def internal_target(href: str, src: Path, base_root: bool = False) -> str | None:
    """링크가 가리키는 사이트 안 파일 경로(루트 기준). 외부·메일·앵커는 None."""
    href = href.strip()
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:", "data:", "sms:", "webcal:")):
        return None
    u = urlparse(href)
    if u.scheme in ("http", "https"):
        if u.netloc.lower() not in ("calrank.kr", "www.calrank.kr"):
            return None
        path = u.path
    elif u.scheme:
        return None
    else:
        path = u.path
        if not path:
            return None
        if not path.startswith("/"):
            if base_root:  # <base href="/"> 가 있으면 루트 기준으로 해석된다
                path = "/" + path
            else:
                path = "/" + str((src.parent.relative_to(ROOT) / path).as_posix())
    path = unquote(path)
    # ../ 정리
    parts = []
    for seg in path.split("/"):
        if seg == "..":
            if parts:
                parts.pop()
        elif seg not in ("", "."):
            parts.append(seg)
    path = "/" + "/".join(parts)
    return "/index.html" if path == "/" else path


def main():
    as_json = "--json" in sys.argv
    critical, warn = [], []

    urls = sitemap_urls()
    files = {}
    for u in urls:
        f = to_file(u)
        if f is None:
            critical.append(f"사이트맵에 있는데 파일이 없음: {u}")
        else:
            files[u] = f

    # noindex·canonical (사이트맵 페이지)
    titles, descs = defaultdict(list), defaultdict(list)
    for u, f in files.items():
        html = read(f)
        head = html[:12000]
        if re.search(r'<meta[^>]+name=["\']robots["\'][^>]*noindex', head, re.I):
            critical.append(f"사이트맵 페이지가 noindex: {u}")
        m = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]*href=["\']([^"\']+)', head, re.I)
        if not m:
            if not f.name.startswith("google"):
                warn.append(f"canonical 없음: {u}")
        else:
            can = m.group(1).rstrip("/")
            if can != u.rstrip("/") and not (u.rstrip("/") == BASE and can in (BASE, BASE + "/index.html")):
                critical.append(f"canonical 불일치: {u} → {m.group(1)}")
        t = re.search(r"<title>([^<]*)</title>", head, re.I)
        d = re.search(r'<meta[^>]+name=["\']description["\'][^>]*content=["\']([^"\']*)', head, re.I)
        if t:
            titles[t.group(1).strip()].append(u)
        if d:
            descs[d.group(1).strip()].append(u)

    # 내부 링크 전수 점검
    all_html = [p for p in ROOT.rglob("*.html") if ".git" not in p.parts and "node_modules" not in p.parts]
    inbound = Counter()
    broken = defaultdict(set)
    nav_hrefs = set()
    for p in all_html:
        src_rel = "/" + p.relative_to(ROOT).as_posix()
        body = read(p)
        base_root = bool(re.search(r'<base[^>]+href=["\']/["\']', body[:6000], re.I))
        for href in re.findall(r'<a\b[^>]*?\shref=["\']([^"\']+)["\']', body, re.I):
            tgt = internal_target(href, p, base_root)
            if tgt is None:
                continue
            if not (ROOT / tgt.lstrip("/")).exists():
                if not tgt.startswith(("/api/", "/_")):
                    broken[tgt].add(src_rel)
                continue
            if tgt != src_rel:
                inbound[tgt] += 1
    for tgt, srcs in sorted(broken.items()):
        critical.append(f"깨진 내부 링크 {tgt} ← {len(srcs)}곳(예: {sorted(srcs)[0]})")

    # 고아 페이지(사이트맵에는 있는데 어느 페이지도 링크하지 않음)
    orphans = []
    for u, f in files.items():
        rel = "/" + f.relative_to(ROOT).as_posix()
        if rel != "/index.html" and not f.name.startswith("google") and inbound[rel] == 0:
            orphans.append(rel)
    if orphans:
        warn.append(f"고아 페이지 {len(orphans)}개(사이트맵에만 있음). 예: {', '.join(orphans[:3])}")

    dup_t = [(k, v) for k, v in titles.items() if len(v) > 1]
    dup_d = [(k, v) for k, v in descs.items() if len(v) > 1]
    if dup_t:
        warn.append(f"제목 중복 {len(dup_t)}종·{sum(len(v) for _, v in dup_t)}쪽. 예: {dup_t[0][0][:40]} ({len(dup_t[0][1])}쪽)")
    if dup_d:
        warn.append(f"설명 중복 {len(dup_d)}종·{sum(len(v) for _, v in dup_d)}쪽. 예: {dup_d[0][0][:40]} ({len(dup_d[0][1])}쪽)")

    # 홈의 봇 판별 회귀: 알려진 크롤러를 모두 걸러야 한다
    idx = read(ROOT / "index.html")
    m = re.search(r"var isBot = /([^/]+)/i\.test", idx)
    if not m:
        critical.append("index.html 에서 봇 판별 정규식을 찾지 못함")
    else:
        rx = re.compile(m.group(1), re.I)
        for name, ua in CRAWLER_UAS.items():
            if not rx.search(ua):
                critical.append(f"홈 봇 판별이 크롤러를 놓침: {name}")

    result = {"sitemap_urls": len(urls), "critical": critical, "warnings": warn,
              "orphans": orphans[:50], "html_files": len(all_html)}
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
    else:
        print(f"[site-health] 사이트맵 {len(urls)}개 · HTML {len(all_html)}개 점검")
        for c in critical[:40]:
            print("  ✗ 치명:", c)
        if len(critical) > 40:
            print(f"  … 치명 항목 {len(critical) - 40}개 더")
        for w in warn:
            print("  △ 경고:", w)
        if not critical:
            print("  ✓ 치명 항목 없음")
    sys.exit(1 if critical else 0)


if __name__ == "__main__":
    main()

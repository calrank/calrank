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


def main_text(html: str) -> str:
    # <main> 밖에 본문 구획이 붙는 페이지가 있어(이벤트 페이지) 몸통 전체에서 머리글·바닥글·내비만 뺀다.
    b = re.sub(r"<(nav|header|footer)\b.*?</\1>", "", html, flags=re.S | re.I)
    b = re.sub(r"<(script|style|svg)\b.*?</\1>", "", b, flags=re.S | re.I)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", b)).strip()


def group_of(f: Path) -> str:
    stem = re.sub(r"[-_].*", "", f.name.replace(".html", ""))
    return (f.parent.name + "/" + stem) if f.parent != ROOT else stem


THIN_CHARS = 500      # 본문(머리글·바닥글 제외) 글자 수 기준
DUP_JACCARD = 0.8     # 5단어 조각 기준 유사도


def content_quality(files: dict) -> list[str]:
    """얇거나 서로 거의 같은 페이지를 유형별로 집계한다(경고). 구글이 '크롤링됨-색인 안 됨'으로
    넘기는 흔한 원인이라 숫자로 본다."""
    groups = defaultdict(list)
    for u, f in files.items():
        t = main_text(read(f))
        words = t.split()
        sh = {hash(" ".join(words[i:i + 5])) for i in range(max(len(words) - 4, 0))}
        groups[group_of(f)].append((u, len(t), sh))
    out = []
    thin_total = dup_total = 0
    for g, items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        if len(items) < 3:
            continue
        thin = sum(1 for _, n, _ in items if n < THIN_CHARS)
        dup = 0
        if len(items) <= 600:
            sets = [x[2] for x in items]
            flagged = set()
            for i in range(len(sets)):
                if i in flagged or not sets[i]:
                    continue
                for j in range(i + 1, len(sets)):
                    if not sets[j]:
                        continue
                    inter = len(sets[i] & sets[j])
                    if inter and inter / len(sets[i] | sets[j]) >= DUP_JACCARD:
                        flagged.add(j)
            dup = len(flagged)
        thin_total += thin
        dup_total += dup
        if thin or dup:
            out.append(f"{g}: {len(items)}쪽 중 얇음(<{THIN_CHARS}자) {thin}쪽, 유사(≥{int(DUP_JACCARD*100)}%) {dup}쪽")
    if out:
        out.insert(0, f"본문 품질 요약: 얇은 페이지 {thin_total}쪽, 다른 페이지와 거의 같은 페이지 {dup_total}쪽")
    return out


def click_depth(files: dict, adj: dict) -> dict:
    """홈에서 몇 번 눌러야 닿는지(너비 우선 탐색). 구글은 깊은 페이지를 덜 자주 크롤링한다."""
    depth = {"/index.html": 0}
    frontier = ["/index.html"]
    while frontier:
        nxt = []
        for u in frontier:
            for v in adj.get(u, ()):
                if v not in depth:
                    depth[v] = depth[u] + 1
                    nxt.append(v)
        frontier = nxt
    hist = Counter()
    deep, lost = [], []
    for u, f in files.items():
        rel = "/" + f.relative_to(ROOT).as_posix()
        d = depth.get(rel)
        if d is None:
            if not f.name.startswith("google"):
                lost.append(rel)
            hist["닿지 않음"] += 1
        else:
            hist[str(d)] += 1
            if d > 3:
                deep.append(rel)
    warnings = []
    if lost:
        warnings.append(f"홈에서 링크를 따라 닿지 않는 페이지 {len(lost)}개. 예: {', '.join(lost[:3])}")
    if deep:
        warnings.append(f"홈에서 4번 넘게 눌러야 하는 페이지 {len(deep)}개. 예: {', '.join(deep[:3])}")
    return {"depth": depth, "hist": dict(hist), "warnings": warnings}


INDEX_REQUESTED = ROOT / "data" / "index_requested.json"   # {주소: 요청한 날}. 배포에서는 뺀다.
GROUP_WEIGHT = {"weekend": 60, "monthly": 40, "open-registration": 40, "grade": 35, "column": 25,
                "events-index": 30, "trailroot": 30, "mountains": 30, "landing": 20, "gear": 20}


def index_queue(files: dict, inbound: Counter, depth: dict, n: int = 10) -> list[dict]:
    """서치 콘솔에서 '색인 생성 요청'을 누를 후보 n개. 하루 한도(약 10건)가 있어 사람이 가려 눌러야 한다.
    점수 = 유형 가중치 + 들어오는 링크 수 + 최근 7일 안에 본문이 바뀐 가산점 - 이미 요청한 것 제외."""
    try:
        done = json.loads(INDEX_REQUESTED.read_text(encoding="utf-8"))
    except Exception:
        done = {}
    lm = {}
    for name in ("sitemap.xml",):
        for blk in re.findall(r"<url>.*?</url>", read(ROOT / name), re.S):
            loc = re.search(r"<loc>([^<]+)", blk)
            m = re.search(r"<lastmod>([^<]+)", blk)
            if loc and m:
                lm[loc.group(1)] = m.group(1)
    from datetime import date, timedelta
    recent = (date.today() - timedelta(days=7)).isoformat()
    rows = []
    for u, f in files.items():
        if u in done or "/e/" in u:
            continue
        rel = "/" + f.relative_to(ROOT).as_posix()
        stem = re.sub(r"[-_.].*", "", f.name)
        w = GROUP_WEIGHT.get(stem, 5)
        score = w + min(inbound.get(rel, 0), 40) + (25 if lm.get(u, "") >= recent else 0) - 3 * min(depth.get(rel, 6), 6)
        rows.append({"url": u, "score": score, "inbound": inbound.get(rel, 0), "depth": depth.get(rel), "lastmod": lm.get(u)})
    rows.sort(key=lambda r: -r["score"])
    return rows[:n]


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
    adj = defaultdict(set)
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
                adj[src_rel].add(tgt)
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

    warn += content_quality(files)

    depth_info = click_depth(files, adj)
    warn += depth_info["warnings"]
    queue = index_queue(files, inbound, depth_info["depth"])

    dup_t = [(k, v) for k, v in titles.items() if len(v) > 1]
    dup_d = [(k, v) for k, v in descs.items() if len(v) > 1]
    if dup_t:
        warn.append(f"제목 중복 {len(dup_t)}종·{sum(len(v) for _, v in dup_t)}쪽. 예: {dup_t[0][0][:40]} ({len(dup_t[0][1])}쪽)")
    if dup_d:
        warn.append(f"설명 중복 {len(dup_d)}종·{sum(len(v) for _, v in dup_d)}쪽. 예: {dup_d[0][0][:40]} ({len(dup_d[0][1])}쪽)")

    # 제휴 링크(쿠팡 파트너스) 규정 점검: 링크가 있는 페이지는 대가성 문구가 있어야 하고, 링크에 sponsored 가 있어야 한다.
    for p in all_html:
        body = read(p)
        if "link.coupang.com" not in body and "coupang.com/np" not in body:
            continue
        rel = "/" + p.relative_to(ROOT).as_posix()
        if "쿠팡 파트너스 활동의 일환으로" not in body:
            critical.append(f"제휴 링크가 있는데 대가성 문구가 없음: {rel}")
        for m in re.finditer(r'<a\b[^>]*href=["\'][^"\']*coupang\.com[^"\']*["\'][^>]*>', body, re.I):
            if "sponsored" not in m.group(0):
                critical.append(f"제휴 링크에 rel=sponsored 가 없음: {rel}")
                break

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
              "orphans": orphans[:50], "html_files": len(all_html),
              "depth_histogram": depth_info["hist"], "index_queue": queue}
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
        print("  링크 깊이(홈 기준):", ", ".join((f"{k}번 {v}개" if k.isdigit() else f"{k} {v}개") for k, v in sorted(depth_info["hist"].items())))
        print("  색인 요청 후보 상위:", ", ".join(q["url"].rsplit("/", 1)[-1] or "홈" for q in queue[:5]))
        if not critical:
            print("  ✓ 치명 항목 없음")
    sys.exit(1 if critical else 0)


if __name__ == "__main__":
    main()

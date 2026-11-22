"""서치 콘솔 URL 검사 API 로 색인 상태를 매일 표본 조사한다(읽기 전용).

서비스 계정 키(GSC_SA_KEY)로 인증하고, 사이트맵 앞쪽 우선 페이지 + 날짜로 돌려 가며 고른 페이지
최대 LIMIT 개를 검사해 gsc_index_daily 에 저장한다. 하루 검사 한도는 속성당 2,000건이라 넉넉하다.
키·토큰은 출력하지 않는다.
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://calrank.kr/"          # URL 접두어 속성
LIMIT = int(os.environ.get("GSC_LIMIT", "60"))
SB = "https://mlbzsqeoqlyvnyzeegeu.supabase.co"


def token() -> str:
    import google.auth.transport.requests as tr
    from google.oauth2 import service_account
    info = json.loads(os.environ["GSC_SA_KEY"])
    cred = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
    cred.refresh(tr.Request())
    return cred.token


def pick() -> list[str]:
    xml = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    urls = re.findall(r"<loc>([^<]+)</loc>", xml)
    urls = [u for u in urls if "/e/" not in u]
    head = urls[:20]                                   # 사이트맵 앞쪽(중요 페이지)은 매일
    rest = urls[20:]
    if rest:
        k = LIMIT - len(head)
        off = (date.today().toordinal() * k) % len(rest)
        rot = (rest[off:] + rest[:off])[:k]            # 나머지는 날짜로 돌려 가며
    else:
        rot = []
    return head + rot


def inspect(tok: str, url: str) -> dict:
    body = json.dumps({"inspectionUrl": url, "siteUrl": SITE, "languageCode": "ko"}).encode()
    req = urllib.request.Request(
        "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect", data=body,
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        res = json.load(r)
    s = res.get("inspectionResult", {}).get("indexStatusResult", {})
    return {"day": date.today().isoformat(), "url": url, "verdict": s.get("verdict"),
            "coverage": s.get("coverageState"), "last_crawl": s.get("lastCrawlTime"),
            "google_canonical": s.get("googleCanonical")}


def save(rows: list[dict]) -> None:
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not key or not rows:
        print("저장 건너뜀(키 없음 또는 결과 없음)")
        return
    req = urllib.request.Request(
        f"{SB}/rest/v1/gsc_index_daily?on_conflict=day,url", data=json.dumps(rows).encode(), method="POST",
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "Prefer": "resolution=merge-duplicates,return=minimal"})
    urllib.request.urlopen(req, timeout=60).read()


def main():
    if not os.environ.get("GSC_SA_KEY"):
        print("GSC_SA_KEY 가 없어 건너뜁니다.")
        return 0
    tok = token()
    rows, errs = [], 0
    for u in pick():
        try:
            rows.append(inspect(tok, u))
        except Exception as e:
            errs += 1
            print(f"검사 실패 {u}: {type(e).__name__}", file=sys.stderr)
            if errs >= 5:
                break
        time.sleep(0.3)
    save(rows)
    ok = sum(1 for r in rows if r["verdict"] == "PASS")
    print(f"검사 {len(rows)}건, 색인됨 {ok}건, 실패 {errs}건")
    cov = {}
    for r in rows:
        cov[r["coverage"] or "(없음)"] = cov.get(r["coverage"] or "(없음)", 0) + 1
    for k, v in sorted(cov.items(), key=lambda x: -x[1]):
        print(f"- {k}: {v}")
    return 0 if rows else 1


if __name__ == "__main__":
    sys.exit(main())

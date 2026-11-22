"""서치 콘솔에 제출된 사이트맵의 처리 상태를 매일 기록한다(읽기 전용 권한).

왜: 색인 표본에서 '구글에 아직 알려지지 않은 URL'이 대부분이면 품질보다 먼저 발견(사이트맵 제출·읽기) 단계를 의심해야 한다.
사이트맵이 제출됐는지, 마지막으로 언제 내려받았는지, 오류·경고가 있는지, 제출 수 대비 색인 수가 얼마인지를
gsc_sitemaps_daily 에 쌓아 두고 월요일 점검 작업이 읽는다. 키·토큰은 출력하지 않는다.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import date

SITE = "https://calrank.kr/"
SB = "https://mlbzsqeoqlyvnyzeegeu.supabase.co"


def token() -> str:
    import google.auth.transport.requests as tr
    from google.oauth2 import service_account
    info = json.loads(os.environ["GSC_SA_KEY"])
    cred = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
    cred.refresh(tr.Request())
    return cred.token


def fetch(tok: str) -> list[dict]:
    url = "https://searchconsole.googleapis.com/webmasters/v3/sites/" + urllib.parse.quote(SITE, safe="") + "/sitemaps"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r).get("sitemap", [])


def convert(items: list[dict], day: str) -> list[dict]:
    rows = []
    for s in items:
        sub = idx = 0
        for c in s.get("contents", []) or []:
            sub += int(c.get("submitted", 0) or 0)
            idx += int(c.get("indexed", 0) or 0)
        rows.append({"day": day, "path": s.get("path", ""), "last_submitted": s.get("lastSubmitted"),
                     "last_downloaded": s.get("lastDownloaded"), "is_pending": bool(s.get("isPending")),
                     "errors": int(s.get("errors", 0) or 0), "warnings": int(s.get("warnings", 0) or 0),
                     "submitted": sub, "indexed": idx})
    return rows


def save(rows: list[dict]) -> int:
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not key or not rows:
        return 0
    req = urllib.request.Request(
        f"{SB}/rest/v1/gsc_sitemaps_daily?on_conflict=day,path", data=json.dumps(rows).encode(), method="POST",
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "Prefer": "resolution=merge-duplicates,return=minimal"})
    urllib.request.urlopen(req, timeout=60).read()
    return len(rows)


def main() -> int:
    if not os.environ.get("GSC_SA_KEY"):
        print("GSC_SA_KEY 가 없어 건너뜁니다.")
        return 0
    rows = convert(fetch(token()), date.today().isoformat())
    if not rows:
        print("제출된 사이트맵이 없습니다. 서치 콘솔 > 사이트맵에서 sitemap.xml, sitemap-events.xml 을 제출해야 합니다.")
    for r in rows:
        print(f"{r['path']}: 제출 {r['submitted']} · 색인 {r['indexed']} · 마지막 읽음 {r['last_downloaded']} · "
              f"처리중 {r['is_pending']} · 오류 {r['errors']} · 경고 {r['warnings']}")
    print(f"저장 {save(rows)}건")
    return 0


if __name__ == "__main__":
    sys.exit(main())

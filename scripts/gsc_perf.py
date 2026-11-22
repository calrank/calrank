"""서치 콘솔 검색 성과(검색어×페이지×날짜)를 매일 가져와 gsc_perf_daily 에 쌓는다(읽기 전용 권한).

왜 쌓나: 서치 콘솔 화면은 16개월만 보여 주고, 페이지×검색어 단위의 변화를 내려받아 비교하기 어렵다.
쌓아 두면 (1) 노출은 많은데 클릭이 적은 페이지(제목·설명 개선 후보), (2) 2~3쪽에 걸린 검색어(보강 후보),
(3) 제목을 바꾼 뒤 CTR 이 실제로 올랐는지를 같은 기준으로 비교할 수 있다.

최근 며칠은 서치 콘솔 쪽 집계가 덜 끝나 값이 바뀌므로, 매일 끝에서 DAYS 일 전까지 다시 받아 덮어쓴다
(같은 키는 병합이라 여러 번 돌려도 중복되지 않는다). 처음에는 GSC_DAYS=90 으로 한 번 채워 둔다.
키·토큰은 출력하지 않는다.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import date, timedelta

SITE = "https://calrank.kr/"
SB = "https://mlbzsqeoqlyvnyzeegeu.supabase.co"
DAYS = int(os.environ.get("GSC_DAYS", "7"))
LAG = 2          # 서치 콘솔 값은 보통 2일 뒤에 안정된다
PAGE = 25000


def token() -> str:
    import google.auth.transport.requests as tr
    from google.oauth2 import service_account
    info = json.loads(os.environ["GSC_SA_KEY"])
    cred = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
    cred.refresh(tr.Request())
    return cred.token


def fetch(tok: str, start: str, end: str) -> list[dict]:
    url = ("https://searchconsole.googleapis.com/webmasters/v3/sites/"
           + urllib.parse.quote(SITE, safe="") + "/searchAnalytics/query")
    out, row = [], 0
    while True:
        body = json.dumps({"startDate": start, "endDate": end, "dimensions": ["date", "page", "query"],
                           "rowLimit": PAGE, "startRow": row}).encode()
        req = urllib.request.Request(url, data=body, headers={
            "Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            rows = json.load(r).get("rows", [])
        out += rows
        if len(rows) < PAGE:
            return out
        row += PAGE


def convert(rows: list[dict]) -> list[dict]:
    """API 행 → 저장 행. 같은 (날짜,페이지,검색어)가 겹치면 하나로 합친다."""
    acc: dict[tuple, dict] = {}
    for r in rows:
        k = r.get("keys") or []
        if len(k) != 3:
            continue
        key = (k[0], k[1], k[2])
        imp = int(r.get("impressions", 0))
        cur = acc.get(key)
        if cur is None:
            acc[key] = {"day": k[0], "page": k[1], "query": k[2], "clicks": int(r.get("clicks", 0)),
                        "impressions": imp, "position": round(float(r.get("position", 0)), 2)}
        else:
            tot = cur["impressions"] + imp
            if tot:
                cur["position"] = round((cur["position"] * cur["impressions"] + float(r.get("position", 0)) * imp) / tot, 2)
            cur["clicks"] += int(r.get("clicks", 0))
            cur["impressions"] = tot
    return list(acc.values())


def save(rows: list[dict]) -> int:
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not key or not rows:
        print("저장 건너뜀(키 없음 또는 결과 없음)")
        return 0
    n = 0
    for i in range(0, len(rows), 1000):
        chunk = rows[i:i + 1000]
        req = urllib.request.Request(
            f"{SB}/rest/v1/gsc_perf_daily?on_conflict=day,page,query", data=json.dumps(chunk).encode(), method="POST",
            headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json",
                     "Prefer": "resolution=merge-duplicates,return=minimal"})
        urllib.request.urlopen(req, timeout=120).read()
        n += len(chunk)
    return n


def main() -> int:
    if not os.environ.get("GSC_SA_KEY"):
        print("GSC_SA_KEY 가 없어 건너뜁니다.")
        return 0
    end = date.today() - timedelta(days=LAG)
    start = end - timedelta(days=max(DAYS, 1) - 1)
    rows = convert(fetch(token(), start.isoformat(), end.isoformat()))
    n = save(rows)
    clicks = sum(r["clicks"] for r in rows)
    imps = sum(r["impressions"] for r in rows)
    print(f"{start}~{end}: 행 {len(rows)}개, 클릭 {clicks}, 노출 {imps}, 저장 {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

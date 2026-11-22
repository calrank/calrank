#!/usr/bin/env python3
"""제휴 배너의 인기 상품을 쿠팡 파트너스 오픈 API 로 갱신한다(매주 GitHub Actions).

흐름: data/affiliate_links.json 의 banners(검색어·브랜드) → 오픈 API 상품 검색 → 이름 있는 브랜드만 남김 →
      Supabase affiliate_products 에 덮어쓰기. 페이지는 aff.js 가 affiliate_cards() 로 읽어 상품 카드를 그린다.
      데이터가 없거나 3주 넘게 낡으면 쿠팡 다이나믹 배너(iframe)가 그대로 보인다.
키(COUPANG_ACCESS_KEY, COUPANG_SECRET_KEY)는 파트너스 "최종 승인" 뒤에 사용자가 직접 발급해 GitHub Secret 에 넣는다.
키가 없으면 아무것도 하지 않고 0으로 끝난다.

  python3 scripts/affiliate_refresh.py            # 실제 갱신
  python3 scripts/affiliate_refresh.py --dry-run  # 쓰지 않고 고른 상품만 출력
"""
import hashlib
import hmac
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = "https://api-gateway.coupang.com"
BASE = "/v2/providers/affiliate_open_api/apis/openapi/v1"
KEEP = 8
MIN_OK = 3          # 이보다 적게 걸러지면 기존 데이터를 지키고 건너뛴다
BAD = re.compile(r"중고|리퍼|케이스|스티커|장난감|키링|모형|미니어처|어린이|주니어|키즈")
SUPA = "https://mlbzsqeoqlyvnyzeegeu.supabase.co"


def sign(method, path_query, secret, access):
    """쿠팡 HMAC-SHA256 서명 헤더. path_query 는 '/v2/...?a=b' 형태."""
    path, _, query = path_query.partition("?")
    dt = datetime.now(timezone.utc).strftime("%y%m%dT%H%M%SZ")
    msg = dt + method + path + query
    sig = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return f"CEA algorithm=HmacSHA256, access-key={access}, signed-date={dt}, signature={sig}"


def search(keyword, access, secret, limit=20, opener=urllib.request.urlopen):
    pq = f"{BASE}/products/search?keyword={urllib.parse.quote(keyword)}&limit={limit}"
    req = urllib.request.Request(HOST + pq, headers={"Authorization": sign("GET", pq, secret, access),
                                                     "Content-Type": "application/json;charset=UTF-8"})
    with opener(req, timeout=30) as r:
        j = json.loads(r.read().decode("utf-8"))
    return (j.get("data") or {}).get("productData") or []


def choose(rows, brands):
    """이름 있는 브랜드만, 같은 상품 중복 없이, 앞에서부터 KEEP 개. 링크·이미지가 정상인 것만."""
    rx = re.compile(brands, re.I)
    out, seen = [], set()
    for x in rows:
        name = str(x.get("productName", ""))
        url, img = str(x.get("productUrl", "")), str(x.get("productImage", ""))
        pid = x.get("productId")
        if not pid or pid in seen or not rx.search(name) or BAD.search(name):
            continue
        if not url.startswith("https://link.coupang.com/") or not img.startswith("https://"):
            continue
        seen.add(pid)
        out.append({"product_id": int(pid), "name": name[:120], "price": int(x.get("productPrice") or 0) or None,
                    "image": img, "url": url, "rocket": bool(x.get("isRocket"))})
        if len(out) >= KEEP:
            break
    return out


def save(banner, items, key):
    """해당 배너 행을 새 목록으로 바꾼다(없어진 상품은 지운다)."""
    hdr = {"apikey": key, "Authorization": "Bearer " + key, "Content-Type": "application/json"}
    ids = ",".join(str(i["product_id"]) for i in items)
    urllib.request.urlopen(urllib.request.Request(
        f"{SUPA}/rest/v1/affiliate_products?banner=eq.{urllib.parse.quote(banner)}&product_id=not.in.({ids})",
        method="DELETE", headers=hdr), timeout=30).read()
    rows = [dict(i, banner=banner, rank=n + 1, updated_at=datetime.now(timezone.utc).isoformat()) for n, i in enumerate(items)]
    req = urllib.request.Request(f"{SUPA}/rest/v1/affiliate_products?on_conflict=banner,product_id", method="POST",
                                 data=json.dumps(rows).encode(), headers=dict(hdr, Prefer="resolution=merge-duplicates"))
    urllib.request.urlopen(req, timeout=30).read()


def main(dry):
    access, secret = os.environ.get("COUPANG_ACCESS_KEY", ""), os.environ.get("COUPANG_SECRET_KEY", "")
    if not access or not secret:
        print("쿠팡 API 키가 없어 갱신하지 않습니다(파트너스 최종 승인 뒤 COUPANG_ACCESS_KEY·COUPANG_SECRET_KEY 를 GitHub Secret 에 넣으세요). 배너는 쿠팡 다이나믹 배너로 보입니다.")
        return 0
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not dry and not key:
        print("SUPABASE_SERVICE_ROLE_KEY 가 없습니다")
        return 1
    banners = json.loads((ROOT / "data" / "affiliate_links.json").read_text(encoding="utf-8")).get("banners", {})
    skipped = []
    for name, b in banners.items():
        try:
            items = choose(search(b["query"], access, secret), b["brands"])
        except Exception as e:  # 한 배너가 실패해도 나머지는 계속한다
            print(f"{name}: 조회 실패 {type(e).__name__}")
            skipped.append(name)
            time.sleep(1)
            continue
        print(f"{name}: {len(items)}개 " + " / ".join(i["name"][:18] for i in items[:3]))
        if len(items) < MIN_OK:
            skipped.append(name)
        elif not dry:
            save(name, items, key)
        time.sleep(1)  # 호출 간격(분당 호출 제한 대비)
    if skipped:
        print("건너뜀(상품이 적거나 조회 실패, 기존 데이터 유지):", ", ".join(skipped))
    return 0


if __name__ == "__main__":
    sys.exit(main("--dry-run" in sys.argv))

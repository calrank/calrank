"""
러닝화 등 러닝 장비의 실시간 최저가를 네이버 쇼핑 검색 API로 수집한다.

리뷰 본문이나 저작권 있는 콘텐츠를 긁어오는 것이 아니라, 네이버가 공식
공개한 API를 통해 "최저가·쇼핑몰명·상품링크" 같은 사실 데이터만 가져온다.
API 키(NAVER_CLIENT_ID, NAVER_CLIENT_SECRET)는 GitHub Actions Secrets에서
환경변수로 주입되며, 이 코드에는 절대 하드코딩하지 않는다.

출력: gear_prices.json
  {
    "updatedAt": "2026-09-17T12:00:00+09:00",
    "items": {
      "아식스 노바블라스트 5": [ {title, lprice, mallName, link, image, brand}, ... ],
      ...
    }
  }
"""
import json
import os
import re
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
API_URL = "https://openapi.naver.com/v1/search/shop.json"

# 오늘 만든 "러닝화 선택 가이드" 칼럼에서 실제로 언급한 모델들부터 시작한다.
# 종목이 늘어나면 자전거·트레일화 등도 이 리스트에 추가하면 된다.
GEAR_QUERIES = [
    "아식스 노바블라스트 5",
    "뉴발란스 1080 v15",
    "나이키 페가수스 41",
    "호카 클리프톤 10",
    "브룩스 글리세린",
    "아디다스 슈퍼노바 라이즈 3",
]

RESULTS_PER_QUERY = 3


def strip_tags(text):
    return re.sub(r"<.*?>", "", text)


def fetch_query(query, client_id, client_secret):
    params = urllib.parse.urlencode({
        "query": query,
        "display": RESULTS_PER_QUERY,
        "sort": "asc",  # 가격 낮은 순
    })
    req = urllib.request.Request(f"{API_URL}?{params}")
    req.add_header("X-Naver-Client-Id", client_id)
    req.add_header("X-Naver-Client-Secret", client_secret)
    with urllib.request.urlopen(req, timeout=10) as res:
        data = json.loads(res.read().decode("utf-8"))
    items = []
    for item in data.get("items", []):
        items.append({
            "title": strip_tags(item.get("title", "")),
            "lprice": item.get("lprice", ""),
            "mallName": item.get("mallName", ""),
            "link": item.get("link", ""),
            "image": item.get("image", ""),
            "brand": item.get("brand", ""),
        })
    return items


def main():
    client_id = os.environ.get("NAVER_CLIENT_ID")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수가 없어 건너뜁니다.")
        return

    result = {
        "updatedAt": datetime.now(KST).isoformat(),
        "items": {},
    }

    for query in GEAR_QUERIES:
        try:
            result["items"][query] = fetch_query(query, client_id, client_secret)
            print(f"OK: {query} ({len(result['items'][query])}건)")
        except Exception as e:
            print(f"FAIL: {query} - {e}")
            result["items"][query] = []

    with open("gear_prices.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("gear_prices.json 저장 완료")


if __name__ == "__main__":
    main()

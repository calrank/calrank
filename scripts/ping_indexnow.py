"""바뀐 주소를 IndexNow 로 알린다 — 네이버·Bing 색인 요청, 할당량 없음.

왜 필요한가
  구글 서치콘솔의 "색인 생성 요청" 은 하루 10여 건이 한도다. 새 페이지가
  수백 개 생기는 사이트에서는 손으로 넣는 것으로 따라갈 수가 없다.
  IndexNow 는 요청당 최대 10,000개까지 받고 하루 횟수 제한이 없다.
  네이버가 2023년부터, Bing 이 처음부터 지원한다. 구글은 지원하지 않으므로
  구글 쪽은 사이트맵과 내부 링크에 계속 기대야 한다.

키에 대하여
  IndexNow 의 키는 비밀이 아니다. 오히려 사이트 루트에 <키>.txt 로 공개돼
  있어야 검색엔진이 "이 사이트 주인이 맞다" 고 확인한다. 그래서 GitHub
  Secret 이 아니라 그냥 코드에 적어 둔다. 바꾸려면 아래 KEY 와 루트의
  <키>.txt 를 같이 바꾸면 된다.

보내는 범위
  바뀐 주소만 골라 보낸다. 전체를 매일 보내면 의미가 없다.

보낼 주소를 어떻게 고르나
  git 이 방금 커밋에서 바뀌었다고 알려 준 .html 파일만 보낸다.
  바뀐 게 없으면 아무것도 보내지 않는다.
"""
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://calrank.vercel.app"
HOST = "calrank.vercel.app"

# 네이버와 Bing. 한 곳에만 보내도 서로 공유된다고 하지만, 둘 다 보내 둔다.
# indexnow.org FAQ 기준 공식 주소. 참여 엔진끼리 제출을 공유하므로
# 한 곳만 보내도 되지만, 네이버가 주 타깃이라 네이버에도 직접 보낸다.
# (처음에 api.searchadvisor.naver.com 으로 적었다가 그런 호스트가 없어
#  DNS 조회부터 실패했다. api. 가 붙지 않는다.)
ENDPOINTS = [
    ("네이버", "https://searchadvisor.naver.com/indexnow"),
    ("IndexNow 공용", "https://api.indexnow.org/indexnow"),
]
MAX_URLS = 10000
KEY_RE = re.compile(r"^[A-Za-z0-9-]{8,128}$")
KEY = "324bbff02cfb1892920af20f38ff7252"


def changed_html(rev_range: str, use_git: bool = False) -> list[str]:
    """바뀐 .html 파일 목록.

    기본은 커밋 단계가 남겨 준 목록 파일을 읽는다. actions/checkout 은
    기본값이 fetch-depth: 1 이라 HEAD~1 이 아예 없고, git diff 가 통하지
    않는다. (이것 때문에 처음엔 매일 돌아도 아무것도 안 보냈다)
    목록 파일이 없을 때만 git 에 물어본다.
    """
    listed = os.environ.get("CHANGED_FILES")
    if not use_git and listed and Path(listed).exists():
        lines = Path(listed).read_text(encoding="utf-8").split("\n")
        return [p.strip() for p in lines if p.strip().endswith(".html")]
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACMR", rev_range],
            cwd=ROOT, capture_output=True, text=True, timeout=60, check=True).stdout
    except (subprocess.SubprocessError, OSError) as exc:
        print(f"[indexnow] git diff 실패: {exc}")
        return []
    return [p for p in out.split("\n") if p.endswith(".html")]


def to_url(path: str) -> str:
    from urllib.parse import quote
    if path == "index.html":
        return f"{SITE}/"
    return f"{SITE}/" + "/".join(quote(seg) for seg in path.split("/"))


def submit(key: str, urls: list[str]) -> None:
    body = json.dumps({
        "host": HOST,
        "key": key,
        "keyLocation": f"{SITE}/{key}.txt",
        "urlList": urls[:MAX_URLS],
    }, ensure_ascii=False).encode("utf-8")
    for name, endpoint in ENDPOINTS:
        req = urllib.request.Request(
            endpoint, data=body,
            headers={"Content-Type": "application/json; charset=utf-8"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                print(f"[indexnow] {name}: HTTP {resp.status} ({len(urls)}개 주소)")
        except urllib.error.HTTPError as exc:
            # 400 은 보통 키 파일을 못 읽은 경우다. 실패해도 수집은 계속되어야 하니
            # 예외를 올리지 않고 이유만 남긴다.
            print(f"[indexnow] {name}: HTTP {exc.code} — {exc.read()[:200]!r}")
        except (urllib.error.URLError, OSError) as exc:
            print(f"[indexnow] {name}: 보내지 못했습니다 — {exc}")


def main() -> None:
    key = (os.environ.get("INDEXNOW_KEY") or KEY).strip()
    if not KEY_RE.match(key):
        print("[indexnow] 키 형식이 올바르지 않습니다 (영문·숫자·하이픈 8~128자)")
        return

    # 키 파일이 사이트에서 읽혀야 검색엔진이 요청을 받아 준다.
    key_file = ROOT / f"{key}.txt"
    if not key_file.exists() or key_file.read_text(encoding="utf-8").strip() != key:
        key_file.write_text(key + "\n", encoding="utf-8")
        print(f"[indexnow] 키 파일 생성: {key}.txt")

    manual = sys.argv[1].strip() if len(sys.argv) > 1 else ""
    rev = manual or "HEAD~1..HEAD"
    paths = changed_html(rev, use_git=bool(manual))
    if not paths:
        print("[indexnow] 바뀐 페이지가 없어 보내지 않습니다")
        return
    urls = sorted({to_url(p) for p in paths})
    print(f"[indexnow] 바뀐 페이지 {len(urls)}개")
    for u in urls[:5]:
        print(f"           {u}")
    if len(urls) > 5:
        print(f"           … 외 {len(urls)-5}개")
    submit(key, urls)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""도메인 이전 도우미 (기본은 점검만 한다).

사용법
  python3 scripts/domain_migrate.py NEW_HOST            # 어디가 바뀌는지만 보여 줌
  python3 scripts/domain_migrate.py NEW_HOST --apply    # 실제로 바꾼다

NEW_HOST 는 https:// 없이 호스트만 적는다 (예: calrank.kr).

하는 일
  1. 사이트 안의 모든 텍스트 파일에서 calrank.vercel.app 을 NEW_HOST 로 바꾼다.
     (canonical, og:url, sitemap, robots, rss, ics, 생성기 상수, IndexNow 호스트 포함)
  2. 바꾸지 않는 곳: .git, node_modules, __pycache__, 이 스크립트 자체, README 의 설명 문장.
  3. vercel.json 에 옛 호스트 → 새 호스트 301 리다이렉트를 넣는다 (이미 있으면 건너뜀).
     모든 경로를 그대로 넘기는 규칙이라 색인된 주소가 새 주소로 이어진다.

이 스크립트가 못 하는 일 (직접 해야 함)
  - Vercel 에서 새 도메인 연결, DNS 설정
  - Search Console 에 새 속성 등록 후 '주소 변경' (옛 속성에서) 실행
  - 네이버 서치어드바이저에 새 사이트 등록
  - Supabase Auth 의 Site URL / Redirect URLs 에 새 주소 추가 (비밀번호 재설정 메일이 새 주소로 오게)
  - IndexNow 키 파일(`<key>.txt`)은 호스트가 바뀌어도 루트에 있으면 그대로 쓰인다
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OLD = "calrank.vercel.app"
SKIP_DIRS = {".git", "node_modules", "__pycache__"}
SKIP_FILES = {"scripts/domain_migrate.py", "README.md"}
TEXT_EXT = {".html", ".js", ".json", ".xml", ".txt", ".ics", ".py", ".yml", ".yaml", ".md", ".css", ".webmanifest"}


def targets():
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in TEXT_EXT:
            continue
        rel = p.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts) or str(rel) in SKIP_FILES:
            continue
        yield p, rel


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply = "--apply" in sys.argv
    if len(args) != 1 or not re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", args[0]):
        print(__doc__)
        sys.exit(1)
    new = args[0]
    if new == OLD:
        print("새 호스트가 옛 호스트와 같습니다.")
        sys.exit(1)

    changed, total, groups = 0, 0, {}
    for p, rel in targets():
        try:
            txt = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        n = txt.count(OLD)
        if not n:
            continue
        # vercel.json 의 리다이렉트 규칙에 쓰는 옛 호스트는 건드리지 않는다
        total += n
        changed += 1
        key = "e/ (대회 페이지)" if rel.parts[0] == "e" else ("scripts/" if rel.parts[0] == "scripts" else "그 외")
        groups[key] = groups.get(key, 0) + 1
        if apply:
            p.write_text(txt.replace(OLD, new), encoding="utf-8")

    print(f"{'적용' if apply else '점검'}: {changed}개 파일, {total}곳")
    for k, v in groups.items():
        print(f"  {k}: {v}개 파일")

    vj = ROOT / "vercel.json"
    data = json.loads(vj.read_text(encoding="utf-8"))
    rule = {
        "source": "/:path*",
        "has": [{"type": "host", "value": OLD}],
        "destination": f"https://{new}/:path*",
        "permanent": True,
    }
    have = any(r.get("has") == rule["has"] for r in data.get("redirects", []))
    print(f"vercel.json 301 규칙: {'이미 있음' if have else ('추가' if apply else '추가 예정')}")
    if apply and not have:
        data.setdefault("redirects", []).append(rule)
        vj.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if apply:
        print("다음: python3 scripts/sync_all.py → sync_all.py --check → 푸시 → Search Console '주소 변경'")


if __name__ == "__main__":
    main()

"""
git 이력의 events.json 으로 대회 일정 변경 이력을 과거로 복원한다 (한 번 돌리는 도구).

수집 봇이 events.json 을 매일 커밋해 왔으므로, 날짜별 마지막 커밋을 하루치 수집으로 보고
track_event_changes.run 에 순서대로 넣는다. 복원한 기록에는 via="git" 이 붙고,
'처음 확인한 날'은 그 커밋 날짜이므로 소스에 올라온 날이 아니다.
이 스크립트는 data/event_history.json 을 처음부터 다시 만든다. 오늘 상태까지 이어서 반영하려면
끝난 뒤 python scripts/track_event_changes.py 를 한 번 더 돌린다 (워크플로가 매일 한다).

사용: python scripts/backfill_event_history.py [--dry-run]
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from track_event_changes import run, today_kst  # noqa: E402


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, check=True).stdout


def show_json(commit, path, default):
    try:
        return json.loads(git("show", f"{commit}:{path}"))
    except (subprocess.CalledProcessError, ValueError):
        return default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--history", default="data/event_history.json")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    rows = [l.split() for l in git("log", "--reverse", "--format=%H %ad", "--date=format:%Y-%m-%d", "--", "events.json").splitlines()]
    last = {}  # 날짜별 마지막 커밋
    for h, d in rows:
        last[d] = h
    hist, total = {}, {}
    for d in sorted(last):
        h = last[d]
        evs = show_json(h, "events.json", None)
        if not isinstance(evs, list) or not evs:
            print(d, "events.json 을 읽지 못해 건너뜀")
            continue
        new = run(evs, hist, show_json(h, "event_aliases.json", {}), d, via="git")
        for x in new:
            total[x["type"]] = total.get(x["type"], 0) + 1
        print(d, h[:7], f"대회 {len(evs)}건 · 새 기록 {len(new)}건")
    print("복원 합계:", total, "· 누적", len(hist.get("log", [])))
    if a.dry_run:
        return 0
    import track_event_changes as t
    # 저장은 본 스크립트와 같은 형식으로 한다.
    tmp = a.history + ".tmp"
    dump = lambda v: json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("{\n")
        f.write(f'"since":{dump(hist["since"])},\n"updated":{dump(hist["updated"])},\n')
        f.write('"events":{\n' + ",\n".join(f"{dump(k)}:{dump(v)}" for k, v in sorted(hist["events"].items())) + "\n},\n")
        f.write('"log":[\n' + ",\n".join(dump(x) for x in hist["log"]) + "\n]\n}\n")
    os.replace(tmp, a.history)
    return 0


if __name__ == "__main__":
    sys.exit(main())

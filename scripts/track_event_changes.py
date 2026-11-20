"""
대회 일정 변경 이력: 매일 events.json 을 지난번 상태와 비교해 바뀐 것만 날짜와 함께 쌓는다.

왜 쌓나: 크롤러가 매일 읽는 값은 '오늘의 모습'뿐이고, 소스 사이트는 지난 모습을 남기지 않는다.
접수 마감일이 언제 바뀌었는지, 날짜·장소가 언제 옮겨졌는지, 목록에서 언제 사라졌는지는
오늘부터 저장하지 않으면 나중에 되찾을 수 없다.

기록하는 것 (data/event_history.json 의 log):
  added     칼랭크가 처음 확인한 대회 (처음 확인한 날 = 소스에 올라온 날이 아니다)
  changed   같은 대회의 접수 마감일·장소·거리·접수 링크·시간·접수 마감 여부가 바뀜
  moved     같은 대회가 다른 날짜로 옮겨짐 (이름·지역이 같고 날짜만 다른 한 쌍일 때만)
  dropped   앞으로 열릴 대회가 3번 연속 목록에서 보이지 않음 (취소를 뜻하지 않는다: 소스에서 내렸을 뿐일 수 있다)
  restored  dropped 로 기록했던 대회가 다시 보임

잡음을 줄이는 규칙:
  - 값이 비었다가 채워지거나 채워졌다가 비는 것은 변경이 아니다(상세 페이지 수집 실패와 구분이 안 된다).
    양쪽 다 값이 있고 서로 다를 때만 기록한다.
  - 중복 합치기로 주소가 바뀐 대회(event_aliases.json)는 조용히 넘긴다.
  - 첫 실행은 기준선이다. 그때 있던 대회는 baseline 으로 표시하고 added 로 세지 않는다.
  - 같은 상태로 다시 돌려도 아무것도 더해지지 않는다.

사용: python scripts/track_event_changes.py [--events events.json] [--history data/event_history.json]
"""
import argparse
import json
import os
import re
import sys
from urllib.parse import urlsplit
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_events import normalize_name, _meaningful  # noqa: E402

TRACKED = ("date", "time", "location", "distances", "regDeadline", "regClosed", "applyUrl")
LABEL = {"date": "날짜", "time": "시간", "location": "장소", "distances": "거리",
         "regDeadline": "접수 마감일", "regClosed": "접수 마감 여부", "applyUrl": "접수 링크"}
DROP_AFTER = 3  # 연속으로 안 보인 횟수


def today_kst() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=9)).strftime("%Y-%m-%d")


_DIST_RE = re.compile(r"^(\d+(\.\d+)?\s*(km|k|m)|풀|하프|마라톤|울트라)$", re.I)


def _norm_url(u: str) -> str:
    """주소 비교용: 스킴·www·끝 슬래시·추적용 쿼리(utm_*)·대소문자 차이를 무시한다."""
    try:
        sp = urlsplit(str(u).strip())
    except ValueError:
        return str(u).strip()
    q = "&".join(sorted(p for p in sp.query.split("&") if p and not p.lower().startswith(("utm_", "viewtype"))))
    host = sp.netloc.lower().removeprefix("www.")
    return f"{host}{sp.path.rstrip('/')}" + (f"?{q}" if q else "")


def norm(field, v):
    """비교용 값. 거리는 순서·중복·수집기가 덧붙이는 합성 표기를 무시하고, 주소는 표기 차이를 무시한다."""
    if field == "distances":
        items = set()
        for x in (v or []):
            if _meaningful(x) and _DIST_RE.match(str(x).strip().replace(" ", "")):
                items.add(str(x).strip().replace(" ", "").lower())
        return tuple(sorted(items))
    if field == "applyUrl":
        return _norm_url(v) if v else v
    if isinstance(v, str):
        return " ".join(v.split())
    return v


def has_value(field, v) -> bool:
    if field == "distances":
        return bool(norm(field, v))
    if field == "regClosed":
        return v is not None
    return _meaningful(v)


def snap_of(ev: dict) -> dict:
    s = {f: ev.get(f) for f in TRACKED}
    s["name"] = ev.get("name")
    s["region"] = ev.get("region")
    return s


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def run(events: list, hist: dict, aliases: dict, day: str, via: str = None) -> list:
    """hist 를 제자리에서 갱신하고, 이번에 새로 쌓인 로그 항목을 돌려준다."""
    first_run = not hist.get("since")
    if first_run:
        hist["since"] = day
    ents = hist.setdefault("events", {})
    log = hist.setdefault("log", [])
    cur = {e["id"]: e for e in events if e.get("id")}
    new_log = []

    def add(**kw):
        kw["day"] = day
        if via:
            kw["via"] = via  # "git": 과거 events.json 커밋에서 복원한 기록
        new_log.append(kw)

    # 1) 이미 알던 대회: 값이 바뀌었나
    for i, ev in cur.items():
        ent = ents.get(i)
        if ent is None:
            continue
        old = ent["snap"]
        for f in TRACKED:
            a, b = old.get(f), ev.get(f)
            if has_value(f, a) and has_value(f, b) and norm(f, a) != norm(f, b):
                add(type="changed", id=i, name=ev.get("name"), date=ev.get("date"), field=f,
                    old=a, new=b)
        for f in TRACKED:  # 비어 있다가 채워진 값은 조용히 받아 둔다
            if has_value(f, ev.get(f)):
                old[f] = ev.get(f)
        old["name"], old["region"] = ev.get("name"), ev.get("region")
        if ent.get("dropped"):
            ent["dropped"] = False
            add(type="restored", id=i, name=ev.get("name"), date=ev.get("date"))
        ent["miss"], ent["last"] = 0, day

    # 2) 안 보이는 대회: 합쳐졌거나 사라졌거나
    gone = {}
    for i, ent in ents.items():
        if i in cur or ent.get("merged") or ent.get("moved_to"):
            continue
        if i in aliases:
            ent["merged"] = aliases[i]
            continue
        ent["miss"] = ent.get("miss", 0) + 1
        gone[i] = ent

    # 3) 처음 보는 대회 (이름·지역이 같고 날짜만 다른 사라진 대회가 정확히 하나면 '옮겨짐')
    newbies = [i for i in cur if i not in ents]
    by_key = {}
    for i, ent in gone.items():
        k = (normalize_name(ent["snap"].get("name")), ent["snap"].get("region"))
        by_key.setdefault(k, []).append(i)
    new_by_key = {}
    for i in newbies:
        k = (normalize_name(cur[i].get("name")), cur[i].get("region"))
        new_by_key.setdefault(k, []).append(i)
    for i in newbies:
        ev = cur[i]
        k = (normalize_name(ev.get("name")), ev.get("region"))
        ents[i] = {"first": day, "baseline": first_run, "last": day, "miss": 0, "snap": snap_of(ev)}
        if first_run:
            continue
        olds = [o for o in by_key.get(k, []) if ents[o]["snap"].get("date") != ev.get("date")]
        if len(olds) == 1 and len(new_by_key.get(k, [])) == 1:
            o = olds[0]
            add(type="moved", id=i, name=ev.get("name"), from_id=o, old=ents[o]["snap"].get("date"),
                new=ev.get("date"))
            ents[o]["moved_to"] = i
            gone.pop(o, None)
        else:
            add(type="added", id=i, name=ev.get("name"), date=ev.get("date"),
                regDeadline=ev.get("regDeadline") if _meaningful(ev.get("regDeadline")) else None)

    # 4) 앞으로 열릴 대회가 계속 안 보이면 dropped
    for i, ent in gone.items():
        if ent["miss"] >= DROP_AFTER and not ent.get("dropped") and (ent["snap"].get("date") or "") >= day:
            ent["dropped"] = True
            add(type="dropped", id=i, name=ent["snap"].get("name"), date=ent["snap"].get("date"))

    log.extend(new_log)
    hist["updated"] = day
    return new_log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", default="events.json")
    ap.add_argument("--history", default="data/event_history.json")
    ap.add_argument("--aliases", default="event_aliases.json")
    ap.add_argument("--day", default=None, help="시험용: 오늘 날짜(YYYY-MM-DD)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    events = load_json(a.events, None)
    if not isinstance(events, list) or not events:
        print("events.json 을 읽지 못했습니다. 이력을 건드리지 않습니다.")
        return 1
    hist = load_json(a.history, {})
    day = a.day or today_kst()
    new = run(events, hist, load_json(a.aliases, {}), day)
    kinds = {}
    for x in new:
        kinds[x["type"]] = kinds.get(x["type"], 0) + 1
    print(f"{day}: 추적 {len(hist['events'])}건, 새 기록 {len(new)}건 {kinds or ''}, 누적 기록 {len(hist['log'])}건")
    if a.dry_run:
        return 0
    os.makedirs(os.path.dirname(a.history) or ".", exist_ok=True)
    tmp = a.history + ".tmp"
    # 대회 한 건을 한 줄로 쓴다: 파일이 작고, 매일 바뀐 줄만 git diff 에 보인다.
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

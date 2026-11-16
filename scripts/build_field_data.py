"""현장 보기용 코스 자료: data/courses.json(2MB)을 코스별 작은 파일로 쪼갠다.

폰에서 한 코스만 열 때 2MB를 받지 않게 하고, 나중에 오프라인 저장(PWA)할 때 코스 단위로
담을 수 있게 하려는 것이다. 값은 바꾸지 않고 필요한 필드만 옮긴다.
  field/<id>.json   {id, name, region, km, profile, path, src}
  field/index.json  [[id, name, region, km], ...]
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
courses = json.load(open(ROOT / "data/courses.json", encoding="utf-8"))["courses"]
out = ROOT / "field"
out.mkdir(exist_ok=True)
index = []
for c in courses:
    prof = c.get("profile") or []
    path = c.get("path") or []
    if len(prof) < 5 or len(path) < 5:
        continue
    km = round(prof[-1][0] / 1000, 1)
    src = (c.get("source") or {}).get("label") or ""
    (out / f"{c['id']}.json").write_text(
        json.dumps({"id": c["id"], "name": c["name"], "region": c.get("region", ""), "km": km,
                    "profile": prof, "path": path, "src": src}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")
    index.append([c["id"], c["name"], c.get("region", ""), km])
index.sort(key=lambda r: (r[2], r[1]))
(out / "index.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(f"현장 보기 자료 {len(index)}개 코스")

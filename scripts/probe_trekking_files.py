"""data.go.kr 파일데이터(한국등산트레킹지원센터 둘레길 GPX) 내려받기 경로를 찾는다. 로그에만 남는다.
인증키는 쓰지 않는다. 파일은 저장하지 않는다."""
import re
import requests

H = {"User-Agent": "Mozilla/5.0 (calrank-probe)"}
for did in ("15098179", "15108080"):
    print("==", did)
    j = requests.get(f"https://www.data.go.kr/catalog/{did}/fileData.json", headers=H, timeout=40).text
    print("JSON:", j[:1400])
    t = requests.get(f"https://www.data.go.kr/data/{did}/fileData.do", headers=H, timeout=40).text
    seen = set()
    for m in re.finditer(r"(fileDown|atchFile|fileDetailSn|download|다운로드)", t, re.I):
        sn = t[max(0, m.start() - 90): m.end() + 140].replace("\n", " ")
        k = sn[60:120]
        if k in seen: continue
        seen.add(k)
        print("  ..", sn[:230])
        if len(seen) > 14: break

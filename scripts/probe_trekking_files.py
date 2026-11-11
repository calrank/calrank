"""data.go.kr 파일데이터(한국등산트레킹지원센터 둘레길 GPX)가 내려받아지는지 확인한다. 로그에만 남는다.
인증키는 쓰지 않는다. 파일은 저장하지 않는다."""
import re
import requests

IDS = {"15098179": "오감만족 숲길", "15108080": "국가숲길 코스"}
H = {"User-Agent": "Mozilla/5.0 (calrank-probe)"}
for did, nm in IDS.items():
    print("==", did, nm)
    for url in (f"https://www.data.go.kr/data/{did}/fileData.do", f"https://www.data.go.kr/catalog/{did}/fileData.json"):
        try:
            r = requests.get(url, headers=H, timeout=40)
            t = r.text
            print(url, r.status_code, len(t))
            for m in sorted(set(re.findall(r"atchFileId[\"'=:\s]+([A-Za-z0-9_]+)", t)))[:5]:
                print("  atchFileId", m)
            for m in sorted(set(re.findall(r"(?:contentUrl|downloadURL|fileDownload\.do[^\"'<> ]*)[\"':= ]*([^\"'<> ,}]*)", t)))[:8]:
                print("  link", m[:200])
            for m in sorted(set(re.findall(r"[\w.\-]+\.(?:gpx|zip|xlsx?)", t)))[:12]:
                print("  file", m)
        except Exception as e:
            print(url, "ERR", type(e).__name__, str(e)[:120])

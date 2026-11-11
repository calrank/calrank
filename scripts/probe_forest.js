// 산림청 산·등산로 API 가 응답하는지, 좌표와 고도가 들어 있는지 확인한다.
// 인증키는 환경변수 DURUNUBI_API_KEY 에서만 읽고 어떤 출력에도 찍지 않는다. 저장하지 않는다.
"use strict";
const RAW = (process.env.DURUNUBI_API_KEY || "").trim();
if (!RAW) { console.log("DURUNUBI_API_KEY 가 비어 있습니다."); process.exit(1); }
const KEY = decodeURIComponent(RAW);
const mask = (s) => String(s).split(RAW).join("***").split(KEY).join("***").split(encodeURIComponent(KEY)).join("***");
const H = "https://apis.data.go.kr/1400000";
// 활용가이드를 아직 못 봐서, 알려진 이름을 후보로 시험한다. 맞는 것만 응답한다.
const CANDS = [
  [H + "/service/cultureInfoService2/mntInfoOpenAPI2", { searchWrd: "북한산" }],
  [H + "/service/cultureInfoService2/mntInfoOpenAPI2", { mntnNm: "북한산" }],
  [H + "/service/cultureInfoService2/mntInfoImgOpenAPI2", { mntiListNo: "100100501" }],
  [H + "/service/cultureInfoService2/mntInfoDtlInfoOpenAPI2", { mntiListNo: "100100501" }],
  [H + "/cultureInfoService/gdTrailInfoOpenAPI", { mntnNm: "북한산" }],
  [H + "/cultureInfoService/gdTrailInfoOpenAPI", {}],
  [H + "/cultureInfoService/gdTrailInfoOpenAPI", { searchMtNm: "북한산" }],
  [H + "/trailInfoService/getTrailInfo", {}],
  [H + "/trailInfoService/getforestspatialdataservice", {}],
  [H + "/trailInfoService/getforeststoryservice", {}],
  [H + "/trailInfoService", {}],
  [H + "/cultureInfoService", {}],
  [H + "/service/cultureInfoService2", {}],
];
(async () => {
  for (const [url, extra] of CANDS) {
    const q = new URLSearchParams(Object.assign({ serviceKey: KEY, numOfRows: 3, pageNo: 1 }, extra));
    try {
      const r = await fetch(url + "?" + q, { headers: { "User-Agent": "calrank-probe" } });
      const t = mask(await r.text());
      const ct = r.headers.get("content-type") || "";
      const head = t.replace(/\s+/g, " ").slice(0, 260);
      const tags = [...new Set((t.match(/<([a-zA-Z0-9_]+)>/g) || []).map((x) => x.slice(1, -1)))].slice(0, 40).join(",");
      console.log(`[${r.status}] ${url.replace(H, "")} ${JSON.stringify(extra)} (${ct.split(";")[0]})\n   ${head}\n   태그: ${tags}`);
    } catch (e) { console.log(`[실패] ${url.replace(H, "")}: ${mask(e.message)}`); }
  }
})();

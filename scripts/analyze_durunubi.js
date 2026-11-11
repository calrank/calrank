// 두루누비 코스 전체의 GPX 품질을 점검한다.
// - 인증키는 환경변수 DURUNUBI_API_KEY 에서만 읽고 어떤 출력에도 찍지 않는다.
// - GPX 원본과 응답 원문은 저장하지 않는다. 계산한 숫자만 요약해서 로그에 남기고,
//   코스별 표는 실행 결과 파일(artifact)로만 남긴다(저장소에 커밋하지 않는다).
// - 계산은 course.js(트레일루트 계산 엔진)를 그대로 쓴다.
"use strict";
const C = require("../course.js");
const fs = require("fs");

const RAW = (process.env.DURUNUBI_API_KEY || "").trim();
if (!RAW) { console.log("DURUNUBI_API_KEY 가 비어 있습니다."); process.exit(1); }
const KEY = decodeURIComponent(RAW);
const BASE = "https://apis.data.go.kr/B551011/Durunubi";
const mask = (s) => String(s).split(RAW).join("***").split(KEY).join("***").split(encodeURIComponent(KEY)).join("***");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function api(op, params) {
  const q = new URLSearchParams(Object.assign({ serviceKey: KEY, MobileOS: "ETC", MobileApp: "calrank", _type: "json" }, params));
  const r = await fetch(`${BASE}/${op}?${q}`, { headers: { "User-Agent": "calrank-analyze" } });
  const t = await r.text();
  try { return JSON.parse(t); } catch (e) { throw new Error("JSON 아님: " + mask(t.slice(0, 200))); }
}
const itemsOf = (d) => { const it = d && d.response && d.response.body && d.response.body.items && d.response.body.items.item; return !it ? [] : Array.isArray(it) ? it : [it]; };

function parseGpx(text) {
  // 속성 순서가 달라도 읽도록 lat/lon 을 따로 찾는다.
  const out = [], re = /<trkpt\b([^>]*)>([\s\S]*?)<\/trkpt>/g;
  let m;
  while ((m = re.exec(text))) {
    const la = /lat\s*=\s*["']([-0-9.]+)["']/.exec(m[1]), lo = /lon\s*=\s*["']([-0-9.]+)["']/.exec(m[1]);
    if (!la || !lo) continue;
    const e = /<ele>\s*([-0-9.eE+]+)\s*<\/ele>/.exec(m[2]);
    out.push({ lat: +la[1], lon: +lo[1], ele: e ? +e[1] : NaN });
  }
  return out;
}
function haversine(a, b) {
  const R = 6371000, rad = Math.PI / 180, dLat = (b.lat - a.lat) * rad, dLon = (b.lon - a.lon) * rad;
  const x = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(x));
}
const pct = (arr, p) => { const s = arr.slice().sort((a, b) => a - b); return s.length ? s[Math.min(s.length - 1, Math.floor(p * s.length))] : NaN; };

(async () => {
  // 1) 코스 목록 전체
  const courses = [];
  for (let page = 1; page <= 10; page++) {
    const d = await api("courseList", { numOfRows: 100, pageNo: page });
    const its = itemsOf(d);
    courses.push(...its);
    const total = +(d.response && d.response.body && d.response.body.totalCount) || 0;
    if (!its.length || courses.length >= total) break;
  }
  console.log("받은 코스 수:", courses.length);

  // 2) 코스마다 GPX 읽고 품질 계산
  const rows = [];
  let noGpx = 0, fail = 0, noEle = 0;
  for (const c of courses) {
    const url = c.gpxpath;
    if (!url) { noGpx++; continue; }
    try {
      const r = await fetch(url, { headers: { "User-Agent": "calrank-analyze" } });
      if (!r.ok) { fail++; continue; }
      const pts = parseGpx(await r.text());
      const good = pts.filter((p) => isFinite(p.ele));
      if (pts.length < 2 || good.length < pts.length * 0.9) { noEle++; continue; }
      let dist = 0, rawGain = 0, rawLoss = 0;
      for (let i = 1; i < good.length; i++) {
        dist += haversine(good[i - 1], good[i]);
        const dz = good[i].ele - good[i - 1].ele;
        if (dz > 0) rawGain += dz; else rawLoss -= dz;
      }
      const res = C.segsFromPoints(good);
      const a = C.analyze(res.segs, { flatPaceSecPerKm: 600 });
      const offKm = parseFloat(c.crsDstnc);
      rows.push({
        id: c.crsIdx, name: c.crsKorNm, sigun: c.sigun || "", level: c.crsLevel,
        officialKm: offKm, officialMin: +c.crsTotlRqrmHour || null,
        points: good.length, gpxKm: +(dist / 1000).toFixed(2),
        spacingM: +(dist / (good.length - 1)).toFixed(1),
        distRatio: offKm ? +(dist / 1000 / offKm).toFixed(3) : null,
        rawGainM: Math.round(rawGain), smoothGainM: Math.round(a.gainM),
        gainRatio: a.gainM > 0 ? +(rawGain / a.gainM).toFixed(2) : null,
        index: +a.index.toFixed(2),
      });
    } catch (e) { fail++; }
    await sleep(150);
  }

  // 3) 요약
  console.log(`GPX 없음 ${noGpx}, 읽기 실패 ${fail}, 고도 없음 ${noEle}, 분석 ${rows.length}`);
  const dr = rows.map((r) => r.distRatio).filter((x) => x), gr = rows.map((r) => r.gainRatio).filter((x) => x);
  const sp = rows.map((r) => r.spacingM);
  console.log("GPX 거리 / 공식 거리: 중앙값", pct(dr, 0.5), " 10%~90%", pct(dr, 0.1), "~", pct(dr, 0.9));
  console.log("원본 상승 / 다듬은 상승: 중앙값", pct(gr, 0.5), " 10%~90%", pct(gr, 0.1), "~", pct(gr, 0.9));
  console.log("점 간격(m): 중앙값", pct(sp, 0.5), " 10%~90%", pct(sp, 0.1), "~", pct(sp, 0.9));
  const lv = {}; rows.forEach((r) => { lv[r.level] = (lv[r.level] || 0) + 1; });
  console.log("공식 난이도(crsLevel) 분포:", JSON.stringify(lv));
  console.log("부하 지수: 최소", Math.min(...rows.map((r) => r.index)), "중앙값", pct(rows.map((r) => r.index), 0.5), "최대", Math.max(...rows.map((r) => r.index)));
  // 공식 소요시간 대비 거리 → 걷기 속도(참고)
  const spd = rows.filter((r) => r.officialMin && r.officialKm).map((r) => r.officialKm / (r.officialMin / 60));
  console.log("공식 거리 / 공식 소요시간 (km/h): 중앙값", pct(spd, 0.5).toFixed ? pct(spd, 0.5).toFixed(2) : pct(spd, 0.5), " 10%~90%", pct(spd, 0.1).toFixed(2), "~", pct(spd, 0.9).toFixed(2));
  console.log("고도 흔들림이 큰 코스(원본/다듬은 > 2):", rows.filter((r) => r.gainRatio > 2).length);
  console.log("거리 차이 10% 초과 코스:", rows.filter((r) => r.distRatio && Math.abs(r.distRatio - 1) > 0.1).length);
  // 4) 공식 난이도와 우리 지수가 같은 방향인지
  const rank = (a) => { const o = a.map((v, i) => [v, i]).sort((x, y) => x[0] - y[0]); const r = new Array(a.length); let i = 0; while (i < o.length) { let j = i; while (j + 1 < o.length && o[j + 1][0] === o[i][0]) j++; const avg = (i + j) / 2 + 1; for (let k = i; k <= j; k++) r[o[k][1]] = avg; i = j + 1; } return r; };
  const corr = (x, y) => { const n = x.length, mx = x.reduce((a, b) => a + b) / n, my = y.reduce((a, b) => a + b) / n; let sxy = 0, sxx = 0, syy = 0; for (let i = 0; i < n; i++) { sxy += (x[i] - mx) * (y[i] - my); sxx += (x[i] - mx) ** 2; syy += (y[i] - my) ** 2; } return sxy / Math.sqrt(sxx * syy); };
  const lvRows = rows.filter((r) => isFinite(+r.level));
  for (const L of [1, 2, 3]) {
    const g = lvRows.filter((r) => +r.level === L);
    if (!g.length) continue;
    const idx = g.map((r) => r.index), per = g.map((r) => r.smoothGainM / (r.gpxKm || 1)), km = g.map((r) => r.officialKm).filter((x) => x);
    console.log(`공식 난이도 ${L}: ${g.length}개, 지수 중앙값 ${pct(idx, 0.5)}, km당 상승(다듬은) 중앙값 ${pct(per, 0.5).toFixed(1)} m, 공식 거리 중앙값 ${pct(km, 0.5)} km`);
  }
  console.log("순위 상관(공식 난이도 vs 우리 지수):", corr(rank(lvRows.map((r) => +r.level)), rank(lvRows.map((r) => r.index))).toFixed(2));
  const withMin = rows.filter((r) => r.officialMin && r.officialKm);
  console.log("순위 상관(공식 소요시간÷거리 vs 우리 지수):", corr(rank(withMin.map((r) => r.officialMin / r.officialKm)), rank(withMin.map((r) => r.index))).toFixed(2));
  // 5) 거리가 크게 다른 코스 (코스 이름은 공개 정보)
  const bad = rows.filter((r) => r.distRatio && Math.abs(r.distRatio - 1) > 0.1).sort((a, b) => Math.abs(b.distRatio - 1) - Math.abs(a.distRatio - 1)).slice(0, 12);
  console.log("거리 차이가 큰 코스(상위 12):");
  bad.forEach((r) => console.log(`  ${r.name} | 공식 ${r.officialKm}km, GPX ${r.gpxKm}km (x${r.distRatio}), 점 ${r.points}개`));
  fs.writeFileSync("durunubi_quality.json", JSON.stringify(rows));
})().catch((e) => { console.log("실패:", mask(e && e.message ? e.message : e)); process.exit(1); });

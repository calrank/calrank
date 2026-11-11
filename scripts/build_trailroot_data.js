// 두루누비 코스를 받아 data/courses.json 을 만든다 (GitHub Actions 에서만 돈다).
// - 인증키는 환경변수 DURUNUBI_API_KEY 에서만 읽고 어떤 출력에도 찍지 않는다.
// - GPX 원본은 저장하지 않는다. 25m 간격으로 다듬은 고도 단면(최대 300점)과 숫자만 남긴다.
// - 거리가 공식 거리와 10% 넘게 다르거나 점이 부족한 코스는 싣지 않는다(제외 개수만 로그에 남긴다).
// - 사람이 손으로 적은 technical / checks 는 같은 id 가 있으면 그대로 보존한다.
"use strict";
const C = require("../course.js");
const fs = require("fs");
const path = require("path");

const RAW = (process.env.DURUNUBI_API_KEY || "").trim();
if (!RAW) { console.log("DURUNUBI_API_KEY 가 비어 있습니다."); process.exit(1); }
const KEY = decodeURIComponent(RAW);
const BASE = "https://apis.data.go.kr/B551011/Durunubi";
const OUT = path.join(__dirname, "..", "data", "courses.json");
const mask = (s) => String(s).split(RAW).join("***").split(KEY).join("***").split(encodeURIComponent(KEY)).join("***");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function api(op, params) {
  const q = new URLSearchParams(Object.assign({ serviceKey: KEY, MobileOS: "ETC", MobileApp: "calrank", _type: "json" }, params));
  const r = await fetch(`${BASE}/${op}?${q}`, { headers: { "User-Agent": "calrank-trailroot" } });
  const t = await r.text();
  try { return JSON.parse(t); } catch (e) { throw new Error("JSON 아님: " + mask(t.slice(0, 200))); }
}
const itemsOf = (d) => { const it = d && d.response && d.response.body && d.response.body.items && d.response.body.items.item; return !it ? [] : Array.isArray(it) ? it : [it]; };

function parseGpx(text) {
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
const slugId = (idx) => {
  const m = /(\d+)\s*$/.exec(String(idx));
  return "dr-" + (m ? String(+m[1]) : String(idx).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""));
};

(async () => {
  const courses = [];
  for (let page = 1; page <= 10; page++) {
    const d = await api("courseList", { numOfRows: 100, pageNo: page });
    const its = itemsOf(d);
    courses.push(...its);
    const total = +(d.response && d.response.body && d.response.body.totalCount) || 0;
    if (!its.length || courses.length >= total) break;
  }
  console.log("받은 코스 수:", courses.length);
  if (courses[0]) console.log("항목 필드:", Object.keys(courses[0]).sort().join(", "));

  let prev = {};
  try { JSON.parse(fs.readFileSync(OUT, "utf8")).courses.forEach((c) => { prev[c.id] = c; }); } catch (e) { /* 처음 */ }

  const today = new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 10);
  const out = [], skip = { noGpx: 0, fail: 0, noEle: 0, dist: 0, short: 0, dup: 0 };
  const seen = new Set();
  for (const c of courses) {
    if (!c.gpxpath) { skip.noGpx++; continue; }
    const id = slugId(c.crsIdx);
    if (seen.has(id)) { skip.dup++; continue; }
    try {
      const r = await fetch(c.gpxpath, { headers: { "User-Agent": "calrank-trailroot" } });
      if (!r.ok) { skip.fail++; continue; }
      const pts = parseGpx(await r.text());
      const good = pts.filter((p) => isFinite(p.ele));
      if (pts.length < 2 || good.length < pts.length * 0.9) { skip.noEle++; continue; }
      let dist = 0, rawGain = 0;
      for (let i = 1; i < good.length; i++) {
        dist += haversine(good[i - 1], good[i]);
        const dz = good[i].ele - good[i - 1].ele;
        if (dz > 0) rawGain += dz;
      }
      const offKm = parseFloat(c.crsDstnc);
      if (!offKm || Math.abs(dist / 1000 / offKm - 1) > 0.1) { skip.dist++; continue; }
      const res = C.segsFromPoints(good);
      if (!res || res.profile.length < 20) { skip.short++; continue; }
      const stride = Math.ceil(res.profile.length / 300);
      const prof = [];
      res.profile.forEach((p, i) => { if (i % stride === 0 || i === res.profile.length - 1) prof.push([Math.round(p.x), Math.round(p.y * 10) / 10]); });
      let gain = 0;
      for (let i = 1; i < res.profile.length; i++) { const dz = res.profile[i].y - res.profile[i - 1].y; if (dz > 0) gain += dz; }
      const old = prev[id] || {};
      seen.add(id);
      out.push({
        id, name: String(c.crsKorNm || "").trim(), region: String(c.sigun || "").trim(),
        official: { level: +c.crsLevel || null, km: offKm, min: +c.crsTotlRqrmHour || null },
        quality: { distRatio: +(dist / 1000 / offKm).toFixed(3), rawGainM: Math.round(rawGain), smoothGainM: Math.round(gain), points: good.length },
        source: {
          label: "한국관광공사 두루누비 코스 정보(공공데이터포털 오픈 API)",
          url: "https://www.durunubi.kr",
          license: "이용 조건 확인 중",
          fetched: today
        },
        profile: prof,
        technical: old.technical || { level: null, note: "", basis: "" },
        checks: old.checks || {},
        edited: old.edited || ""
      });
    } catch (e) { skip.fail++; }
    await sleep(150);
  }
  console.log("제외:", JSON.stringify(skip), "/ 실린 코스:", out.length);
  console.log("지역 표기가 있는 코스:", out.filter((c) => c.region).length);
  if (out.length < 20) { console.log("실린 코스가 너무 적어 파일을 바꾸지 않습니다."); process.exit(1); }

  out.sort((a, b) => (a.region || "~").localeCompare(b.region || "~", "ko") || a.name.localeCompare(b.name, "ko"));
  const cur = JSON.parse(fs.readFileSync(OUT, "utf8"));
  cur.courses = out;
  fs.writeFileSync(OUT, JSON.stringify(cur, null, 1) + "\n");
})().catch((e) => { console.log("실패:", mask(e && e.message ? e.message : e)); process.exit(1); });

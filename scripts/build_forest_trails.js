// 한국등산트레킹지원센터 둘레길 GPX(공공데이터포털 파일데이터, 이용허락범위 제한 없음)로 data/forest_trails.json 을 만든다.
// 포털은 내려받기에 자동입력 방지가 걸려 있어 파일은 사람이 받아 둔다. 이 스크립트는 받아 둔 폴더를 읽는다.
//
//   node scripts/build_forest_trails.js <GPX가 든 폴더들의 상위 폴더>
//
// - GPX 원본은 저장하지 않는다. 25m 간격으로 다듬은 고도 단면(최대 300점), 단순화한 경로(최대 400점),
//   경로에서 80m 안에 있는 시설·지점 이름만 남긴다.
// - 오감만족 숲길 자료의 한라산둘레길 파일에는 다른 길의 지점이 섞여 있어, 경로에서 먼 지점은 버린다.
"use strict";
const C = require("../course.js");
const fs = require("fs");
const path = require("path");

const SRC = process.argv[2];
if (!SRC) { console.log("사용법: node scripts/build_forest_trails.js <폴더>"); process.exit(1); }
const OUT = path.join(__dirname, "..", "data", "forest_trails.json");
const NAMES = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "data", "forest_trail_names.json"), "utf8"));

const LIC = "이용허락범위 제한 없음(공공데이터포털 표기)";
const SRC5 = { label: "한국등산트레킹지원센터 오감만족 숲길(공공데이터포털 파일데이터, 2022-01-12 기준)", url: "https://www.data.go.kr/data/15098179/fileData.do", license: LIC };
const SRCN = { label: "한국등산트레킹지원센터 국가숲길 코스(공공데이터포털 파일데이터, 2023-08-25 기준)", url: "https://www.data.go.kr/data/15108080/fileData.do", license: LIC };

// 폴더 → 길 이름, 시도, 이야기 한 줄(자료에서 확인되는 사실만)
const TRAILS = [
  { dir: "1.서울둘레길", trail: "서울둘레길", slug: "seoul", region: "서울", src: SRC5, files: (f) => { const m = /_(\d+)코스/.exec(f); return m ? { n: +m[1], name: `서울둘레길 ${+m[1]}코스` } : null; } },
  { dir: "2.한라산둘레길", trail: "한라산둘레길", slug: "hallasan", region: "제주", src: SRC5, nowpt: true, files: (f) => { const m = /한라산둘레길[ _](.+)\.gpx$/.exec(f); return m ? { n: 0, name: `한라산둘레길 ${m[1]}` } : null; } },
  { dir: "4.광릉숲길", trail: "광릉숲길", slug: "gwangneung", region: "경기", src: SRC5, files: () => ({ n: 1, name: "광릉숲길" }) },
  { dir: "9900000006_지리산둘레길", trail: "지리산둘레길", slug: "jirisan", region: "지리산권", src: SRCN, key: "지리산둘레길", files: nat("구간") },
  { dir: "9900000001_DMZ펀치볼둘레길", trail: "DMZ펀치볼둘레길", slug: "dmz-punchbowl", region: "강원", src: SRCN, key: "DMZ펀치볼둘레길", files: nat("") },
  { dir: "9900000002_내포문화숲길", trail: "내포문화숲길", slug: "naepo", region: "충남", src: SRCN, key: "내포문화숲길", files: nat("") },
  { dir: "9900000003_대관령숲길", trail: "대관령숲길", slug: "daegwallyeong", region: "강원", src: SRCN, key: "대관령숲길", files: nat("") },
  { dir: "9900000004_백두대간트레일", trail: "백두대간트레일", slug: "baekdudaegan", region: "강원", src: SRCN, key: "백두대간트레일", files: nat("") },
  { dir: "9900000005_울진금강소나무숲길", trail: "울진금강소나무숲길", slug: "uljin", region: "경북", src: SRCN, key: "울진금강소나무숲길", files: nat("") }
];
function nat(suffix) {
  return function (f, T) {
    const m = /_(\d{10})\.gpx$/.exec(f); if (!m) return null;
    const raw = (NAMES[T.key] || {})[m[1]]; if (!raw) return null;
    let label = raw.replace(/_/g, " ").replace(/대관련/g, "대관령");   // 원 자료의 오타(대관련숲길1코스)는 바로잡는다
    if (suffix === "구간" && /^[가-힣]+-[가-힣]+$/.test(label)) label += " 구간";
    return { n: +m[1], name: `${T.trail} ${label}` };
  };
}

function parseGpx(text) {
  const out = [], re = /<trkpt\b([^>]*)>([\s\S]*?)<\/trkpt>/g; let m;
  while ((m = re.exec(text))) {
    const la = /lat\s*=\s*["']([-0-9.]+)["']/.exec(m[1]), lo = /lon\s*=\s*["']([-0-9.]+)["']/.exec(m[1]); if (!la || !lo) continue;
    const e = /<ele>\s*([-0-9.eE+]+)\s*<\/ele>/.exec(m[2]);
    out.push({ lat: +la[1], lon: +lo[1], ele: e ? +e[1] : NaN });
  }
  return out;
}
function parseWpt(text) {
  const out = [], re = /<wpt\b([^>]*)>([\s\S]*?)<\/wpt>/g; let m;
  while ((m = re.exec(text))) {
    const la = /lat\s*=\s*["']([-0-9.]+)["']/.exec(m[1]), lo = /lon\s*=\s*["']([-0-9.]+)["']/.exec(m[1]); if (!la || !lo) continue;
    const nm = /<name>\s*(?:<!\[CDATA\[)?([\s\S]*?)(?:\]\]>)?\s*<\/name>/.exec(m[2]);
    const e = /<ele>\s*([-0-9.eE+]+)\s*<\/ele>/.exec(m[2]);
    out.push({ lat: +la[1], lon: +lo[1], ele: e ? +e[1] : NaN, name: nm ? nm[1].trim() : "" });
  }
  return out;
}
const hav = (a, b) => { const R = 6371000, r = Math.PI / 180, dLa = (b.lat - a.lat) * r, dLo = (b.lon - a.lon) * r; const x = Math.sin(dLa / 2) ** 2 + Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(dLo / 2) ** 2; return 2 * R * Math.asin(Math.sqrt(x)); };
function simplify(pts, tolM) {
  const k = Math.cos(pts[0].lat * Math.PI / 180), X = (p) => p.lon * 111320 * k, Y = (p) => p.lat * 110540;
  const keep = new Uint8Array(pts.length); keep[0] = keep[pts.length - 1] = 1; const st = [[0, pts.length - 1]];
  while (st.length) {
    const [a, b] = st.pop(); const ax = X(pts[a]), ay = Y(pts[a]), dx = X(pts[b]) - ax, dy = Y(pts[b]) - ay, L = Math.hypot(dx, dy) || 1; let mx = 0, mi = -1;
    for (let i = a + 1; i < b; i++) { const d = Math.abs((X(pts[i]) - ax) * dy - (Y(pts[i]) - ay) * dx) / L; if (d > mx) { mx = d; mi = i; } }
    if (mx > tolM && mi > 0) { keep[mi] = 1; st.push([a, mi], [mi, b]); }
  }
  const out = []; pts.forEach((p, i) => { if (keep[i]) out.push([+p.lat.toFixed(5), +p.lon.toFixed(5)]); }); return out;
}

// 지점 이름을 종류로 묶는다. 안내용 점(갈림길, 이정표, 방향 표시)은 개수만 세고, 눈에 띄는 이름만 따로 남긴다.
const GENERIC = /^(갈림길|이정표|Way ?point|waypoint|ㅜ|Y|T|十|ㅏ|ㅓ|횡단보도|둘레길 방향.*|둘레길 안내|길안내|안내판|표지판|리본.*|방향.*|[0-9]+)$/i;
function kindOf(n) {
  const s = n.replace(/\s*\d+$/, "").trim();
  if (/화장실|화징실|공중화장/.test(s)) return "화장실";
  if (/쉼터|쉼팡|휴게/.test(s)) return "쉼터";
  if (/전망/.test(s)) return "전망";
  if (/약수터|샘터|우물/.test(s)) return "약수터·샘터";
  if (/정자|벤치|의자/.test(s)) return "";
  if (/주차/.test(s)) return "주차장";
  if (/안내소|탐방지원센터|탐방안내|방문자|센터/.test(s)) return "안내소";
  if (/스탬프|스템프/.test(s)) return "스탬프";
  if (/갈림길/.test(s)) return "갈림길";
  return "";
}

const rows = [], GEO = {};
const skip = [];
for (const T of TRAILS) {
  const dir = path.join(SRC, T.dir);
  if (!fs.existsSync(dir)) { skip.push(T.dir + " 폴더 없음"); continue; }
  const files = fs.readdirSync(dir).filter((f) => /\.gpx$/i.test(f)).sort();
  for (const f of files) {
    const meta = T.files(f, T); if (!meta) { skip.push(f + " 이름 해석 못 함"); continue; }
    const text = fs.readFileSync(path.join(dir, f), "utf8");
    const pts = parseGpx(text), good = pts.filter((p) => isFinite(p.ele));
    if (pts.length < 2 || good.length < pts.length * 0.9) { skip.push(f + " 고도 없음"); continue; }
    let dist = 0, raw = 0; const cum = [0];
    for (let i = 1; i < good.length; i++) { const d = hav(good[i - 1], good[i]); dist += d; cum.push(dist); const dz = good[i].ele - good[i - 1].ele; if (dz > 0) raw += dz; }
    // 국가숲길 코스 GPX 는 고도 칸이 전부 0 이다. 그런 코스는 경로만 두고, 고도는 위성 고도 자료(Copernicus DEM)로 따로 채운다.
    const flatEle = Math.max(...good.map((p) => p.ele)) - Math.min(...good.map((p) => p.ele)) < 0.5;
    let res = null, ys = [];
    if (!flatEle) {
      res = C.segsFromPoints(good);
      if (!res || res.profile.length < 20) { skip.push(f + " 점 부족"); continue; }
      ys = res.profile.map((q) => q.y);
      if (Math.max(...ys) - Math.min(...ys) < 5 && dist > 3000) { skip.push(f + " 고도 고정"); continue; }
    } else if (dist < 500) { skip.push(f + " 너무 짧음"); continue; }
    const prof = [];
    if (res) { const stride = Math.ceil(res.profile.length / 300); res.profile.forEach((p, i) => { if (i % stride === 0 || i === res.profile.length - 1) prof.push([Math.round(p.x), Math.round(p.y * 10) / 10]); }); }
    let tol = 12, pth = simplify(good, tol); while (pth.length > 400) { tol *= 1.5; pth = simplify(good, tol); }
    let gain = 0; if (res) for (let i = 1; i < res.profile.length; i++) { const dz = res.profile[i].y - res.profile[i - 1].y; if (dz > 0) gain += dz; }
    // 고도를 따로 채울 코스: 25m 간격으로 다시 찍은 위경도를 남긴다
    let geo = null;
    if (!res) {
      geo = []; let next = 0;
      for (let i = 0; i < good.length; i++) { if (cum[i] >= next || i === good.length - 1) { geo.push([+good[i].lat.toFixed(5), +good[i].lon.toFixed(5)]); next = cum[i] + 25; } }
    }

    // 지점: 경로에서 80m 안에 있는 것만. 경로를 따라 몇 m 지점인지도 구한다.
    let counts = {}, pois = [], wptAll = 0, wptNear = 0;
    if (!T.nowpt) {
      const wp = parseWpt(text); wptAll = wp.length;
      const k = Math.cos(good[0].lat * Math.PI / 180);
      const step = Math.max(1, Math.floor(good.length / 1500));
      const seen = new Set();
      for (const w of wp) {
        let best = Infinity, bi = 0;
        for (let i = 0; i < good.length; i += step) { const d = Math.hypot((w.lat - good[i].lat) * 110540, (w.lon - good[i].lon) * 111320 * k); if (d < best) { best = d; bi = i; } }
        if (best > 80) continue;
        wptNear++;
        const nm = w.name, kd = kindOf(nm);
        if (kd) counts[kd] = (counts[kd] || 0) + 1;
        if (!nm || GENERIC.test(nm.replace(/\s*\d+$/, "")) || kd === "갈림길" || kd === "쉼터") continue;
        const key = nm.replace(/\s+/g, "");
        if (seen.has(key)) continue; seen.add(key);
        pois.push([Math.round(cum[bi]), nm.slice(0, 40), isFinite(w.ele) ? Math.round(w.ele) : null, kd]);
      }
      pois.sort((a, b) => a[0] - b[0]);
      if (pois.length > 16) { const every = pois.length / 16; pois = Array.from({ length: 16 }, (_, i) => pois[Math.floor(i * every)]); }
    }
    if (geo) GEO[`${T.slug}|${meta.n}`] = geo;
    rows.push({
      id: "", _n: meta.n,
      name: meta.name, trail: T.trail, trailSlug: T.slug, region: T.region,
      official: { level: null, km: null, min: null },
      quality: { distRatio: null, rawGainM: Math.round(raw), smoothGainM: Math.round(gain), points: good.length, spacingM: +(dist / (good.length - 1)).toFixed(1) },
      source: Object.assign({}, T.src, { fetched: new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 10) }),
      profile: prof, path: pth, needsDem: !res, lengthM: Math.round(dist),
      waypoints: { total: wptAll, near: wptNear, counts, pois },
      technical: { level: null, note: "", basis: "" }, checks: {}, edited: ""
    });
  }
}
// 한라산둘레길처럼 번호가 없는 길은 id 를 이름 순서로 매긴다
const byTrail = {}; rows.forEach((r) => { (byTrail[r.trail] = byTrail[r.trail] || []).push(r); });
Object.keys(byTrail).forEach((t) => byTrail[t].forEach((r, i) => { r.id = `ft-${r.trailSlug}-${i + 1}`; }));
console.log("실린 코스:", rows.length, "제외:", skip.length, skip.slice(0, 10));
rows.forEach((r) => { const L = (r.lengthM || 0) / 1000; console.log(r.id, r.name, L.toFixed(1) + "km", "오르막", r.quality.smoothGainM, "m", "지점", r.waypoints.near + "/" + r.waypoints.total, JSON.stringify(r.waypoints.counts)); });
const geoOut = {};
Object.keys(byTrail).forEach((t) => byTrail[t].forEach((r) => { const k = Object.keys(GEO).find((g) => g.startsWith(r.trailSlug + '|') && GEO[g]._for === undefined && g === r.trailSlug + '|' + r._n); if (k) geoOut[r.id] = GEO[k]; }));
if (rows.length < 20) { console.log("너무 적어 쓰지 않습니다."); process.exit(1); }
rows.forEach((r) => { delete r._n; });
fs.writeFileSync(path.join(__dirname, "..", "data", "forest_trails_geo.json"), JSON.stringify(geoOut) + "\n");
fs.writeFileSync(OUT, JSON.stringify({ note: "한국등산트레킹지원센터 둘레길 GPX에서 계산한 코스. 원본 GPX는 저장하지 않았습니다.", courses: rows }, null, 1) + "\n");

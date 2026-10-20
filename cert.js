// 기록증 사진에서 완주 시간을 읽어 등급 카드를 만든다.
//
// 설계 메모
//  - 사진은 기기 밖으로 나가지 않는다. 전처리와 글자 인식 모두 브라우저에서 한다.
//  - 이름은 읽지 않는다. 필요한 건 완주 시간과 거리뿐이고, 개인정보를 굳이
//    읽을 이유가 없다.
//  - 기록증 전체를 한 번에 인식하면 큰 글씨로 박힌 완주 시간을 거의 못 읽는다.
//    (배경 블록 때문에 이진화가 깨진다.) 그래서 글자가 있는 "행"을 찾아
//    한 줄씩 인식하되, 완주 시간은 보통 가장 큰 글씨라서 높이가 큰 행부터
//    훑는다. 실측으로 두세 번 안에 찾는다.
//  - 실패해도 멈추지 않는다. 시간을 직접 입력하면 그대로 진행된다.

(function () {
  "use strict";

  var G = window.CalrankGrade;
  var TESS_URL = "https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js";

  var fileInput = document.getElementById("certFile");
  var statusEl = document.getElementById("ctStatus");
  var formEl = document.getElementById("ctForm");
  var raceInput = document.getElementById("ctRace");
  var raceList = document.getElementById("ctRaceList");
  var distSel = document.getElementById("ctDist");
  var timeInput = document.getElementById("ctTime");
  var genderSel = document.getElementById("ctGender");
  var yearInput = document.getElementById("ctYear");
  var cardWrap = document.getElementById("ctCard");
  var canvas = document.getElementById("ctCanvas");

  function say(msg) { statusEl.textContent = msg || ""; }
  function showForm() { formEl.classList.add("on"); }

  // ---------- 1. 대회 자동완성 ----------
  var nameInput = document.getElementById("ctName");
  var raceMap = null;
  fetch("events.json").then(function (r) { return r.json(); }).then(function (events) {
    var today = new Date().toISOString().slice(0, 10);
    var byName = new Map();
    events.forEach(function (e) {
      var n = (e.name || "").trim();
      if (!n) return;
      var prev = byName.get(n);
      var isPast = (e.date || "") <= today;
      if (!prev) { byName.set(n, e); return; }
      var prevPast = (prev.date || "") <= today;
      if (isPast && !prevPast) { byName.set(n, e); return; }
      if (isPast === prevPast && (e.date || "") > (prev.date || "")) byName.set(n, e);
    });
    raceMap = byName;
    var arr = Array.from(byName.values()).sort(function (a, b) {
      return (b.date || "").localeCompare(a.date || "");
    });
    var frag = document.createDocumentFragment();
    arr.forEach(function (e) {
      var o = document.createElement("option");
      o.value = e.name;
      o.label = [(e.date || "").slice(0, 10), e.region].filter(Boolean).join(" · ");
      frag.appendChild(o);
    });
    raceList.appendChild(frag);
  }).catch(function () { /* 자동완성이 없어도 직접 입력은 된다 */ });

  // 대회를 고르면 거리 후보를 맞춰 준다
  function onRacePicked() {
    if (!raceMap) return;
    var e = raceMap.get((raceInput.value || "").trim());
    if (!e) return;
    var raw = (e.distances || []).join(" ");
    var want = null;
    if (/하프/.test(raw)) want = "21.0975";
    if (/10\s*km/i.test(raw)) want = "10";
    if (!want && /5\s*km/i.test(raw)) want = "5";
    if (!want && /(풀|42)/.test(raw)) want = "42.195";
    if (want) distSel.value = want;
  }
  raceInput.addEventListener("input", onRacePicked);
  raceInput.addEventListener("change", onRacePicked);

  // ---------- 2. 이미지 전처리 ----------
  // 몇 배로 그릴지. 기록증을 화면 캡처로 저장하면 600px 남짓한 그림이 되는데,
  // 그대로 읽으면 '종 목 · 하프' 같은 작은 글씨가 뭉개져 아예 안 읽힙니다.
  // 작은 그림은 키워서 읽습니다 (너무 키우면 흐려지니 2.5배까지만).
  var MAX_PX = 4.2e6;   // 이보다 크게 그리면 휴대폰에서 읽는 데 너무 오래 걸립니다

  function fitScale(img, targetW) {
    var s = targetW / img.width;
    if (s > 4) s = 4;
    if (s < 0.15) s = 0.15;
    var px = img.width * img.height * s * s;
    if (px > MAX_PX) s = Math.sqrt(MAX_PX / (img.width * img.height));
    return s;
  }

  function toGray(img, maxW) {
    var scale = fitScale(img, maxW);
    var w = Math.max(1, Math.round(img.width * scale));
    var h = Math.max(1, Math.round(img.height * scale));
    var c = document.createElement("canvas");
    c.width = w; c.height = h;
    var ctx = c.getContext("2d");
    ctx.drawImage(img, 0, 0, w, h);
    var d = ctx.getImageData(0, 0, w, h).data;
    var g = new Uint8ClampedArray(w * h);
    for (var i = 0, p = 0; i < d.length; i += 4, p++) {
      g[p] = (d[i] * 299 + d[i + 1] * 587 + d[i + 2] * 114) / 1000;
    }
    return { gray: g, w: w, h: h };
  }

  // 전체 읽기용 캔버스. 한글은 획이 많아서 작은 글씨에서 뭉개지므로
  // 숫자 인식용(1100px)보다 크게 그리고, 이진화하지 않고 회색조로 둡니다.
  // 획이 가는 글꼴은 이진화하면 끊어져서 오히려 더 못 읽습니다.
  function fullCanvas(img, maxW) {
    var scale = fitScale(img, maxW);
    var w = Math.max(1, Math.round(img.width * scale));
    var h = Math.max(1, Math.round(img.height * scale));
    var c = document.createElement("canvas");
    c.width = w; c.height = h;
    var ctx = c.getContext("2d");
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(img, 0, 0, w, h);
    var im = ctx.getImageData(0, 0, w, h);
    var d = im.data;
    // 명암을 살짝 벌려 줍니다 (하위 5% ~ 상위 95% 를 0~255 로)
    var hist = new Uint32Array(256), i;
    for (i = 0; i < d.length; i += 4) {
      hist[(d[i] * 299 + d[i + 1] * 587 + d[i + 2] * 114) / 1000 | 0]++;
    }
    var total = w * h, acc = 0, lo = 0, hi = 255;
    for (i = 0; i < 256; i++) { acc += hist[i]; if (acc > total * 0.05) { lo = i; break; } }
    acc = 0;
    for (i = 255; i >= 0; i--) { acc += hist[i]; if (acc > total * 0.05) { hi = i; break; } }
    var span = Math.max(1, hi - lo);
    for (i = 0; i < d.length; i += 4) {
      var g = (d[i] * 299 + d[i + 1] * 587 + d[i + 2] * 114) / 1000;
      var v = Math.max(0, Math.min(255, ((g - lo) / span) * 255));
      d[i] = d[i + 1] = d[i + 2] = v;
      d[i + 3] = 255;
    }
    ctx.putImageData(im, 0, 0);
    return c;
  }

  // 대회 이름만 따로 읽기 위한 캔버스.
  // 대회 이름은 로고처럼 꾸민 글씨라 전체를 한 번에 읽으면 거의 뭉개집니다.
  // 위쪽 띠만 잘라 크게 그리면 제법 읽힙니다. 잘라 놓으니 넓이도 얼마 안 듭니다.
  function titleCanvas(img) {
    var sh = Math.max(1, Math.round(img.height * 0.42));
    var s = 1800 / img.width;
    if (s > 4) s = 4;
    if (s < 0.3) s = 0.3;
    var px = img.width * sh * s * s;
    if (px > MAX_PX) s = Math.sqrt(MAX_PX / (img.width * sh));
    var w = Math.max(1, Math.round(img.width * s));
    var h = Math.max(1, Math.round(sh * s));
    var c = document.createElement("canvas");
    c.width = w; c.height = h;
    var ctx = c.getContext("2d");
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(img, 0, 0, img.width, sh, 0, 0, w, h);
    var im = ctx.getImageData(0, 0, w, h), d = im.data;
    var hist = new Uint32Array(256), i;
    for (i = 0; i < d.length; i += 4) {
      hist[(d[i] * 299 + d[i + 1] * 587 + d[i + 2] * 114) / 1000 | 0]++;
    }
    var total = w * h, acc = 0, lo = 0, hi = 255;
    for (i = 0; i < 256; i++) { acc += hist[i]; if (acc > total * 0.03) { lo = i; break; } }
    acc = 0;
    for (i = 255; i >= 0; i--) { acc += hist[i]; if (acc > total * 0.03) { hi = i; break; } }
    var span = Math.max(1, hi - lo);
    for (i = 0; i < d.length; i += 4) {
      var g = (d[i] * 299 + d[i + 1] * 587 + d[i + 2] * 114) / 1000;
      var v = Math.max(0, Math.min(255, ((g - lo) / span) * 255));
      d[i] = d[i + 1] = d[i + 2] = v;
      d[i + 3] = 255;
    }
    ctx.putImageData(im, 0, 0);
    return c;
  }

  // 띠에서 읽은 줄 가운데 대회 이름처럼 보이는 것을 고릅니다.
  function titleGuess(text) {
    var lines = String(text || "").split(/[\r\n]+/);
    var best = null, bestScore = 0;
    for (var i = 0; i < lines.length; i++) {
      var raw = lines[i].trim();
      if (raw.length < 4) continue;
      // 글자 사이에 낀 기호와 홀로 선 알파벳은 OCR 찌꺼기입니다
      var t = raw.replace(/[|_~^`"'\\\/\[\]{}<>=+*#@]/g, " ")
                 .replace(/\s+/g, " ").trim();
      if (!/마\s*라\s*톤|대\s*회|러\s*닝|마\s*라\s*손|\brun\b|\bmarathon\b/i.test(t)) continue;
      var hangul = (t.match(/[가-힣]/g) || []).length;
      if (hangul < 3) continue;
      // 한글 비중이 높고 적당히 긴 줄이 제목일 가능성이 큽니다
      var sc = hangul / t.length + Math.min(t.length, 24) / 60;
      if (sc > bestScore) { bestScore = sc; best = t; }
    }
    if (!best) return null;
    // 양끝에 남은 찌꺼기를 떼어 냅니다. 앞에 홀로 붙은 짧은 숫자나 알파벳은
    // 로고 조각이 숫자로 읽힌 것이라 떼어 냅니다 (연도 네 자리는 남깁니다).
    best = best.replace(/^[^가-힣0-9A-Za-z]+/, "").replace(/[^가-힣0-9A-Za-z)]+$/, "");
    for (var k = 0; k < 3; k++) {
      var m2 = best.match(/^(\d{1,3}|[A-Za-z]{1,2})\s+(.*)$/);
      if (!m2 || !/[가-힣]/.test(m2[2])) break;
      best = m2[2].trim();
    }
    // 글자 사이에 낀 한 자리 숫자도 OCR 찌꺼기입니다 ('손7 정펑하' → '손정펑하')
    best = best.replace(/([가-힣])\s*\d\s*([가-힣])/g, "$1$2")
               .replace(/[。、·．,]+/g, " ")
               .replace(/\s+/g, " ").trim();

    // 제목 뒤에 딸려 온 찌꺼기를 떼어 냅니다 ('… 마라톤 대회。 세 g' → '… 마라톤 대회').
    // '대회'·'마라톤' 뒤에 남은 토막이 제대로 된 말이 아니면 버립니다.
    var kw = /(대\s*회|마\s*라\s*톤|러\s*닝|마\s*라\s*손|run|marathon)/gi, last = null, km4;
    while ((km4 = kw.exec(best))) last = km4.index + km4[0].length;
    if (last !== null && last < best.length) {
      var tail = best.slice(last).trim();
      var tailOk = /^[가-힣]{2,}/.test(tail) && !/[^가-힣0-9A-Za-z\s()]/.test(tail);
      if (!tailOk) best = best.slice(0, last).trim();
    }
    return best.length >= 4 && best.length <= 60 ? best : null;
  }

  // 적분영상으로 지역 평균을 구해 적응형 이진화한다.
  // 기록증은 색 블록이 많아 전역 임계값으로는 글자가 뭉개진다.
  function adaptiveInk(gray, w, h, win, C) {
    var sum = new Float64Array((w + 1) * (h + 1));
    for (var y = 0; y < h; y++) {
      var rowSum = 0;
      for (var x = 0; x < w; x++) {
        rowSum += gray[y * w + x];
        sum[(y + 1) * (w + 1) + (x + 1)] = sum[y * (w + 1) + (x + 1)] + rowSum;
      }
    }
    var r = win >> 1;
    var ink = new Uint8Array(w * h);
    for (var yy = 0; yy < h; yy++) {
      var y0 = Math.max(0, yy - r), y1 = Math.min(h - 1, yy + r);
      for (var xx = 0; xx < w; xx++) {
        var x0 = Math.max(0, xx - r), x1 = Math.min(w - 1, xx + r);
        var area = (y1 - y0 + 1) * (x1 - x0 + 1);
        var s = sum[(y1 + 1) * (w + 1) + (x1 + 1)] - sum[y0 * (w + 1) + (x1 + 1)]
              - sum[(y1 + 1) * (w + 1) + x0] + sum[y0 * (w + 1) + x0];
        if (gray[yy * w + xx] < s / area - C) ink[yy * w + xx] = 1;
      }
    }
    return ink;
  }

  // 글자가 있는 y구간을 찾는다. 가로를 가득 채우는 색 띠는 글자가 아니므로 뺀다.
  function textRows(ink, w, h) {
    var rows = [], start = null;
    for (var y = 0; y < h; y++) {
      var c = 0, base = y * w;
      for (var x = 0; x < w; x++) c += ink[base + x];
      var frac = c / w;
      var isText = frac > 0.005 && frac < 0.55;
      if (isText && start === null) start = y;
      else if (!isText && start !== null) {
        if (y - start >= 8) rows.push([start, y]);
        start = null;
      }
    }
    if (start !== null) rows.push([start, h]);
    return rows.filter(function (r) {
      var d = r[1] - r[0];
      return d >= 0.012 * h && d <= 0.25 * h;
    });
  }

  function otsu(vals) {
    var hist = new Array(256).fill(0), i;
    for (i = 0; i < vals.length; i++) hist[vals[i]]++;
    var total = vals.length, sum = 0;
    for (i = 0; i < 256; i++) sum += i * hist[i];
    var sumB = 0, wB = 0, best = 0, thr = 127;
    for (i = 0; i < 256; i++) {
      wB += hist[i];
      if (!wB) continue;
      var wF = total - wB;
      if (!wF) break;
      sumB += i * hist[i];
      var mB = sumB / wB, mF = (sum - sumB) / wF;
      var between = wB * wF * (mB - mF) * (mB - mF);
      if (between > best) { best = between; thr = i; }
    }
    return thr;
  }

  // 한 행을 잘라 3배 확대 + Otsu 이진화한 캔버스를 만든다
  function rowCanvas(gray, w, h, a, b) {
    var pad = Math.round((b - a) * 0.15);
    var y0 = Math.max(0, a - pad), y1 = Math.min(h, b + pad);
    var rh = y1 - y0;
    var vals = new Uint8ClampedArray(w * rh);
    for (var y = 0; y < rh; y++) {
      for (var x = 0; x < w; x++) vals[y * w + x] = gray[(y0 + y) * w + x];
    }
    var thr = otsu(vals);
    var S = 3;
    var c = document.createElement("canvas");
    c.width = w * S; c.height = rh * S;
    var ctx = c.getContext("2d");
    var out = ctx.createImageData(w * S, rh * S);
    for (var yy = 0; yy < rh * S; yy++) {
      var sy = (yy / S) | 0;
      for (var xx = 0; xx < w * S; xx++) {
        var v = vals[sy * w + ((xx / S) | 0)] > thr ? 255 : 0;
        var o = (yy * w * S + xx) * 4;
        out.data[o] = out.data[o + 1] = out.data[o + 2] = v;
        out.data[o + 3] = 255;
      }
    }
    ctx.putImageData(out, 0, 0);
    return c;
  }

  // ---------- 3. 글자 인식 ----------
  //
  // 기록증은 대회마다 생김새가 전부 다릅니다. 그래서 한 번만 읽어서는
  // 완주 시간 말고는 거의 못 건집니다. 두 번 나눠 읽습니다.
  //
  //   A. 숫자만 읽기  — 가장 큰 글씨 줄부터 훑어 완주 시간을 찾습니다.
  //                    글자 후보를 숫자와 콜론으로 좁혀서 빠르고 정확합니다.
  //   B. 전체 읽기    — 한글과 영문을 같이 켜고 사진 전체를 읽습니다.
  //                    대회명·날짜·거리·배번·순위·구간기록이 여기서 나옵니다.
  //
  // 그리고 대회명은 OCR 결과를 그대로 믿지 않습니다. 우리가 이미 822개
  // 대회 목록을 들고 있으니, 읽어낸 글자와 그 목록을 대조해서 가장 가까운
  // 대회를 고릅니다. 글자 몇 개가 틀려도 맞출 수 있습니다.
  //
  // 사진은 기기 밖으로 나가지 않습니다. 이름은 일부러 읽지 않습니다.

  function loadTesseract() {
    if (window.Tesseract) return Promise.resolve(window.Tesseract);
    return new Promise(function (res, rej) {
      var s = document.createElement("script");
      s.src = TESS_URL;
      s.onload = function () { res(window.Tesseract); };
      s.onerror = function () { rej(new Error("글자 인식 모듈을 불러오지 못했습니다")); };
      document.head.appendChild(s);
    });
  }

  // ---- 문자열 정규화: 비교할 때 방해가 되는 것들을 턴다
  function norm(s) {
    return String(s || "")
      .replace(/제\s*\d+\s*회/g, "")      // '제24회'
      .replace(/20\d\d\s*년?/g, "")        // 연도
      .replace(/[\s·・\-_()[\]{}'"`.,~!?:;/\\|]/g, "")
      .toLowerCase();
  }

  // ---- 두 글자씩 끊어 겹치는 비율 (한글에 잘 맞습니다)
  function bigrams(s) {
    var out = [];
    for (var i = 0; i < s.length - 1; i++) out.push(s.slice(i, i + 2));
    return out;
  }

  function similarity(a, b) {
    if (!a || !b) return 0;
    if (a.length < 2 || b.length < 2) return a === b ? 1 : 0;
    var A = bigrams(a), B = bigrams(b);
    var map = Object.create(null), hit = 0;
    A.forEach(function (g) { map[g] = (map[g] || 0) + 1; });
    B.forEach(function (g) { if (map[g] > 0) { map[g]--; hit++; } });
    return (2 * hit) / (A.length + B.length);
  }

  // ---- 읽어낸 글자에서 가장 가까운 대회를 고른다
  function matchRace(text, dateHint) {
    if (!raceMap || !text) return null;
    var flat = norm(text);

    // 글자를 전부 이어 붙여 놓고 창을 옮겨 가며 맞춰 봤더니, 맨 아래 서명 줄
    // ('중랑구육상연맹 회장 김 석')이 옆 글자들과 뭉쳐 엉뚱한 '○○육상연맹
    // 회장배' 대회로 이어졌습니다. 그래서 줄 단위로 견줍니다. 제목이 두 줄로
    // 나뉘어 읽히는 일이 있어 이웃한 두 줄을 붙인 것도 함께 봅니다.
    var lines = String(text).split(/[\r\n]+/).map(function (x) { return x.trim(); })
                 .filter(function (x) { return x.length >= 2; });
    var head = Math.max(3, Math.ceil(lines.length * 0.4));
    var cands = [];
    lines.forEach(function (ln, i) {
      cands.push({ s: norm(ln), top: i < head });
      if (i + 1 < lines.length) {
        cands.push({ s: norm(ln + " " + lines[i + 1]), top: i < head });
      }
    });
    cands = cands.filter(function (c) { return c.s.length >= 3; });
    if (!cands.length) return null;

    var best = null, bestScore = 0;
    raceMap.forEach(function (ev, name) {
      var n = norm(name);
      if (n.length < 3) return;
      var score = 0;
      if (flat.indexOf(n) >= 0) {
        score = 1;                               // 이름이 통째로 들어 있으면 확실
      } else {
        for (var i = 0; i < cands.length; i++) {
          var sc = similarity(n, cands[i].s);
          // 대회 이름은 거의 언제나 기록증 위쪽에 있습니다
          if (cands[i].top) sc += 0.05;
          if (sc > score) score = sc;
        }
      }
      // 기록증의 날짜와 대회 날짜가 맞으면 점수를 올려 준다
      if (dateHint && ev.date && ev.date.slice(0, 10) === dateHint) score += 0.25;
      if (score > bestScore) { bestScore = score; best = { name: name, ev: ev, score: score }; }
    });
    if (!best || bestScore < 0.45) return null;
    // 이름이 통째로 들어 있었던 경우만 '확실'로 봅니다. 나머지는 비슷해 보이는
    // 것을 고른 것뿐이라, 채워는 두되 확인해 달라고 말합니다.
    best.exact = bestScore >= 0.95;
    // 2005년 기록증이 '인권마라톤' 이라는 겹치는 말만으로 올해 대회에 걸린 적이
    // 있습니다. 연도가 다르면 비슷해 보이는 것만으로는 받아들이지 않습니다.
    if (!best.exact && dateHint && best.ev && best.ev.date &&
        best.ev.date.slice(0, 4) !== dateHint.slice(0, 4)) {
      return null;
    }
    return best;
  }

  // ---- 읽어낸 글자 전체에서 쓸 수 있는 것을 전부 뽑는다
  // 초 → 'H:MM:SS' (한글 단위로 적힌 기록을 다른 시간과 같은 모양으로 맞춥니다)
  function clock(sec) {
    var h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s2 = sec % 60;
    return h + ":" + ("0" + m).slice(-2) + ":" + ("0" + s2).slice(-2);
  }

  // 한 토막에서 종목을 읽습니다. 풀과 하프가 같이 있으면 그건 그 대회의
  // 종목 목록이지 내가 뛴 종목이 아니므로 아무것도 고르지 않습니다.
  function courseOf(v) {
    if (!v) return null;
    // 구간 표시가 섞인 토막은 종목이 아닙니다 ('5km지점', '하프지점')
    v = String(v).replace(/[^\s]{0,6}\s*(?:지\s*점|구\s*간)/g, " ");
    var full = /42\.?195|풀(?!\s*이)|\bfull\b(?!\s*name)/i.test(v);
    var half = /21\.?0975|하\s*프|\bhalf\b/i.test(v);
    if (full && half) return null;
    if (full) return "42.195";
    if (half) return "21.0975";
    var k = String(v).match(/(\d{1,3}(?:\.\d+)?)\s*(?:km|킬로|k(?![a-z]))/i);
    if (k) {
      var n = parseFloat(k[1]);
      // 5km 와 10km 가 함께 적혀 있으면 그것도 목록입니다
      var all = String(v).match(/\d{1,3}(?:\.\d+)?\s*(?:km|킬로|k(?![a-z]))/gi) || [];
      if (all.length > 1) return null;
      if (n > 0 && n <= 100) return String(n);
    }
    return null;
  }

  // ── 낱말 상자로 칸 읽기 ──────────────────────────────────
  // 글자를 전부 이어 붙인 뒤에 정규식으로 찾으면, 왼쪽 사진 자리에서 나온
  // 찌꺼기가 칸 사이에 끼어들어 값을 가립니다. Tesseract 가 돌려주는 낱말
  // 상자에는 좌표가 들어 있으니, 이름표 오른쪽에 같은 줄로 놓인 낱말만
  // 모으면 그 칸의 값이 그대로 나옵니다.
  var WORD_LABELS = [
    ["name",   /^(성\s*명|이\s*름|성|명|name|참가자)$/i],
    ["course", /^(종\s*목|부\s*문|구\s*분|목|course|division)$/i],
    ["record", /^(완\s*주\s*기\s*록|기\s*록|record)$/i],
    ["bib",    /^(참\s*가\s*번\s*호|배\s*번|번호|bib|no\.?)$/i]
  ];

  function wordRows(words) {
    var W = [];
    for (var i = 0; i < (words || []).length; i++) {
      var w = words[i];
      if (!w || !w.bbox || !w.text) continue;
      var t = String(w.text).trim();
      if (!t) continue;
      var h = w.bbox.y1 - w.bbox.y0;
      if (h < 5) continue;
      W.push({ t: t, x0: w.bbox.x0, x1: w.bbox.x1, y0: w.bbox.y0, y1: w.bbox.y1,
               cy: (w.bbox.y0 + w.bbox.y1) / 2, h: h,
               c: typeof w.confidence === "number" ? w.confidence : 0 });
    }
    W.sort(function (a, b) { return a.cy - b.cy || a.x0 - b.x0; });
    var rows = [];
    for (i = 0; i < W.length; i++) {
      var r = rows[rows.length - 1];
      if (r && Math.abs(W[i].cy - r.cy) < Math.max(W[i].h, r.h) * 0.6) {
        r.ws.push(W[i]);
        r.cy = (r.cy * r.n + W[i].cy) / (r.n + 1);
        r.n++;
        r.h = Math.max(r.h, W[i].h);
      } else {
        rows.push({ cy: W[i].cy, h: W[i].h, n: 1, ws: [W[i]] });
      }
    }
    for (i = 0; i < rows.length; i++) {
      rows[i].ws.sort(function (a, b) { return a.x0 - b.x0; });
    }
    return rows;
  }

  function isLabel(t) {
    for (var i = 0; i < WORD_LABELS.length; i++) {
      if (WORD_LABELS[i][1].test(t)) return true;
    }
    return false;
  }

  function fieldsFromWords(words) {
    var rows = wordRows(words), out = {};
    for (var i = 0; i < rows.length; i++) {
      var ws = rows[i].ws;
      for (var j = 0; j < ws.length; j++) {
        for (var k = 0; k < WORD_LABELS.length; k++) {
          var key = WORD_LABELS[k][0];
          if (out[key] || !WORD_LABELS[k][1].test(ws[j].t)) continue;
          var vals = [], conf = 0, n = 0;
          for (var m = j + 1; m < ws.length; m++) {
            if (isLabel(ws[m].t)) break;
            vals.push(ws[m].t);
            conf += ws[m].c; n++;
          }
          var v = vals.join(" ").trim();
          if (v) out[key] = { text: v, conf: n ? conf / n : 0 };
        }
      }
    }
    return out;
  }

  // 'NAME : 양한규' 에서 이름만. 한글이 이어진 가장 긴 토막을 씁니다.
  function nameFromValue(v) {
    // 기록증은 이름도 글자 사이를 벌려 놓는 일이 많고, 낱말 상자도 글자별로
    // 쪼개져 나옵니다 ('왔 한 규'). 한글끼리는 먼저 붙여 놓고 봅니다.
    var t = String(v || "").replace(/([가-힣])[\s.·]+(?=[가-힣])/g, "$1");
    var runs = t.match(/[가-힣]{2,6}/g);
    if (!runs) return null;
    runs.sort(function (a, b) { return b.length - a.length; });
    var n = runs[0];
    // '성명'·'이름' 같은 이름표가 값 쪽으로 넘어온 경우는 버립니다
    if (/^(성명|이름|참가자|선수명)$/.test(n)) return null;
    return n.length >= 2 && n.length <= 5 ? n : null;
  }

  // OCR 이 가운뎃점을 자주 흘립니다 ('0348:56.24' → '03:48:56').
  function repairClock(v) {
    var t = String(v || "").replace(/[^0-9:.]/g, " ");
    var m = t.match(/\b(\d{1,2}):([0-5]\d):([0-5]\d)\b/);
    if (m) return m[1] + ":" + m[2] + ":" + m[3];
    m = t.match(/\b(\d{2})(\d{2}):([0-5]\d)\b/);          // 0348:56
    if (m && +m[2] < 60) return m[1] + ":" + m[2] + ":" + m[3];
    m = t.match(/\b(\d{1,2}):([0-5]\d)(\d{2})\b/);         // 3:4856
    if (m && +m[3] < 60) return m[1] + ":" + m[2] + ":" + m[3];
    m = t.match(/\b(\d{2})(\d{2})(\d{2})\b/);              // 034856
    if (m && +m[2] < 60 && +m[3] < 60) return m[1] + ":" + m[2] + ":" + m[3];
    m = t.match(/\b(\d{1,2}):([0-5]\d)\b/);
    if (m) return m[1] + ":" + m[2];
    return null;
  }

  function parseFields(text) {
    var t = String(text || "");
    var flat = t.replace(/\s+/g, " ");
    // OCR 이 숫자를 글자로 잘못 읽는 일이 잦습니다 (0→O, 1→I·l, 5→S, 8→B).
    // 단위(km) 바로 앞에서는 숫자일 수밖에 없으니 그 자리만 되돌립니다.
    flat = flat.replace(/([0-9OIlSB]{1,4})\s*(km|KM|Km|킬로)/g, function (_, d, u) {
      return d.replace(/O/g, "0").replace(/[Il]/g, "1")
              .replace(/S/g, "5").replace(/B/g, "8") + u;
    });
    var out = {};

    // 시간: 1:23:45 / 01:23:45 / 23:45 (분:초만 있는 경우도 있습니다)
    var times = [];
    var re = /\b(\d{1,2}):([0-5]\d)(?::([0-5]\d))?(\.\d+)?/g, m;
    while ((m = re.exec(flat))) {
      var h, mi, se;
      if (m[3] !== undefined) { h = +m[1]; mi = +m[2]; se = +m[3]; }
      else { h = 0; mi = +m[1]; se = +m[2]; }
      var sec = h * 3600 + mi * 60 + se;
      if (sec < 60 || sec > 15 * 3600) continue;          // 터무니없는 값은 버립니다
      times.push({
        text: (m[3] !== undefined ? m[1] + ":" + m[2] + ":" + m[3] : m[1] + ":" + m[2]),
        sec: sec, at: m.index, frac: !!m[4]
      });
    }

    // 한글 단위로 적힌 기록 — '00 시간 53 분 31 초' / '53분 31초'
    // 오래된 기록증에 흔하고, OCR 이 '초' 를 엉뚱한 글자로 읽는 일이 잦아
    // 초 단위는 없어도 되게 두었습니다.
    var kre = /(?:(\d{1,2})\s*시\s*간?\s*)?(\d{1,3})\s*분\s*(\d{1,2})?(?!\s*\d)/g, km2;
    while ((km2 = kre.exec(flat))) {
      // '시간' 없이 분만 적혀 있는데 10분 미만이면 기록이 아니라 페이스입니다
      // ('5분 09초/km'). 완주 기록이 10분 아래로 내려가는 경우는 없습니다.
      if (km2[1] === undefined && (+km2[2] < 10 || +km2[2] > 180)) continue;
      var ks = (+(km2[1] || 0)) * 3600 + (+km2[2]) * 60 + (+(km2[3] || 0));
      if (ks < 60 || ks > 15 * 3600) continue;
      times.push({ text: clock(ks), sec: ks, at: km2.index, korean: true });
    }

    times.sort(function (a, b) { return a.at - b.at; });
    out.times = times;

    // 이름표 붙이기.
    // 한 줄에 여러 시간이 늘어서 있는 기록증이 많아서(GROSS 3:52:10 NET 3:50:22)
    // 주변에 그 낱말이 '있는지' 가 아니라 '가장 가까운 이름표가 무엇인지' 로 고릅니다.
    var LABELS = [
      ["split", /지\s*점|구\s*간|중간|split|lap|랩|반환/gi],
      ["net",   /순기록|실기록|net|넷/gi],
      ["gross", /총기록|총시간|gross|그로스/gi],
      ["pace",  /pace|페이스/gi],
      ["record",/기\s*록|record/gi]
    ];
    times.forEach(function (x) {
      var before = flat.slice(Math.max(0, x.at - 30), x.at);

      // 구간기록은 바로 앞에 거리가 적혀 있습니다 — '(4.7km지점 : 00:25:30.03)'.
      // OCR 이 '지점' 을 '# 3' 처럼 엉뚱하게 읽어도 걸리도록 느슨하게 둡니다.
      //
      // 소수점(0.01초)이 붙었다는 것만으로는 구간기록이라고 볼 수 없습니다.
      // 양양 Yrun 기록증은 완주기록 자체가 01:30:26.19 로 적혀 있었고,
      // 소수점을 구간기록 표시로 삼았더니 완주 시간을 통째로 버렸습니다.
      if (/\d(?:\.\d+)?\s*(?:km|k)\b[^a-zA-Z가-힣]{0,10}$/i.test(before)) {
        x.kind = "split";
        return;
      }

      var best = null, j, mm, rx;
      for (j = 0; j < LABELS.length; j++) {
        rx = LABELS[j][1]; rx.lastIndex = 0;
        while ((mm = rx.exec(before))) {
          var end = mm.index + mm[0].length;
          if (!best || end > best.end) best = { kind: LABELS[j][0], end: end };
        }
      }
      if (!best) return;
      if (best.kind === "record") { x.labelled = true; return; }
      // 페이스는 분:초 단위라 15분을 넘지 않습니다. 길이로 한 번 더 거릅니다.
      if (best.kind === "pace" && x.sec >= 900) return;
      x.kind = best.kind;
    });

    // 날짜: 2026.10.19 / 2026-10-19 / 2026년 10월 19일
    var d = flat.match(/\b(20\d\d)\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})\b/);
    if (d) {
      out.date = d[1] + "-" + ("0" + d[2]).slice(-2) + "-" + ("0" + d[3]).slice(-2);
    } else {
      // 'October 16, 2005' — 한글 년·월·일이 뭉개져도 영문 줄이 남아 있는 일이 많습니다.
      var MON = ["january","february","march","april","may","june",
                 "july","august","september","october","november","december"];
      var e = flat.match(/\b([A-Za-z]{3,9})\.?\s+(\d{1,2})\s*,?\s*(20\d\d)\b/);
      if (e) {
        var mi2 = -1;
        for (var q = 0; q < 12; q++) {
          if (MON[q].indexOf(e[1].toLowerCase()) === 0 && e[1].length >= 3) { mi2 = q + 1; break; }
        }
        if (mi2 > 0 && +e[2] >= 1 && +e[2] <= 31) {
          out.date = e[3] + "-" + ("0" + mi2).slice(-2) + "-" + ("0" + e[2]).slice(-2);
        }
      }
    }

    // 거리
    // 'MARATHON' 은 거의 모든 대회 이름에 들어가므로 거리 판단에 쓰면 안 됩니다.
    // (예: 'JTBC SEOUL MARATHON 2026 HALF' 가 풀코스로 잡혔습니다)
    // 'MARATHON' 과 달리 'FULL' 은 홀로 쓰여도 풀코스를 뜻합니다.
    // 다만 'FULL NAME' 은 이름 칸이라 빼 둡니다.
    // 기록증 아래쪽에 그 대회의 전 종목을 늘어놓는 일이 많습니다
    // ('종목 : 풀코스, 하프코스, 10km코스, 5km코스'). 아무 데나 적힌 '하프'를
    // 집으면 10km 를 뛴 사람이 하프로 잡히니, 이름표가 붙은 '값' 을 먼저 봅니다.
    // 이름표가 여러 번 나오면(칸 하나 + 아래쪽 안내 줄) 쓸 만한 첫 값을 씁니다
    var lre = /(?:종\s*목|부\s*문|구\s*분|course|division)\s*(?:\([^)]{0,14}\))?\s*[:：.·\-]?\s*([^\n]{0,16})/gi;
    var lm, picked = null;
    while (!picked && (lm = lre.exec(flat))) picked = courseOf(lm[1]);
    out.km = picked || courseOf(flat) || undefined;
    if (out.km === undefined) {
      // '부문 (Division): 10km 코스' 처럼 이름표가 붙은 거리를 먼저 봅니다.
      var kre2 = /(\d{1,3}(?:\.\d+)?)\s*(?:km|킬로|k(?![a-z]))/gi, km3, best = null;
      while ((km3 = kre2.exec(flat))) {
        var v = parseFloat(km3[1]);
        if (!(v > 0 && v <= 100)) continue;
        var pre = flat.slice(Math.max(0, km3.index - 30), km3.index);
        var post = flat.slice(km3.index + km3[0].length, km3.index + km3[0].length + 8);
        // 구간 거리(4.7km지점)는 종목이 아닙니다.
        if (/지\s*점|구\s*간|중간|split|반환/.test(post)) continue;
        var score = /부\s*문|종\s*목|코\s*스|course|division|event|구\s*분/i.test(pre) ? 2 : 1;
        if (!best || score > best.score) best = { v: v, score: score };
      }
      if (best) out.km = String(best.v);
    }
    if (!out.km) delete out.km;

    // 이름 — 폼을 대신 채워 주려고 읽습니다. 어디로도 보내지 않습니다.
    var nm = flat.match(
      /(?:성\s*명|이\s*름|참\s*가\s*자|\bname\b)\s*(?:\([^)]{0,10}\))?\s*[:：.·]?\s*([가-힣]{2,5})(?![가-힣])/i);
    if (nm) out.name = nm[1];

    // 배번 (사진 찾을 때 쓰입니다)
    var b = flat.match(/(?:배번|번호|bib|no\.?)\s*[:#]?\s*(\d{1,6})\b/i);
    if (b) out.bib = b[1];

    // 순위: '종합 123위' / '123 / 4,567'
    // 순위도 천 단위 쉼표가 들어갑니다 ('종합 1,204위')
    var r = flat.match(/(?:종합|전체|overall|rank)\s*[:#]?\s*([\d,]{1,9})\s*위?/i);
    if (r) out.rank = r[1].replace(/,/g, "");
    var rt = flat.match(/\b([\d,]{1,9})\s*\/\s*([\d,]{2,9})\b/);
    if (rt) {
      var mine = rt[1].replace(/,/g, ""), all = rt[2].replace(/,/g, "");
      // 순위가 참가자 수보다 많을 수는 없습니다
      if (+mine > 0 && +all > 0 && +mine <= +all) {
        out.rank = out.rank || mine;
        out.rankTotal = all;
      }
    }

    // 성별 — 기록증에 부문이 적혀 있을 때만. 추측하지 않습니다.
    if (/남자부|남성부|\bmale\b|\bM\s*부/i.test(flat) && !/여자부|female/i.test(flat)) out.gender = "male";
    else if (/여자부|여성부|\bfemale\b/i.test(flat)) out.gender = "female";

    return out;
  }

  // 완주 시간을 건졌는지 — 구간기록·페이스는 빼고 봅니다
  function hasFinish(f) {
    return (f.times || []).some(function (x) {
      return x.kind !== "split" && x.kind !== "pace" &&
             (x.labelled || x.kind === "net" || x.sec >= 600);
    });
  }

  // 어느 쪽이 더 많이 읽혔는지 견주는 점수
  function score(f) {
    return (hasFinish(f) ? 4 : 0) + (f.km ? 2 : 0) + (f.date ? 1 : 0) +
           ((f.times || []).length ? 1 : 0);
  }

  function readCertificate(img, onStep) {
    var prep = toGray(img, 1100);
    var ink = adaptiveInk(prep.gray, prep.w, prep.h, 31, 10);
    var rows = textRows(ink, prep.w, prep.h);
    // 완주 시간은 보통 가장 큰 글씨 → 높이 내림차순으로 훑는다
    rows.sort(function (p, q) { return (q[1] - q[0]) - (p[1] - p[0]); });

    return loadTesseract().then(function (T) {
      var result = { bigTime: null, fields: {}, race: null, raw: "", raceDone: false };

      // --- A. 숫자만: 큰 글씨에서 완주 시간
      onStep("완주 시간을 찾는 중…");
      return T.createWorker("eng").then(function (worker) {
        return worker.setParameters({
          tessedit_pageseg_mode: "7",
          tessedit_char_whitelist: "0123456789:"
        }).then(function () {
          var i = 0;
          function step() {
            if (i >= Math.min(rows.length, 8)) return Promise.resolve(null);
            var rc = rowCanvas(prep.gray, prep.w, prep.h, rows[i][0], rows[i][1]);
            i++;
            return worker.recognize(rc).then(function (res) {
              var mm = (res.data.text || "").match(/\b\d{1,2}:[0-5]\d:[0-5]\d\b/);
              return mm ? mm[0] : step();
            });
          }
          return step();
        }).then(function (t) {
          result.bigTime = t;
          return worker.terminate();
        });
      }).then(function () {
        // --- B. 한글+영문 전체 읽기
        onStep("대회명과 나머지 정보를 읽는 중… (처음 한 번은 한글 데이터를 내려받습니다)");
        // 기록증 칸의 글씨는 작습니다. 키워 놓아야 '종 목 : 풀' 같은 줄이 읽힙니다.
        // (너무 커지지 않게 fitScale 이 넓이 상한을 걸어 둡니다)
        var canvas = fullCanvas(img, 2400);

        var wordsOf = {};
        function readFull(psm) {
          return T.createWorker("kor+eng").then(function (worker) {
            return worker.setParameters({ tessedit_pageseg_mode: psm })
              .then(function () { return worker.recognize(canvas); })
              .then(function (res) {
                var txt = (res.data && res.data.text) || "";
                wordsOf[psm] = (res.data && res.data.words) || [];
                return worker.terminate().then(function () { return txt; });
              });
          });
        }

        // 기록증은 테두리와 도장, 워터마크가 많습니다. 단을 나눠 읽는 모드(3)가
        // 이걸 단 경계로 잘못 보고 '기록 (Record): 00 시간 53 분 31 초' 줄을
        // 통째로 흘리는 일이 있었습니다. 한 덩어리로 읽는 모드(6)를 먼저 씁니다.
        // 대회 이름은 꾸민 글씨라 전체 읽기로는 거의 안 잡힙니다.
        // 위쪽 띠만 크게 잘라 한 번 더 읽습니다 (1초 남짓).
        function readTitle() {
          return T.createWorker("kor+eng").then(function (worker) {
            return worker.setParameters({ tessedit_pageseg_mode: "6" })
              .then(function () { return worker.recognize(titleCanvas(img)); })
              .then(function (res) {
                var txt = (res.data && res.data.text) || "";
                return worker.terminate().then(function () { return txt; });
              });
          }).catch(function () { return ""; });
        }

        return readTitle().then(function (tt) {
          result.titleText = tt;
          return readFull("6");
        }).then(function (t6) {
          var f6 = parseFields(t6);
          var tt = result.titleText || "";
          // 띠에서 읽은 글자로도 대회를 찾아 보고, 더 또렷한 쪽을 씁니다
          var rT = matchRace(tt, f6.date);
          var r6 = matchRace(t6, f6.date);
          if (rT && (!r6 || rT.score > r6.score)) r6 = rT;
          // 대회 이름은 꾸민 글씨나 로고로 박혀 있어 한 모드에서만 또렷하게
          // 읽히는 일이 많습니다. 비슷해 보이는 정도로만 걸렸으면 다른 모드로
          // 한 번 더 봅니다. (아예 안 걸렸으면 목록에 없는 대회이니 넘어갑니다)
          var thin = !hasFinish(f6) || !f6.km || (r6 && !r6.exact);
          if (!thin) {
            result.raw = t6; result.fields = f6; result.words = wordsOf["6"];
            result.race = r6; result.raceDone = true; return null;
          }
          return readFull("3").then(function (t3) {
            var f3 = parseFields(t3);
            var r3 = matchRace(t3, f3.date);
            if (score(f3) > score(f6)) { result.raw = t3; result.fields = f3; result.words = wordsOf["3"]; }
            else { result.raw = t6; result.fields = f6; result.words = wordsOf["6"]; }
            // 대회는 따로 고릅니다 — 더 또렷하게 걸린 쪽
            result.race = (r3 && (!r6 || r3.score > r6.score)) ? r3 : r6;
            result.raceDone = true;
          }).catch(function () {
            result.raw = t6; result.fields = f6; result.words = wordsOf["6"];
            result.race = r6; result.raceDone = true;
          });
        });
      }).catch(function () {
        // 한글 데이터를 못 받아도 시간은 이미 찾았으니 계속 갑니다
        return null;
      }).then(function () {
        if (!result.fields || !result.fields.times) result.fields = parseFields(result.raw);

        // 낱말 상자로 읽은 칸 값이 있으면 그쪽을 믿습니다.
        // 이름표 바로 옆에 놓인 값이라 글자를 이어 붙여 찾은 것보다 확실합니다.
        var fw = fieldsFromWords(result.words || []);
        var F = result.fields;
        if (fw.course) {
          var km = courseOf(fw.course.text);
          if (km) { F.km = km; F.kmSure = true; }
        }
        if (fw.record) {
          var rc = repairClock(fw.record.text);
          if (rc) { F.boxTime = rc; F.boxTimeConf = fw.record.conf; }
        }
        if (fw.name) {
          var nm2 = nameFromValue(fw.name.text);
          if (nm2) { F.name = nm2; F.nameSure = fw.name.conf >= 55; }
        }
        if (fw.bib) {
          var bb = (fw.bib.text.match(/\d{1,6}/) || [])[0];
          if (bb) F.bib = bb;
        }
        if (!result.raceDone) result.race = matchRace(result.raw, result.fields.date);
        // 목록에 없는 대회 — 오래된 기록증이면 흔한 일입니다.
        // 그래도 칸을 비워 두지 않고, 읽은 글자를 그대로 넣어 줍니다.
        if (!result.race) {
          var g = titleGuess(result.titleText) || titleGuess(result.raw);
          if (g) result.raceText = g;
        }
        return result;
      });
    });
  }

  // ---- 읽어낸 것을 폼에 채우고, 무엇을 읽었는지 보여 준다
  function applyResult(r) {
    var f = r.fields || {};
    var got = [];

    // 완주 시간 고르는 순서:
    //   '기록 (Record):' 이름표가 붙은 것 > 넷타임 > 큰 글씨 > 가장 긴 시간
    // 큰 글씨를 맨 앞에 두었더니 '(4.7km지점 : 00:25:30.03)' 같은 구간기록을
    // 완주 시간으로 집어 오는 일이 있었습니다. 이름표가 큰 글씨보다 믿을 만합니다.
    var all = f.times || [];
    var ok = all.filter(function (x) { return x.kind !== "split" && x.kind !== "pace"; });

    // 큰 글씨로 읽은 값이 구간기록으로 판명났다면 쓰지 않습니다.
    var big = r.bigTime;
    if (big) {
      var bigSec = (function (t) {
        var q = String(t).split(":").map(Number);
        return q.length === 3 ? q[0] * 3600 + q[1] * 60 + q[2] : q[0] * 60 + q[1];
      })(big);
      var bad = all.some(function (x) { return x.kind === "split" && x.sec === bigSec; });
      if (bad) big = null;
    }

    // 이름표 바로 옆 상자에서 읽은 값 > 글자 속에서 이름표가 붙은 값 >
    // 넷타임 > 큰 글씨 > 가장 긴 시간
    var time = f.boxTime ||
               (ok.filter(function (x) { return x.labelled; })[0] || {}).text ||
               (ok.filter(function (x) { return x.kind === "net"; })[0] || {}).text ||
               big || null;
    if (!time) {
      var cands = ok.filter(function (x) { return x.sec >= 600; });
      cands.sort(function (a, b) { return b.sec - a.sec; });
      if (cands[0]) time = cands[0].text;
    }
    if (time) {
      if (/^\d{1,2}:\d{2}$/.test(time)) time = "0:" + time;
      timeInput.value = time;
      got.push("완주 시간 " + time);
    }

    // 대회명 — 목록과 대조해서 고른 것
    if (r.race) {
      raceInput.value = r.race.name;
      got.push("대회 " + r.race.name + (r.race.exact ? "" : " (맞는지 봐 주세요)"));
      if (typeof onRacePicked === "function") onRacePicked();
    } else if (r.raceText) {
      // 목록에 없는 대회입니다. 읽은 그대로 넣어 두었으니 고쳐 쓰시면 됩니다.
      raceInput.value = r.raceText;
      got.push("대회 " + r.raceText + " (읽은 그대로예요 — 고쳐 주세요)");
    }

    // 이름 — 읽어서 칸만 채웁니다. 어디로도 보내지 않습니다.
    if (f.name && nameInput && !nameInput.value) {
      nameInput.value = f.name;
      got.push("이름 " + f.name + (f.nameSure === false ? " (흐릿해요 — 봐 주세요)" : ""));
    }

    // 거리 — 기록증에서 읽은 것을 우선, 없으면 대회 정보에서
    var km = f.km;
    if (km) {
      var opts = Array.prototype.map.call(distSel.options, function (o) { return o.value; });
      var pick = opts.filter(function (v) {
        return v && Math.abs(parseFloat(v) - parseFloat(km)) < 0.3;
      })[0];
      if (pick) { distSel.value = pick; got.push("거리 " + distLabel(parseFloat(pick))); }
    }

    // 성별 — 기록증에 부문이 적혀 있을 때만
    if (f.gender && genderSel) {
      genderSel.value = f.gender;
      got.push("부문 " + (f.gender === "male" ? "남자" : "여자"));
    }

    if (f.date) got.push("대회일 " + f.date);
    if (f.bib) got.push("배번 " + f.bib);
    if (f.rank) got.push("순위 " + f.rank + (f.rankTotal ? " / " + f.rankTotal : "") + "위");

    return got;
  }

  fileInput.addEventListener("change", function () {
    var f = fileInput.files && fileInput.files[0];
    if (!f) return;
    // 기록증을 새로 올렸으면 앞 사진에서 읽은 이름은 지웁니다.
    // (다른 사람의 기록증일 수도 있는데 앞 이름이 남아 있으면 안 됩니다)
    if (nameInput) nameInput.value = "";
    say("사진을 읽는 중…");
    var img = new Image();
    img.onload = function () {
      readCertificate(img, say).then(function (r) {
        showForm();
        var got = applyResult(r);
        if (got.length) {
          say("읽었습니다 — " + got.join(" · ") + ". 비어 있는 칸만 채워 주세요.");
        } else {
          say("자동으로 읽지 못했습니다. 아래에 직접 입력해 주세요.");
        }
        URL.revokeObjectURL(img.src);
      }).catch(function (e) {
        showForm();
        say((e && e.message ? e.message : "읽기에 실패했습니다") + ". 아래에 직접 입력해 주세요.");
      });
    };
    img.onerror = function () { showForm(); say("이미지를 열 수 없습니다. 아래에 직접 입력해 주세요."); };
    img.src = URL.createObjectURL(f);
  });

  // ---------- 4. 등급 계산 + 카드 ----------
  function buildResult() {
    var sec = G.parseTime(timeInput.value);
    var km = parseFloat(distSel.value);
    var gender = genderSel.value;
    var year = parseInt(yearInput.value, 10);
    if (!sec || !km || !year) return null;
    var age = new Date().getFullYear() - year;
    if (age < 5 || age > 100) return null;

    var tier = G.tierOf(sec, km, age, gender);
    var ra = G.runningAge(sec, km, gender);
    var ms = G.nextMilestone(sec, km);
    return {
      sec: sec, km: km, age: age, gender: gender, tier: tier,
      runningAge: ra, youngerBy: age - ra, milestone: ms,
      race: (raceInput.value || "").trim(),
    };
  }

  function distLabel(km) {
    if (Math.abs(km - 21.0975) < 0.01) return "하프";
    if (Math.abs(km - 42.195) < 0.01) return "풀코스";
    return km + "km";
  }

  function drawCard(r) {
    var ctx = canvas.getContext("2d");
    var W = canvas.width, H = canvas.height;
    ctx.fillStyle = "#0B0B0B";
    ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = "#FF3D1A";
    ctx.fillRect(0, 0, W, 10);

    var pad = 90;
    ctx.textAlign = "left";

    ctx.fillStyle = "#8E8884";
    ctx.font = "400 34px 'Noto Sans KR', sans-serif";
    var head = [r.race || "내 기록", distLabel(r.km)].filter(Boolean).join(" · ");
    ctx.fillText(head, pad, 150);

    ctx.fillStyle = "#FFFFFF";
    ctx.font = "900 150px 'Noto Sans KR', sans-serif";
    ctx.fillText(G.formatTime(r.sec), pad, 300);

    // 헤드라인은 "사실 중에 가장 유리한 것"을 고른다.
    // 러닝 나이는 실제보다 10살 이상 젊을 때만 쓴다 (빠른 기록은 20세에서
    // 포화되고, 느린 젊은 러너에게는 역효과이기 때문).
    var y = 470;
    if (r.youngerBy >= 10) {
      ctx.fillStyle = "#8E8884";
      ctx.font = "700 40px 'Noto Sans KR', sans-serif";
      ctx.fillText("러닝 나이", pad, y);
      ctx.fillStyle = "#FF3D1A";
      ctx.font = "900 190px 'Noto Sans KR', sans-serif";
      ctx.fillText(r.runningAge + "세", pad, y + 170);
      ctx.fillStyle = "#E8E4E1";
      ctx.font = "700 44px 'Noto Sans KR', sans-serif";
      ctx.fillText("실제 " + r.age + "세 · 또래보다 " + r.youngerBy + "살 젊은 몸", pad, y + 250);
      y += 340;
    } else {
      ctx.fillStyle = "#8E8884";
      ctx.font = "700 40px 'Noto Sans KR', sans-serif";
      ctx.fillText(Math.floor(r.age / 10) * 10 + "대 " + (r.gender === "male" ? "남성" : "여성") + " 기준", pad, y);
      ctx.fillStyle = "#FF3D1A";
      ctx.font = "900 118px 'Noto Sans KR', sans-serif";
      ctx.fillText(r.tier, pad, y + 120);
      y += 210;
    }

    if (r.youngerBy >= 10) {
      ctx.fillStyle = "#8E8884";
      ctx.font = "400 38px 'Noto Sans KR', sans-serif";
      ctx.fillText(Math.floor(r.age / 10) * 10 + "대 기준 " + r.tier, pad, y);
      y += 80;
    }

    if (r.milestone) {
      ctx.fillStyle = "#141110";
      ctx.fillRect(pad - 30, y, W - (pad - 30) * 2, 220);
      ctx.fillStyle = "#8E8884";
      ctx.font = "400 36px 'Noto Sans KR', sans-serif";
      ctx.fillText("다음 목표", pad, y + 70);
      ctx.fillStyle = "#FFFFFF";
      ctx.font = "900 62px 'Noto Sans KR', sans-serif";
      ctx.fillText(G.formatTime(r.milestone.targetSeconds) + "까지 " +
                   G.formatTime(r.milestone.gapSeconds), pad, y + 145);
      ctx.fillStyle = "#B8B0AC";
      ctx.font = "400 36px 'Noto Sans KR', sans-serif";
      ctx.fillText("1km당 " + r.milestone.perKmSeconds.toFixed(1) + "초만 줄이면 됩니다", pad, y + 198);
    }

    ctx.fillStyle = "#6A6A6A";
    ctx.font = "400 32px 'Noto Sans KR', sans-serif";
    ctx.fillText("나이·성별 보정 기준 · calrank 자체 지표", pad, H - 110);
    ctx.fillStyle = "#FF3D1A";
    ctx.font = "900 40px 'Noto Sans KR', sans-serif";
    ctx.fillText("calrank.vercel.app", pad, H - 55);
  }

  formEl.addEventListener("submit", function (e) {
    e.preventDefault();
    var r = buildResult();
    if (!r) { say("완주기록과 출생연도를 확인해 주세요."); return; }
    say("");
    var go = function () { drawCard(r); cardWrap.classList.add("on");
      // 카드를 본 다음에 통계 동의를 묻습니다. 자기 결과를 보고 납득한
      // 뒤라야 무엇을 보태는 것인지 알고 고를 수 있습니다.
      if (typeof refreshGive === "function") refreshGive();
      cardWrap.scrollIntoView({ behavior: "smooth", block: "nearest" }); };
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(go);
    else go();
  });

  function canvasBlob() {
    return new Promise(function (res) { canvas.toBlob(res, "image/png"); });
  }

  document.getElementById("ctSave").addEventListener("click", function () {
    canvasBlob().then(function (b) {
      var a = document.createElement("a");
      a.href = URL.createObjectURL(b);
      a.download = "calrank-record.png";
      a.click();
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
    });
  });

  document.getElementById("ctShare").addEventListener("click", function () {
    canvasBlob().then(function (b) {
      var file = new File([b], "calrank-record.png", { type: "image/png" });
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        navigator.share({ files: [file], title: "내 러닝 등급",
          text: "calrank에서 확인한 내 기록 등급" }).catch(function () {});
      } else {
        say("이 브라우저는 공유를 지원하지 않습니다. '이미지 저장'을 눌러 주세요.");
      }
    });
  });

  // ---------- 5. 동의받은 기록만 통계로 보내기 ----------
  //
  // 왜 이걸 모으는가
  //   "내 기록이 상위 몇 %인가" 는 가장 많이 받는 질문인데, 한국 러너의
  //   기록 분포가 없으면 답할 수 없습니다. 타이밍 업체가 공개한 결과는
  //   실명·배번이 함께 있는 개인정보라 가져오지 않기로 했습니다.
  //   남은 길은 본인이 직접 보태 주는 것뿐입니다.
  //
  // 무엇을 보내지 않는가
  //   이름, 배번, 기록증 사진, 정확한 생년, 대회 순위, 계정 식별자.
  //   사진은 브라우저 밖으로 나가지 않습니다. 여기서 보내는 것은
  //   화면에 떠 있는 값, 즉 사용자가 눈으로 확인한 값뿐입니다.
  //
  //   계정 식별자를 일부러 빼서 누가 보냈는지 알 수 없게 했습니다.
  //   그래서 개별 삭제가 불가능하고, 그 사실을 동의 화면에 먼저 적어
  //   두었습니다. 알려 주고 받는 동의라야 동의입니다.

  var SB_URL = "https://mlbzsqeoqlyvnyzeegeu.supabase.co";
  var SB_KEY = "sb_publishable_byKae86vGA0M5NjoZC0ELw_NMkm8ObR";
  var giveBox = document.getElementById("ctGive");
  var consentCk = document.getElementById("ctConsent");
  var giveBtn = document.getElementById("ctGiveBtn");
  var giveMsg = document.getElementById("ctGiveMsg");

  function ageBand(age) {
    if (age >= 80) return "80대 이상";
    if (age < 10) return null;                   // 통계 구간 밖
    return (Math.floor(age / 10) * 10) + "대";
  }

  function distCategory(km) {
    if (Math.abs(km - 5) < 0.3) return "5km";
    if (Math.abs(km - 10) < 0.3) return "10km";
    if (Math.abs(km - 21.0975) < 0.3) return "half";
    if (Math.abs(km - 42.195) < 0.4) return "full";
    return null;
  }

  // 같은 기록을 두 번 보내지 않도록 하는 가벼운 장치입니다.
  // 브라우저를 바꾸면 뚫리지만, 실수로 두 번 누르는 것은 막아 줍니다.
  function giveKey(row) {
    return "crGave:" + [row.race_name, row.distance_category,
                        row.finish_time_seconds, row.age_band, row.gender].join("|");
  }

  function buildRow() {
    var d = buildResult();
    if (!d) return null;
    var cat = distCategory(d.km);
    var band = ageBand(d.age);
    if (!cat || !band) return null;
    if (d.sec < 300 || d.sec > 54000) return null;     // 서버 제약과 같은 범위
    var race = (raceInput.value || "").trim();
    if (!race || race.length > 120) return null;
    var row = {
      race_name: race,
      sport: "marathon",
      distance_category: cat,
      finish_time_seconds: Math.round(d.sec),
      age_band: band,
      gender: d.gender,
      source: "cert"
    };
    // 대회를 목록에서 고른 경우에만 날짜를 함께 보냅니다.
    // 직접 적은 이름은 어느 해 대회인지 알 수 없어 추측하지 않습니다.
    if (raceMap) {
      var ev = raceMap.get(race);
      if (ev && ev.date) row.race_date = String(ev.date).slice(0, 10);
    }
    return row;
  }

  function refreshGive() {
    if (!giveBox) return;
    var row = buildRow();
    if (!row) { giveBox.hidden = true; return; }
    var done = false;
    try { done = !!localStorage.getItem(giveKey(row)); } catch (e) {}
    if (done) {
      giveBox.hidden = false;
      if (consentCk) { consentCk.checked = true; consentCk.disabled = true; }
      if (giveBtn) { giveBtn.disabled = true; giveBtn.textContent = "보태 주셔서 고맙습니다"; }
      if (giveMsg) giveMsg.textContent = "이 기록은 이미 통계에 들어갔습니다.";
      return;
    }
    giveBox.hidden = false;
  }

  if (consentCk && giveBtn) {
    consentCk.addEventListener("change", function () {
      giveBtn.disabled = !consentCk.checked;
    });

    giveBtn.addEventListener("click", function () {
      var row = buildRow();
      if (!row) { giveMsg.textContent = "값을 다시 확인해 주세요."; return; }
      if (!window.supabase) { giveMsg.textContent = "지금은 보낼 수 없습니다. 잠시 뒤 다시 시도해 주세요."; return; }
      giveBtn.disabled = true;
      giveBtn.textContent = "보내는 중…";
      try {
        var sb = window.supabase.createClient(SB_URL, SB_KEY);
        sb.from("record_stats").insert(row).then(function (res) {
          if (res && res.error) {
            giveBtn.textContent = "통계에 보태기";
            giveBtn.disabled = false;
            giveMsg.textContent = "보내지 못했습니다. 잠시 뒤 다시 시도해 주세요.";
            return;
          }
          try { localStorage.setItem(giveKey(row), "1"); } catch (e) {}
          giveBtn.textContent = "보태 주셔서 고맙습니다";
          consentCk.disabled = true;
          giveMsg.textContent = "고맙습니다. 표본이 쌓이면 같은 나이·성별 안에서 내 위치를 보여 드릴 수 있습니다.";
        });
      } catch (e) {
        giveBtn.textContent = "통계에 보태기";
        giveBtn.disabled = false;
        giveMsg.textContent = "보내지 못했습니다.";
      }
    });
  }

})();
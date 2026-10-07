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
  function toGray(img, maxW) {
    var scale = Math.min(1, maxW / img.width);
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

  function readCertificate(img) {
    var prep = toGray(img, 1100);
    var ink = adaptiveInk(prep.gray, prep.w, prep.h, 31, 10);
    var rows = textRows(ink, prep.w, prep.h);
    // 완주 시간은 보통 가장 큰 글씨 → 높이 내림차순으로 훑는다
    rows.sort(function (p, q) { return (q[1] - q[0]) - (p[1] - p[0]); });

    return loadTesseract().then(function (T) {
      return T.createWorker("eng").then(function (worker) {
        var time = null, dist = null;

        function pass(list, params, matcher, limit) {
          return worker.setParameters(params).then(function () {
            var i = 0;
            function step() {
              if (i >= Math.min(list.length, limit)) return Promise.resolve(null);
              var rc = rowCanvas(prep.gray, prep.w, prep.h, list[i][0], list[i][1]);
              i++;
              return worker.recognize(rc).then(function (res) {
                var hit = matcher(res.data.text || "");
                return hit || step();
              });
            }
            return step();
          });
        }

        return pass(rows, { tessedit_pageseg_mode: "7", tessedit_char_whitelist: "0123456789:" },
          function (t) { var m = t.match(/\b\d{1,2}:\d{2}:\d{2}\b/); return m ? m[0] : null; }, 8)
          .then(function (t) {
            time = t;
            return pass(rows, { tessedit_pageseg_mode: "7", tessedit_char_whitelist: "" },
              function (s) {
                var m = s.match(/\b(\d{1,2})\s*[kK][mM]\b/);
                if (m) return m[1];
                if (/half|하프/i.test(s)) return "21.0975";
                return null;
              }, 12);
          })
          .then(function (d) { dist = d; return worker.terminate(); })
          .then(function () { return { time: time, dist: dist }; });
      });
    });
  }

  fileInput.addEventListener("change", function () {
    var f = fileInput.files && fileInput.files[0];
    if (!f) return;
    say("사진을 읽는 중…");
    var img = new Image();
    img.onload = function () {
      say("기록을 찾는 중… (기기에서 처리됩니다)");
      readCertificate(img).then(function (r) {
        showForm();
        if (r.time) {
          timeInput.value = r.time;
          if (r.dist) {
            var map = { "5": "5", "10": "10", "21.0975": "21.0975", "42": "42.195" };
            if (map[r.dist]) distSel.value = map[r.dist];
          }
          say("완주 시간 " + r.time + " 을 찾았습니다. 대회와 나이만 채워 주세요.");
        } else {
          say("시간을 자동으로 읽지 못했습니다. 아래에 직접 입력해 주세요.");
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
})();

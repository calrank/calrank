// 칼랭크 기기 안 저장소 — 장비 서랍, 기록 이력, 예상 기록 노트가 같이 쓴다.
//
// 서버로 보내지 않는다. 브라우저 localStorage 에만 쓰고, 막혀 있으면(사생활 보호
// 창 등) 이 탭이 열려 있는 동안만 메모리에 둔다. 읽고 쓰는 곳을 한 군데로 모아
// 두면 "내 정보가 어디에 있나"를 한 파일로 설명할 수 있다.
//
// 저장하는 것
//   results  등급 계산 결과 (날짜, 거리, 기록, 나이, 성별, 연령등급 %)
//   kit      장비 서랍 (규정 항목별 내 수치)
//   seen     규정 값의 지문 (칼랭크의 규정 값이 바뀌었는지 알아보는 용도)
//   ledger   예상 기록 노트 (대회 전 예측과 대회 뒤 실제 기록)
(function (g) {
  "use strict";
  var KEY = "calrank.me.v1";
  var mem = {};
  var persistent = true;

  function read() {
    try {
      var raw = g.localStorage.getItem(KEY);
      var o = raw ? JSON.parse(raw) : {};
      return o && typeof o === "object" ? o : {};
    } catch (e) {
      persistent = false;
      return mem;
    }
  }

  function write(o) {
    mem = o;
    try {
      g.localStorage.setItem(KEY, JSON.stringify(o));
      return true;
    } catch (e) {
      persistent = false;
      return false;
    }
  }

  function update(fn) {
    var o = read();
    var r = fn(o);
    write(o);
    return r;
  }

  function today() {
    var d = new Date();
    var p = function (n) { return n < 10 ? "0" + n : "" + n; };
    return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate());
  }

  // ── 등급 계산 결과 ────────────────────────────────────────
  // 같은 날 같은 거리를 다시 계산하면 새로 쌓지 않고 덮어쓴다.
  function pushResult(r) {
    return update(function (o) {
      o.results = o.results || [];
      var rec = {
        t: today(), km: r.km, sec: Math.round(r.sec), age: r.age,
        gender: r.gender, pct: r.pct == null ? null : Math.round(r.pct * 10) / 10
      };
      var i = o.results.findIndex(function (x) { return x.t === rec.t && x.km === rec.km; });
      if (i >= 0) o.results[i] = rec; else o.results.push(rec);
      o.results = o.results.slice(-60);
      return rec;
    });
  }

  // 같은 거리의 이전 기록 중 가장 최근 것. 오늘 것은 제외한다.
  function lastResult(km) {
    var rs = (read().results || []).filter(function (x) { return x.km === km && x.t !== today(); });
    return rs.length ? rs[rs.length - 1] : null;
  }

  function results() { return (read().results || []).slice(); }

  // ── 장비 서랍 ────────────────────────────────────────────
  function kit() { return Object.assign({}, read().kit || {}); }
  function setKit(id, value) {
    update(function (o) {
      o.kit = o.kit || {};
      if (value === null || value === "" || isNaN(value)) delete o.kit[id];
      else o.kit[id] = value;
    });
  }

  // ── 규정 지문 ────────────────────────────────────────────
  // FNV-1a. 보안용이 아니라 "값이 달라졌나"만 본다.
  function fingerprint(text) {
    var h = 0x811c9dc5;
    for (var i = 0; i < text.length; i++) {
      h ^= text.charCodeAt(i);
      h = (h + ((h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24))) >>> 0;
    }
    return h.toString(16);
  }
  function seen() { return Object.assign({}, read().seen || {}); }
  function setSeen(map) {
    update(function (o) { o.seen = Object.assign(o.seen || {}, map); });
  }

  // ── 예상 기록 노트 ────────────────────────────────────────────
  function ledger() { return (read().ledger || []).slice(); }
  function addPrediction(p) {
    return update(function (o) {
      o.ledger = o.ledger || [];
      p.id = "p" + Date.now().toString(36);
      p.madeAt = today();
      o.ledger.push(p);
      return p;
    });
  }
  function settle(id, actualSec) {
    update(function (o) {
      (o.ledger || []).forEach(function (p) {
        if (p.id === id) { p.actualSec = Math.round(actualSec); p.settledAt = today(); }
      });
    });
  }
  function removePrediction(id) {
    update(function (o) { o.ledger = (o.ledger || []).filter(function (p) { return p.id !== id; }); });
  }

  function clearAll() {
    mem = {};
    try { g.localStorage.removeItem(KEY); } catch (e) {}
  }

  g.CalrankLocal = {
    pushResult: pushResult, lastResult: lastResult, results: results,
    kit: kit, setKit: setKit,
    fingerprint: fingerprint, seen: seen, setSeen: setSeen,
    ledger: ledger, addPrediction: addPrediction, settle: settle, removePrediction: removePrediction,
    clearAll: clearAll, today: today,
    isPersistent: function () { read(); return persistent; }
  };
})(typeof window !== "undefined" ? window : globalThis);

(function () {
  var SB = "https://mlbzsqeoqlyvnyzeegeu.supabase.co";
  var KEY = "sb_publishable_byKae86vGA0M5NjoZC0ELw_NMkm8ObR";
  var MIN = 5;
  var DIST = [["5km", "5km"], ["10km", "10km"], ["half", "하프"], ["full", "풀"]];
  var BANDS = ["10대", "20대", "30대", "40대", "50대", "60대", "70대", "80대 이상"];
  var H = { apikey: KEY, "Content-Type": "application/json" };
  function bar(n) {
    var pct = Math.min(100, Math.round(n / MIN * 100));
    return '<div class="dist-bar' + (n >= MIN ? " ok" : "") + '"><i style="width:' + pct + '%"></i><span>' + n + "/" + MIN + "</span></div>";
  }
  fetch(SB + "/rest/v1/rpc/record_stats_progress", { method: "POST", headers: H, body: "{}" })
    .then(function (r) { if (!r.ok) throw 0; return r.json(); })
    .then(function (rows) {
      var m = {}, tot = 0;
      rows.forEach(function (x) { m[x.distance_category + "|" + x.gender + "|" + x.age_band] = x.sample_count; tot += x.sample_count; });
      document.getElementById("distTotal").textContent = "지금까지 " + tot + "건이 모였습니다. 아직 중앙값을 공개할 만큼 찬 칸은 " +
        rows.filter(function (x) { return x.enough; }).length + "곳입니다.";
      document.getElementById("distGrid").innerHTML = DIST.map(function (d) {
        var h = '<section class="dist-sec"><h2>' + d[1] + '</h2><div class="dist-row dist-head"><span></span><span>남성</span><span>여성</span></div>';
        BANDS.forEach(function (b) {
          h += '<div class="dist-row"><span>' + b + "</span>" + bar(m[d[0] + "|male|" + b] || 0) + bar(m[d[0] + "|female|" + b] || 0) + "</div>";
        });
        return h + "</section>";
      }).join("");
    })
    .catch(function () { document.getElementById("distTotal").textContent = "지금은 불러오지 못했습니다. 잠시 뒤 다시 열어 주세요."; });
})();

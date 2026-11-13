// 다녀온 코스 카드: 내 목록의 '다녀온 곳'을 이미지 한 장으로 만든다. 이 기기 안에서만 그린다(서버로 보내지 않음).
// 색은 등급 카드와 같은 팔레트를 쓰고, 그림은 넣지 않는다(글자와 숫자만).
(function (g) {
  "use strict";
  var W = 1080, H = 1350, BG = "#0A0A0A", PANEL = "#141414", LINE = "rgba(255,255,255,.08)",
    ACCENT = "#FF3D1A", INK = "#FFFFFF", SOFT = "#C9C2BE", FAINT = "#7E7874";
  var KR = '"Noto Sans KR", "Apple SD Gothic Neo", "Malgun Gothic", sans-serif';

  function rr(c, x, y, w, h, r) {
    c.beginPath(); c.moveTo(x + r, y); c.arcTo(x + w, y, x + w, y + h, r); c.arcTo(x + w, y + h, x, y + h, r);
    c.arcTo(x, y + h, x, y, r); c.arcTo(x, y, x + w, y, r); c.closePath();
  }
  function fit(c, text, weight, px, maxW) {
    while (px > 22) { c.font = weight + " " + px + "px " + KR; if (c.measureText(text).width <= maxW) break; px -= 2; }
    return text;
  }

  function build(d) {
    var fonts = g.document && g.document.fonts && g.document.fonts.load ?
      Promise.all([g.document.fonts.load('700 40px "Noto Sans KR"'), g.document.fonts.load('900 40px "Noto Sans KR"')]).catch(function () {}) : Promise.resolve();
    return fonts.then(function () {
      var cv = document.createElement("canvas"); cv.width = W; cv.height = H;
      var c = cv.getContext("2d");
      c.fillStyle = BG; c.fillRect(0, 0, W, H);
      c.fillStyle = PANEL; rr(c, 40, 40, W - 80, H - 80, 28); c.fill();
      c.strokeStyle = LINE; c.lineWidth = 2; c.stroke();
      var L = 96, R = W - 96;
      c.textBaseline = "alphabetic";
      c.fillStyle = INK; c.font = "900 44px " + KR; c.textAlign = "left"; c.fillText("칼랭크", L, 150);
      c.fillStyle = FAINT; c.font = "700 26px " + KR; c.fillText("CALRANK · 트레일루트", L, 192);
      c.fillStyle = ACCENT; c.fillRect(L, 236, 64, 6);

      c.fillStyle = SOFT; c.font = "700 36px " + KR; c.fillText(d.title || "내가 다녀온 코스", L, 330);
      c.fillStyle = INK; c.font = "900 260px " + KR; c.fillText(String(d.n), L, 580);
      var nw = c.measureText(String(d.n)).width;
      c.fillStyle = SOFT; c.font = "700 64px " + KR; c.fillText(d.total ? "/ " + d.total + " 코스" : "곳", L + nw + 20, 580);

      var rows = [];
      if (d.km > 0) rows.push(["걸은 거리", d.km.toFixed(1) + " km"]);
      if (d.km > 0) rows.push(["누적 오르막", Math.round(d.gain).toLocaleString("ko-KR") + " m"]);
      var y = 700;
      rows.forEach(function (r) {
        c.fillStyle = FAINT; c.font = "700 30px " + KR; c.textAlign = "left"; c.fillText(r[0], L, y);
        c.fillStyle = INK; c.font = "900 64px " + KR; c.textAlign = "right"; c.fillText(r[1], R, y + 4);
        c.strokeStyle = LINE; c.beginPath(); c.moveTo(L, y + 34); c.lineTo(R, y + 34); c.stroke();
        y += 112;
      });
      c.textAlign = "left";
      y += 20;
      c.fillStyle = FAINT; c.font = "700 28px " + KR; c.fillText(d.total ? "다녀온 코스" : "최근 다녀온 곳", L, y); y += 22;
      d.names.slice(0, 4).forEach(function (nm) {
        y += 58; c.fillStyle = SOFT; fit(c, nm, "700", 36, R - L); c.fillText(nm, L, y);
      });

      c.fillStyle = FAINT; c.font = "700 28px " + KR; c.textAlign = "left"; c.fillText("calrank.vercel.app", L, H - 96);
      c.textAlign = "right"; c.fillText(d.date, R, H - 96);
      return new Promise(function (res) { cv.toBlob(function (b) { res(b); }, "image/png"); });
    });
  }
  g.CalrankTrailCard = { build: build };
})(window);

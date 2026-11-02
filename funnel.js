// 퍼널이 어디서 끊기는지 보려고 단계마다 한 번씩 찍는다.
//
// 왜 이렇게 하나
// --------------
// 재방문과 공유가 되는지 두 달째 이야기하면서, 정작 그걸 재는 게 하나도
// 없었다. 검색 지표만 측정되니 그쪽 이야기만 하게 됐다.
//
// Vercel Web Analytics 는 Hobby 플랜에서 커스텀 이벤트를 막아 놓았다
// (요금표에 Hobby "-", Pro "Included"). 대신 스크립트가 노출하는
// va('pageview', …) 는 막히지 않아서, 가상 경로를 페이지뷰로 보낸다.
// 주소창은 건드리지 않는다 — history 를 바꾸면 뒤로가기가 더러워진다.
//
// 남기는 것은 단계 이름뿐이다. 이름·기록·나이 같은 건 찍지 않는다.
// 한 번 방문에 같은 단계는 한 번만 센다(카드를 세 번 만들어도 1).
//
// Analytics 에서는 /_f/<단계> 경로로 보인다:
//   /_f/grade-calc    등급 결과를 봤다
//   /_f/card-made     공유 카드를 만들었다
//   /_f/card-saved    카드를 저장했다
//   /_f/card-shared   카드를 공유했다
//   /_f/record-saved  기록을 저장했다
//   /_f/cert-done     인증을 마쳤다
(function () {
  var done = {};

  function mark(step) {
    if (!step || done[step]) return;
    done[step] = 1;
    try {
      var p = "/_f/" + step;
      if (typeof window.va === "function") {
        window.va("pageview", { route: p, path: p });
      } else {
        // insights 스크립트는 defer 라서 아주 이른 동작은 va 가 없을 수 있다.
        // 한 번만 더 기다렸다 보낸다.
        setTimeout(function () {
          try {
            if (typeof window.va === "function") {
              window.va("pageview", { route: p, path: p });
            }
          } catch (e2) {}
        }, 1500);
      }
    } catch (e) {
      // 측정은 거드는 일이다. 실패해도 화면은 그대로 간다.
    }
  }

  window.calrankMark = mark;
})();

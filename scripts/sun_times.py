#!/usr/bin/env python3
"""일출·일몰 시각. NOAA Solar Calculator 식을 그대로 옮겼다.

왜 직접 계산하나
----------------
대회 상세 822장이 서로 2/3쯤 같은 글이라 색인이 안 되고 있다. 대회마다
다른 '진짜 정보'가 필요한데, 좌표와 날짜만 있으면 해 뜨는 시각은 계산된다.
API 도, 키도, 허가도 필요 없다. 그리고 11월 강원 07:00 출발처럼 출발할 때
아직 어두운 대회가 실제로 있어서, 챙길 것이 달라지는 정보다.

검증: 울산 당사항(35.633, 129.457) 기준
  2024-06-21  계산 05:07 / 19:41  ·  공표 05:07 / 19:41   (일치)
  2024-06-01  계산 05:08 / 19:32  ·  공표 05:08 / 19:33   (일몰 1분 차)
1분 차이는 좌표 근사와 지평선 기준 차이에서 온다.

zenith 90.833도는 태양의 반지름과 대기 굴절을 함께 본 통상값이다.
"""
import math, datetime as dt

def _jday(d):
    return d.toordinal() + 1721424.5

def sun_times(lat, lon, date, tz_hours=9.0, zenith=90.833):
    """(일출, 일몰) 을 그 지역 시각(분)으로. 극야·백야면 None."""
    jd = _jday(date)
    t = (jd - 2451545.0) / 36525.0
    # 기하평균 황경·근점이각
    L0 = (280.46646 + t * (36000.76983 + t * 0.0003032)) % 360.0
    M = 357.52911 + t * (35999.05029 - 0.0001537 * t)
    e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)
    Mr = math.radians(M)
    C = (math.sin(Mr) * (1.914602 - t * (0.004817 + 0.000014 * t))
         + math.sin(2 * Mr) * (0.019993 - 0.000101 * t)
         + math.sin(3 * Mr) * 0.000289)
    true_long = L0 + C
    omega = 125.04 - 1934.136 * t
    app_long = true_long - 0.00569 - 0.00478 * math.sin(math.radians(omega))
    eps0 = (23.0 + (26.0 + ((21.448 - t * (46.815 + t * (0.00059 - t * 0.001813)))) / 60.0) / 60.0)
    eps = eps0 + 0.00256 * math.cos(math.radians(omega))
    decl = math.degrees(math.asin(math.sin(math.radians(eps))
                                  * math.sin(math.radians(app_long))))
    # 균시차 (분)
    y = math.tan(math.radians(eps / 2.0)) ** 2
    L0r = math.radians(L0)
    eot = 4 * math.degrees(
        y * math.sin(2 * L0r) - 2 * e * math.sin(Mr)
        + 4 * e * y * math.sin(Mr) * math.cos(2 * L0r)
        - 0.5 * y * y * math.sin(4 * L0r) - 1.25 * e * e * math.sin(2 * Mr))
    latr, declr = math.radians(lat), math.radians(decl)
    cos_ha = ((math.cos(math.radians(zenith)) / (math.cos(latr) * math.cos(declr)))
              - math.tan(latr) * math.tan(declr))
    if cos_ha > 1 or cos_ha < -1:
        return None, None
    ha = math.degrees(math.acos(cos_ha))
    noon = 720 - 4 * lon - eot + tz_hours * 60     # 그 지역 시각(분)
    return noon - 4 * ha, noon + 4 * ha

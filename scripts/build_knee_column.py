#!/usr/bin/env python3
"""칼럼: 달리기와 무릎 연골. 근거는 모두 원 논문 초록에서 확인한 수치만 싣는다.
다대구 코스 칼럼의 틀(머리말·헤더·푸터)을 가져와 본문만 바꾼다."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SLUG = "column-running-knee-cartilage-evidence.html"
BASE = ROOT / "column-daegu-marathon-course-guide.html"

TITLE = "달리기를 하면 무릎 연골이 닳을까? 임상·코호트 연구로 확인한 허와 실"
DESC = ("달리기와 무릎 관절염, 이미 무릎이 아픈 사람의 달리기, 당뇨·사망률·노년 장애까지 "
        "메타분석과 장기 추적 연구 14편의 수치로 따져 봤습니다. 진짜 주의할 점도 함께 적었습니다.")

SOURCES = [
    ("Alentorn-Geli E, Samuelsson K, Musahl V, Green CL, Bhandari M, Karlsson J. The Association of Recreational and Competitive Running With Hip and Knee Osteoarthritis: A Systematic Review and Meta-analysis. J Orthop Sports Phys Ther 2017;47(6):373-390. doi:10.2519/jospt.2017.7137"),
    ("Williams PT. Effects of running and walking on osteoarthritis and hip replacement risk. Med Sci Sports Exerc 2013;45(7):1292-1297. doi:10.1249/mss.0b013e3182885f26"),
    ("Chakravarty EF, Hubert HB, Lingala VB, Zatarain E, Fries JF. Long distance running and knee osteoarthritis. A prospective study. Am J Prev Med 2008;35(2):133-138. doi:10.1016/j.amepre.2008.03.032"),
    ("Lo GH, Musa SM, Driban JB, Kriska AM, McAlindon TE, Souza RB, Petersen NJ, Storti KL, Eaton CB, Hochberg MC, Jackson RD, Kwoh CK, Nevitt MC, Suarez-Almazor ME. Running does not increase symptoms or structural progression in people with knee osteoarthritis: data from the osteoarthritis initiative. Clin Rheumatol 2018;37(9):2497-2504. doi:10.1007/s10067-018-4121-3"),
    ("Heckelman LN 외, DeFrate LE. Quantifying the biochemical state of knee cartilage in response to running using T1rho magnetic resonance imaging. Sci Rep 2020;10:1870. doi:10.1038/s41598-020-58573-8"),
    ("Fransen M, McConnell S, Harmer AR, Van der Esch M, Simic M, Bennell KL. Exercise for osteoarthritis of the knee. Cochrane Database Syst Rev 2015;(1):CD004376. doi:10.1002/14651858.CD004376.pub3"),
    ("Videbæk S, Bueno AM, Nielsen RO, Rasmussen S. Incidence of Running-Related Injuries Per 1000 h of Running in Different Types of Runners: A Systematic Review and Meta-Analysis. Sports Med 2015;45(7):1017-1026. doi:10.1007/s40279-015-0333-8"),
    ("Nielsen RØ, Parner ET, Nohr EA, Sørensen H, Lind M, Rasmussen S. Excessive progression in weekly running distance and risk of running-related injuries: an association which varies according to type of injury. J Orthop Sports Phys Ther 2014;44(10):739-747. doi:10.2519/jospt.2014.5164"),
    ("Umpierre D, Ribeiro PAB, Kramer CK, Leitão CB, Zucatti ATN, Azevedo MJ, Gross JL, Ribeiro JP, Schaan BD. Physical activity advice only or structured exercise training and association with HbA1c levels in type 2 diabetes: a systematic review and meta-analysis. JAMA 2011;305(17):1790-1799."),
    ("Williams PT, Thompson PD. Walking versus running for hypertension, cholesterol, and diabetes mellitus risk reduction. Arterioscler Thromb Vasc Biol 2013;33(5):1085-1091. doi:10.1161/ATVBAHA.112.300878"),
    ("Colberg SR, Sigal RJ, Yardley JE, Riddell MC, Dunstan DW 외. Physical Activity/Exercise and Diabetes: A Position Statement of the American Diabetes Association. Diabetes Care 2016;39(11):2065-2079. doi:10.2337/dc16-1728 (권고 수치는 같은 합의문을 정리한 Sigal RJ의 2017년 강연 자료에서 확인)"),
    ("Lee DC, Pate RR, Lavie CJ, Sui X, Church TS, Blair SN. Leisure-time running reduces all-cause and cardiovascular mortality risk. J Am Coll Cardiol 2014;64(5):472-481. doi:10.1016/j.jacc.2014.04.058"),
    ("Pedisic Z, Shrestha N, Kovalchik S, Stamatakis E, Liangruenrom N, Grgic J, Titze S, Biddle SJH, Bauman AE, Oja P. Is running associated with a lower risk of all-cause, cardiovascular and cancer mortality, and is the more the better? A systematic review and meta-analysis. Br J Sports Med 2020;54(15):898-905. doi:10.1136/bjsports-2018-100493"),
    ("Chakravarty EF, Hubert HB, Lingala VB, Fries JF. Reduced disability and mortality among aging runners: a 21-year longitudinal study. Arch Intern Med 2008;168(15):1638-1646. doi:10.1001/archinte.168.15.1638"),
]

def ref(*n):
    return '<sup class="rf">[' + ",".join(str(i) for i in n) + ']</sup>'

BODY = f'''
<p>무릎이 닳을 것 같아서, 연골이 걱정돼서, 달리면 더 아플 것 같아서 달리기를 미루고 계신 분들이 많습니다. 이 글은 그 걱정이 연구로 얼마나 뒷받침되는지, 반대로 어디까지가 사실인지를 가려 본 것입니다. 사람을 상대로 한 메타분석과 장기 추적 연구, 임상시험의 수치만 실었고, 모든 수치에 출처 번호를 달았습니다.</p>

<div class="fun-fact-box"><strong>먼저 결론</strong><br>
① 취미로 달리는 사람이 달리지 않는 사람보다 무릎·고관절 관절염이 많다는 증거는 없었습니다{ref(1,2,3)}.<br>
② 이미 무릎 관절염이 있는 사람 1,203명을 4년간 본 연구에서도, 달리는 사람의 증상과 X선 소견이 더 나빠지지 않았고, 잦던 통증이 사라진 비율은 오히려 높은 경향이었습니다{ref(4)}.<br>
③ 달리기를 비롯한 유산소 운동은 당뇨 환자의 당화혈색소를 0.7%포인트 안팎 낮췄고{ref(9)}, 달리는 사람은 사망 위험이 27~30% 낮았습니다{ref(12,13)}.<br>
④ 다만 부상은 실제로 있고, 선수급으로 달리는 경우나 체중·이전 부상 같은 변수는 따로 봐야 합니다. 달리기가 모든 사람에게 안전하다는 말이 아니라, "달리면 무릎이 닳는다"는 한 문장이 연구와 맞지 않는다는 뜻입니다.</div>

<h2>1. 달리는 사람의 무릎이 더 닳을까</h2>
<p>가장 큰 근거는 25편의 연구(125,810명)를 모은 2017년 메타분석입니다. 이 중 17편(114,829명)으로 계산한 고관절·무릎 관절염 유병률은 아래와 같았습니다{ref(1)}.</p>
<div class="table-scroll"><table class="segment-table"><thead><tr><th>집단</th><th>관절염 유병률(95% 신뢰구간)</th><th>대조군 대비 오즈비</th></tr></thead><tbody>
<tr><th>취미로 달리는 사람</th><td>3.5% (3.4~3.6)</td><td>0.86 (0.69~1.07)</td></tr>
<tr><th>달리지 않는 사람(대조군)</th><td>10.2% (9.9~10.6)</td><td>—</td></tr>
<tr><th>엘리트·국제대회급 선수</th><td>13.3% (11.6~15.2)</td><td>1.34 (0.97~1.86)</td></tr>
</tbody></table></div>
<p>숫자가 말하는 것은 두 가지입니다. 취미 러너의 오즈비 신뢰구간(0.69~1.07)에는 1이 들어 있어, "관절염이 줄어든다"고 단정할 수는 없고 "늘어난다는 증거가 없다"가 정확합니다. 반대로 엘리트급 선수는 방향이 높은 쪽(1.34)이지만 이쪽도 신뢰구간이 1을 걸치고 있습니다. 저자들은 취미 러너가 선수급이나 대조군보다 관절염이 적었다고 결론 내렸고, 과거 부상 같은 다른 요인의 영향을 배제하지는 못했다고 밝혔습니다{ref(1)}.</p>

<p>미국의 대규모 코호트도 비슷합니다. 달리기 74,752명과 걷기 14,625명을 각각 평균 7.1년, 5.7년 추적한 연구에서 관절염을 보고한 사람은 러너 2,004명, 걷는 사람 696명이었고, 고관절 치환술은 각각 259명과 114명이었습니다{ref(2)}. 하루 1.8 MET·시(운동 강도와 시간을 곱한 에너지 소비 단위) 이상 달린 사람은 그보다 적게 달린 사람보다 관절염 위험이 18.1%, 고관절 치환술 위험이 35.1% 낮았습니다. 단, 이 이점의 상당 부분은 체중과 관련이 있었습니다. BMI를 보정하자 관절염 위험 감소는 16.5%에서 8.6%로, 치환술 위험 감소는 40.4%에서 28.5%로 줄었습니다. BMI가 1 오를 때마다 관절염 위험은 5.0% 올랐습니다{ref(2)}. 달리기 자체의 이점과 체중 관리 효과가 섞여 있다는 뜻입니다.</p>

<p>같은 연구에서 눈여겨볼 점이 하나 더 있습니다. 달리기가 아닌 다른 운동은 오히려 관절염 위험을 높이는 쪽(1 MET·시당 2.4%)으로 나왔습니다{ref(2)}. 다만 이 연구는 자가 보고 설문이라 정확도에 한계가 있고, 이 결과를 어떻게 해석할지는 조심스럽습니다.</p>

<p>사람의 X선을 직접 찍어 추적한 연구도 있습니다. 50~72세 장거리 러너 45명과 달리지 않는 53명을 1984년부터 2002년까지 약 18년 동안 X선으로 비교했는데, 마지막 시점의 무릎 관절염은 러너 20%, 대조군 32%로 러너가 더 많지 않았고(p=0.25), 심한 관절염도 2.2% 대 9.4%였습니다(p=0.21){ref(3)}. 다만 두 집단 모두 인원이 100명 안팎이라 통계적으로 의미 있는 차이를 가려내기에는 작은 연구입니다. 이 연구에서 관절염이 나빠지는 것과 관련된 요인은 달리기가 아니라 시작 시점의 높은 BMI와 이미 있던 X선상의 손상이었습니다{ref(3)}.</p>

<h2>2. 달리는 동안 연골은 어떻게 반응하나</h2>
<p>달리면 연골 상태가 일시적으로 달라지는 것은 사실입니다. 무릎 통증이 없는 27~40세 남성 러너 8명이 3마일(약 4.8km)과 10마일(약 16km)을 달리고 MRI를 찍은 연구에서, 연골의 단백다당 농도를 반영하는 지표(T1rho)는 3마일 뒤 65에서 62ms로, 10마일 뒤 69에서 62ms로 달라졌습니다. 10마일 쪽의 변화가 더 컸고(약 11%), 24시간 뒤에는 거의 원래 값(2% 이내)으로 돌아왔습니다{ref(5)}.</p>
<p>달리면 연골 상태가 일시적으로 바뀌고 하루 안에 되돌아온다는 관찰입니다. 8명의 소규모 연구이고, 저자들도 이 거리가 안전한 범위라고 말하려면 더 많은 연구가 필요하다고 밝혔습니다{ref(5)}. 이것만으로 장기적인 이득이나 손상을 판단할 수는 없고, 앞의 장기 추적 연구가 그 부분을 보완하는 자료입니다.</p>

<h2>3. 이미 무릎이 안 좋은 사람은 달리면 안 될까</h2>
<p>가장 많이 듣는 걱정이라 따로 봅니다. 대규모 코호트(Osteoarthritis Initiative)에서 50세 이상, 무릎 관절염이 있는 1,203명(평균 63.2세, 평균 BMI 29.5, 러너 11.5%)을 48개월 동안 추적했습니다. 달리는 사람과 달리지 않는 사람을 비교하니, X선상 악화(오즈비 0.9, 95% 신뢰구간 0.6~1.3)와 새로 생기는 잦은 무릎 통증(0.9, 0.6~1.6) 모두 차이가 없었고, 기존의 잦은 무릎 통증이 사라진 비율은 달리는 쪽이 높았습니다(1.7, 1.0~2.8). 저자들은 "달리기를 만류할 필요가 없다"고 결론 내렸습니다{ref(4)}.</p>
<p>이 연구는 무작위 임상시험이 아니라 관찰 연구입니다. 달리기를 스스로 고른 사람들이라 애초에 무릎 상태가 괜찮은 사람이 많았을 수 있습니다. 하지만 "관절염이 있으면 달리기가 병을 악화시킨다"는 주장은 이 데이터에서 확인되지 않았습니다.</p>
<p>무릎 관절염에 대한 운동 치료는 무작위 임상시험으로 많이 검증되어 있습니다. 54편(통증 44편, 3,537명)을 합친 코크란 리뷰에서 지상 운동은 통증을 0~100점 척도에서 평균 12점(95% 신뢰구간 10~15) 낮췄고(대조군 44점, 운동군 32점), 신체 기능은 10점 개선했습니다. 통증 개선의 근거 수준은 '높음'으로 평가되었습니다{ref(6)}. 이 연구의 운동은 달리기가 아니라 근력·유산소 등 다양한 지상 운동이었고, 운동 때문에 무릎이나 허리 통증이 늘었다는 보고가 8개 연구에 있었지만 심각한 이상반응은 없었습니다{ref(6)}. 따라서 이 결과는 "움직이는 것이 무릎에 해롭지 않고 도움이 된다"는 근거이지, 달리기 자체의 효과를 직접 보여 주는 것은 아닙니다.</p>

<h2>4. 달리면 더 아프다는 말은 맞나: 부상의 실제</h2>
<p>이 부분은 근거가 아니라 현실을 있는 그대로 적어야 합니다. 13편을 모은 메타분석에서 러닝 관련 부상은 달린 시간 1,000시간당 초보 러너 17.8건(95% 신뢰구간 16.7~19.1), 취미 러너 7.7건(6.9~8.7)이었습니다{ref(7)}. 초보일수록 부상이 2배 넘게 잦습니다. 달리다 보면 아픈 것은 어느 정도 흔한 일이고, 이것이 달리기를 시작하는 사람들이 가장 크게 느끼는 장벽일 것입니다.</p>
<p>그렇다면 막을 방법이 있을까요. 초보 러너 874명을 1년간 GPS로 추적한 연구에서 주간 거리를 2주 사이 30% 넘게 늘린 사람은 10% 미만으로 늘린 사람보다 무릎 등의 '거리 관련 부상'이 많은 경향(위험비 1.59)이 있었지만, 신뢰구간이 0.96~2.66으로 통계적으로 확정된 결과는 아니었습니다{ref(8)}. 확정은 아니어도, 갑자기 거리를 늘리지 않는 것이 조심스러운 선택이라는 정도의 결론은 내릴 수 있습니다.</p>

<h2>5. 당뇨가 있다면</h2>
<p>무작위 임상시험 47편, 8,538명을 합친 JAMA 메타분석에서 구조화된 운동은 제2형 당뇨 환자의 당화혈색소를 평균 0.67%포인트(95% 신뢰구간 -0.84~-0.49) 낮췄고, 유산소 운동만 따로 보면 0.73%포인트(-1.06~-0.40) 낮췄습니다. 주당 150분을 넘게 운동한 경우 낮아진 폭이 0.89%포인트로, 150분 이하(0.36%포인트)보다 컸습니다. 운동하라는 조언만 한 경우는 식이 조언이 함께 있을 때만 효과가 있었습니다{ref(9)}.</p>
<p>이 임상시험들은 달리기만이 아니라 걷기·자전거·근력운동 등을 포함한 운동 중재입니다. 달리기에 한정한 증거로는 미국의 대규모 코호트가 있는데, 같은 에너지를 썼을 때 달리기와 걷기의 당뇨 위험 감소폭은 거의 같았습니다(1 MET·시당 12.1%와 12.3%, 차이 없음, p=0.94){ref(10)}. 달리기가 걷기보다 당뇨에 특별히 더 좋다는 근거는 없고, 같은 양을 채우기 위해 더 짧은 시간에 할 수 있다는 점이 달리기의 이점이라고 보시는 편이 정확합니다.</p>
<p>미국당뇨병학회 합의문의 권고는 중강도 이상 유산소 운동을 주당 최소 150분, 주 3일 이상으로 나누어 하고, 쉬는 날이 이틀 넘게 이어지지 않게 하며, 근력 운동을 주 2회 이상 더하는 것입니다. 신경병증이 있는 경우에도 체중이 실리는 유산소 운동은 발 관리를 제대로 하면 안전하다고 합니다{ref(11)}. 당뇨 환자는 약물에 따라 저혈당이 올 수 있고 합병증(신경병증, 망막병증, 심혈관 질환)에 따라 운동 방식이 달라질 수 있으므로, 시작 전에 주치의와 먼저 상의하셔야 합니다.</p>

<h2>6. 얼마나 오래, 얼마나 건강하게 사나</h2>
<p>달리기를 하면 오래 산다는 근거는 대규모 코호트에 있습니다. 미국 성인 55,137명을 평균 15년 추적한 연구에서 달리는 사람은 전체 사망 위험이 30%, 심혈관 사망 위험이 45% 낮았고 기대 수명은 약 3년 길었습니다{ref(12)}. 주당 51분 미만, 6마일(약 9.7km) 미만, 주 1~2회 달린 사람도 사망 위험이 낮았습니다{ref(12)}. 14개 연구를 합친 메타분석(232,149명, 사망 25,951건)도 달리는 사람의 전체 사망 위험비를 0.73(0.68~0.79)으로 계산했고, 달리는 양에 따른 뚜렷한 용량-반응 관계는 없었습니다. 저자들은 "일주일에 한 번이라도 달리지 않는 것보다 낫다"고 정리했습니다{ref(13)}.</p>
<p>나이 든 사람에게는 어떨까요. 50세 이상 러너 538명과 대조군 423명을 21년간 추적한 연구에서 19년 시점의 사망은 러너 15%, 대조군 34%였고(위험비 0.61, 0.45~0.82), 장애 점수가 0.5(0~3점 척도)에 이르는 위험도 러너가 낮았습니다(위험비 0.62, 0.46~0.84){ref(14)}. 다만 이 연구에서 러너는 처음부터 더 젊고 말랐으며 흡연이 적은 집단이었습니다. 보정을 했어도 달리기를 하는 사람이 원래 건강한 사람일 가능성은 완전히 지워지지 않습니다.</p>

<h2>7. 그래도 조심해야 할 것</h2>
<p>근거를 정직하게 적으면 이렇게 정리됩니다.</p>
<div class="table-scroll"><table class="segment-table"><thead><tr><th>주의점</th><th>근거</th></tr></thead><tbody>
<tr><th>선수급 훈련량은 별개</th><td>엘리트급 러너의 관절염 유병률은 13.3%로 대조군(10.2%)보다 높은 쪽이었음(통계적으로는 확정되지 않음){ref(1)}</td></tr>
<tr><th>체중이 큰 변수</th><td>BMI가 1 오를 때 관절염 위험 5.0% 상승, 러너의 이점도 BMI를 보정하면 절반 가까이 줄었음{ref(2)}</td></tr>
<tr><th>초보 시기의 부상</th><td>초보 러너의 부상 발생률이 취미 러너의 2배 넘음{ref(7)}</td></tr>
<tr><th>관찰 연구의 한계</th><td>달리기가 연골을 지킨다고 증명하는 무작위 임상시험은 없음. 러너는 원래 건강한 사람일 수 있음{ref(1,14)}</td></tr>
<tr><th>작은 표본</th><td>X선 추적 연구는 러너 45명과 대조군 53명, MRI 연구는 8명{ref(3,5)}</td></tr>
</tbody></table></div>

<h2>8. 달리기가 어렵다면</h2>
<p>무릎이 아주 안 좋거나 체중이 많이 나가서 달리기가 부담스러운 분들에게 달리기만이 답은 아닙니다. 앞의 코호트에서 걷기와 달리기는 같은 에너지 소비에서 당뇨 위험을 비슷하게 낮췄고{ref(10)}, 무릎 관절염에는 지상 운동 전반이 통증을 줄였습니다{ref(6)}. 무릎 통증이 있거나 당뇨, 심장질환이 있다면 달리기를 시작하기 전에 의사와 상의하시고, 통증이 갑자기 심해지거나 붓고 열이 나면 운동을 멈추고 진료를 받으세요. 이 글은 의학적 진단이나 처방을 대신하지 않습니다.</p>

<div class="source-box"><strong>📌 이 글의 출처</strong> (원 논문의 초록에서 확인한 수치만 인용함)<br>
{"<br>".join(f"[{i}] {s}" for i, s in enumerate(SOURCES, 1))}
</div>
<div class="column-cta"><p>내 기록이 어느 등급인지, 목표 기록에 필요한 페이스는 얼마인지 칼랭크에서 계산해 볼 수 있습니다.</p>
<a href="level.html">내 칼랭크 등급 계산하기 →</a></div>
'''

def build():
    h = BASE.read_text(encoding="utf-8")
    t = f"{TITLE} — calrank"
    h = re.sub(r"<title>.*?</title>", f"<title>{t}</title>", h, count=1)
    h = re.sub(r'(<meta name="description" content=")[^"]*(")', rf"\g<1>{DESC}\g<2>", h, count=1)
    h = re.sub(r'(<meta property="og:title" content=")[^"]*(")', rf"\g<1>{TITLE}\g<2>", h, count=1)
    h = re.sub(r'(<meta property="og:description" content=")[^"]*(")', rf"\g<1>{DESC}\g<2>", h, count=1)
    h = h.replace("column-daegu-marathon-course-guide.html", SLUG)
    h = h.replace("  .column-cta {", "  .rf { font-size: 11px; color: var(--ink-faint); margin-left: 1px; }\n  .column-cta {", 1)
    main = ('<main class="column-wrap">\n<p class="column-meta">🩺 건강 · 근거 정리</p>\n'
            f'<h1 class="column-title">{TITLE}</h1>\n<div class="column-body">{BODY}</div>\n</main>')
    h = re.sub(r'<main class="column-wrap">.*?</main>', lambda m: main, h, count=1, flags=re.S)
    (ROOT / SLUG).write_text(h, encoding="utf-8")
    print("wrote", SLUG)

if __name__ == "__main__":
    build()

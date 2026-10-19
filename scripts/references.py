"""
calrank 칼럼 근거(출처) 레지스트리 — 단일 진실 공급원.

왜 이 파일이 따로 있는가
------------------------
칼럼 본문에서 "연구에 따르면", "권고에 따르면" 같은 문장을 쓸 때마다
출처를 본문에 직접 적으면, 시간이 지나면서 확인되지 않은 출처가
섞여 들어갑니다. 그래서 인용 가능한 자료를 이 파일에 먼저 등록하고,
본문에서는 등록된 키만 참조하도록 했습니다.

generate_guides.py 는 본문이 참조한 키가 여기에 없으면 **생성을 중단**합니다.
즉 등록되지 않은 출처는 사이트에 올라갈 수 없습니다.

등록 기준
---------
1. 국제 학술지에 실린 합의문(consensus statement) / 공식 입장문(position stand)
   또는 체계적 문헌고찰·메타분석.
2. 국제 경기단체·정부기관의 공식 문서.
3. 2026-10-19 에 실제로 원문을 열어 수치를 직접 확인한 것만 등록했습니다.
   확인하지 못한 자료는 등록하지 않습니다 — 요약만 보고 등록하지 않습니다.

각 항목의 `verified` 는 원문에서 직접 확인한 날짜입니다.
`claims` 는 그 문헌이 실제로 뒷받침하는 내용을 한국어로 적어둔 것으로,
집필할 때 문헌이 말하지 않은 것을 쓰지 않도록 하는 체크리스트 역할을 합니다.
"""

REFERENCES = {
    # ------------------------------------------------------------------
    "noap2016": {
        "label": "Thomas DT, Erdman KA, Burke LM (2016)",
        "title": "Position of the Academy of Nutrition and Dietetics, Dietitians of "
                 "Canada, and the American College of Sports Medicine: "
                 "Nutrition and Athletic Performance",
        "venue": "Journal of the Academy of Nutrition and Dietetics 116(3):501–528. "
                 "동일 문서가 Medicine & Science in Sports & Exercise 48(3):543–568 "
                 "에도 함께 실렸습니다.",
        "org": "미국스포츠의학회(ACSM)·미국영양학회(AND)·캐나다영양사협회(DC) 공동 입장문",
        "url": "https://www.dietitians.ca/DietitiansOfCanada/media/Documents/Resources/noap-position-paper.pdf",
        "verified": "2026-10-19",
        "claims": [
            "하루 탄수화물: 가벼운 훈련(하루 1시간 내외) 5~7 g/kg, "
            "지구력 훈련(하루 1~3시간) 6~10 g/kg, 매우 많은 훈련(하루 4~5시간 초과) 8~12 g/kg",
            "대회 전 식사(60분 넘는 경기): 체중 1kg당 탄수화물 1~4 g 을 1~4시간 전에",
            "카보로딩(90분 넘는 경기): 24시간당 10~12 g/kg 을 36~48시간 동안",
            "경기 중 탄수화물: 45분 미만 불필요, 45~75분 소량(입 헹굼 포함), "
            "1~2.5시간 시간당 30~60 g, 2.5~3시간 초과 시간당 최대 90 g",
            "복합 탄수화물(포도당:과당 등 흡수 경로가 다른 조합)은 초장거리에서 더 높은 산화율",
            "단백질: 하루 1.2~2.0 g/kg, 운동 후 0.25~0.3 g/kg(고품질 단백질 15~25 g)",
            "운동 전 수분: 2~4시간 전 체중 1kg당 5~10 mL, 소변이 옅은 노란색이 목표",
            "운동 중 땀 배출량은 시간당 0.3~2.4 L 로 개인차가 큼. "
            "일반적인 섭취 계획은 시간당 0.4~0.8 L, 체중 감소를 2% 이내로 유지",
            "나트륨 보충은 땀 배출량이 시간당 1.2 L 를 넘거나, 땀이 짜거나, 2시간을 넘는 경기에서",
            "운동 후 수분: 잃은 양의 125~150%(1kg 당 1.25~1.5 L)",
            "저나트륨혈증은 혈중 나트륨 135 mmol/L 미만, 주된 원인은 과음수",
        ],
    },
    # ------------------------------------------------------------------
    "eah2015": {
        "label": "Hew-Butler T, Rosner MH, Fowkes-Godek S, 외 (2015)",
        "title": "Statement of the Third International Exercise-Associated "
                 "Hyponatremia Consensus Development Conference, Carlsbad, California, 2015",
        "venue": "Clinical Journal of Sport Medicine 25(4):303–320",
        "org": "제3차 국제 운동연관 저나트륨혈증 합의회의",
        "url": "https://pubmed.ncbi.nlm.nih.gov/26102445/",
        "verified": "2026-10-19",
        "claims": [
            "운동연관 저나트륨혈증(EAH)은 운동 중 또는 운동 후 24시간 이내에 "
            "혈중 나트륨이 135 mmol/L 미만으로 떨어지는 상태",
            "예방 권고: 갈증이라는 타고난 기전에 따라 마시면 과음수를 막을 수 있음 "
            "(권고 등급 1C). 원문 표현은 "
            "'using the innate thirst mechanism to guide fluid consumption is a "
            "strategy that should limit drinking in excess'",
            "위험 요인: 물·스포츠음료 등 저장성 음료의 과다 섭취, 경기 중 체중 증가, "
            "4시간을 넘는 운동 시간, 대회 경험 부족 또는 훈련 부족, 느린 페이스, "
            "체질량지수가 매우 높거나 낮은 경우, 음료를 너무 쉽게 구할 수 있는 환경",
        ],
    },
    # ------------------------------------------------------------------
    "acsm2007fluid": {
        "label": "Sawka MN, Burke LM, Eichner ER, Maughan RJ, Montain SJ, Stachenfeld NS (2007)",
        "title": "American College of Sports Medicine Position Stand: "
                 "Exercise and Fluid Replacement",
        "venue": "Medicine & Science in Sports & Exercise 39(2):377–390",
        "org": "미국스포츠의학회(ACSM) 공식 입장문",
        "url": "https://journals.lww.com/acsm-msse/fulltext/2007/02000/exercise_and_fluid_replacement.22.aspx",
        "verified": "2026-10-19",
        "claims": [
            "수분 보충 계획은 개인별 땀 배출량에 맞춰야 하며 모두에게 같은 양을 적용할 수 없음",
            "탈수와 과음수(저나트륨혈증) 양쪽 모두가 위험",
        ],
    },
    # ------------------------------------------------------------------
    "dupuy2018": {
        "label": "Dupuy O, Douzi W, Theurot D, Bosquet L, Dugué B (2018)",
        "title": "An Evidence-Based Approach for Choosing Post-exercise Recovery "
                 "Techniques to Reduce Markers of Muscle Damage, Soreness, Fatigue, "
                 "and Inflammation: A Systematic Review With Meta-Analysis",
        "venue": "Frontiers in Physiology 9:403. doi:10.3389/fphys.2018.00403",
        "org": "체계적 문헌고찰 및 메타분석",
        "url": "https://www.frontiersin.org/journals/physiology/articles/10.3389/fphys.2018.00403/full",
        "verified": "2026-10-19",
        "claims": [
            "근육통(DOMS) 감소 효과크기(Hedges' g, 음수가 감소): "
            "마사지 -2.26, 압박의류 -0.92, 가벼운 활동 회복 -0.94, "
            "냉수침수 -0.47, 전신냉각요법 -0.53, 냉온교대욕 -0.40",
            "피로감 감소: 마사지 -2.55, 압박의류 -0.88, 냉수침수 -1.16",
            "마사지가 근육통과 피로감 양쪽에서 가장 큰 효과",
            "스트레칭은 근육통에도 피로감에도 통계적으로 의미 있는 효과가 없었음",
        ],
    },
    # ------------------------------------------------------------------
    "herbert_cochrane": {
        "label": "Herbert RD, de Noronha M, Kamper SJ",
        "title": "Stretching to prevent or reduce muscle soreness after exercise",
        "venue": "Cochrane Database of Systematic Reviews 2022, Issue 4. "
                 "Art. No.: CD004577. doi:10.1002/14651858.CD004577.pub3",
        "org": "코크란 체계적 문헌고찰",
        "url": "https://www.cochrane.org/evidence/CD004577_stretching-prevent-or-reduce-muscle-soreness-after-exercise",
        "verified": "2026-10-19",
        "claims": [
            "무작위 배정 연구 12편을 종합한 결과, 운동 전·후·전후 어느 쪽으로 "
            "스트레칭을 해도 지연성 근육통이 임상적으로 의미 있게 줄지 않았음",
            "운동 전 스트레칭, 하루 뒤 근육통(100점 척도) 평균차 -0.52 "
            "(95% 신뢰구간 -11.30 ~ 10.26, 연구 3편)",
            "운동 후 스트레칭, 하루 뒤 근육통 평균차 -1.04 "
            "(95% 신뢰구간 -6.88 ~ 4.79, 연구 4편)",
            "참가자 2,300명 이상의 대규모 현장 연구에서 운동 전후 모두 스트레칭한 경우 "
            "일주일간 최고 근육통 평균차 -3.80 (95% 신뢰구간 -5.17 ~ -2.43). "
            "통계적으로는 유의하지만 저자들은 그 크기가 매우 작다고 평가",
        ],
    },
    # ------------------------------------------------------------------
    "er2020": {
        "label": "O'Connor FG, Deuster PA, Leggit JC, 외 (2020)",
        "title": "Clinical Practice Guideline for the Management of Exertional "
                 "Rhabdomyolysis in Warfighters",
        "venue": "Consortium for Health and Military Performance (CHAMP), "
                 "Uniformed Services University of the Health Sciences",
        "org": "미국 군의학 임상진료지침",
        "url": "https://www.hprc-online.org/sites/default/files/document/Clinical_Practice_Guideline_for_Managing_ER_19May2020.pdf",
        "verified": "2026-10-19",
        "claims": [
            "운동성 횡문근융해증(ER)을 의심해야 하는 신호: "
            "운동량에 비해 지나치게 심한 통증과 압통, 근육 부종, "
            "능동·수동 관절 가동범위의 뚜렷한 제한, "
            "특히 엉덩이·어깨 부위의 근력 저하, 콜라색 소변, "
            "활동 후 5~7일이 지나도 낫지 않거나 더 심해지는 통증",
            "격렬한 운동 후 24시간 이내에 시작된 짙은 소변은 ER 을 강하게 시사",
            "진단 기준치는 크레아틴키나아제(CK) 가 정상 상한의 5배 이상",
        ],
    },
    # ------------------------------------------------------------------
    "acsm2007heat": {
        "label": "Armstrong LE, Casa DJ, Millard-Stafford M, Moran DS, Pyne SW, Roberts WO (2007)",
        "title": "American College of Sports Medicine Position Stand: "
                 "Exertional Heat Illness during Training and Competition",
        "venue": "Medicine & Science in Sports & Exercise 39(3):556–572",
        "org": "미국스포츠의학회(ACSM) 공식 입장문",
        "url": "https://acsm.org/wp-content/uploads/2025/01/Exertional-heat-illness-during-training-and-competition.pdf",
        "verified": "2026-10-19",
        "claims": [
            "성인 기준 습구흑구온도(WBGT)별 권고: 10℃ 이하 평소대로, "
            "18.4~22.2℃ 고위험자 관찰, 22.3~25.6℃ 휴식을 늘리고 시간을 줄임, "
            "25.7~27.8℃ 운동과 휴식을 1:1 로 하고 강도·시간을 줄임, "
            "27.9~30.0℃ 고강도 운동을 제한하고 고위험자를 밀착 관찰, "
            "30.1~32.2℃ 중단하고 노출을 제한, 32.3℃ 이상 취소. "
            "WBGT 28℃ 를 넘으면 취소나 일정 변경을 고려",
            "열사병 위험 요인: 최대산소섭취량 75% 를 넘는 고강도, WBGT 28℃ 초과, "
            "환경 측정 없이 한 시간을 넘기는 운동, 더위 적응 부족, 훈련량의 급격한 증가, "
            "통기가 나쁜 복장, 수분·수면 부족, 비만, 낮은 체력, 탈수, 열사병 병력, "
            "최근 발열·호흡기 감염·구토·설사, 일부 약물과 보조제, 40세 이상",
            "열탈진의 징후: 혈압 저하, 빠른 맥박과 호흡, 많은 땀, 창백함, 두통, 무력감, "
            "어지러움, 오한, 구역, 구토, 협응 저하. 직장 온도 40℃ 미만이면 열탈진 쪽",
            "열사병의 조기 징후: 동작이 느려짐, 넘어짐, 두통, 구역, 어지러움, "
            "반응이 느려짐, 혼동. 더위 속에서 행동 변화가 보이면 열사병을 의심해야 함. "
            "직장 온도 40℃ 초과면 열사병 쪽",
            "열사병 응급처치는 이송 전 현장에서 즉시 냉각. 냉수 침수가 가장 빠름",
        ],
    },
    # ------------------------------------------------------------------
    "wms_hypothermia": {
        "label": "Zafren K, Giesbrecht GG, Danzl DF, 외",
        "title": "Wilderness Medical Society Practice Guidelines for the "
                 "Out-of-Hospital Evaluation and Treatment of Accidental Hypothermia",
        "venue": "Wilderness & Environmental Medicine 25(4 Suppl):S66–S85",
        "org": "미국 야생의학회(WMS) 임상진료지침 (이후 개정판이 있습니다)",
        "url": "https://wms.org/common/Uploaded%20files/Magazine/WMS%20Accidental%20Hypothermia%20PG%20Summary.pdf",
        "verified": "2026-10-19",
        "claims": [
            "저체온증 단계: 경증 심부체온 32~35℃, 중등증 28~32℃, 중증 28℃ 미만",
            "떨림은 심부체온 약 30℃ 까지 몸이 보이는 주된 반응이고 그 아래에서는 멈춤",
            "떨면서 스스로를 돌볼 수 있는 사람은 저체온증일 가능성이 낮고, "
            "추운 환경에서 스스로 움직이지 못하거나 의식이 없으면 저체온증을 의심",
            "현장 조치: 추위에서 벗어나게 하고 더 이상의 열 손실을 막음. "
            "젖은 옷은 벗기기보다 잘라 내고 단열재를 덮음. "
            "방수층 위에 단열재를 덮어 증발과 차가운 바닥과의 접촉을 차단",
            "경증 저체온증에서는 잘 감싼 채 누워서 떠는 것 자체가 효과적인 체온 회복 방법",
        ],
    },
    # ------------------------------------------------------------------
    "hody2019": {
        "label": "Hody S, Croisier JL, Bury T, Rogister B, Leprince P (2019)",
        "title": "Eccentric Muscle Contractions: Risks and Benefits",
        "venue": "Frontiers in Physiology 10:536. doi:10.3389/fphys.2019.00536",
        "org": "종설 논문",
        "url": "https://www.frontiersin.org/journals/physiology/articles/10.3389/fphys.2019.00536/full",
        "verified": "2026-10-19",
        "claims": [
            "내리막 달리기처럼 근육이 늘어나면서 힘을 쓰는 신장성 수축은 "
            "같은 조건의 단축성 수축보다 근손상이 큼",
            "익숙하지 않은 신장성 운동 뒤 근육통은 보통 12~24시간에 나타나 "
            "24~72시간에 가장 심하고 5~7일 안에 가라앉음",
            "근력 저하가 신장성 운동에 의한 근손상의 가장 좋은 간접 지표이며, "
            "통증이 사라진 뒤에도 근기능은 아직 완전히 회복되지 않은 상태일 수 있음",
            "반복 부하 효과(repeated bout effect): 한 번 신장성 운동을 겪으면 "
            "다음 번 같은 운동에서 근손상·통증·부종이 줄고 회복이 빨라짐. "
            "한 번만으로도 상당한 보호 효과가 있고 여러 번 할수록 더 완전해짐",
            "보호 효과는 수 주간 지속되며 약 6개월까지 남을 수 있으나 시간이 지날수록 약해짐",
            "손상을 일으키지 않는 수준의 가벼운 신장성 운동을 반복하는 것만으로도 "
            "이후의 강한 부하에 대한 보호 효과를 얻을 수 있음",
        ],
    },
    # ------------------------------------------------------------------
    "wt_rules": {
        "label": "World Triathlon",
        "title": "World Triathlon Competition Rules (2026)",
        "venue": "국제철인3종연맹 경기 규정. 국내 대회는 대한철인3종협회 및 "
                 "개별 대회 요강이 우선하므로 참가 전 해당 대회 규정을 확인하세요.",
        "org": "국제철인3종연맹(World Triathlon) 공식 규정",
        "url": "https://cms.triathlon.org/download-file/world-triathlon-competition-rules-2026",
        "verified": "2026-10-19",
        "claims": [
            "연령대별(Age-Group) 웻슈트 규정 — 수온 15.9℃ 이하에서는 모든 구간 착용 의무",
            "55-59세 이하, 수영 1500m 까지: 수온 22.0℃ 이상이면 착용 금지",
            "55-59세 이하, 수영 1501m 이상: 수온 24.6℃ 이상이면 착용 금지",
            "60-64세 이상: 모든 거리에서 수온 24.6℃ 이상이면 착용 금지",
            "의무 기준과 금지 기준 사이 수온에서는 착용이 선택",
            "연령대별 최대 수영 시간 — 300m 까지 20분, 301~750m 는 수온 31℃ 미만에서 30분 "
            "(31℃ 이상이면 20분), 751~1000m 50분, 1001~1500m 1시간 10분, "
            "1501~3000m 1시간 40분, 3001~4000m 2시간 20분",
            "수온에 따라 수영 거리를 줄이거나 취소할 수 있음. "
            "33.0℃ 초과 또는 11.9℃ 미만에서는 대부분의 거리가 취소",
            "다른 선수에게 자전거·프레임·휠·헬멧 같은 필수 장비를 건네면 양쪽 모두 실격",
            "펌프, 튜브, 펑크 수리 키트 같은 부수적인 물품은 선수끼리 주고받을 수 있음",
            "다른 선수의 전진을 물리적으로 도우면 실격",
            "주의를 분산시키는 방식의 기기 사용(음악 재생 등)은 실격 사유",
        ],
    },
    # ------------------------------------------------------------------
    "stoggl2015": {
        "label": "Stöggl TL, Sperlich B (2015)",
        "title": "The training intensity distribution among well-trained and "
                 "elite endurance athletes",
        "venue": "Frontiers in Physiology 6:295. doi:10.3389/fphys.2015.00295",
        "org": "종설 논문 (Focused Review)",
        "url": "https://www.frontiersin.org/articles/10.3389/fphys.2015.00295/full",
        "verified": "2026-10-19",
        "claims": [
            "잘 훈련된 지구력 선수의 훈련은 대부분 낮은 강도에 몰려 있는 "
            "피라미드형 분포. 낮은 강도(1구간) 비중이 대략 70~95%, "
            "준비기에는 84~95% 에 이르기도 함",
            "역치 구간(2구간) 약 2~22%, 높은 강도(3구간) 약 1~20% 이며 "
            "대회가 가까워질수록 높은 강도 비중이 올라가는 경향",
            "일부 종목·시기에서는 양극화(polarized) 분포. 예로 주니어 크로스컨트리 "
            "스키 약 75% / 5~10% / 15~20%, 마라톤 그룹 약 78% / 4% / 18%",
            "3구간 모델의 기준 — 1구간은 제1환기역치(VT1) 아래 또는 혈중 젖산 약 2 mM "
            "이하, 최대심박수의 대략 54~83%. 2구간은 젖산 약 4 mM 또는 제2환기역치(VT2) "
            "부근, 최대심박수의 대략 74~88%. 3구간은 젖산 4 mM 이상 또는 VT2 위, "
            "최대심박수 약 90% 초과",
            "무작위 배정 연구들에서는 양극화 훈련이 역치 위주 훈련이나 저강도 대량 훈련보다 "
            "지구력 지표를 더 크게 향상시키는 경우가 많았음",
            "다만 저자들은 모든 선수에게 맞는 단 하나의 최적 분포가 확인되지는 "
            "않았다고 결론지음",
        ],
    },
    # ------------------------------------------------------------------
    "damsted2018": {
        "label": "Damsted C, Glad S, Nielsen RO, Sørensen H, Malisoux L (2018)",
        "title": "Is there evidence for an association between changes in training "
                 "load and running-related injuries? A systematic review",
        "venue": "International Journal of Sports Physical Therapy 13(6):931–942. "
                 "doi:10.26603/ijspt20180931",
        "org": "체계적 문헌고찰",
        "url": "https://www.theinjuryclinic.com.au/wp-content/uploads/2022/03/IS-THERE-EVIDENCE-FOR-AN-ASSOCIATION-BETWEEN-CHANGES-IN-TRAINING-LOAD-AND-RUNNING-RELATED-INJURIES-A-SYSTEMATIC-REVIEW.pdf",
        "verified": "2026-10-19",
        "claims": [
            "연구 4편을 종합한 결과, 훈련량의 변화(증가든 감소든)와 러닝 부상 발생을 "
            "잇는 근거는 매우 제한적이라고 결론",
            "위험한 급증의 경계가 몇 % 인지에 대한 기준은 아직 밝혀지지 않았음",
            "주간 훈련량을 10% 넘게 올리지 말라는 이른바 '10% 룰' 을 뒷받침하는 "
            "근거는 찾지 못했다고 명시",
        ],
    },
    # ------------------------------------------------------------------
    "fradkin2010": {
        "label": "Fradkin AJ, Zazryn TR, Smoliga JM (2010)",
        "title": "Effects of warming-up on physical performance: "
                 "a systematic review with meta-analysis",
        "venue": "Journal of Strength and Conditioning Research 24(1):140–148. "
                 "doi:10.1519/JSC.0b013e3181c643a0",
        "org": "체계적 문헌고찰 및 메타분석",
        "url": "https://research.monash.edu/en/publications/effects-of-warming-up-on-physical-performance-a-systematic-review/",
        "verified": "2026-10-19",
        "claims": [
            "스트레칭 외의 활동을 포함한 워밍업을 다룬 연구 32편을 종합. "
            "모두 PEDro 척도에서 높은 품질(6.5~9점, 평균 7.6점)로 평가됨",
            "워밍업이 운동수행을 향상시킨 지표가 79건",
            "워밍업이 수행에 해롭다는 근거는 거의 없다고 저자들이 기술",
            "다만 잘 설계된 무작위 대조 연구가 적어 추가 연구가 필요하다고 지적",
        ],
    },
}


class UnknownReference(KeyError):
    """등록되지 않은 출처 키를 참조했을 때."""


def cite(key):
    """등록된 출처를 돌려준다. 없으면 즉시 실패한다."""
    if key not in REFERENCES:
        raise UnknownReference(
            f"등록되지 않은 출처 키입니다: {key!r}. "
            f"scripts/references.py 에 원문을 직접 확인한 뒤 등록하세요. "
            f"현재 등록된 키: {sorted(REFERENCES)}"
        )
    return REFERENCES[key]


def check_keys(keys):
    """키 묶음을 한 번에 검증한다."""
    unknown = [k for k in keys if k not in REFERENCES]
    if unknown:
        raise UnknownReference(
            f"등록되지 않은 출처 키: {unknown}. scripts/references.py 를 먼저 갱신하세요."
        )
    return True

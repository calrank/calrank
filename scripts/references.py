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

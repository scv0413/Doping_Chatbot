from app.chat.pharmacology.schemas import HalfLifeInfo, PharmacologySource


PHARMACOLOGY_REFERENCE_RECORDS = {
    "pseudoephedrine": {
        "substance_name": "pseudoephedrine",
        "aliases": [
            "pseudoephedrine",
            "슈도에페드린",
            "슈도에페드린염산염",
            "수도에페드린",
        ],
        "half_life": HalfLifeInfo(
            typical_range="대략 4-8시간 범위로 안내할 수 있으나 자료와 조건에 따라 달라집니다.",
            wider_range="소변 pH 등 조건에 따라 약 1.9-21시간까지 달라질 수 있다고 보고된 자료가 있습니다.",
            factors=[
                "소변 pH",
                "신장 기능",
                "복용량과 제형",
                "반복 복용 여부",
                "개인별 대사와 수분 상태",
            ],
            interpretation_notes=[
                "반감기는 혈중 농도가 절반으로 줄어드는 평균적 약동학 지표입니다.",
                "반감기만으로 도핑검사 검출 가능 시간이나 경기기간 중 사용 가능 여부를 확정할 수 없습니다.",
                "슈도에페드린은 경기기간 중 소변 농도 기준 등 도핑 규정 확인이 필요한 성분입니다.",
            ],
        ),
        "recommended_action": (
            "제품명, 성분명, 1회 복용량, 총 복용량, 마지막 복용 시각, 경기 시작 시각을 정리한 뒤 "
            "팀 닥터, 약사, KADA 또는 도핑 담당자에게 확인하세요."
        ),
        "safety_notes": [
            "이 정보는 선수와 지도자의 응급 판단을 돕는 참고자료이며 복용 허가나 도핑 안전 판정이 아닙니다.",
            "경기기간 중 복용 여부는 KADA 약물검색 결과와 WADA 금지목록 기준을 함께 확인해야 합니다.",
            "이미 복용했다면 임의로 숨기지 말고 복용 기록과 제품 사진을 남겨 전문가에게 즉시 공유하세요.",
        ],
        "sources": [
            PharmacologySource(
                title="PubChem Compound Summary: Pseudoephedrine",
                url="https://pubchem.ncbi.nlm.nih.gov/compound/pseudoephedrine",
                note="Pseudoephedrine half-life and urine pH dependent elimination summaries.",
            ),
            PharmacologySource(
                title="Brater et al. Renal excretion of pseudoephedrine, Clinical Pharmacology & Therapeutics",
                url="https://ascpt.onlinelibrary.wiley.com/doi/pdf/10.1038/clpt.1980.222",
                note="Reports large half-life changes under urine pH manipulation.",
            ),
            PharmacologySource(
                title="DailyMed drug label source",
                url="https://dailymed.nlm.nih.gov/dailymed/",
                note="Official U.S. drug labeling source for active ingredient cross-checks.",
            ),
        ],
    }
}

from app.chat.pharmacology.schemas import HalfLifeInfo, PharmacologySource


def source(title: str, url: str, note: str) -> PharmacologySource:
    return PharmacologySource(title=title, url=url, note=note)


def common_recommended_action() -> str:
    return (
        "제품명, 성분명, 1회 복용량, 총 복용량, 마지막 복용 시각, 경기 시작 시각을 정리한 뒤 "
        "팀 닥터, 약사, KADA 또는 도핑 담당자에게 확인하세요."
    )


def common_safety_notes() -> list[str]:
    return [
        "이 정보는 선수와 지도자의 응급 판단을 돕는 참고자료이며 복용 허가나 도핑 안전 판정이 아닙니다.",
        "경기기간 중 복용 여부는 KADA 약물검색 결과와 WADA 금지목록 기준을 함께 확인해야 합니다.",
        "이미 복용했다면 임의로 숨기지 말고 복용 기록과 제품 사진을 남겨 전문가에게 즉시 공유하세요.",
    ]


def common_half_life_notes(category_note: str) -> list[str]:
    return [
        "반감기는 혈중 농도가 절반으로 줄어드는 평균적 약동학 지표입니다.",
        "반감기만으로 도핑검사 검출 가능 시간이나 경기기간 중 사용 가능 여부를 확정할 수 없습니다.",
        category_note,
    ]


def stimulant_factors() -> list[str]:
    return [
        "소변 pH",
        "신장 기능",
        "복용량과 제형",
        "반복 복용 여부",
        "개인별 대사와 수분 상태",
    ]


WADA_PROHIBITED_LIST_SOURCE = source(
    title="WADA 2026 Prohibited List",
    url="https://www.wada-ama.org/en/resources/world-anti-doping-program/prohibited-list",
    note="Official prohibited list resource; use it to confirm in-competition category status.",
)

USADA_HALF_LIFE_GUIDE_SOURCE = source(
    title="USADA Half-Life of a Drug",
    url="https://www.usada.org/spirit-of-sport/drug-half-life/",
    note="Explains why half-life cannot predict anti-doping detection time with certainty.",
)

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
            factors=stimulant_factors(),
            interpretation_notes=common_half_life_notes(
                "슈도에페드린은 경기기간 중 S6 흥분제 관련 기준과 소변 농도 기준 확인이 필요한 성분입니다."
            ),
        ),
        "recommended_action": common_recommended_action(),
        "safety_notes": common_safety_notes(),
        "sources": [
            source(
                title="PubChem Compound Summary: Pseudoephedrine",
                url="https://pubchem.ncbi.nlm.nih.gov/compound/pseudoephedrine",
                note="Pseudoephedrine half-life and urine pH dependent elimination summaries.",
            ),
            source(
                title="Brater et al. Renal excretion of pseudoephedrine, Clinical Pharmacology & Therapeutics",
                url="https://ascpt.onlinelibrary.wiley.com/doi/pdf/10.1038/clpt.1980.222",
                note="Reports large half-life changes under urine pH manipulation.",
            ),
            USADA_HALF_LIFE_GUIDE_SOURCE,
            WADA_PROHIBITED_LIST_SOURCE,
        ],
    },
    "ephedrine": {
        "substance_name": "ephedrine",
        "aliases": [
            "ephedrine",
            "에페드린",
            "에페드린염산염",
        ],
        "half_life": HalfLifeInfo(
            typical_range="대략 3-6시간 또는 약 6시간 전후로 안내되는 자료가 있습니다.",
            wider_range="소변 pH, 신장 기능, 개인차에 따라 더 길거나 짧아질 수 있습니다.",
            factors=stimulant_factors(),
            interpretation_notes=common_half_life_notes(
                "에페드린은 경기기간 중 S6 흥분제 관련 기준과 소변 농도 기준 확인이 필요한 성분입니다."
            ),
        ),
        "recommended_action": common_recommended_action(),
        "safety_notes": common_safety_notes(),
        "sources": [
            source(
                title="PubChem Compound Summary: Ephedrine",
                url="https://pubchem.ncbi.nlm.nih.gov/compound/ephedrine",
                note="Ephedrine elimination and half-life summaries.",
            ),
            USADA_HALF_LIFE_GUIDE_SOURCE,
            WADA_PROHIBITED_LIST_SOURCE,
        ],
    },
    "methylephedrine": {
        "substance_name": "methylephedrine",
        "aliases": [
            "methylephedrine",
            "메틸에페드린",
            "메칠에페드린",
            "dl-메틸에페드린",
            "dl메틸에페드린",
        ],
        "half_life": HalfLifeInfo(
            typical_range="관련 자료에서는 에페드린 계열 참고값으로 대략 3-6시간 범위를 제시합니다.",
            wider_range="자료가 제한적이므로 실제 판단에서는 제품명, 용량, 대사체, 소변 기준 확인이 더 중요합니다.",
            factors=stimulant_factors(),
            interpretation_notes=common_half_life_notes(
                "메틸에페드린은 경기기간 중 S6 흥분제 관련 기준과 소변 농도 기준 확인이 필요한 성분입니다."
            ),
        ),
        "recommended_action": common_recommended_action(),
        "safety_notes": common_safety_notes(),
        "sources": [
            source(
                title="PubChem Compound Summary: Methylephedrine",
                url="https://pubchem.ncbi.nlm.nih.gov/compound/Methylephedrine",
                note="Methylephedrine pharmacology and ephedrine-related half-life summary.",
            ),
            USADA_HALF_LIFE_GUIDE_SOURCE,
            WADA_PROHIBITED_LIST_SOURCE,
        ],
    },
    "cathine": {
        "substance_name": "cathine",
        "aliases": [
            "cathine",
            "카틴",
            "norpseudoephedrine",
            "노르슈도에페드린",
            "norpseudoephedrine",
        ],
        "half_life": HalfLifeInfo(
            typical_range="자료에 따라 약 5.2 ± 3.4시간 정도로 안내됩니다.",
            wider_range="개인차, 섭취 형태, 신장 배설 조건에 따라 달라질 수 있습니다.",
            factors=stimulant_factors(),
            interpretation_notes=common_half_life_notes(
                "카틴은 경기기간 중 S6 흥분제 관련 기준과 소변 농도 기준 확인이 필요한 성분입니다."
            ),
        ),
        "recommended_action": common_recommended_action(),
        "safety_notes": common_safety_notes(),
        "sources": [
            source(
                title="PubChem Compound Summary: Cathine",
                url="https://pubchem.ncbi.nlm.nih.gov/compound/D-NORPSEUDOEPHEDRINE",
                note="Cathine synonyms and half-life summary.",
            ),
            USADA_HALF_LIFE_GUIDE_SOURCE,
            WADA_PROHIBITED_LIST_SOURCE,
        ],
    },
    "tramadol": {
        "substance_name": "tramadol",
        "aliases": [
            "tramadol",
            "트라마돌",
            "트라마돌염산염",
        ],
        "half_life": HalfLifeInfo(
            typical_range="트라마돌은 대략 6시간 전후, 주요 활성 대사체 M1은 약 7-9시간 전후로 안내됩니다.",
            wider_range="간 기능, 신장 기능, CYP2D6 대사 차이, 반복 복용 여부에 따라 달라질 수 있습니다.",
            factors=[
                "간 기능",
                "신장 기능",
                "CYP2D6 대사 차이",
                "복용량과 제형",
                "반복 복용 여부",
            ],
            interpretation_notes=common_half_life_notes(
                "트라마돌은 2024년부터 경기기간 중 S7 마약류로 금지되어 TUE 필요 여부 확인이 중요한 성분입니다."
            ),
        ),
        "recommended_action": common_recommended_action(),
        "safety_notes": [
            *common_safety_notes(),
            "트라마돌은 통증 조절 목적이라도 경기기간 중 사용하면 TUE 검토가 필요할 수 있으므로 임의 복용을 피하세요.",
        ],
        "sources": [
            source(
                title="DailyMed: Tramadol Hydrochloride Label",
                url="https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=674803a0-4cf5-4416-a5e3-c1a1e332cdcd&version=104",
                note="Tramadol and M1 plasma elimination half-life labeling information.",
            ),
            source(
                title="USADA 2024 Prohibited List Key Changes: Tramadol",
                url="https://www.usada.org/athlete-advisory/key-changes-2024-prohibited-list/",
                note="Tramadol prohibited in-competition beginning January 1, 2024.",
            ),
            USADA_HALF_LIFE_GUIDE_SOURCE,
            WADA_PROHIBITED_LIST_SOURCE,
        ],
    },
}

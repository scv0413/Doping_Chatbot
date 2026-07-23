from app.chat.domain.drug_search.kada_client import (
    build_kada_search_terms,
    parse_kada_drug_detail,
    parse_kada_search_result,
    select_detail_drug_code,
)
from app.chat.domain.drug_search.schemas import CompetitionPeriod, DrugRiskStatus, DrugSearchInput


def test_parse_kada_result_requests_product_selection_for_multiple_products() -> None:
    search_input = DrugSearchInput(
        query="타이레놀 먹어도 돼?",
        product_name="타이레놀",
        competition_period=CompetitionPeriod.IN_COMPETITION,
    )

    result = parse_kada_search_result(
        search_input=search_input,
        product_payload={
            "page": {"total": 2},
            "list": [
                {
                    "drug_name": "어린이타이레놀현탁액",
                    "list_sunb_name": "Acetaminophen 3.2g/100mL",
                    "firm_name": "한국존슨앤드존슨판매",
                },
                {
                    "drug_name": "타이레놀8시간이알서방정",
                    "list_sunb_name": "Acetaminophen 325mg",
                    "firm_name": "한국존슨앤드존슨판매",
                },
            ],
        },
        substance_payload={
            "page": {"total": 1},
            "list": [
                {
                    "sunb_ename": "Acetaminophen",
                    "sunb_name": "아세트아미노펜",
                    "ingame": None,
                    "outgame": None,
                }
            ],
        },
        retrieved_at="2026-07-17T00:00:00+00:00",
    )

    assert result.status is DrugRiskStatus.LOW_RISK
    assert result.requires_product_selection is True
    assert len(result.matched_candidates) == 3
    assert "아세트아미노펜" in result.matched_substances


def test_parse_kada_result_preserves_kada_herbal_verification_unavailable() -> None:
    result = parse_kada_search_result(
        search_input=DrugSearchInput(query="감초", product_name="감초"),
        product_payload={
            "page": {"total": 1},
            "list": [
                {
                    "drug_code": "herbal-1",
                    "drug_name": "작약감초탕",
                    "list_sunb_name": "Glycyrrhizae Radix",
                    "herbal": "1",
                }
            ],
        },
        substance_payload={
            "page": {"total": 1},
            "list": [
                {
                    "sunb_name": "감초",
                    "ingame": None,
                    "outgame": None,
                    "herbal": "1",
                }
            ],
        },
    )

    assert result.herbal_verification_unavailable is True
    assert result.status is DrugRiskStatus.NEEDS_VERIFICATION
    assert result.requires_product_selection is False
    assert "생약성분 포함 의약품 금지여부 확인 불가" in result.recommended_action


def test_select_detail_drug_code_uses_only_single_non_herbal_product() -> None:
    regular_result = parse_kada_search_result(
        search_input=DrugSearchInput(query="지르텍", product_name="지르텍"),
        product_payload={
            "page": {"total": 1},
            "list": [{"drug_code": "zyrtec-1", "drug_name": "지르텍정", "herbal": "0"}],
        },
        substance_payload={"page": {"total": 0}, "list": []},
    )
    herbal_result = parse_kada_search_result(
        search_input=DrugSearchInput(query="감초", product_name="감초"),
        product_payload={
            "page": {"total": 1},
            "list": [{"drug_code": "herbal-1", "drug_name": "작약감초탕", "herbal": "1"}],
        },
        substance_payload={"page": {"total": 0}, "list": []},
    )

    assert select_detail_drug_code(regular_result, requested_drug_code=None) == "zyrtec-1"
    assert select_detail_drug_code(herbal_result, requested_drug_code="herbal-1") is None


def test_parse_kada_result_marks_in_competition_banned_substance() -> None:
    search_input = DrugSearchInput(
        query="슈도에페드린",
        ingredient_name="슈도에페드린",
        competition_period=CompetitionPeriod.IN_COMPETITION,
    )

    result = parse_kada_search_result(
        search_input=search_input,
        product_payload={"page": {"total": 0}, "list": []},
        substance_payload={
            "page": {"total": 1},
            "list": [
                {
                    "sunb_ename": "pseudoephedrine",
                    "sunb_name": "슈도에페드린",
                    "ingame": "금지",
                    "outgame": "허용",
                }
            ],
        },
    )

    assert result.status is DrugRiskStatus.PROHIBITED_POSSIBLE
    assert result.requires_product_selection is False
    assert result.requires_dose_confirmation is True
    assert "금지 가능성" in result.recommended_action


def test_parse_kada_result_marks_out_of_competition_limited_substance_as_caution() -> None:
    search_input = DrugSearchInput(
        query="슈도에페드린",
        ingredient_name="슈도에페드린",
        competition_period=CompetitionPeriod.OUT_OF_COMPETITION,
    )

    result = parse_kada_search_result(
        search_input=search_input,
        product_payload={"page": {"total": 0}, "list": []},
        substance_payload={
            "page": {"total": 1},
            "list": [
                {
                    "sunb_ename": "pseudoephedrine",
                    "sunb_name": "슈도에페드린",
                    "ingame": "금지",
                    "outgame": "허용",
                }
            ],
        },
    )

    assert result.status is DrugRiskStatus.CAUTION
    assert result.requires_dose_confirmation is True


def test_parse_kada_result_marks_always_banned_substance() -> None:
    search_input = DrugSearchInput(
        query="테스토스테론",
        ingredient_name="테스토스테론",
        competition_period=CompetitionPeriod.OUT_OF_COMPETITION,
    )

    result = parse_kada_search_result(
        search_input=search_input,
        product_payload={"page": {"total": 0}, "list": []},
        substance_payload={
            "page": {"total": 1},
            "list": [
                {
                    "sunb_ename": "1-testosterone",
                    "sunb_name": "1-테스토스테론",
                    "ingame": "금지",
                    "outgame": "금지",
                    "mapid": "S1_007",
                }
            ],
        },
    )

    assert result.status is DrugRiskStatus.PROHIBITED_POSSIBLE
    assert result.prohibited_categories == ["S1_007"]


def test_parse_kada_result_marks_no_result_as_needs_verification() -> None:
    search_input = DrugSearchInput(query="알수없는약")

    result = parse_kada_search_result(
        search_input=search_input,
        product_payload={"page": {"total": 0}, "list": []},
        substance_payload={"page": {"total": 0}, "list": []},
    )

    assert result.status is DrugRiskStatus.NEEDS_VERIFICATION
    assert result.matched_candidates == []
    assert "조회 결과가 없습니다" in result.recommended_action


def test_build_kada_search_terms_adds_verified_product_spelling_alias() -> None:
    assert build_kada_search_terms("스트랩실") == ["스트랩실", "스트렙실"]


def test_build_kada_search_terms_adds_verified_ingredient_spelling_alias() -> None:
    assert build_kada_search_terms("세리티진염산염") == ["세리티진염산염", "세티리진염산염"]


def test_parse_product_candidates_splits_kada_combined_product_names() -> None:
    result = parse_kada_search_result(
        search_input=DrugSearchInput(query="스트렙실"),
        product_payload={
            "list": [
                {
                    "drug_code": "2009092800048",
                    "drug_name": "스트렙실허니앤레몬트로키, 스트렙실오렌지트로키",
                    "list_sunb_name": "Flurbiprofen 8.75mg",
                    "firm_name": "옥시레킷벤키저",
                }
            ]
        },
        substance_payload={"list": []},
        retrieved_at="2026-07-23T00:00:00+00:00",
    )

    products = [candidate for candidate in result.matched_candidates if candidate.match_type.value == "product"]

    assert [candidate.name for candidate in products] == [
        "스트렙실허니앤레몬트로키",
        "스트렙실오렌지트로키",
    ]
    assert {candidate.drug_code for candidate in products} == {"2009092800048"}
    assert result.requires_product_selection is True


def test_parse_kada_drug_detail_uses_kada_statuses_images_and_dosage() -> None:
    detail = parse_kada_drug_detail(
        drug_code="2009092800048",
        html="""
        <script>
        var drug = {"drug_name":"스트렙실허니앤레몬트로키, 스트렙실오렌지트로키", "pack_img":"https://example.com/package.jpg", "idfy_img":"https://example.com/pill.jpg"};
        var dopg = [{"sunb_name":"플루르비프로펜 [Flurbiprofen]", "inGame":"허용", "outGame":"허용", "dopingInfo":"코 스프레이로 사용하는 것은 예외적으로 허용됩니다."}];
        </script>
        <p id="dosage">성인: 1개를 서서히 녹여 복용합니다.</p>
        """,
        retrieved_at="2026-07-23T00:00:00+00:00",
    )

    assert detail.product_name == "스트렙실허니앤레몬트로키, 스트렙실오렌지트로키"
    assert detail.ingredients == ["플루르비프로펜 [Flurbiprofen]"]
    assert detail.in_competition_status == "허용"
    assert detail.out_of_competition_status == "허용"
    assert detail.doping_notices == ["코 스프레이로 사용하는 것은 예외적으로 허용됩니다."]
    assert detail.package_image_url == "https://example.com/package.jpg"
    assert detail.pill_image_url == "https://example.com/pill.jpg"
    assert detail.dosage == "성인: 1개를 서서히 녹여 복용합니다."

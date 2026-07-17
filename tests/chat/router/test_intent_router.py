from app.chat.router.intent_router import ChatRoute, route_question


def test_routes_product_name_question_to_drug_search() -> None:
    decision = route_question("타이레놀 먹어도 돼?")

    assert decision.route is ChatRoute.DRUG_SEARCH
    assert "타이레놀" in decision.matched_terms


def test_routes_ingredient_with_competition_context_to_drug_search_with_rag() -> None:
    decision = route_question("슈도에페드린 경기기간 중 먹어도 돼?")

    assert decision.route is ChatRoute.DRUG_SEARCH_WITH_RAG
    assert "슈도에페드린" in decision.matched_terms
    assert "경기기간" in decision.matched_terms


def test_routes_route_dependent_drug_question_to_drug_search_with_rag() -> None:
    decision = route_question("분사형 코감기약은 금지약물이야?")

    assert decision.route is ChatRoute.DRUG_SEARCH_WITH_RAG
    assert "코감기" in decision.matched_terms
    assert "금지약물" in decision.matched_terms


def test_routes_tue_application_question_to_rag() -> None:
    decision = route_question("TUE 신청 방법과 대리 신청 가능 여부를 알려줘")

    assert decision.route is ChatRoute.RAG


def test_routes_doping_test_identity_question_to_rag() -> None:
    decision = route_question("도핑검사관 신분이 불분명하면 어떻게 확인해야 해?")

    assert decision.route is ChatRoute.RAG
    assert "검사관" in decision.matched_terms


def test_defaults_to_rag_when_no_drug_signal_exists() -> None:
    decision = route_question("도핑 교육 자료는 어디서 확인해?")

    assert decision.route is ChatRoute.RAG

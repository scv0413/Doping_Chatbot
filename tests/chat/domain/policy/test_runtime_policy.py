from app.chat.domain.policy.runtime_policy import RuntimeEngine, decide_runtime_policy


def test_half_life_drug_question_uses_formatter_baseline() -> None:
    decision = decide_runtime_policy("슈도에페드린 반감기가 얼마나 돼? 경기 전날 먹었으면 괜찮아?")

    assert decision.top_k == 3
    assert decision.engine is RuntimeEngine.GRAPH
    assert decision.use_llm is False
    assert "half_life_safety_baseline_formatter" in decision.matched_rules


def test_complex_field_scenario_uses_llm_answer_chain() -> None:
    decision = decide_runtime_policy("새벽에 혈액 시료채취를 요청받았고 검사관 신분도 불분명하면 어떻게 해?")

    assert decision.use_llm is True
    assert decision.engine is RuntimeEngine.GRAPH
    assert "complex_field_scenario_llm" in decision.matched_rules


def test_simple_drug_search_uses_formatter() -> None:
    decision = decide_runtime_policy("타이레놀 먹어도 돼?")

    assert decision.use_llm is False
    assert "simple_drug_search_formatter" in decision.matched_rules


def test_explicit_overrides_are_respected() -> None:
    decision = decide_runtime_policy(
        "슈도에페드린 반감기가 얼마나 돼?",
        top_k=5,
        use_llm=True,
        engine=RuntimeEngine.PIPELINE,
        recursion_limit=9,
    )

    assert decision.top_k == 5
    assert decision.use_llm is True
    assert decision.engine is RuntimeEngine.PIPELINE
    assert decision.recursion_limit == 9
    assert "explicit_use_llm_override" in decision.matched_rules
    assert "explicit_top_k_override" in decision.matched_rules
    assert "explicit_engine_override" in decision.matched_rules


def test_runtime_policy_uses_llm_for_general_doping_control_explanation() -> None:
    decision = decide_runtime_policy("도핑검사할 때 뭐해?")

    assert decision.use_llm is True
    assert "general_doping_control_llm" in decision.matched_rules


def test_runtime_policy_uses_llm_for_urine_collection_scenario() -> None:
    decision = decide_runtime_policy("검사 중 소변이 안 나오면 어떻게 해야 해?")

    assert decision.use_llm is True
    assert "complex_field_scenario_llm" in decision.matched_rules


def test_runtime_policy_uses_llm_for_specific_gravity_explanation() -> None:
    decision = decide_runtime_policy("굴절계 기준 비중 1.003 이상이 뭐야?")

    assert decision.use_llm is True
    assert "complex_field_scenario_llm" in decision.matched_rules

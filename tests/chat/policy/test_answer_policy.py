from app.chat.policy.answer_policy import (
    ANSWER_RULES,
    CHATBOT_PERSONA,
    OFFICIAL_DECISION_DISCLAIMER,
    build_answer_writing_instructions,
    build_system_prompt,
    get_answer_rule,
)


def test_answer_policy_defines_persona_and_rag_six_rules() -> None:
    assert "엘리트 선수" in CHATBOT_PERSONA
    assert "트레이너" in CHATBOT_PERSONA
    assert len(ANSWER_RULES) == 6
    assert [rule.rule_id for rule in ANSWER_RULES] == [
        "restrict_to_context",
        "explicit_citations",
        "handle_insufficient_info",
        "prevent_fabrication",
        "enforce_persona_tone",
        "apply_safety_caveats",
    ]


def test_answer_rules_keep_rag_meaning_and_doping_application() -> None:
    assert "provided retrieved chunks" in get_answer_rule("restrict_to_context").description
    assert "cite the source" in get_answer_rule("explicit_citations").description
    assert "unknown" in get_answer_rule("handle_insufficient_info").description
    assert "invented" in get_answer_rule("prevent_fabrication").description
    assert "target audience" in get_answer_rule("enforce_persona_tone").description
    assert "warnings" in get_answer_rule("apply_safety_caveats").description
    assert "KADA" in get_answer_rule("restrict_to_context").doping_application


def test_build_system_prompt_uses_policy_source_of_truth() -> None:
    prompt = build_system_prompt()

    assert CHATBOT_PERSONA in prompt
    for rule in ANSWER_RULES:
        assert rule.name in prompt
        assert rule.description in prompt
        assert rule.doping_application in prompt


def test_writing_instructions_and_disclaimer_are_explicit() -> None:
    instructions = build_answer_writing_instructions()

    assert "1." in instructions
    assert "근거" in instructions
    assert "제공된 근거" in instructions
    assert "공식 판정" in OFFICIAL_DECISION_DISCLAIMER
    assert "대체하지 않습니다" in OFFICIAL_DECISION_DISCLAIMER

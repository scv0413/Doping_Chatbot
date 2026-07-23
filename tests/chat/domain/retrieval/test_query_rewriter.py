from app.chat.domain.retrieval.query_rewriter import rewrite_query


def test_rewrite_query_expands_notification_signature_terms() -> None:
    rewritten = rewrite_query("도핑검사 통지서 서명을 거부하면 어떻게 돼?")

    assert "Article 5.4.3" in rewritten
    assert "Failure to Comply" in rewritten


def test_rewrite_query_expands_delay_and_observation_terms() -> None:
    rewritten = rewrite_query("치료나 통역 때문에 도핑관리소 도착을 미뤄도 돼? 혼자 움직여도 돼?")

    assert "Article 5.4.4" in rewritten
    assert "지속 관찰" in rewritten


def test_rewrite_query_expands_general_doping_control_terms() -> None:
    rewritten = rewrite_query("도핑검사할 때 뭐해?")

    assert "doping control" in rewritten
    assert "sample collection" in rewritten


def test_rewrite_query_expands_urine_collection_terms() -> None:
    rewritten = rewrite_query("검사 중 오줌이 안 나오면 어떻게 해야 해?")

    assert "partial Sample" in rewritten
    assert "Annex E" in rewritten
    assert "continuous observation" in rewritten


def test_rewrite_query_expands_bathroom_leave_terms() -> None:
    rewritten = rewrite_query("검사 도중 대변이 마려우면 어떻게 해야 해?")

    assert "Article 7.3.5" in rewritten
    assert "Article 7.3.6" in rewritten
    assert "Doping Control Station" in rewritten


def test_rewrite_query_expands_urine_volume_and_specific_gravity_terms() -> None:
    rewritten = rewrite_query("오줌은 몇 ml 이상 나와야 검사로 인정돼?")

    assert "90 mL" in rewritten
    assert "specific gravity" in rewritten
    assert "1.005" in rewritten


def test_rewrite_query_expands_specific_gravity_explanation_terms() -> None:
    rewritten = rewrite_query("굴절계 기준 비중 1.003 이상이 뭐야?")

    assert "Suitable Specific Gravity for Analysis" in rewritten
    assert "refractometer" in rewritten
    assert "urine Sample" in rewritten

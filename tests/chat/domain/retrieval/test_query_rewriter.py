from app.chat.domain.retrieval.query_rewriter import rewrite_query


def test_rewrite_query_expands_notification_signature_terms() -> None:
    rewritten = rewrite_query("도핑검사 통지서 서명을 거부하면 어떻게 돼?")

    assert "Article 5.4.3" in rewritten
    assert "Failure to Comply" in rewritten


def test_rewrite_query_expands_delay_and_observation_terms() -> None:
    rewritten = rewrite_query("치료나 통역 때문에 도핑관리소 도착을 미뤄도 돼? 혼자 움직여도 돼?")

    assert "Article 5.4.4" in rewritten
    assert "지속 관찰" in rewritten

from app.chat.domain.answer.chain import generate_answer
from app.chat.domain.drug_search.kada_client import search_kada_drugs
from app.chat.domain.pharmacology.service import search_pharmacology_info
from app.chat.domain.policy.answer_policy import OFFICIAL_DECISION_DISCLAIMER
from app.chat.domain.retrieval.retriever import search


def test_domain_imports_are_available() -> None:
    assert all([generate_answer, search_kada_drugs, search_pharmacology_info, search])
    assert OFFICIAL_DECISION_DISCLAIMER

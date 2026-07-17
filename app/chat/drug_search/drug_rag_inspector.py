from app.chat.answer.formatter import format_answer
from app.chat.drug_search.formatter import format_drug_search_answer
from app.chat.drug_search.kada_client import search_kada_drugs
from app.chat.drug_search.schemas import CompetitionPeriod, DrugSearchInput
from app.chat.pipeline.chat_pipeline import (
    build_retrieval_query,
    run_chat_pipeline,
    should_run_drug_search,
    should_run_retrieval,
)
from app.chat.retrieval.query_rewriter import rewrite_query
from app.chat.retrieval.retriever import search
from app.chat.retrieval.schemas import RetrievalMatch
from app.chat.router.intent_router import route_question

TEST_INPUTS = [
    DrugSearchInput(
        query="타이레놀 먹어도 돼?",
        product_name="타이레놀",
        competition_period=CompetitionPeriod.IN_COMPETITION,
    ),
    DrugSearchInput(
        query="슈도에페드린 경기기간 중 먹어도 돼?",
        ingredient_name="슈도에페드린",
        competition_period=CompetitionPeriod.IN_COMPETITION,
    ),
    DrugSearchInput(
        query="분사형 코감기약은 금지약물이야?",
        product_name="코감기약",
        competition_period=CompetitionPeriod.IN_COMPETITION,
    ),
    DrugSearchInput(
        query="TUE 신청 방법과 대리 신청 가능 여부를 알려줘",
    ),
    DrugSearchInput(
        query="도핑검사관 신분이 불분명하면 어떻게 확인해야 해?",
    ),
]


def inspect_drug_rag_flow(top_k: int = 5, use_llm: bool = False) -> None:
    for search_input in TEST_INPUTS:
        decision = route_question(search_input.query)
        drug_result = None
        matches: list[RetrievalMatch] = []

        print("#" * 100)
        print(f"QUERY: {search_input.query}")
        print(f"ROUTE: {decision.route}")
        print(f"REASON: {decision.reason}")
        print(f"MATCHED TERMS: {decision.matched_terms}")

        if should_run_drug_search(decision):
            print("-" * 80)
            print("DRUG SEARCH RESULT")
            try:
                drug_result = search_kada_drugs(search_input)
            except Exception as exc:
                print(f"DRUG SEARCH ERROR: {type(exc).__name__}: {exc}")
                drug_result = None

            if drug_result:
                print(format_drug_search_answer(drug_result, candidate_limit=3))

        if should_run_retrieval(decision):
            print("-" * 80)
            print("RETRIEVAL RESULT")
            retrieval_query = build_retrieval_query(
                search_input=search_input,
                decision=decision,
                drug_result=drug_result,
            )
            rewritten_query = rewrite_query(retrieval_query)
            print(f"RETRIEVAL QUERY: {retrieval_query}")
            if rewritten_query != retrieval_query:
                print("REWRITTEN QUERY:")
                print(rewritten_query)

            try:
                matches = search(rewritten_query, top_k=top_k)
            except Exception as exc:
                print(f"RETRIEVAL ERROR: {type(exc).__name__}: {exc}")
                continue

            print_retrieval_matches(matches)

        print("-" * 80)
        print("FINAL FORMATTED ANSWER")
        print(
            format_answer(
                query=search_input.query,
                decision=decision,
                drug_result=drug_result,
                retrieval_matches=matches,
            )
        )
        print("-" * 80)
        print("FINAL CHAIN ANSWER")
        result = run_chat_pipeline(
            search_input=search_input,
            top_k=top_k,
            use_llm=use_llm,
        )
        print(result.answer)


def print_retrieval_matches(matches: list[RetrievalMatch]) -> None:
    for match in matches:
        preview = match.text[:300].replace("\n", " ")
        print("-" * 60)
        print(
            f"rank={match.rank} "
            f"distance={match.distance:.4f} "
            f"chunk_id={match.chunk_id} "
            f"source_id={match.metadata.source_id} "
            f"page={match.metadata.page}"
        )
        print(preview)


if __name__ == "__main__":
    inspect_drug_rag_flow()

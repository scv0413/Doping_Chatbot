from app.chat.retrieval.query_rewriter import rewrite_query
from app.chat.retrieval.retriever import search

TEST_QUERIES = [
    "S0 비승인약물이 뭐야?",
    "TUE 신청 방법과 대리 신청 가능 여부를 알려줘",
    "도핑검사 시료채취를 거부하거나 회피하면 어떤 불이익이 있어?",
    "도핑검사관 또는 시료채취요원의 신분이 불분명하면 어떻게 확인해야 해?",
    "경기기간 중 복용하려는 약이 금지약물인지 어떻게 확인해?",
    "새벽에 혈액 시료 채취를 요청받으면 어떻게 안전하게 대응해야 해?",
    "분사형 코감기 약은 금지약물이야?"
]


def inspect_queries(top_k: int = 5, use_rewrite: bool = True) -> None:
    for query in TEST_QUERIES:
        search_query = rewrite_query(query) if use_rewrite else query
        print("#" * 100)
        print(f"QUERY: {query}")

        if search_query != query:
            print("REWRITTEN QUERY:")
            print(search_query)

        for match in search(search_query, top_k=top_k):
            preview = match.text[:300].replace("\n", " ")
            print("-" * 80)
            print(
                f"rank={match.rank} "
                f"distance={match.distance:.4f} "
                f"chunk_id={match.chunk_id} "
                f"source_id={match.metadata.source_id} "
                f"page={match.metadata.page}"
            )
            print(preview)


if __name__ == "__main__":
    inspect_queries()

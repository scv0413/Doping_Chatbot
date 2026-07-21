import argparse

from app.chat.graph.graph import run_chat_graph


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--no-llm", action="store_true")
    args = parser.parse_args()

    result = run_chat_graph(
        args.query,
        top_k=args.top_k,
        use_llm=not args.no_llm,
    )
    print(f"route: {result.decision.route}")
    print(f"errors: {len(result.errors)}")
    print(f"chunks: {[match.chunk_id for match in result.retrieval_matches]}")
    print("=" * 80)
    print(result.answer)


if __name__ == "__main__":
    main()

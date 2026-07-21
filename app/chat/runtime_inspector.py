import argparse

from app.chat.runtime import ChatEngine, ChatRequest, run_chat


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--engine", choices=[engine.value for engine in ChatEngine], default=ChatEngine.GRAPH.value)
    parser.add_argument("--no-llm", action="store_true")
    args = parser.parse_args()

    response = run_chat(
        ChatRequest(
            query=args.query,
            top_k=args.top_k,
            engine=ChatEngine(args.engine),
            use_llm=not args.no_llm,
        )
    )
    print(f"engine: {response.engine}")
    print(f"route: {response.route}")
    print(f"errors: {len(response.errors)}")
    print(f"retrieval_attempts: {response.retrieval_attempts}")
    print(f"retry_reason: {response.retrieval_retry_reason}")
    print(f"citations: {[citation.chunk_id for citation in response.citations]}")
    print("=" * 80)
    print(response.answer)


if __name__ == "__main__":
    main()

import argparse

from langchain_core.documents import Document

from app.chat.retrieval.schemas import RetrievalMatch, RetrievalMetadata
from app.chat.retrieval.vector_store import get_vector_store


def search(query: str, top_k: int = 5) -> list[RetrievalMatch]:
    vector_store = get_vector_store()
    results = vector_store.similarity_search_with_score(query, k=top_k)

    matches: list[RetrievalMatch] = []
    for rank, (document, distance) in enumerate(results, start=1):
        chunk_id = get_chunk_id(document)
        metadata = RetrievalMetadata.model_validate({**document.metadata, "chunk_id": chunk_id})
        matches.append(
            RetrievalMatch(
                rank=rank,
                chunk_id=chunk_id,
                distance=distance,
                metadata=metadata,
                text=document.page_content,
            )
        )

    return matches


def get_chunk_id(document: Document) -> str:
    document_id = getattr(document, "id", None)
    if document_id:
        return document_id

    metadata_chunk_id = document.metadata.get("chunk_id")
    if isinstance(metadata_chunk_id, str):
        return metadata_chunk_id

    return "unknown"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    for match in search(args.query, top_k=args.top_k):
        preview = match.text[:350].replace("\n", " ")
        print("=" * 80)
        print(f"rank: {match.rank}")
        print(f"distance: {match.distance:.4f}")
        print(f"chunk_id: {match.chunk_id}")
        print(f"source_id: {match.metadata.source_id}")
        print(f"page: {match.metadata.page}")
        print(preview)


if __name__ == "__main__":
    main()

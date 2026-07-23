import argparse
import re

from langchain_core.documents import Document

from app.chat.domain.retrieval.schemas import RetrievalMatch, RetrievalMetadata
from app.chat.domain.retrieval.vector_store import get_vector_store


SECTION_REFERENCE_PATTERN = re.compile(r"\b(?:Article\s+)?(\d+(?:\.\d+)+)\b", re.IGNORECASE)
CANDIDATE_MULTIPLIER = 5


def rerank_section_matches(matches: list[RetrievalMatch], query: str) -> list[RetrievalMatch]:
    """Prioritize an explicitly requested document section without changing normal search order."""

    requested_sections = set(SECTION_REFERENCE_PATTERN.findall(query))
    if not requested_sections:
        return matches

    return sorted(
        matches,
        key=lambda match: (match.metadata.section not in requested_sections, match.distance),
    )


def search(query: str, top_k: int = 5) -> list[RetrievalMatch]:
    vector_store = get_vector_store()
    candidate_k = max(top_k, top_k * CANDIDATE_MULTIPLIER)
    results = vector_store.similarity_search_with_score(query, k=candidate_k)

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

    ranked_matches = rerank_section_matches(matches, query)[:top_k]
    return [
        match.model_copy(update={"rank": rank})
        for rank, match in enumerate(ranked_matches, start=1)
    ]


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

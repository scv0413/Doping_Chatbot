import json

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings

ChromaMetadata = dict[str, str | int | float | bool]


def to_chroma_metadata(metadata: dict[str, object]) -> ChromaMetadata:
    chroma_metadata: ChromaMetadata = {}

    for key, value in metadata.items():
        if value is None:
            continue

        if isinstance(value, str | int | float | bool):
            chroma_metadata[key] = value
            continue

        chroma_metadata[key] = json.dumps(value, ensure_ascii=False)

    return chroma_metadata


def get_chroma_persist_directory(create: bool = True) -> str:
    persist_directory = settings.index_dir / "chroma"

    if create:
        persist_directory.mkdir(parents=True, exist_ok=True)

    return str(persist_directory)


def get_embedding_model() -> OpenAIEmbeddings:
    if settings.embedding_provider != "openai":
        raise ValueError("Only OpenAI embeddings are supported.")

    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.openai_api_key,
    )


def get_vector_store(collection_metadata: dict[str, str] | None = None) -> Chroma:
    return Chroma(
        collection_name=settings.chroma_collection_name,
        embedding_function=get_embedding_model(),
        persist_directory=get_chroma_persist_directory(),
        collection_metadata=collection_metadata,
    )


def count_vector_store_documents(vector_store: Chroma) -> int:
    result = vector_store.get(include=[])
    return len(result.get("ids", []))

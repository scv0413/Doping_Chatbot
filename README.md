# Doping Chatbot

KADA/WADA 도핑 관련 규정, 금지약물, 현장 대응 시나리오를 근거 기반으로 검색하고 답변하는 RAG 챗봇 프로젝트입니다.

목표 사용자는 엘리트 선수와 트레이너입니다. 포트폴리오 프로젝트이지만 실제 현장에서 쓸 수 있는 구조를 목표로 합니다.

## Current Architecture

```text
app/
  preprocess/      # PDF/manual source 전처리, page JSONL 생성, chunk 생성
  chat/
    retrieval/     # LangChain OpenAI embeddings + LangChain Chroma 검색
    drug_search/   # KADA 약물검색 client, mock searcher, formatter
    router/        # 질문 intent route 결정
    answer/        # deterministic formatter + LangChain ChatOpenAI answer chain
    pipeline/      # router -> drug_search -> retrieval -> answer 실행 흐름
    docs/          # 기획, 평가, 발표용 문서
tests/
  chat/            # runtime chat layer unit tests
logs/              # 설계 판단과 검증 기록
data/
  source_manifest.csv
  raw/             # 원본 PDF, git 제외
  processed/       # 전처리/chunk 결과, git 제외
  indexes/         # Chroma index, git 제외
```

## Environment

Python은 3.12를 사용합니다.

```bash
uv sync --extra dev
```

환경변수는 `.env.example`을 기준으로 `.env`에 작성합니다.

필수:

```text
OPENAI_API_KEY
```

현재 기본 모델:

```text
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
```

## Main Commands

전처리:

```bash
uv run python -m app.preprocess.preprocess
uv run python -m app.preprocess.chunker
```

색인:

```bash
uv run python -m app.chat.retrieval.indexer
```

검색 확인:

```bash
uv run python -m app.chat.retrieval.retriever "슈도에페드린 경기기간" --top-k 3
uv run python -m app.chat.retrieval.retrieval_inspector
```

약물검색 + RAG 통합 확인:

```bash
uv run python -m app.chat.drug_search.drug_rag_inspector
```

검증:

```bash
uv run ruff check app tests
uv run pytest
```

## Design Notes

- RAG 검색 결과는 `RetrievalMatch` schema로 전달합니다.
- Vector store 생성은 `app/chat/retrieval/vector_store.py`에서 표준화합니다.
- Answer chain은 `langchain-openai`의 `ChatOpenAI`를 사용합니다.
- KADA 약물검색은 도메인 API 성격이 강하므로 LangChain으로 감싸기 전에 명시적 client로 유지합니다.
- LLM은 retrieval과 약물조회 결과를 새로 판단하지 않고, 구조화된 context를 사용자 답변으로 정리하는 역할을 맡습니다.

## Next Steps

1. LangGraph node 분리
2. LangSmith tracing/evaluation 연결
3. Gradio UI 생성

# Runtime Entrypoint for UI and API

## Goal

Gradio 또는 FastAPI가 내부 구현(`pipeline`, `graph`, `retrieval`, `drug_search`)을 직접 알 필요 없도록 단일 실행 진입점을 만든다.

UI/API는 앞으로 `app.chat.runtime.run_chat`만 호출하면 된다.

## Files

- `app/chat/runtime.py`
  - `ChatRequest`
  - `ChatResponse`
  - `ChatEngine`
  - `ChatRuntimeDependencies`
  - `run_chat`

- `app/chat/runtime_inspector.py`
  - CLI에서 runtime entrypoint를 직접 확인하는 도구

- `tests/chat/runtime/test_runtime.py`
  - graph engine 기본 실행
  - pipeline engine 선택 실행
  - string / `DrugSearchInput` 입력 허용
  - query/top_k validation

## Why This Structure

기존에는 외부에서 `run_chat_pipeline` 또는 `run_chat_graph` 중 무엇을 호출할지 직접 알아야 했다.

이 구조는 UI/API가 내부 orchestration 선택을 몰라도 되게 한다.

```text
Gradio / FastAPI
  -> run_chat(ChatRequest)
      -> graph engine or pipeline engine
      -> ChatResponse
```

## Request

```python
from app.chat.runtime import ChatRequest, run_chat

response = run_chat(
    ChatRequest(
        query="도핑 검사관 신분이 불분명하면 어떻게 확인해야 해?",
        top_k=3,
        use_llm=False,
    )
)
print(response.answer)
```

## Response Shape

`ChatResponse`는 UI/API가 바로 쓰기 좋은 형태다.

- `answer`
- `route`
- `query`
- `engine`
- `citations`
- `drug_status`
- `retrieval_attempts`
- `retrieval_retry_reason`
- `errors`

## Engine Selection

기본 engine은 `graph`다.

```python
from app.chat.runtime import ChatEngine, ChatRequest, run_chat

response = run_chat(
    ChatRequest(
        query="TUE는 어떻게 신청해?",
        engine=ChatEngine.GRAPH,
    )
)
```

비교나 fallback이 필요하면 pipeline engine도 선택할 수 있다.

```python
response = run_chat(
    ChatRequest(
        query="TUE는 어떻게 신청해?",
        engine=ChatEngine.PIPELINE,
    )
)
```

## Validation

```bash
uv run ruff check app tests
uv run pytest tests/chat/runtime/test_runtime.py
uv run pytest
uv run python -m app.chat.runtime_inspector '도핑 검사관 신분이 불분명하면 어떻게 확인해야 해?' --no-llm --engine graph --top-k 3
uv run python -m app.chat.runtime_inspector '도핑 검사관 신분이 불분명하면 어떻게 확인해야 해?' --no-llm --engine pipeline --top-k 3
```

결과:

- runtime tests: 4 passed
- full tests: 72 passed, 1 warning
- graph runtime inspector: route rag, errors 0, retrieval_attempts 1
- pipeline runtime inspector: route rag, errors 0, retrieval_attempts 1

## Next Step

이제 Gradio는 `run_chat(ChatRequest(...))`를 호출하고, `response.answer`를 화면에 표시하면 된다. FastAPI도 동일하게 `ChatRequest`를 request body로 받고 `ChatResponse`를 반환하면 된다.

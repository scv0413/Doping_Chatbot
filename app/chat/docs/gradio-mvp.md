# Gradio MVP

## Goal

Gradio MVP의 목표는 전체 챗봇 기능을 화려하게 만드는 것이 아니라, 현재 구축한 `runtime.run_chat`이 실제 사용자 화면에서 동작하는지 확인하는 것이다.

UI는 내부 구조를 알지 않는다. 사용자는 질문만 입력하고, Runtime Policy가 내부 실행 방식을 결정한다.

```text
Gradio UI
  -> ChatRequest(query only)
  -> run_chat
  -> Runtime Policy
  -> ChatResponse
  -> answer / citations 표시
```

## Files

- `app/chat/ui/gradio_app.py`
  - Gradio Blocks UI
  - `respond` 함수
  - `build_demo` 함수
  - CLI launch entrypoint

- `tests/chat/ui/test_gradio_app.py`
  - UI 응답 formatter 검증
  - 빈 질문 처리 검증
  - Gradio Blocks 생성 검증

## Dependency

추가된 dependency:

```toml
gradio>=5.0.0,<6.0.0
```

`uv add gradio>=5.0.0,<6.0.0` 실행 과정에서 Gradio 호환성 때문에 `pydantic`이 `2.13.4`에서 `2.12.3`으로 조정되었다.

이 변경이 기존 구조를 흔드는지 확인하기 위해 전체 테스트를 다시 실행했다.

## UI Scope

현재 MVP 화면은 다음만 제공한다.

- 질문 입력
- 답변 출력
- 근거 citation 출력

검색 문서 수, LLM 답변 사용 여부, graph/pipeline engine 같은 개발자 옵션은 화면에서 제거했다. 운영 기본값은 Runtime Policy가 결정한다.

로그인, 대화 히스토리, 보고서 생성, 알림 기능은 아직 포함하지 않는다.

## Run

```bash
uv run python -u -m app.chat.ui.gradio_app --server-port 7861
```

확인된 실행 로그:

```text
* Running on local URL:  http://127.0.0.1:7861
```

같은 권한 컨텍스트에서 포트 확인:

```bash
curl -I http://127.0.0.1:7861
```

결과:

```text
HTTP/1.1 200 OK
```

## Validation

```bash
uv run ruff check app tests
uv run pytest tests/chat/ui/test_gradio_app.py tests/chat/runtime/test_runtime.py
uv run pytest
uv run python -m compileall -q app tests
```

결과:

- UI/runtime tests: 8 passed
- full tests: 121 passed, 1 warning
- ruff: pass
- compileall: pass

## Detected Errors and Fixes

1. 문자열 join syntax error

파일 생성 과정에서 `"\n".join(...)`이 물리적 줄바꿈으로 깨져 syntax error가 발생했다.

수정: `"\n".join(lines)` 형태로 복구했다.

2. Citation object type mismatch

테스트에서 `ChatResponse.citations`에 내부 retrieval 객체인 `RetrievalMatch`를 넣었다. 하지만 runtime 응답 계약은 UI용 `CitationSummary`다.

수정: 테스트 fixture를 `CitationSummary`로 변경했다.

3. 서버 확인에서 sandbox curl 실패

Gradio 서버는 escalated context에서 실행되었고, 일반 sandbox `curl`에서는 연결 실패했다. 같은 escalated context에서 확인하니 `HTTP 200 OK`가 나왔다.

## Structure Judgment

Gradio UI는 `runtime` 위에 얇게 올라간다. 따라서 기존 retrieval, drug_search, graph, answer 구조를 직접 건드리지 않는다.

이 구조는 다음 단계의 FastAPI wrapper에도 그대로 사용할 수 있다.


## Final UI Cleanup

사용자 화면에서 내부 실행 정보를 제거했다.

변경 전:

- top_k slider
- LLM checkbox
- graph/pipeline radio
- route/retry/error metadata 표시

변경 후:

- 질문 textbox
- 답변 markdown
- 근거 markdown

이렇게 바꾼 이유는 이 챗봇의 목적이 사용자가 내부 RAG 설정을 고르는 것이 아니라, 도핑 관련 질문을 빠르게 입력하고 근거 기반 답변을 받는 것이기 때문이다. 내부 선택은 Runtime Policy가 담당한다.

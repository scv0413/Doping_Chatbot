# LangGraph Guardrails

## 목적

LangGraph 전환 전에 다음 세 가지 위험을 막기 위한 기본 정책을 정의한다.

1. state bloat
2. infinite loop
3. token issue

현재 결론은 다음과 같다.

```text
기본 방어벽: trim_messages
고도화 후 조건부 확장: summarization node
마지막 정리 지점: exit node
실행 안전장치: recursion_limit
```

## 1. State Bloat 방지

LangGraph state는 데이터 저장소가 아니라 node 간 계약이다.

state에 넣을 것:

```text
search_input
RouteDecision
DrugSearchResult 요약
retrieval_query / rewritten_query
list[RetrievalMatch]
answer
errors
step_count / attempts counters
```

state에 넣지 말 것:

```text
원본 PDF 전체 text
KADA raw JSON 전체 payload
검색된 page 전체
모든 prompt/debug text
전체 대화 history
```

원칙:

```text
state에는 다음 node가 반드시 필요한 정보만 둔다.
디버깅 정보는 state가 아니라 LangSmith trace 또는 local log로 보낸다.
```

## 2. Infinite Loop 방지

초기 LangGraph는 loop 없는 DAG로 구성한다.

```text
START
-> route_node
-> drug_search_node / query_rewrite_node / retrieval_node
-> answer_node
-> exit_node
-> END
```

실행 시 기본 recursion limit을 둔다.

```python
graph.invoke(input_state, config={"recursion_limit": 8})
```

나중에 재검색이나 agentic tool loop가 들어가면 다음 counter를 둔다.

```text
retrieval_attempts <= 2
tool_call_count <= 3
step_count <= 8
```

## 3. Token Issue 방지

초기 방어벽은 `trim_messages`다.

현재 구현 위치:

```text
app/chat/answer/chain.py
```

현재 정책:

```text
DEFAULT_MAX_PROMPT_TOKENS = 6000
TRIM_TEXT_CHUNK_SIZE = 800
system message 유지
user message가 사라질 경우 fallback user message 복구
```

중요한 이유:

```text
RAG에서 많은 context를 넣는다고 답변이 항상 좋아지지 않는다.
너무 긴 context는 비용, 지연, irrelevant evidence 문제를 만든다.
```

## 4. Summarization Node 정책

요약 노드는 처음부터 기본으로 넣지 않는다.

이유:

```text
도핑 도메인에서는 약물명, 용량, 투여경로, 경기기간 같은 조건이 요약 중 사라질 수 있다.
요약 결과가 공식 근거처럼 오해될 수 있다.
```

따라서 summarization node는 조건부로만 추가한다.

실행 조건 후보:

```text
conversation turns > 6
message token estimate > 6000
tool_call_count > 3
report generation mode
```

요약 가능한 것:

```text
이전 대화 history
반복 tool 결과
사용자 선호 또는 상황 맥락
```

요약하지 말아야 할 것:

```text
공식 규정 citation
약물명
성분명
용량/농도 기준
투여경로
경기기간 여부
TUE 필수 조건
```

## 5. Exit Node 정책

exit node는 어떤 경로로 왔든 최종 응답 형태를 정리한다.

역할:

```text
answer가 비어 있으면 fallback answer 생성
errors 정리
사용자에게 보여줄 response shape 정리
내부 debug 정보 제거
citation / warning section 확인
```

추천 최종 response:

```text
answer
route
citations
warnings
errors_for_display
```

## 6. 현재 구현 상태

완료:

```text
trim_messages 기본 방어벽
system message 보존
user message fallback 복구
query_rewriter 실패 fallback
pipeline errors 기록
```

아직 미구현:

```text
LangGraph state.py
nodes.py
graph.py
exit_node
summarization_node
```

다음 구현 순서:

```text
1. graph/state.py
2. graph/nodes.py
3. graph/graph.py
4. graph/runner.py
5. exit_node
6. LangSmith trace
7. summarization node는 multi-turn 이후 조건부 추가
```

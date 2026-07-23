# Project Current Status and Next Steps

## 현재 위치

이 프로젝트는 현재 “실무형 RAG 챗봇의 serving foundation”까지 도달했다.

완료된 큰 흐름은 다음과 같다.

```text
기획/목적 정의
  -> 문서 source inventory
  -> PDF inspection/preprocessing
  -> chunking
  -> embedding/indexing
  -> retrieval/rewrite 실험
  -> drug_search + RAG 결합
  -> pharmacology_info 결합
  -> answer formatter/chain
  -> LangGraph 1차 graph
  -> LangSmith retrieval/answer/graph eval
  -> Gradio MVP
  -> FastAPI REST API
  -> Docker packaging
  -> API error standardization
  -> request_id + JSON structured logging
```

즉, 아직 “완성된 서비스”라기보다는, 실제 운영 가능한 API 기반이 만들어진 상태다. 지금부터 남은 작업은 기능을 더 붙이는 일보다 운영 안정성, 평가 품질, 보안, 배포 자동화, agentic 확장이다.

## 현재 완성된 주요 구조

```text
app/preprocess/
  문서 로딩, 정제, chunking

app/chat/retrieval/
  Chroma indexing/retrieval/query rewrite

app/chat/drug_search/
  KADA 약물검색 성격의 도핑 위험 조회

app/chat/pharmacology/
  반감기/대사/배출 참고 정보

app/chat/policy/
  6 rules와 safety caveat

app/chat/answer/
  deterministic formatter와 LLM answer chain

app/chat/graph/
  LangGraph 실행 흐름

app/chat/runtime.py
  UI/API 공통 entrypoint

app/chat/interfaces/api/
  FastAPI REST API, error handling, readiness, logging

app/chat/interfaces/ui/
  Gradio MVP
```

## 남은 작업

### 1. 평가 고도화

가장 먼저 할 만한 일은 반감기/pharmacology 전용 LangSmith eval이다.

목표:

- 반감기를 복용 가능 판정으로 오해시키지 않는가
- 제품명/성분명/복용량/복용시각/경기시각 확인을 요구하는가
- KADA/팀닥터/약사 확인으로 연결하는가
- 경기기간 중 금지 가능성을 단정 없이 설명하는가

초기에는 LLM judge보다 rule-based eval로 시작하는 것이 좋다.

### 2. API 보안

외부 공개 전에는 인증과 rate limit이 필요하다.

후보:

- API key header
- local/admin mode 분리
- rate limiting
- CORS policy
- request body size limit

### 3. OpenAPI 문서 보강

현재 API endpoint는 동작하지만, OpenAPI response examples가 부족하다.

추가할 것:

- 성공 response example
- validation_error example
- internal_server_error example
- ChatRequest field 설명

### 4. Docker/CI 운영 강화

현재 Docker build/run은 검증되었다. 다음은 CI와 운영 환경을 더 단단히 만드는 것이다.

후보:

- GitHub Actions 실제 실행 확인
- image size 최적화
- CI artifact cache
- Docker compose smoke test
- production env sample

### 5. MCP / Agentic tool 확장

초기 목표였던 MCP tool화는 아직 남아 있다. 지금 구조에서는 `run_chat`과 retrieval/drug/pharmacology service가 분리되어 있으므로 MCP로 감싸기 좋은 상태다.

후보 tool:

- `search_doping_documents`
- `search_drug_status`
- `lookup_pharmacology_info`
- `generate_doping_report`
- `send_alert`

### 6. 데이터 확장

현재 한국어 PDF 일부 품질 문제는 영어 원문 pipeline 우선 전략으로 보류했다. 이후 다음을 추가할 수 있다.

- OCR pipeline
- 추가 KADA/WADA 문서
- drug product alias DB
- pharmacology source DB

## 추천 다음 순서

```text
1. pharmacology/half-life LangSmith eval
2. API auth/rate limit
3. OpenAPI response examples
4. MCP tool wrapper 설계
5. OCR/data expansion
```

현재 가장 추천하는 다음 작업은 `pharmacology/half-life LangSmith eval`이다. 이유는 최근에 pharmacology 기능을 추가했고, 이 기능은 오해 위험이 크기 때문에 평가 기준을 먼저 고정하는 것이 좋기 때문이다.

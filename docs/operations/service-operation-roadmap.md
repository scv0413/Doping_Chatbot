# Service Operation Roadmap

## 현재 단계

현재 프로젝트는 local RAG prototype을 넘어 Dockerized FastAPI serving foundation까지 도달했다.

```text
Prototype complete
RAG pipeline complete
Graph orchestration complete
Eval foundation complete
FastAPI API complete
Docker runtime complete
Operational logging/error foundation complete
```

## 다음 실행 우선순위

### 1. Half-life / Pharmacology LangSmith Eval

목적: 반감기 답변이 위험하게 단정되지 않도록 평가한다.

작업:

- `half_life_cases.py` 생성
- rule-based evaluator 작성
- LangSmith experiment 실행
- failure case 문서화

### 2. API Auth and Rate Limit

목적: 아무나 비용이 드는 API를 호출하지 못하게 한다.

작업:

- `X-API-Key` 인증
- local/dev bypass 설정
- role 설계
- rate limit 계획

### 3. OpenAPI Examples

목적: 외부 client가 API를 쉽게 쓸 수 있게 한다.

작업:

- ChatRequest field description
- ChatResponse example
- ApiErrorResponse examples

### 4. CI/CD Deployment

목적: 손으로 서버에 들어가 pull/restart하지 않도록 한다.

작업:

- GitHub Actions docker build 실제 확인
- image registry push
- server deploy script
- rollback plan

### 5. MCP / Agentic Tool Layer

목적: LLM이 단순 답변을 넘어 도구를 사용하도록 한다.

작업:

- retrieval tool
- drug search tool
- pharmacology tool
- report generation tool
- alert sending tool

## 추천 다음 작업

가장 추천하는 다음 작업은 Half-life / Pharmacology LangSmith Eval이다. 이유는 최근에 추가한 기능이고, 실제 선수 판단에 영향을 줄 수 있으므로 정량/정성 평가 기준을 먼저 고정해야 하기 때문이다.

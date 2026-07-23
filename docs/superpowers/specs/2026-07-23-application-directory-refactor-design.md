# 애플리케이션 디렉토리 재구성 설계

## 목표

프로젝트를 문서 전처리, 챗봇 도메인 기능, 실행 오케스트레이션, 외부 인터페이스,
운영 문서로 분리한다. 이 리팩터링은 기능을 새로 만들지 않으며, 기존 API, Gradio,
LangGraph, MCP, 전처리, 평가 실행 결과를 유지한다.

## 최종 구조

~~~text
app/
  core/
    config.py
  preprocess/
    sources/
    pdf/
    transform/
    ocr/
    manual_loader.py
  chat/
    domain/
      retrieval/
      drug_search/
      pharmacology/
      answer/
      policy/
    orchestration/
      router/
      pipeline/
      graph/
      agent/
    tools/
    interfaces/
      api/
      ui/
      mcp/
    runtime.py
    evals/
data/
  raw/
  processed/
  indexes/
  operations/
scripts/
tests/
  preprocess/
  chat/
    domain/
    orchestration/
    interfaces/
    tools/
    evals/
docs/
  architecture/
  operations/
  evaluation/
  superpowers/
local_archive/
~~~

## 책임 경계

- app/core: 전처리와 챗봇이 함께 쓰는 환경 설정, 경로, 변경되지 않는 공통 상수만 둔다.
- app/preprocess: source manifest부터 PDF 추출, OCR, 페이지 정제, 청킹까지 검색 데이터 준비를 담당한다.
- app/chat/domain: retrieval, 약물 검색, 약리 정보, 답변 정책처럼 도핑 챗봇의 업무 규칙과 기능을 둔다.
- app/chat/orchestration: 질문 라우팅, pipeline, LangGraph, agent plan처럼 도메인 기능의 실행 순서를 담당한다.
- app/chat/interfaces: FastAPI, Gradio, MCP처럼 외부 호출 형식과 transport를 담당한다.
- app/chat/tools: 내부 tool 계약, registry, 실행 adapter를 둔다. domain 기능을 호출하지만 interface에 의존하지 않는다.
- app/chat/evals: LangSmith와 로컬 release gate처럼 품질을 측정하는 실행 코드를 둔다.
- data: 원본, 처리 결과, index, 운영 기록을 보관한다. Python 구현 코드를 두지 않는다.
- docs: Git으로 관리할 설계와 운영 문서를 둔다.
- local_archive: 발표 HTML, 개인 학습 자료처럼 보관하되 제출 저장소에는 포함하지 않을 자료를 둔다.

## 의존성 방향

~~~text
interfaces -> runtime/orchestration -> domain/tools -> core
preprocess -> core
scripts -> preprocess, domain.retrieval, core
evals -> runtime/orchestration/domain/tools
~~~

상위 계층이 하위 계층을 호출한다. domain은 FastAPI, Gradio, MCP를 import하지 않는다.
tools는 도메인 기능을 호출할 수 있지만 API나 UI를 import하지 않는다.

## config 이동 원칙

현재 app/chat/config.py의 Settings를 app/core/config.py로 이동한다. 이동 중에는
app/chat/config.py를 settings 재노출 compatibility shim으로 유지할 수 있다. 모든
import가 app.core.config로 바뀌고 전체 테스트가 통과한 뒤 shim을 제거한다. 이 방식은
한 커밋에서 모든 실행 경로가 끊어지는 위험을 줄인다.

runtime_policy가 graph의 recursion limit을 import하는 현재 역방향 의존성은 core의
공통 설정 또는 orchestration의 명시적 입력으로 바꾼다. policy가 graph 구현을 직접
알지 않게 한다.

## 이동 원칙

1. Python 파일은 git mv로 이동해 history를 최대한 보존한다.
2. 한 커밋에는 한 책임 단위만 이동한다.
3. 파일 이동 직후 import, module execution, README와 운영 문서의 실행 명령을 함께 수정한다.
4. generated data와 Chroma index는 이동하지 않는다.
5. local_archive는 .gitignore에 추가한 뒤 기존 발표용 HTML과 개인 학습 자료만 이동한다.
6. app/chat/docs의 Git 관리 운영 문서는 docs/architecture, docs/operations,
   docs/evaluation으로 이동한다. docs/superpowers는 유지한다.
7. source manifest, PDF, processed JSONL 경로는 data/ 아래에서 유지한다.

## 단계별 전환

### Phase 1: 공통 기반과 문서 경계

- app/core/config.py를 만들고 config compatibility shim을 둔다.
- docs 하위의 architecture, operations, evaluation을 만들고 app/chat/docs의 운영 문서를 분류한다.
- local_archive를 Git ignore로 만들고 발표 HTML과 개인 자료를 옮긴다.
- 기능 코드는 아직 대규모 이동하지 않는다.

### Phase 2: preprocess 세분화

- schemas, manifest, inventory를 preprocess/sources로 이동한다.
- pdf_loader, pdf_inspector를 preprocess/pdf로 이동한다.
- preprocess, chunker, processed_inspector를 preprocess/transform으로 이동한다.
- OCR 패키지는 preprocess/ocr에 둔다.
- scripts/data_refresh.py와 README의 전처리 명령을 수정한다.

### Phase 3: chat domain 세분화

- retrieval, drug_search, pharmacology, answer, policy를 chat/domain 아래로 이동한다.
- 각 하위 패키지는 현재 기능 단위 그대로 유지한다.
- chat/config compatibility shim을 제거하기 전 모든 domain import를 core config로 변경한다.

### Phase 4: orchestration과 interface 세분화

- router, pipeline, graph, agent를 chat/orchestration 아래로 이동한다.
- api, ui, mcp를 chat/interfaces 아래로 이동한다.
- runtime.py는 app/chat/에 남겨 외부 코드가 호출할 통합 entrypoint로 유지한다.
- policy와 graph 사이의 역방향 의존성을 제거한다.

### Phase 5: tests, scripts, 문서, 실행 회귀

- tests는 구현 구조를 반영해 preprocess와 chat/domain, orchestration, interfaces,
  tools, evals로 이동한다.
- 모든 scripts, Dockerfile, docker-compose, GitHub workflow, README, 운영 문서의
  import와 module command를 새 경로로 변경한다.
- full test, Ruff, compileall, local API smoke, Gradio import, release quality gate,
  Docker build를 실행한다.

## 호환성과 실패 처리

- 각 phase가 끝난 시점에는 기존 테스트와 최소 한 개의 실제 실행 명령이 통과해야 한다.
- import 오류가 발생하면 다음 phase로 넘어가지 않고 해당 이동 커밋에서 수정한다.
- public API path, request/response contract, MCP tool name, data directory path는 유지한다.
- 테스트나 smoke에서 기능 회귀가 확인되면 해당 phase의 이동만 되돌리는 대신, 원인을
  분리해 수정하고 같은 검증을 다시 실행한다.
- docs 이동 실패는 실행 코드와 별도 커밋으로 다루되, README 링크가 깨진 상태로
  남지 않게 한다.

## 완료 기준

- 사용자가 요청한 최종 디렉토리 구조가 구현된다.
- 모든 Python import가 새 경계를 따른다.
- app/chat/config.py compatibility shim은 제거된다.
- app/chat/docs는 비어 있거나 제거되고, Git 관리 문서는 docs로 이동한다.
- local_archive는 Git ignore 상태다.
- Ruff, 전체 pytest, compileall, release quality gate, staging smoke, Docker build가 통과한다.
- README의 전처리, API, Gradio, MCP, evaluation 명령이 모두 새 경로에서 실행된다.


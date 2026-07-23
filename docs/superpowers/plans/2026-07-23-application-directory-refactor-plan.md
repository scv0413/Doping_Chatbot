# 애플리케이션 디렉토리 재구성 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** 기능과 외부 계약을 바꾸지 않고 app, tests, docs를 전처리·도메인·오케스트레이션·인터페이스 책임으로 재구성한다.

**Architecture:** core는 공통 설정만 제공한다. preprocess는 문서에서 검색용 데이터를 만드는 파이프라인을 담당한다. chat은 domain, orchestration, tools, interfaces, evals로 분리하며 runtime.py를 외부 통합 진입점으로 유지한다. 파일 이동은 git mv를 사용하고 각 phase에서 import와 실행 명령을 함께 갱신한다.

**Tech Stack:** Python 3.12, uv, pytest, Ruff, FastAPI, Gradio, LangGraph, LangSmith, Docker.

## Global Constraints

- public API path와 request/response 형식을 변경하지 않는다.
- Gradio 실행 명령, MCP tool name, source manifest와 data 경로를 변경하지 않는다.
- generated data와 Chroma index를 이동하거나 커밋하지 않는다.
- 동작 변경 없이 import path와 파일 위치만 변경한다. 역방향 의존성 제거는 명시한 Task에서만 수행한다.
- 각 Task는 시작 전에 git status가 깨끗한지 확인하고, 끝에 focused test와 Ruff를 실행한다.
- 각 Task가 통과하면 즉시 독립 커밋한다.
- local_archive는 Git ignore 상태로만 만들며, Git 관리 운영 문서를 보관 디렉토리로 옮기지 않는다.

---

## 최종 파일 이동표

### Core

- app/chat/config.py -> app/core/config.py
- app/chat/config.py는 Task 1과 Task 5 사이에서 settings 재노출 shim으로만 유지한다.

### Preprocess

- app/preprocess/schemas.py -> app/preprocess/sources/schemas.py
- app/preprocess/manifest.py -> app/preprocess/sources/manifest.py
- app/preprocess/source_inventory.py -> app/preprocess/sources/inventory.py
- app/preprocess/pdf_loader.py -> app/preprocess/pdf/loader.py
- app/preprocess/pdf_inspector.py -> app/preprocess/pdf/inspector.py
- app/preprocess/preprocess.py -> app/preprocess/transform/preprocess.py
- app/preprocess/chunker.py -> app/preprocess/transform/chunker.py
- app/preprocess/processed_inspector.py -> app/preprocess/transform/inspector.py
- app/preprocess/manual_loader.py는 유지한다.
- OCR 구현이 시작되면 app/preprocess/ocr/에 둔다.

### Chat

- app/chat/retrieval -> app/chat/domain/retrieval
- app/chat/drug_search -> app/chat/domain/drug_search
- app/chat/pharmacology -> app/chat/domain/pharmacology
- app/chat/answer -> app/chat/domain/answer
- app/chat/policy -> app/chat/domain/policy
- app/chat/router -> app/chat/orchestration/router
- app/chat/pipeline -> app/chat/orchestration/pipeline
- app/chat/graph -> app/chat/orchestration/graph
- app/chat/agent -> app/chat/orchestration/agent
- app/chat/api -> app/chat/interfaces/api
- app/chat/ui -> app/chat/interfaces/ui
- app/chat/mcp -> app/chat/interfaces/mcp
- app/chat/tools, app/chat/evals, app/chat/runtime.py는 유지한다.

### Tests

- tests/preprocess는 sources, pdf, transform, ocr 하위 구조를 따른다.
- tests/chat/answer, drug_search, pharmacology, policy, retrieval -> tests/chat/domain/
- tests/chat/agent, graph, pipeline, router -> tests/chat/orchestration/
- tests/chat/api, ui, mcp -> tests/chat/interfaces/
- tests/chat/tools, tests/chat/evals는 유지한다.

### Documentation

- app/chat/docs의 Markdown은 docs/architecture, docs/operations, docs/evaluation으로 분류해 이동한다.
- app/chat/docs의 HTML 파일은 local_archive/presentations/으로 이동한다.
- docs/superpowers는 현재 위치를 유지한다.

## Task 1: Core 설정 이동과 compatibility shim

**Files:**
- Create: app/core/__init__.py
- Create: app/core/config.py
- Modify: app/chat/config.py
- Modify: app/preprocess/chunker.py
- Modify: app/preprocess/manual_loader.py
- Modify: app/preprocess/preprocess.py
- Modify: app/preprocess/processed_inspector.py
- Modify: chat modules that import app.chat.config
- Test: tests/chat/api/test_security.py
- Test: tests/chat/api/test_readiness.py

**Interfaces:**
- Produces: app.core.config.settings as the canonical Settings singleton.
- Compatibility: app.chat.config.settings re-exports app.core.config.settings until Task 5.
- Consumes: existing environment variables with unchanged aliases.

- [ ] **Step 1: baseline을 실행한다.**

~~~bash
git status --short
uv run ruff check app tests scripts
uv run pytest
~~~

Expected: clean status, Ruff PASS, existing test suite PASS.

- [ ] **Step 2: settings identity 테스트를 작성한다.**

~~~python
from app.chat.config import settings as legacy_settings
from app.core.config import settings


def test_legacy_config_reexports_canonical_settings() -> None:
    assert legacy_settings is settings
~~~

Expected file: tests/test_core_config.py

- [ ] **Step 3: 새 core config와 shim을 구현한다.**

~~~bash
mkdir -p app/core
git mv app/chat/config.py app/core/config.py
touch app/core/__init__.py
~~~

Create app/chat/config.py with only:

~~~python
from app.core.config import Settings, settings

__all__ = ["Settings", "settings"]
~~~

Replace direct imports in Python files from app.chat.config to app.core.config. Keep the shim until all phases are completed.

- [ ] **Step 4: focused verification을 실행한다.**

~~~bash
uv run pytest tests/test_core_config.py tests/chat/api/test_security.py tests/chat/api/test_readiness.py -v
uv run ruff check app/core app/chat/config.py app/preprocess tests/test_core_config.py
uv run python -m compileall -q app
~~~

Expected: all tests PASS and no compile errors.

- [ ] **Step 5: 커밋한다.**

~~~bash
git add app/core app/chat/config.py app/preprocess tests/test_core_config.py
git commit -m "refactor: move shared settings to core"
~~~

## Task 2: Preprocess 패키지 세분화

**Files:**
- Create: app/preprocess/sources/__init__.py
- Create: app/preprocess/pdf/__init__.py
- Create: app/preprocess/transform/__init__.py
- Move: schemas.py, manifest.py, source_inventory.py, pdf_loader.py, pdf_inspector.py, preprocess.py, chunker.py, processed_inspector.py according to the table.
- Modify: app/preprocess/manual_loader.py
- Modify: scripts/data_refresh.py
- Modify: README.md and docs commands for preprocess modules.
- Move tests: tests/preprocess/test_source_inventory.py -> tests/preprocess/sources/test_inventory.py

**Interfaces:**
- Produces: app.preprocess.sources, app.preprocess.pdf, app.preprocess.transform packages.
- Preserves: load_source_manifest, load_pdf_pages, preprocess_manifest, chunk_pages, build_source_inventory names and behavior.
- Consumes: app.core.config.settings from Task 1.

- [ ] **Step 1: import regression tests를 작성한다.**

~~~python
from app.preprocess.pdf.loader import load_pdf_pages
from app.preprocess.sources.inventory import build_source_inventory
from app.preprocess.sources.manifest import load_source_manifest
from app.preprocess.transform.chunker import chunk_pages
from app.preprocess.transform.preprocess import preprocess_manifest


def test_preprocess_public_imports_are_available() -> None:
    assert all(
        [load_pdf_pages, build_source_inventory, load_source_manifest, chunk_pages, preprocess_manifest]
    )
~~~

Expected file: tests/preprocess/test_preprocess_package_layout.py

- [ ] **Step 2: 실패를 확인한다.**

~~~bash
uv run pytest tests/preprocess/test_preprocess_package_layout.py -v
~~~

Expected: FAIL because the target packages do not exist.

- [ ] **Step 3: files를 git mv로 이동하고 imports를 갱신한다.**

~~~bash
mkdir -p app/preprocess/sources app/preprocess/pdf app/preprocess/transform
git mv app/preprocess/schemas.py app/preprocess/sources/schemas.py
git mv app/preprocess/manifest.py app/preprocess/sources/manifest.py
git mv app/preprocess/source_inventory.py app/preprocess/sources/inventory.py
git mv app/preprocess/pdf_loader.py app/preprocess/pdf/loader.py
git mv app/preprocess/pdf_inspector.py app/preprocess/pdf/inspector.py
git mv app/preprocess/preprocess.py app/preprocess/transform/preprocess.py
git mv app/preprocess/chunker.py app/preprocess/transform/chunker.py
git mv app/preprocess/processed_inspector.py app/preprocess/transform/inspector.py
git mv tests/preprocess/test_source_inventory.py tests/preprocess/sources/test_inventory.py
~~~

Add empty __init__.py files. Update all imports in app, tests, scripts, README, and Git-managed docs. Do not modify data paths.

- [ ] **Step 4: preprocess regression을 실행한다.**

~~~bash
uv run pytest tests/preprocess -v
uv run ruff check app/preprocess tests/preprocess scripts/data_refresh.py
uv run python -m app.preprocess.transform.preprocess
uv run python -m app.preprocess.transform.chunker
~~~

Expected: tests and Ruff PASS. Module commands create the same local processed outputs without changing source status.

- [ ] **Step 5: 커밋한다.**

~~~bash
git add app/preprocess tests/preprocess scripts/data_refresh.py README.md docs
git commit -m "refactor: organize preprocess packages"
~~~

## Task 3: Chat domain 이동

**Files:**
- Create: app/chat/domain/__init__.py
- Move: retrieval, drug_search, pharmacology, answer, policy directories according to the table.
- Move tests: matching tests/chat directories to tests/chat/domain/.
- Modify: all application, test, script, and documentation imports that reference the moved modules.

**Interfaces:**
- Produces: app.chat.domain.retrieval, drug_search, pharmacology, answer, policy.
- Preserves: public function names including search, rewrite_query, generate_answer, search_kada_drugs, search_pharmacology_info, decide_runtime_policy.
- Consumes: app.core.config and existing Pydantic models.

- [ ] **Step 1: moved domain import tests를 작성한다.**

~~~python
from app.chat.domain.answer.chain import generate_answer
from app.chat.domain.drug_search.kada_client import search_kada_drugs
from app.chat.domain.pharmacology.service import search_pharmacology_info
from app.chat.domain.retrieval.retriever import search
from app.chat.domain.policy.answer_policy import OFFICIAL_DECISION_DISCLAIMER


def test_domain_imports_are_available() -> None:
    assert all([generate_answer, search_kada_drugs, search_pharmacology_info, search])
    assert OFFICIAL_DECISION_DISCLAIMER
~~~

Expected file: tests/chat/domain/test_chat_domain_package_layout.py

- [ ] **Step 2: 실패를 확인한다.**

~~~bash
uv run pytest tests/chat/domain/test_chat_domain_package_layout.py -v
~~~

Expected: FAIL because app.chat.domain packages do not exist.

- [ ] **Step 3: domain packages를 git mv로 이동하고 imports를 갱신한다.**

~~~bash
mkdir -p app/chat/domain tests/chat/domain
git mv app/chat/retrieval app/chat/domain/retrieval
git mv app/chat/drug_search app/chat/domain/drug_search
git mv app/chat/pharmacology app/chat/domain/pharmacology
git mv app/chat/answer app/chat/domain/answer
git mv app/chat/policy app/chat/domain/policy
git mv tests/chat/retrieval tests/chat/domain/retrieval
git mv tests/chat/drug_search tests/chat/domain/drug_search
git mv tests/chat/pharmacology tests/chat/domain/pharmacology
git mv tests/chat/answer tests/chat/domain/answer
git mv tests/chat/policy tests/chat/domain/policy
~~~

Update every app.chat.domain.retrieval, drug_search, pharmacology, answer, policy import. Do not move router, graph, API, UI, MCP, tools, evals, or runtime in this task.

- [ ] **Step 4: focused domain regression을 실행한다.**

~~~bash
uv run pytest tests/chat/domain tests/chat/tools tests/chat/evals -v
uv run ruff check app/chat/domain app/chat/tools app/chat/evals tests/chat/domain
uv run python -c "from app.chat.domain.retrieval.retriever import search; print(search.__name__)"
~~~

Expected: tests and Ruff PASS; retriever command returns local retrieval matches.

- [ ] **Step 5: 커밋한다.**

~~~bash
git add app/chat/domain tests/chat/domain app/chat tools tests scripts README.md docs
git commit -m "refactor: group chat domain modules"
~~~

## Task 4: Orchestration 이동과 policy 역방향 의존성 제거

**Files:**
- Create: app/chat/orchestration/__init__.py
- Move: router, pipeline, graph, agent directories according to the table.
- Move tests: tests/chat/router, pipeline, graph, agent -> tests/chat/orchestration/.
- Modify: app/chat/domain/policy/runtime_policy.py
- Modify: app/chat/runtime.py
- Modify: imports in tools, evals, interfaces, tests, scripts, README, docs.

**Interfaces:**
- Produces: app.chat.orchestration.router, pipeline, graph, agent.
- Preserves: run_chat_graph, run_chat_pipeline, route_question, build_agent_tool_plan.
- Removes: domain.policy.runtime_policy import of orchestration.graph.DEFAULT_RECURSION_LIMIT.
- Uses: a DEFAULT_RECURSION_LIMIT defined in app.core.config or passed as a policy default.

- [ ] **Step 1: policy independence 테스트를 작성한다.**

~~~python
import sys

from app.chat.domain.policy.runtime_policy import decide_runtime_policy


def test_runtime_policy_does_not_import_graph_module() -> None:
    sys.modules.pop("app.chat.orchestration.graph.graph", None)

    decide_runtime_policy(query="S0 비승인약물이 뭐야?")

    assert "app.chat.orchestration.graph.graph" not in sys.modules
~~~

Expected file: tests/chat/domain/policy/test_runtime_policy_dependency.py

- [ ] **Step 2: 실패를 확인한다.**

~~~bash
uv run pytest tests/chat/domain/policy/test_runtime_policy_dependency.py -v
~~~

Expected: FAIL before runtime_policy stops importing graph.

- [ ] **Step 3: packages를 이동하고 recursion default ownership을 고친다.**

~~~bash
mkdir -p app/chat/orchestration tests/chat/orchestration
git mv app/chat/router app/chat/orchestration/router
git mv app/chat/pipeline app/chat/orchestration/pipeline
git mv app/chat/graph app/chat/orchestration/graph
git mv app/chat/agent app/chat/orchestration/agent
git mv tests/chat/router tests/chat/orchestration/router
git mv tests/chat/pipeline tests/chat/orchestration/pipeline
git mv tests/chat/graph tests/chat/orchestration/graph
git mv tests/chat/agent tests/chat/orchestration/agent
~~~

Move DEFAULT_RECURSION_LIMIT to app.core.config as a settings-backed constant or use a default argument in decide_runtime_policy. Update runtime.py to call the new orchestration paths. Keep recursion limit value 12.

- [ ] **Step 4: graph and runtime regression을 실행한다.**

~~~bash
uv run pytest tests/chat/orchestration tests/chat/domain/policy tests/chat/tools -v
uv run ruff check app/chat/orchestration app/chat/domain/policy app/chat/runtime.py tests/chat
uv run python -m app.chat.runtime_inspector "도핑 검사관 신분이 불분명하면 어떻게 확인해야 해?" --no-llm --engine graph --top-k 3
~~~

Expected: tests and Ruff PASS; runtime inspector returns a graph result without API startup.

- [ ] **Step 5: 커밋한다.**

~~~bash
git add app/core app/chat/orchestration app/chat/domain/policy app/chat/runtime.py tests/chat scripts README.md docs
git commit -m "refactor: separate chat orchestration"
~~~

## Task 5: Interface 이동과 config shim 제거

**Files:**
- Create: app/chat/interfaces/__init__.py
- Move: api, ui, mcp according to the table.
- Move tests: tests/chat/api, ui, mcp -> tests/chat/interfaces/.
- Modify: Dockerfile, docker-compose.yml, scripts/staging_smoke.py, scripts/mcp_smoke.py, README.md, docs, workflow references.
- Delete: app/chat/config.py compatibility shim.

**Interfaces:**
- Produces: app.chat.interfaces.api, ui, mcp.
- Preserves: FastAPI routes /health, /ready, /api/v1/chat-responses, /api/v1/debug/chat-responses; Gradio UI; FastMCP tool names.
- Consumes: app.chat.runtime as the stable entrypoint and app.core.config.settings.

- [ ] **Step 1: interface import and route contract tests를 작성한다.**

~~~python
from app.chat.interfaces.api.main import create_app
from app.chat.interfaces.mcp.fastmcp_server import create_mcp_server
from app.chat.interfaces.ui.gradio_app import build_demo


def test_interfaces_are_importable() -> None:
    assert create_app
    assert create_mcp_server
    assert build_demo
~~~

Expected file: tests/chat/interfaces/test_package_layout.py

- [ ] **Step 2: 실패를 확인한다.**

~~~bash
uv run pytest tests/chat/interfaces/test_package_layout.py -v
~~~

Expected: FAIL because app.chat.interfaces does not exist.

- [ ] **Step 3: interface packages를 이동하고 entrypoints를 갱신한다.**

~~~bash
mkdir -p app/chat/interfaces tests/chat/interfaces
git mv app/chat/api app/chat/interfaces/api
git mv app/chat/ui app/chat/interfaces/ui
git mv app/chat/mcp app/chat/interfaces/mcp
git mv tests/chat/api tests/chat/interfaces/api
git mv tests/chat/ui tests/chat/interfaces/ui
git mv tests/chat/mcp tests/chat/interfaces/mcp
git rm app/chat/config.py
~~~

Update Docker and Uvicorn module targets to app.chat.interfaces.api.main. Update Gradio and FastMCP module commands. Replace any final app.chat.config import with app.core.config.

- [ ] **Step 4: interface and container regression을 실행한다.**

~~~bash
uv run pytest tests/chat/interfaces tests/chat/tools -v
uv run ruff check app/chat/interfaces app/chat/runtime.py tests/chat/interfaces
uv run python -m app.chat.interfaces.ui.gradio_app --help
uv run python -m app.chat.interfaces.mcp.fastmcp_server --help
docker compose build api
~~~

Expected: imports, help commands, tests, Ruff, and Docker build PASS.

- [ ] **Step 5: 커밋한다.**

~~~bash
git add app/chat/interfaces app/chat/runtime.py app/core tests/chat/interfaces Dockerfile docker-compose.yml scripts README.md docs .github
git commit -m "refactor: move chat interfaces"
~~~

## Task 6: Docs, archive, test finalization, and end-to-end validation

**Files:**
- Create: docs/architecture/, docs/operations/, docs/evaluation/
- Create: local_archive/presentations/
- Modify: .gitignore
- Move: Git-managed Markdown from app/chat/docs into the three docs categories.
- Move: rag_pipeline_presentation.html and portfolio_walkthrough.html into local_archive/presentations/.
- Delete: empty app/chat/docs directory.
- Move remaining tests to requested package mirrors.

**Interfaces:**
- Produces: documentation separated by decision, operation, and evaluation purpose.
- Preserves: README links and all documented module commands.
- Does not commit: local_archive contents.

- [ ] **Step 1: documentation link test를 작성한다.**

~~~python
from pathlib import Path


def test_readme_does_not_link_to_removed_chat_docs_directory() -> None:
    assert "docs/" not in Path("README.md").read_text(encoding="utf-8")
~~~

Expected file: tests/test_documentation_paths.py

- [ ] **Step 2: 실패를 확인한다.**

~~~bash
uv run pytest tests/test_documentation_paths.py -v
~~~

Expected: FAIL until README references are updated.

- [ ] **Step 3: docs와 archive를 이동한다.**

~~~bash
mkdir -p docs/architecture docs/operations docs/evaluation local_archive/presentations
git mv docs/*.md docs/
git mv docs/rag_pipeline_presentation.html local_archive/presentations/
git mv docs/portfolio_walkthrough.html local_archive/presentations/
~~~

Before the Markdown move, classify each file by purpose and move it to exactly one of architecture, operations, or evaluation. Add local_archive/ to .gitignore before moving HTML. Update README and Markdown links using relative paths. Move remaining test files so every test path mirrors its implementation boundary.

- [ ] **Step 4: final local validation을 실행한다.**

~~~bash
uv run ruff check app tests scripts
uv run pytest
uv run python -m compileall -q app tests scripts
uv run python scripts/release_quality_gate.py
uv run python scripts/staging_smoke.py --base-url http://127.0.0.1:8000
docker compose up --build --detach api
uv run python scripts/staging_smoke.py --base-url http://127.0.0.1:8000
docker compose down
git status --short
~~~

Expected: all static checks and tests PASS. First staging command may require an already running local API; Docker staging smoke must PASS. Final status contains only intended Git-managed source, test, docs, and configuration changes; local_archive is ignored.

- [ ] **Step 5: 커밋한다.**

~~~bash
git add app tests docs README.md .gitignore scripts Dockerfile docker-compose.yml .github
git commit -m "refactor: finalize project package layout"
~~~

## 계획 자체 검토

- 요청한 app/core, preprocess, chat/domain, chat/orchestration, chat/interfaces, data, scripts, tests, docs, local_archive 경계를 Task 1~6에 반영했다.
- data 디렉토리는 명시적으로 유지하고 generated artifacts를 Git 이동 범위에서 제외했다.
- config compatibility shim과 policy의 graph 역방향 의존성은 별도 Task로 다뤄 import 회귀를 방지했다.
- public API, Gradio, MCP, data paths는 유지하도록 각 Task의 Interfaces와 검증 명령에 명시했다.
- 각 Task에는 정확한 파일 범위, 실패 테스트, 이동 또는 구현 명령, 검증 명령, 커밋 메시지를 포함했다.


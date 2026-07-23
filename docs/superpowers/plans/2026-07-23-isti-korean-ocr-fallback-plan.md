# ISTI 한국어 OCR Fallback 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** WADA ISTI PDF의 깨진 한국어 페이지에만 로컬 Tesseract OCR을 적용하고, 추출 방식과 품질 상태를 보존한다.

**Architecture:** 기존 PyMuPDF 텍스트 레이어와 span 추출을 우선 사용한다. 한국어 페이지가 결정론적 품질 기준을 통과하지 못했을 때만 PyMuPDF로 해당 페이지를 PNG로 렌더링하고 시스템 Tesseract(kor+eng)를 호출한다. 통과한 결과만 DocumentChunk로 넘기고, 선택 방식과 품질 근거는 metadata에 남긴다.

**Tech Stack:** Python 3.12, PyMuPDF, Pydantic v2, pytest, Ruff, 시스템 Tesseract OCR과 Korean language data.

## Global Constraints

- PDF 전체 OCR을 하지 않고, 품질 기준 미달 한국어 페이지만 fallback 대상으로 한다.
- source_manifest.csv의 needs_review 상태를 코드가 자동으로 ready로 바꾸면 안 된다.
- 원본 source ID와 PDF 페이지 번호를 OCR 뒤에도 유지한다.
- OCR 실패, 빈 결과, 품질 미달 결과는 색인하지 않고 needs_review 이유로 남긴다.
- 클라우드 OCR과 새 Python OCR 래퍼 의존성을 추가하지 않는다.
- 각 작업은 테스트 실패 확인 → 최소 구현 → 좁은 검증 → 커밋 순서로 진행한다.
- 사람이 ISTI 샘플을 승인하기 전에는 재색인하지 않는다.

---

## 파일 구조와 책임

- Create: app/preprocess/ocr/__init__.py
  - OCR fallback 패키지 경계를 표시한다.
- Create: app/preprocess/ocr/quality.py
  - 텍스트 길이, 한글 비율, 깨진 문자 비율을 계산하고 페이지 품질을 판정한다.
- Create: app/preprocess/ocr/tesseract.py
  - PyMuPDF page를 PNG로 렌더링하고 시스템 tesseract 명령을 안전하게 실행한다.
- Create: app/preprocess/ocr/fallback.py
  - text-layer 결과와 OCR 결과를 비교해 선택 결과와 실패 이유를 반환한다.
- Modify: app/preprocess/schemas.py
  - DocumentMetadata에 페이지 추출 provenance를 추가한다.
- Modify: app/preprocess/pdf_loader.py
  - ISTI 한국어 저품질 페이지에서만 fallback을 호출한다.
- Create: tests/preprocess/ocr/test_quality.py
- Create: tests/preprocess/ocr/test_tesseract.py
- Create: tests/preprocess/ocr/test_fallback.py
- Create: tests/preprocess/test_pdf_loader_ocr.py
- Create: scripts/isti_ocr_smoke.py
- Modify: .env.example
- Create: docs/operations/isti-korean-ocr-operations.md

## Task 1: 페이지 품질 계약과 metadata

**Files:**
- Create: app/preprocess/ocr/__init__.py
- Create: app/preprocess/ocr/quality.py
- Modify: app/preprocess/schemas.py
- Test: tests/preprocess/ocr/test_quality.py

**Interfaces:**
- Produces: ExtractionMethod, PageQualityStatus, TextQualityReport, assess_text_quality(text: str, *, expects_korean: bool) -> TextQualityReport.
- Consumes: 원문 텍스트와 expects_korean 플래그.
- Used by: Task 2의 OCR 결과 평가와 Task 3의 fallback selector.

- [ ] **Step 1: 실패하는 품질 테스트를 작성한다.**

~~~python
from app.preprocess.ocr.quality import PageQualityStatus, assess_text_quality


def test_korean_mojibake_is_marked_needs_review() -> None:
    report = assess_text_quality("áᔍ ၰ᳑ ᔍǎᱽ⢽ᵡ " * 20, expects_korean=True)

    assert report.status == PageQualityStatus.NEEDS_REVIEW
    assert report.reason == "suspicious_character_ratio"


def test_readable_korean_is_accepted() -> None:
    report = assess_text_quality("도핑검사는 규정에 따라 실시됩니다. " * 20, expects_korean=True)

    assert report.status == PageQualityStatus.ACCEPTED
    assert report.hangul_ratio > 0.5
~~~

- [ ] **Step 2: 실패를 확인한다.**

Run: uv run pytest tests/preprocess/ocr/test_quality.py -v

Expected: FAIL because app.preprocess.ocr.quality does not exist.

- [ ] **Step 3: 최소 품질 모델과 판정 함수를 구현한다.**

~~~python
class PageQualityStatus(StrEnum):
    ACCEPTED = "accepted"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"


class TextQualityReport(BaseModel):
    status: PageQualityStatus
    reason: str | None
    char_count: int
    hangul_ratio: float
    suspicious_ratio: float


def assess_text_quality(text: str, *, expects_korean: bool) -> TextQualityReport:
    cleaned = "".join(text.split())
    # Empty text is rejected. Korean pages reject suspicious text first,
    # then reject too little Hangul.
~~~

DocumentMetadata에는 기본값이 있는 필드를 추가한다.

~~~python
extraction_method: str = "text_layer"
quality_status: PageQualityStatus = PageQualityStatus.ACCEPTED
quality_reason: str | None = None
ocr_language: str | None = None
~~~

- [ ] **Step 4: 좁은 테스트와 Ruff를 실행한다.**

Run: uv run pytest tests/preprocess/ocr/test_quality.py -v && uv run ruff check app/preprocess/ocr app/preprocess/schemas.py tests/preprocess/ocr/test_quality.py

Expected: tests PASS and All checks passed.

- [ ] **Step 5: 커밋한다.**

~~~bash
git add app/preprocess/ocr/__init__.py app/preprocess/ocr/quality.py \
  app/preprocess/schemas.py tests/preprocess/ocr/test_quality.py
git commit -m "feat: add OCR page quality contract"
~~~

## Task 2: 로컬 Tesseract adapter

**Files:**
- Create: app/preprocess/ocr/tesseract.py
- Create: tests/preprocess/ocr/test_tesseract.py
- Modify: .env.example
- Create: docs/operations/isti-korean-ocr-operations.md

**Interfaces:**
- Produces: run_tesseract_ocr(page: fitz.Page, *, language: str = "kor+eng", dpi: int = 300) -> str.
- Raises: TesseractUnavailableError for missing executable/language data and TesseractExecutionError for nonzero exits.
- Used by: Task 3.

- [ ] **Step 1: missing executable 실패 테스트를 작성한다.**

~~~python
import pytest

from app.preprocess.ocr.tesseract import TesseractUnavailableError, ensure_tesseract_available


def test_ensure_tesseract_available_explains_missing_binary(monkeypatch) -> None:
    monkeypatch.setattr("app.preprocess.ocr.tesseract.shutil.which", lambda _: None)

    with pytest.raises(TesseractUnavailableError, match="tesseract executable"):
        ensure_tesseract_available(language="kor+eng")
~~~

- [ ] **Step 2: 실패를 확인한다.**

Run: uv run pytest tests/preprocess/ocr/test_tesseract.py -v

Expected: FAIL because app.preprocess.ocr.tesseract does not exist.

- [ ] **Step 3: PyMuPDF 렌더링과 subprocess adapter를 구현한다.**

~~~python
def render_page_to_png(page: fitz.Page, *, dpi: int) -> bytes:
    scale = dpi / 72
    pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    return pixmap.tobytes("png")


def run_tesseract_ocr(page: fitz.Page, *, language: str = "kor+eng", dpi: int = 300) -> str:
    ensure_tesseract_available(language=language)
    with TemporaryDirectory() as directory:
        image_path = Path(directory) / "page.png"
        image_path.write_bytes(render_page_to_png(page, dpi=dpi))
        completed = subprocess.run(
            ["tesseract", str(image_path), "stdout", "-l", language],
            check=False, capture_output=True, text=True, timeout=60,
        )
    if completed.returncode != 0:
        raise TesseractExecutionError(completed.stderr.strip())
    return completed.stdout.strip()
~~~

ensure_tesseract_available은 tesseract --list-langs에 kor와 eng가 있는지 확인한다. 운영 문서에는 macOS 설치 명령, PATH 확인, language data 확인, smoke 실행을 기록한다.

- [ ] **Step 4: 단위 테스트와 Ruff를 실행한다.**

Run: uv run pytest tests/preprocess/ocr/test_tesseract.py -v && uv run ruff check app/preprocess/ocr/tesseract.py tests/preprocess/ocr/test_tesseract.py

Expected: mocked tests PASS. Tesseract가 아직 없더라도 단위 테스트는 PASS한다.

- [ ] **Step 5: 커밋한다.**

~~~bash
git add app/preprocess/ocr/tesseract.py tests/preprocess/ocr/test_tesseract.py \
  .env.example docs/operations/isti-korean-ocr-operations.md
git commit -m "feat: add local Tesseract OCR adapter"
~~~

## Task 3: fallback 선택과 provenance

**Files:**
- Create: app/preprocess/ocr/fallback.py
- Create: tests/preprocess/ocr/test_fallback.py

**Interfaces:**
- Produces: PageExtractionResult(text: str | None, extraction_method: str, quality_report: TextQualityReport, ocr_language: str | None).
- Consumes: page: fitz.Page, text_layer_text: str, expects_korean: bool.
- Used by: Task 4 loader.

- [ ] **Step 1: text-layer 우선과 OCR fallback 테스트를 작성한다.**

~~~python
def test_accepted_text_layer_does_not_call_ocr(monkeypatch, fake_page) -> None:
    monkeypatch.setattr(
        "app.preprocess.ocr.fallback.run_tesseract_ocr",
        lambda *args, **kwargs: pytest.fail("OCR must not run"),
    )
    result = resolve_page_text(
        fake_page,
        text_layer_text="도핑검사는 규정에 따라 실시됩니다. " * 20,
        expects_korean=True,
    )

    assert result.extraction_method == "text_layer"


def test_low_quality_korean_uses_ocr(monkeypatch, fake_page) -> None:
    monkeypatch.setattr(
        "app.preprocess.ocr.fallback.run_tesseract_ocr",
        lambda *args, **kwargs: "도핑검사는 규정에 따라 실시됩니다. " * 20,
    )
    result = resolve_page_text(fake_page, text_layer_text="áᔍ ၰ᳑ " * 30, expects_korean=True)

    assert result.extraction_method == "tesseract_ocr"
    assert result.ocr_language == "kor+eng"
~~~

- [ ] **Step 2: 실패를 확인한다.**

Run: uv run pytest tests/preprocess/ocr/test_fallback.py -v

Expected: FAIL because resolve_page_text does not exist.

- [ ] **Step 3: fallback selector를 구현한다.**

~~~python
def resolve_page_text(page: fitz.Page, *, text_layer_text: str, expects_korean: bool) -> PageExtractionResult:
    text_report = assess_text_quality(text_layer_text, expects_korean=expects_korean)
    if text_report.status == PageQualityStatus.ACCEPTED or not expects_korean:
        return PageExtractionResult.from_text_layer(text_layer_text, text_report)

    try:
        ocr_text = run_tesseract_ocr(page)
    except TesseractError as error:
        return PageExtractionResult.needs_review(reason=f"ocr_unavailable:{error}")

    ocr_report = assess_text_quality(ocr_text, expects_korean=True)
    if ocr_report.status != PageQualityStatus.ACCEPTED:
        return PageExtractionResult.needs_review(reason=f"ocr_{ocr_report.reason}")
    return PageExtractionResult.from_ocr(ocr_text, ocr_report)
~~~

- [ ] **Step 4: fallback 테스트와 Ruff를 실행한다.**

Run: uv run pytest tests/preprocess/ocr/test_fallback.py -v && uv run ruff check app/preprocess/ocr tests/preprocess/ocr

Expected: tests PASS and All checks passed.

- [ ] **Step 5: 커밋한다.**

~~~bash
git add app/preprocess/ocr/fallback.py tests/preprocess/ocr/test_fallback.py
git commit -m "feat: add Korean OCR fallback selection"
~~~

## Task 4: loader 연결과 회귀 방지

**Files:**
- Modify: app/preprocess/pdf_loader.py
- Create: tests/preprocess/test_pdf_loader_ocr.py

**Interfaces:**
- Consumes: resolve_page_text from Task 3 plus 현재 block/span/TOC/footer 정리 함수.
- Produces: DocumentChunk.metadata의 extraction_method, quality_status, quality_reason, ocr_language.
- Preserves: 기존 toc_page, empty_text, low_quality_text skip 이유와 page number.

- [ ] **Step 1: loader가 OCR provenance를 보존하는 테스트를 작성한다.**

~~~python
def test_isti_low_quality_page_uses_resolved_ocr_text(monkeypatch, isti_metadata) -> None:
    monkeypatch.setattr(
        "app.preprocess.pdf.loader.resolve_page_text",
        lambda page, **kwargs: PageExtractionResult(
            text="복구된 한국어 본문 " * 20,
            extraction_method="tesseract_ocr",
            quality_report=accepted_report(),
            ocr_language="kor+eng",
        ),
    )

    chunks = load_pdf_pages(isti_metadata, start_page=4, end_page=4)

    assert chunks[0].metadata.extraction_method == "tesseract_ocr"
    assert chunks[0].metadata.quality_status.value == "accepted"
    assert chunks[0].metadata.page == 4
~~~

- [ ] **Step 2: 실패를 확인한다.**

Run: uv run pytest tests/preprocess/test_pdf_loader_ocr.py -v

Expected: FAIL because the loader does not import or call resolve_page_text.

- [ ] **Step 3: 기존 loader에 최소 변경으로 연결한다.**

ISTI의 짝수 페이지에서만 expects_korean을 True로 계산한다.

~~~python
expects_korean = (
    metadata.source_id == "wada_isti_2021_ko_en"
    and page_number % 2 == 0
)
~~~

기존 blocks → clean → sort → blocks_to_text 처리 직후 fallback을 호출한다. PageExtractionResult.text가 None이면 chunk를 만들지 않고 inspection 결과에는 quality_reason을 기록한다. DocumentMetadata.model_copy(update=...)에는 provenance 네 필드를 추가한다. 다른 출처와 영어 ISTI 페이지 동작은 바꾸지 않는다.

- [ ] **Step 4: 전처리 테스트와 Ruff를 실행한다.**

Run: uv run pytest tests/preprocess -v && uv run ruff check app/preprocess tests/preprocess

Expected: tests PASS and All checks passed.

- [ ] **Step 5: 커밋한다.**

~~~bash
git add app/preprocess/pdf_loader.py tests/preprocess/test_pdf_loader_ocr.py
git commit -m "feat: apply OCR fallback in ISTI loader"
~~~

## Task 5: 실제 smoke와 승인 전 재색인 보호

**Files:**
- Create: scripts/isti_ocr_smoke.py
- Modify: docs/operations/isti-korean-ocr-operations.md
- Modify: tests/preprocess/ocr/test_tesseract.py

**Interfaces:**
- Consumes: load_source_manifest, resolve_page_text, assess_text_quality.
- Produces: 단일 페이지 extraction method, quality metrics, bounded Korean preview.
- Does not produce: manifest 상태 변경, processed JSONL 덮어쓰기, Chroma 재색인.

- [ ] **Step 1: CLI 입력 검증 테스트를 작성한다.**

~~~python
def test_smoke_rejects_non_isti_source() -> None:
    result = main(["--source-id", "kada_anti_doping_rules_2021_ko", "--page", "4"])

    assert result == 2
~~~

- [ ] **Step 2: 실패를 확인한다.**

Run: uv run pytest tests/preprocess/ocr/test_tesseract.py -v

Expected: FAIL because scripts.isti_ocr_smoke does not exist.

- [ ] **Step 3: narrow smoke script를 구현한다.**

~~~python
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-id", default="wada_isti_2021_ko_en")
    parser.add_argument("--page", type=int, required=True)
    args = parser.parse_args(argv)
    # Load exactly one ISTI page, run the same fallback boundary,
    # print provenance, ratios, and a bounded preview.
~~~

실제 실행 전 다음을 확인한다.

~~~bash
brew install tesseract tesseract-lang
tesseract --list-langs
uv run python scripts/isti_ocr_smoke.py --page 4
~~~

운영 문서에는 4, 20, 84, 166 페이지의 초반·중간·후반 표본, 목차, 표가 많은 페이지를 확인하는 체크리스트를 추가한다.

- [ ] **Step 4: 실제 smoke와 전체 회귀 검증을 실행한다.**

Run:

~~~bash
uv run python scripts/isti_ocr_smoke.py --page 4
uv run python scripts/isti_ocr_smoke.py --page 84
uv run ruff check app tests scripts
uv run pytest
uv run python scripts/release_quality_gate.py
~~~

Expected: smoke는 읽을 수 있는 한국어 preview와 tesseract_ocr provenance를 출력한다. manifest는 여전히 needs_review이며, 현재 verified index의 release gate는 PASS한다.

- [ ] **Step 5: 커밋한다.**

~~~bash
git add scripts/isti_ocr_smoke.py docs/operations/isti-korean-ocr-operations.md \
  tests/preprocess/ocr/test_tesseract.py
git commit -m "feat: add ISTI OCR smoke workflow"
~~~

## Task 6: 사람 검토 뒤의 데이터 갱신 결정

**Files:**
- Modify only after explicit human approval: data/source_manifest.csv
- Generated only after explicit human approval: data/processed/pages.jsonl, data/processed/chunks.jsonl, data/indexes/, data/operations/source-inventory.json

**Interfaces:**
- Consumes: Task 5의 표본 검토 기록과 scripts/data_refresh.py 보호 절차.
- Produces: 승인된 경우에만 새 processed corpus와 Chroma index.

- [ ] **Step 1: dry-run으로 재구축 차단을 확인한다.**

Run: uv run python scripts/data_refresh.py

Expected: ISTI가 needs_review이면 apply가 차단된다고 출력한다.

- [ ] **Step 2: 사용자에게 승인 자료를 제시한다.**

페이지별 OCR preview, quality metrics, 실패 페이지 수, 예상 재색인 범위를 제시한다. 승인 전에는 --apply나 --include-needs-review를 실행하지 않는다.

- [ ] **Step 3: 승인된 경우에만 manifest와 corpus를 갱신한다.**

~~~bash
# Explicit user approval is required before this step.
# Change the ISTI row from needs_review to ready, then:
uv run python scripts/data_refresh.py --apply
uv run python scripts/release_quality_gate.py
~~~

- [ ] **Step 4: focused LangSmith evaluation을 실행한다.**

~~~bash
uv run python -m app.chat.evals.langsmith_tool_eval --top-k 3
uv run python -m app.chat.evals.langsmith_field_scenario_eval --top-k 3
~~~

Expected: 기존 실험과 새 trace를 비교해 retrieval quality, source hit, term hit 저하 여부를 확인할 수 있다.

- [ ] **Step 5: 승인된 데이터 갱신만 별도 커밋한다.**

~~~bash
git add data/source_manifest.csv data/operations/source-inventory.json
git commit -m "data: approve reviewed ISTI Korean extraction"
~~~

data/processed와 data/indexes가 Git ignore라면 커밋하지 않는다. 대신 inventory hash, release gate, LangSmith 비교 결과를 change log에 남긴다.

## 계획 자체 검토

- 하이브리드 fallback, provenance, 품질 검증, 사람 승인, 재색인 보호 요구사항을 Task 1~6에 모두 반영했다.
- 자동 ready 변경과 전체 OCR을 명시적으로 제외했다.
- 새 public API, 배포, cloud OCR는 범위 밖으로 유지했다.
- 모든 새 함수와 타입은 선행 Task의 Interfaces에 선언했고, 구현 Task는 테스트 실패 → 최소 구현 → 통과 → 커밋 순서를 포함한다.


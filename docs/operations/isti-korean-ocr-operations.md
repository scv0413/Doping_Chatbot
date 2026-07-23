# ISTI Korean OCR Operations

The ISTI Korean OCR fallback is local-only and runs only when a Korean page's
PDF text layer fails the deterministic quality check. It does not change a
source manifest status or rebuild an index automatically.

## Prerequisites

```bash
tesseract --version
tesseract --list-langs
```

The language list must include both `kor` and `eng`. On macOS with Homebrew,
install the Tesseract binary and Korean language data through the approved
package source for the local environment, then rerun the commands above.

## Smoke Test

The later OCR smoke script will render a selected ISTI page at 300 DPI and run
`tesseract` with `kor+eng`. A missing executable or language pack is reported
as a reviewable error; the page is not silently indexed.

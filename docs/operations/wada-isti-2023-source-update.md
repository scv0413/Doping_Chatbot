# WADA ISTI 2023 Source Update

## Verified Source

The current official English candidate is the WADA International Standard for
Testing and Investigations with `effective_date = 2023-01-01`. It is registered as `downloaded_validated` in `data/operations/source-candidates.csv` and as a `ready` English source in `data/source_manifest.csv`. The browser-downloaded copy is stored at:

```text
data/raw/pdf/wada/wada_isti_2023_en.pdf
```

Candidate URL:

```text
https://www.wada-ama.org/sites/default/files/2022-09/2022_09_23_approved_ec_isti_2023_clean_final_compressed_1.pdf
```

## Acquisition Rule

Use the safe acquisition script when the official host permits automated
download:

```bash
uv run python scripts/acquire_official_pdf.py \
  --url "https://www.wada-ama.org/sites/default/files/2022-09/2022_09_23_approved_ec_isti_2023_clean_final_compressed_1.pdf" \
  --output-path data/raw/pdf/wada/wada_isti_2023_en.pdf
```

The script accepts only HTTPS URLs from official WADA/KADA hosts, writes to a
temporary file, and checks for a non-empty PDF signature before replacing the
target path. It intentionally rejects WAF challenge pages and empty responses.

## Acquisition History

The WADA host returned a CloudFront WAF challenge for automated acquisition on
2026-07-23. The PDF was then downloaded in a normal browser session. Local
validation confirmed a PDF signature, SHA-256 identity, 88 pages, a readable
English text layer, and table-of-contents pages 3-5. The source is indexed as
an official English original; it is not represented as an official Korean translation.

## Korean Guidance Status

The 2021 bilingual source and its project-reviewed Korean guide were removed from
the active corpus when the source policy changed to 2023-only. No Korean ISTI
guide is currently indexed. Any future Korean guide must be newly reviewed
against `wada_isti_2023_en` and cite the relevant 2023 English page; it must not
be presented as an official WADA Korean translation.

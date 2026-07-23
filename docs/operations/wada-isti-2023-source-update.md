# WADA ISTI 2023 Source Update

## Candidate

The current official English candidate is the WADA International Standard for
Testing and Investigations effective 1 January 2023. Store a browser-downloaded
copy at:

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

## Current Limitation

The WADA host returned a CloudFront WAF challenge in this environment on
2026-07-23, so automated acquisition was rejected without creating a source
file. Download the official PDF in a normal browser session instead, then run
the PDF inspection and source comparison before adding it to the manifest.

## Required Review Before Use

1. Compare 2023 clauses that affect notification, blood collection, athlete
   identification, and overnight testing with the current 2021 source.
2. Record changed or removed clause references in a human-reviewed manual.
3. Add the new source to `data/source_manifest.csv` as `needs_review`.
4. Mark it `ready` and reindex only after the content review is approved.

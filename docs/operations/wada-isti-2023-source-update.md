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

## Required Review Before Korean Guidance Changes

1. Compare 2023 clauses that affect notification, blood collection, athlete
   identification, and overnight testing with the current 2021 source.
2. Record changed or removed clause references in a human-reviewed Korean manual.
3. Do not claim that the project Korean guidance is an official WADA Korean
   translation.
4. Update or supersede a reviewed Korean manual only after the changed clause
   scope has been checked.

## Automated Comparison Result

The project compared the English text that underlies the reviewed Korean guide
(Articles 5.3.5 through 5.4.1) against the 2023 source. Article 5.3.5 matched
exactly. Article 5.3.6 adds `as applicable` in 2023. Article 5.3.7 has
formatting and punctuation differences, and Article 5.4.1 continues onto 2023
p.43. Therefore the existing Korean reviewed guide continues to cite the 2021
original p.83 until a human confirms whether its Korean wording remains
appropriate for the 2023 clause scope. This does not block indexing the 2023
English original itself.

# ISTI Korean OCR Review Decision

## Decision

Keep `wada_isti_2021_ko_en` in `needs_review`. Do not add Korean OCR output to
the validated retrieval corpus or change the manifest status to `ready`.

## Reviewed Samples

The local review smoke script processed Korean PDF pages 4, 84, and 164 with
Tesseract `kor+eng` at 300 DPI. All three were classified as `needs_review`
because their OCR noise token ratio exceeded the conservative threshold.

- Page 4: 680 characters; dates, headings, and organization names were distorted.
- Page 84: 951 characters; notification and sample-collection terms were heavily distorted.
- Page 164: 756 characters; blood-collection procedure terms were heavily distorted.

Because these pages contain procedural obligations, partially readable Korean
text is not sufficient for a safety-critical RAG source.

## Runtime Policy

- English ISTI pages that pass the existing text-layer pipeline remain usable.
- Korean OCR output is retained only as an inspectable review artifact.
- `scripts/isti_ocr_smoke.py` must be used before any later approval decision.
- The source manifest status must be changed manually only after representative
  Korean pages pass human review.

## Next Data Options

1. Obtain an official Korean PDF with a healthy text layer.
2. Obtain an official HTML or accessible Korean source.
3. Create a bounded, human-verified Korean manual source for high-risk sections
   such as notification, sample collection, and blood collection.

# Data Refresh Operations

## Why This Exists

A RAG index is only trustworthy while its source files and processing assumptions are current. Re-running preprocess and index commands blindly can overwrite a working index with incomplete or unreviewed source data. The refresh runner therefore makes source identity, review state, and rebuild intent explicit.

## Dry Run

```bash
uv run python scripts/data_refresh.py
```

The command calculates SHA-256 hashes for manifest files and reports:

- missing source files;
- source files changed since the previous successful refresh;
- manifest additions/removals;
- source records still marked `needs_review`;
- whether a destructive index rebuild is allowed.

Dry-run never writes processed files or the vector index.

## Apply a Refresh

After manual source review is complete, update `data/source_manifest.csv` to `ready` where appropriate, then run:

```bash
uv run python scripts/data_refresh.py --apply
```

The full rebuild order is fixed:

1. PDF/manual preprocessing;
2. page chunk generation;
3. Chroma collection reset and index rebuild;
4. source inventory snapshot write to `data/operations/source-inventory.json`.

When an operator deliberately accepts sources that remain under review, they must make that decision explicit:

```bash
uv run python scripts/data_refresh.py --apply --include-needs-review
```

This override should be exceptional and recorded in the release/change log. It is useful for controlled experimentation but should not be the default production procedure.

## Current Baseline

The current three PDF sources are intentionally still `needs_review`. The Korean WADA ISTI extraction gap remains known, so the runner correctly refuses an unattended index rebuild. This keeps the existing verified index available until source quality is formally accepted or replaced.

## Future Automation

A scheduled job can run dry-run and open an operator ticket when the inventory changes. It should not automatically execute `--apply`; a reviewed source update needs an explicit human approval and a retrieval regression evaluation after reindexing.

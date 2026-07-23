# Container Release and Rollback

## CI and Release Split

`.github/workflows/docker-build.yml` runs on pull requests and `main`. It verifies lint, tests, Docker build, non-root runtime, and health/readiness JSON shape. It does not push an image.

`.github/workflows/release-image.yml` runs only for `v*` git tags or manual dispatch. It logs into GitHub Container Registry (GHCR) using the repository `GITHUB_TOKEN`, builds the Docker image, pushes semantic and SHA tags, and writes the immutable image digest to the workflow summary.

This keeps unreviewed pull requests from publishing production-like images while making a reviewed tag reproducible.

## Release Procedure

1. Run local lint, full test suite, and staging smoke.
2. Create a reviewed version tag such as `v0.2.0` and push it.
3. Confirm the release workflow produced the expected GHCR image and copy its digest.
4. Deploy the exact image digest, not a moving tag, to the target platform.
5. Run `/health`, `/ready`, and `scripts/staging_smoke.py` against the deployed service.

## Rollback

A rollback does not rebuild old source code. Redeploy the previously verified immutable image digest, then repeat health, readiness, and smoke checks. Keep the prior digest in the deployment/change record.

A deployment provider has not been selected for this project, so the workflow intentionally stops at registry publishing. Provider-specific credentials, Terraform, Kubernetes manifests, or SSH deployment scripts should be added only after the target environment and secret-management policy are selected.

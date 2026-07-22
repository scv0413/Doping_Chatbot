# API Security and Role Baseline

## Purpose

The public chat endpoint can invoke embeddings, retrieval, and optionally an LLM. A local prototype can be open, but an operated service needs a minimum boundary so unknown clients cannot consume cost-bearing resources or access internal debug controls.

This project intentionally uses an environment-driven baseline rather than pretending to be a complete identity platform. It is suitable for local, staging, and small controlled deployments. A production identity provider can replace the API key implementation without changing the route-level role contract.

## Configuration

```env
API_AUTH_ENABLED=true
API_KEY_ROLES=athlete-key:athlete,trainer-key:trainer,admin-key:admin
API_RATE_LIMIT_ENABLED=true
API_RATE_LIMIT_REQUESTS=30
API_RATE_LIMIT_WINDOW_SECONDS=60
```

`API_KEY_ROLES` is a comma-separated `api_key:role` list. Keys belong in a secret manager or deployment secret, never in git. Supported roles are `athlete`, `trainer`, and `admin`.

## Access Policy

| Endpoint | Auth disabled | Auth enabled |
| --- | --- | --- |
| `GET /health`, `GET /ready` | public | public for platform probes |
| `POST /api/v1/chat-responses` | local anonymous access | any configured API key |
| `POST /api/v1/debug/chat-responses` | local debug access | `admin` only |

The debug endpoint remains intentionally separate because it exposes runtime options and internal execution metadata. It must not be exposed to general athletes or trainers in a deployed environment.

## Rate Limit and Audit Log

The in-memory limiter counts requests by authenticated principal within the configured sliding window. It is process-local, which is correct for a single-container baseline but not for horizontally scaled production. Replace it with Redis or an API gateway limiter before multi-instance deployment.

Successful chat calls emit a JSON `chat_access` event containing a request id, endpoint, status, role, and a non-reversible API key fingerprint. Raw API keys and question text are never written to the audit event.

## Production Follow-up

1. Replace environment API keys with OAuth/OIDC or an organization SSO provider.
2. Store rate-limit state in Redis or the gateway layer.
3. Persist audit events in a protected retention system and define operator access.
4. Add user/organization identifiers only after privacy and data-retention policy is agreed.

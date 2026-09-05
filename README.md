# UNG-MDM

**Uganda National Grid Master Data Management**

UNG-MDM is the authoritative corporate master-data platform for shared enterprise entities across the UNG ecosystem.

## Current foundation

Version `0.2.0` adds the first production API layer:

- UNG-IAM bearer-token validation through `GET /v1/me`
- Deny-by-default permission checks
- Isolated UNG-MDM database boundary
- PostgreSQL production support with SQLite development fallback
- Master-data domain registry
- Master-data record registry
- Creator identity attribution using the UNG-IAM identity ID

UNG-MDM never imports IAM application code and never shares the IAM database. Identity is validated over the UNG-IAM API.

## Environment

- `UNG_IAM_BASE_URL` — UNG-IAM service URL; defaults to `https://ung-iam-production.up.railway.app`
- `UNG_IAM_TIMEOUT` — IAM request timeout in seconds; default `5`
- `UNG_MDM_DATABASE_URL` — dedicated PostgreSQL URL for production
- `UNG_MDM_DB` — optional SQLite path for local development
- `UNG_MDM_READ_PERMISSION` — read permission; default `platform:corporate`
- `UNG_MDM_WRITE_PERMISSION` — write permission; default `iam:write` during the bootstrap phase

## Endpoints

Public:

- `GET /`
- `GET /health`

IAM protected:

- `GET /v1/me`
- `GET /v1/domains`
- `POST /v1/domains`
- `GET /v1/records`
- `POST /v1/records`

## Next phases

The next MDM phases add dedicated `mdm:*` permissions, stewardship workflows, approval states, record versioning, matching/merging, golden-record resolution, reference-data publication, downstream change events, and audit integration with UNG-Sentinel.

## Local run

```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8080
```

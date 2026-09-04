# UNG-MDM

**Uganda National Grid Master Data Management**

UNG-MDM is a **Corporate Enterprise System**. It is not a regular field-operations application.

## Purpose

UNG-MDM is the authoritative master-data platform for shared enterprise entities used across the Uganda National Grid ecosystem, including customers, vendors, facilities, warehouses, vehicles, employees, locations, products/SKUs, equipment, organizational units, and controlled reference codes.

## Architectural role

- Independent repository and deployment boundary
- Corporate/control-plane system
- Authoritative source for shared enterprise master records
- Other systems consume approved master data through authenticated APIs/events
- No direct dependency on the `uganda-grid-api-clean` runtime
- Designed for integration with UNG-IAM, UNG-NOC, UNG-Sentinel, Data Relay, and operational platforms

## Foundation status

Version `0.1.0` establishes the service shell only. Business CRUD, stewardship workflows, matching/merging, governance rules, and production database schemas will be added in later phases after all platform foundations are created.

## Endpoints

- `GET /` — service identity and classification
- `GET /health` — health check

## Local run

```bash
pip install -r requirements.txt
uvicorn app:app --reload
```

## Container run

```bash
docker build -t ung-mdm .
docker run -p 8080:8080 ung-mdm
```

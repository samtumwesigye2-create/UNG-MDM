from __future__ import annotations

import json
import os
import time
import uuid

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from db import connect, database_name, is_postgres, sql
from iam_client import current_identity, require_permission

APP_ID = "UNG-MDM"
READ_PERMISSION = os.environ.get("UNG_MDM_READ_PERMISSION", "platform:corporate")
WRITE_PERMISSION = os.environ.get("UNG_MDM_WRITE_PERMISSION", "iam:write")

app = FastAPI(
    title="UNG-MDM",
    description="Uganda National Grid Master Data Management corporate enterprise platform.",
    version="0.2.0",
)


def now() -> float:
    return time.time()


def init_db() -> None:
    c = connect()
    try:
        c.execute(
            """CREATE TABLE IF NOT EXISTS mdm_domains(
                id TEXT PRIMARY KEY,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_by TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS mdm_records(
                id TEXT PRIMARY KEY,
                domain_code TEXT NOT NULL,
                record_code TEXT NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                attributes TEXT NOT NULL DEFAULT '{}',
                created_by TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                UNIQUE(domain_code, record_code)
            )"""
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_mdm_records_domain ON mdm_records(domain_code)")
        c.commit()
    finally:
        c.close()


init_db()


class DomainCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[A-Z0-9_-]+$")
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=500)


class RecordCreate(BaseModel):
    domain_code: str = Field(min_length=2, max_length=64)
    record_code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    status: str = Field(default="active", max_length=32)
    attributes: dict = Field(default_factory=dict)


def row_dict(row):
    return dict(row) if row is not None else None


@app.get("/")
def root():
    return {
        "service": APP_ID,
        "name": "Uganda National Grid Master Data Management",
        "classification": "corporate-enterprise",
        "version": "0.2.0",
        "status": "iam-integrated-foundation",
        "database": database_name(),
    }


@app.get("/health")
def health():
    c = None
    try:
        c = connect()
        c.execute("SELECT 1").fetchone()
        return {
            "service": APP_ID,
            "status": "healthy",
            "version": "0.2.0",
            "database": database_name(),
            "production_database": is_postgres(),
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {type(exc).__name__}")
    finally:
        if c:
            c.close()


@app.get("/v1/me")
def me(identity: dict = Depends(current_identity)):
    return {
        "application": APP_ID,
        "identity": identity,
        "authorized": READ_PERMISSION in set(identity.get("permissions") or []),
    }


@app.get("/v1/domains")
def list_domains(identity: dict = Depends(require_permission(READ_PERMISSION))):
    c = connect()
    try:
        rows = c.execute("SELECT * FROM mdm_domains ORDER BY code").fetchall()
        return {"count": len(rows), "results": [row_dict(r) for r in rows]}
    finally:
        c.close()


@app.post("/v1/domains", status_code=201)
def create_domain(body: DomainCreate, identity: dict = Depends(require_permission(WRITE_PERMISSION))):
    code = body.code.strip().upper()
    c = connect()
    try:
        existing = c.execute(sql("SELECT id FROM mdm_domains WHERE code=?"), (code,)).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Domain code already exists")
        item = {
            "id": str(uuid.uuid4()),
            "code": code,
            "name": body.name.strip(),
            "description": body.description.strip(),
            "is_active": 1,
            "created_by": identity["id"],
            "created_at": now(),
            "updated_at": now(),
        }
        c.execute(
            sql("INSERT INTO mdm_domains(id,code,name,description,is_active,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)"),
            tuple(item.values()),
        )
        c.commit()
        return item
    finally:
        c.close()


@app.get("/v1/records")
def list_records(domain: str | None = None, identity: dict = Depends(require_permission(READ_PERMISSION))):
    c = connect()
    try:
        if domain:
            rows = c.execute(
                sql("SELECT * FROM mdm_records WHERE domain_code=? ORDER BY record_code"),
                (domain.strip().upper(),),
            ).fetchall()
        else:
            rows = c.execute("SELECT * FROM mdm_records ORDER BY domain_code, record_code").fetchall()
        results = []
        for row in rows:
            item = row_dict(row)
            try:
                item["attributes"] = json.loads(item.get("attributes") or "{}")
            except Exception:
                item["attributes"] = {}
            results.append(item)
        return {"count": len(results), "results": results}
    finally:
        c.close()


@app.post("/v1/records", status_code=201)
def create_record(body: RecordCreate, identity: dict = Depends(require_permission(WRITE_PERMISSION))):
    domain_code = body.domain_code.strip().upper()
    c = connect()
    try:
        domain = c.execute(sql("SELECT id FROM mdm_domains WHERE code=? AND is_active=1"), (domain_code,)).fetchone()
        if not domain:
            raise HTTPException(status_code=400, detail="Unknown or inactive master-data domain")
        existing = c.execute(
            sql("SELECT id FROM mdm_records WHERE domain_code=? AND record_code=?"),
            (domain_code, body.record_code.strip()),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Record code already exists in this domain")
        ts = now()
        item = {
            "id": str(uuid.uuid4()),
            "domain_code": domain_code,
            "record_code": body.record_code.strip(),
            "name": body.name.strip(),
            "status": body.status.strip().lower(),
            "attributes": json.dumps(body.attributes, separators=(",", ":"), sort_keys=True),
            "created_by": identity["id"],
            "created_at": ts,
            "updated_at": ts,
        }
        c.execute(
            sql("INSERT INTO mdm_records(id,domain_code,record_code,name,status,attributes,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)"),
            tuple(item.values()),
        )
        c.commit()
        item["attributes"] = body.attributes
        return item
    finally:
        c.close()

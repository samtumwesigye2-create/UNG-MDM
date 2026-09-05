from __future__ import annotations

import os
from typing import Callable

import httpx
from fastapi import Header, HTTPException

IAM_BASE_URL = os.environ.get("UNG_IAM_BASE_URL", "https://ung-iam-production.up.railway.app").rstrip("/")
IAM_TIMEOUT = float(os.environ.get("UNG_IAM_TIMEOUT", "5"))


def _bearer(authorization: str) -> str:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Bearer token required")
    return token


def current_identity(authorization: str = Header(default="")) -> dict:
    token = _bearer(authorization)
    try:
        response = httpx.get(
            f"{IAM_BASE_URL}/v1/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=IAM_TIMEOUT,
        )
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="UNG-IAM unavailable")

    if response.status_code == 401:
        raise HTTPException(status_code=401, detail="Invalid or expired UNG-IAM session")
    if response.status_code != 200:
        raise HTTPException(status_code=503, detail="UNG-IAM validation failed")

    identity = response.json()
    if not identity.get("is_active", False):
        raise HTTPException(status_code=403, detail="Identity disabled")
    return identity


def require_permission(permission: str) -> Callable:
    def dependency(authorization: str = Header(default="")) -> dict:
        identity = current_identity(authorization)
        if permission not in set(identity.get("permissions") or []):
            raise HTTPException(status_code=403, detail=f"Missing permission: {permission}")
        return identity

    return dependency

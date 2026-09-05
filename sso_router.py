from __future__ import annotations

import base64
import hashlib
import os
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Cookie, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter()
IAM_BASE_URL = os.environ.get("UNG_IAM_BASE_URL", "https://ung-iam-production.up.railway.app").rstrip("/")
PUBLIC_BASE_URL = os.environ.get("UNG_MDM_PUBLIC_URL", "https://ung-mdm-production.up.railway.app").rstrip("/")
CLIENT_ID = "UNG-MDM"
CALLBACK_URL = f"{PUBLIC_BASE_URL}/sso/callback"
COOKIE_NAME = "ung_mdm_iam"
STATE_COOKIE = "ung_mdm_sso_state"
VERIFIER_COOKIE = "ung_mdm_pkce"


def challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


@router.get("/sso/login")
def sso_login():
    state = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(48)
    params = urlencode({
        "client_id": CLIENT_ID,
        "redirect_uri": CALLBACK_URL,
        "code_challenge": challenge(verifier),
        "state": state,
    })
    response = RedirectResponse(f"{IAM_BASE_URL}/sso/launch?{params}", status_code=302)
    response.set_cookie(STATE_COOKIE, state, max_age=300, httponly=True, secure=True, samesite="lax", path="/")
    response.set_cookie(VERIFIER_COOKIE, verifier, max_age=300, httponly=True, secure=True, samesite="lax", path="/")
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/sso/callback")
def sso_callback(
    code: str = Query(...),
    state: str = Query(...),
    expected_state: str | None = Cookie(default=None, alias=STATE_COOKIE),
    verifier: str | None = Cookie(default=None, alias=VERIFIER_COOKIE),
):
    if not expected_state or not verifier or not secrets.compare_digest(state, expected_state):
        raise HTTPException(400, "SSO state validation failed")
    try:
        r = httpx.post(
            f"{IAM_BASE_URL}/v1/sso/token",
            json={
                "client_id": CLIENT_ID,
                "redirect_uri": CALLBACK_URL,
                "code": code,
                "code_verifier": verifier,
            },
            timeout=8,
        )
    except httpx.RequestError:
        raise HTTPException(503, "UNG-IAM unavailable during SSO exchange")
    if r.status_code != 200:
        detail = "SSO token exchange failed"
        try:
            detail = r.json().get("detail", detail)
        except Exception:
            pass
        raise HTTPException(r.status_code, detail)
    token = r.json().get("access_token")
    if not token:
        raise HTTPException(503, "UNG-IAM returned no access token")
    response = RedirectResponse("/sso/status", status_code=302)
    response.set_cookie(COOKIE_NAME, token, max_age=int(r.json().get("expires_in", 28800)), httponly=True, secure=True, samesite="lax", path="/")
    response.delete_cookie(STATE_COOKIE, path="/")
    response.delete_cookie(VERIFIER_COOKIE, path="/")
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/sso/status", response_class=HTMLResponse)
def sso_status():
    html = '''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>UNG-MDM Access</title>
<style>body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f4f6f8;margin:0;padding:20px;color:#111827}.card{max-width:620px;margin:6vh auto;background:white;padding:24px;border-radius:20px;border:1px solid #e5e7eb}.row{padding:12px;border:1px solid #e5e7eb;border-radius:12px;margin:10px 0}.ok{color:#067647;font-weight:700}.bad{color:#b42318;font-weight:700}button,a.btn{display:inline-block;padding:12px 16px;border-radius:12px;border:0;background:#101828;color:#fff;text-decoration:none;font-weight:700;margin:6px 6px 0 0}</style></head><body><div class="card"><h2>UNG-MDM SSO Acceptance</h2><div id="identity" class="row">Checking identity…</div><div id="read" class="row">Checking protected read…</div><a class="btn" href="/sso/logout">Sign out of MDM</a><a class="btn" href="/">MDM root</a></div>
<script>
async function check(){
 const i=document.getElementById('identity'),r=document.getElementById('read');
 try{const x=await fetch('/v1/me');const d=await x.json();if(!x.ok)throw new Error(d.detail||'Identity check failed');i.innerHTML='<span class="ok">PASS</span> — '+d.identity.display_name+' • '+(d.identity.roles||[]).join(', ');
 const y=await fetch('/v1/domains');const e=await y.json();if(!y.ok)throw new Error(e.detail||'Read check failed');r.innerHTML='<span class="ok">PASS</span> — protected MDM read authorized ('+e.count+' domains)';}
 catch(err){i.innerHTML='<span class="bad">FAIL</span> — '+err.message;r.innerHTML='<span class="bad">NOT COMPLETED</span>';}}
check();
</script></body></html>'''
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})


@router.get("/sso/logout")
def sso_logout(token: str | None = Cookie(default=None, alias=COOKIE_NAME)):
    if token:
        try:
            httpx.post(f"{IAM_BASE_URL}/v1/auth/logout", headers={"Authorization": f"Bearer {token}"}, timeout=5)
        except Exception:
            pass
    response = RedirectResponse("/sso/login", status_code=302)
    response.delete_cookie(COOKIE_NAME, path="/")
    response.headers["Cache-Control"] = "no-store"
    return response

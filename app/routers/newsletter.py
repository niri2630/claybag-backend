"""Newsletter subscription — public endpoint that subscribes a user to Mailchimp.

Reads MAILCHIMP_API_KEY, MAILCHIMP_SERVER, MAILCHIMP_LIST_ID from settings.
If any is missing, returns 503 with a generic message (so the frontend can
show a graceful fallback without leaking config status).

Uses urllib (stdlib) so no extra dependency is required.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import urllib.error
import urllib.request
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, field_validator

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/newsletter", tags=["newsletter"])


class SubscribeRequest(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    source: Optional[str] = None  # e.g. "footer", "popup" — stored as Mailchimp tag

    @field_validator("first_name", "last_name", "source")
    @classmethod
    def _trim(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if len(v) > 80:
            raise ValueError("Field too long")
        return v


class SubscribeResponse(BaseModel):
    ok: bool
    message: str


def _md5_lower(email: str) -> str:
    """Mailchimp identifies members by md5(lowercase(email))."""
    return hashlib.md5(email.lower().encode("utf-8")).hexdigest()


def _put_json(url: str, payload: dict, api_key: str, timeout: float = 10.0):
    """PUT request with Basic Auth — returns (status_code, body_bytes)."""
    data = json.dumps(payload).encode("utf-8")
    auth_str = base64.b64encode(f"anystring:{api_key}".encode("utf-8")).decode("ascii")
    req = urllib.request.Request(
        url,
        data=data,
        method="PUT",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_str}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        # Mailchimp returns 4xx with JSON body — read it for details
        return e.code, e.read()
    # Other errors (URLError, timeout) bubble up to caller


@router.post("/subscribe", response_model=SubscribeResponse)
def subscribe(req: SubscribeRequest) -> SubscribeResponse:
    api_key = (settings.MAILCHIMP_API_KEY or "").strip()
    server = (settings.MAILCHIMP_SERVER or "").strip()
    list_id = (settings.MAILCHIMP_LIST_ID or "").strip()

    if not api_key or not server or not list_id:
        logger.warning("Mailchimp not configured — refusing subscribe")
        raise HTTPException(status_code=503, detail="Newsletter is not available right now.")

    base = f"https://{server}.api.mailchimp.com/3.0"
    member_hash = _md5_lower(req.email)
    url = f"{base}/lists/{list_id}/members/{member_hash}"

    merge_fields: dict[str, str] = {}
    if req.first_name:
        merge_fields["FNAME"] = req.first_name
    if req.last_name:
        merge_fields["LNAME"] = req.last_name

    payload: dict = {
        "email_address": req.email,
        "status_if_new": "subscribed",
        "status": "subscribed",
    }
    if merge_fields:
        payload["merge_fields"] = merge_fields

    if req.source:
        payload["tags"] = [req.source[:50]]

    try:
        status_code, body_bytes = _put_json(url, payload, api_key)
    except (urllib.error.URLError, TimeoutError) as e:
        logger.error("Mailchimp request failed: %s", e)
        raise HTTPException(status_code=502, detail="Couldn't reach our newsletter system. Try again.")
    except Exception as e:  # noqa: BLE001 — defensive catch-all on outbound request
        logger.error("Mailchimp request unexpected error: %s", e)
        raise HTTPException(status_code=502, detail="Couldn't reach our newsletter system. Try again.")

    if status_code in (200, 201):
        return SubscribeResponse(ok=True, message="You're on the list!")

    # Mailchimp error responses: { "title": "...", "detail": "..." }
    try:
        body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
    except (ValueError, UnicodeDecodeError):
        body = {}

    title = (body.get("title") or "").strip()
    detail = (body.get("detail") or "").strip()
    combined = (title + " " + detail).lower()

    if status_code == 400:
        if "exists" in combined:
            return SubscribeResponse(ok=True, message="You're already subscribed.")
        if "fake" in detail.lower() or "looks fake" in detail.lower():
            raise HTTPException(status_code=400, detail="Please use a real email address.")
        if "invalid" in detail.lower():
            raise HTTPException(status_code=400, detail="Please enter a valid email.")
        logger.warning("Mailchimp 400 — title=%s detail=%s", title, detail)
        raise HTTPException(status_code=400, detail="Could not subscribe — check your email and try again.")

    if status_code in (401, 403):
        logger.error("Mailchimp auth failed — title=%s detail=%s", title, detail)
        raise HTTPException(status_code=503, detail="Newsletter is not available right now.")

    logger.error("Mailchimp unexpected status=%s title=%s detail=%s", status_code, title, detail)
    raise HTTPException(status_code=502, detail="Couldn't reach our newsletter system. Try again.")

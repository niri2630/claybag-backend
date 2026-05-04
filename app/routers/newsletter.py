"""Newsletter subscription — public endpoint that subscribes a user to Mailchimp.

Reads MAILCHIMP_API_KEY, MAILCHIMP_SERVER, MAILCHIMP_LIST_ID from settings.
If any is missing, returns 503 with a generic message (so the frontend can
show a graceful fallback without leaking config status).
"""
from __future__ import annotations

import hashlib
import logging
from typing import Optional

import requests
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
        # Mailchimp stores tags via a different endpoint, but we can pass them
        # on initial subscribe as well using the "tags" array.
        payload["tags"] = [req.source[:50]]

    try:
        # PUT upserts the member by hash — works for new and existing.
        resp = requests.put(
            url,
            json=payload,
            auth=("anystring", api_key),
            timeout=10,
        )
    except requests.RequestException as e:
        logger.error("Mailchimp request failed: %s", e)
        raise HTTPException(status_code=502, detail="Couldn't reach our newsletter system. Try again.")

    if resp.status_code in (200, 201):
        return SubscribeResponse(ok=True, message="You're on the list!")

    # Mailchimp error responses: { "title": "...", "detail": "..." }
    try:
        body = resp.json()
    except ValueError:
        body = {}

    title = (body.get("title") or "").strip()
    detail = (body.get("detail") or "").strip()

    # Common cases — map to user-friendly messages.
    if resp.status_code == 400:
        # "Member Exists" can occur if the audience has already-archived users
        # or if double opt-in is set up and the user is in pending state.
        if "exists" in (title + detail).lower():
            return SubscribeResponse(ok=True, message="You're already subscribed.")
        if "fake" in detail.lower() or "looks fake" in detail.lower():
            raise HTTPException(status_code=400, detail="Please use a real email address.")
        if "invalid" in detail.lower():
            raise HTTPException(status_code=400, detail="Please enter a valid email.")
        # Generic 400
        logger.warning("Mailchimp 400 — title=%s detail=%s", title, detail)
        raise HTTPException(status_code=400, detail="Could not subscribe — check your email and try again.")

    if resp.status_code in (401, 403):
        # Auth failure — never expose to user.
        logger.error("Mailchimp auth failed — title=%s detail=%s", title, detail)
        raise HTTPException(status_code=503, detail="Newsletter is not available right now.")

    logger.error("Mailchimp unexpected status=%s title=%s detail=%s", resp.status_code, title, detail)
    raise HTTPException(status_code=502, detail="Couldn't reach our newsletter system. Try again.")

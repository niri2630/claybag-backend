"""Contact Us form — public endpoint that forwards a message to talk2us@claybag.in."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, field_validator

from app.core.email import send_contact_email

router = APIRouter(prefix="/contact", tags=["contact"])


class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    message: str

    @field_validator("name")
    @classmethod
    def _v_name(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("Name is required")
        if len(v) > 120:
            raise ValueError("Name is too long")
        return v

    @field_validator("message")
    @classmethod
    def _v_msg(cls, v: str) -> str:
        v = (v or "").strip()
        if len(v) < 10:
            raise ValueError("Message must be at least 10 characters")
        if len(v) > 5000:
            raise ValueError("Message is too long (5000 char limit)")
        return v


@router.post("")
def submit_contact(payload: ContactRequest):
    sent = send_contact_email(payload.name, payload.email, payload.message)
    if not sent:
        # Don't leak SMTP details to public; keep response generic.
        raise HTTPException(503, "Could not deliver your message right now. Please email talk2us@claybag.in directly.")
    return {"ok": True, "message": "Thanks — our team will reply within 24 hours."}

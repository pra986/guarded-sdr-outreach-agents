"""Data contracts for Guarded SDR Outreach Agents."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class ProspectContext(BaseModel):
    """Input context describing a target prospect and campaign."""

    campaign_id: str = Field(..., min_length=1)
    prospect_name: str = Field(..., min_length=1)
    prospect_email: str = Field(..., min_length=3)
    company: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1)
    verified_facts: list[str] = Field(default_factory=list)
    value_proposition: str = Field(..., min_length=1)


class EmailDraftCandidate(BaseModel):
    """A single generated outreach draft with factual rubric scoring."""

    style: Literal["professional", "concise", "consultative"]
    subject: str
    body: str
    rubric_score: float = 0.0
    rubric_breakdown: dict[str, float] = Field(default_factory=dict)


class CampaignDeliveryReceipt(BaseModel):
    """Auditable receipt separating draft generation from email delivery."""

    campaign_id: str
    recipient_email: str
    selected_draft: EmailDraftCandidate | None = None
    all_candidates: list[EmailDraftCandidate] = Field(default_factory=list)
    delivery_status: Literal[
        "sent",
        "blocked_unapproved_recipient",
        "duplicate_skipped",
        "failed",
    ]
    draft_trace_id: str
    delivery_trace_id: str | None = None
    provider_message_id: str | None = None
    error_message: str | None = None
    timestamp_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

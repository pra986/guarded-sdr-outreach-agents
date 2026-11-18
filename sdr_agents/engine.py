"""Guarded SDR outreach engine with rubric scoring, allowlists, and idempotency."""

from __future__ import annotations

from typing import Callable, Iterable
from uuid import uuid4

from sdr_agents.models import (
    CampaignDeliveryReceipt,
    EmailDraftCandidate,
    ProspectContext,
)

MailProvider = Callable[[str, str, str], str]


def _default_mail_provider(recipient: str, subject: str, body: str) -> str:
    """Simulated mail provider returning a deterministic message ID."""
    return f"msg-{uuid4().hex[:10]}"


class GuardedSDREngine:
    """Multi-writer SDR engine with deterministic guardrails and trace separation."""

    def __init__(
        self,
        approved_recipients: Iterable[str] | None = None,
        approved_domains: Iterable[str] | None = None,
        mail_provider: MailProvider | None = None,
    ) -> None:
        self.approved_recipients = {
            email.strip().lower() for email in (approved_recipients or [])
        }
        self.approved_domains = {
            domain.strip().lower().lstrip("@")
            for domain in (approved_domains or [])
        }
        self._mail_provider = mail_provider or _default_mail_provider
        self._seen_campaigns: dict[str, CampaignDeliveryReceipt] = {}

    def is_recipient_approved(self, email: str) -> bool:
        normalized = email.strip().lower()
        if normalized in self.approved_recipients:
            return True
        if "@" in normalized:
            domain = normalized.split("@", 1)[1]
            if domain in self.approved_domains:
                return True
        return False

    def generate_drafts(self, prospect: ProspectContext) -> list[EmailDraftCandidate]:
        facts_block = "; ".join(prospect.verified_facts) if prospect.verified_facts else "your recent operational milestones"

        professional = EmailDraftCandidate(
            style="professional",
            subject=f"{prospect.company} — Streamlining workflows for {prospect.role}",
            body=(
                f"Hi {prospect.prospect_name},\n\n"
                f"As {prospect.role} at {prospect.company}, you have been leading key initiatives "
                f"including {facts_block}.\n\n"
                f"We help teams {prospect.value_proposition}\n\n"
                f"Would you be open to a brief 15-minute review next week?\n\n"
                f"Best regards,\nSDR Team"
            ),
        )

        concise = EmailDraftCandidate(
            style="concise",
            subject=f"Quick idea for {prospect.company}",
            body=(
                f"Hi {prospect.prospect_name},\n\n"
                f"Noticed {prospect.company}'s progress ({facts_block}). "
                f"For a {prospect.role}, our platform can help you {prospect.value_proposition}\n\n"
                f"Open to a quick chat?\n\nBest,\nSDR Team"
            ),
        )

        consultative = EmailDraftCandidate(
            style="consultative",
            subject=f"Question on {prospect.company}'s 2026 priorities",
            body=(
                f"Hi {prospect.prospect_name},\n\n"
                f"Given your focus as {prospect.role} at {prospect.company} and {facts_block}, "
                f"many peers are exploring how to {prospect.value_proposition}\n\n"
                f"How are you currently approaching this at {prospect.company}?\n\n"
                f"Regards,\nSDR Team"
            ),
        )

        return [professional, concise, consultative]

    def score_draft(
        self, draft: EmailDraftCandidate, prospect: ProspectContext
    ) -> EmailDraftCandidate:
        body_lower = draft.body.lower()

        company_ok = prospect.company.lower() in body_lower
        role_ok = prospect.role.lower() in body_lower
        company_role_score = 0.25 if (company_ok and role_ok) else (0.125 if (company_ok or role_ok) else 0.0)

        if prospect.verified_facts:
            matched_facts = sum(
                1 for fact in prospect.verified_facts if fact.lower() in body_lower
            )
            facts_score = round(0.35 * (matched_facts / len(prospect.verified_facts)), 4)
        else:
            facts_score = 0.35

        value_prop_score = (
            0.25 if prospect.value_proposition.lower() in body_lower else 0.0
        )

        word_count = len(draft.body.split())
        has_cta = "?" in draft.body
        guardrail_score = 0.15 if (has_cta and word_count <= 180) else 0.05

        breakdown = {
            "company_and_role": company_role_score,
            "verified_facts": facts_score,
            "value_proposition": value_prop_score,
            "cta_and_length": guardrail_score,
        }
        total = round(sum(breakdown.values()), 4)

        return draft.model_copy(
            update={
                "rubric_score": total,
                "rubric_breakdown": breakdown,
            }
        )

    def select_best_draft(
        self, candidates: list[EmailDraftCandidate], prospect: ProspectContext
    ) -> tuple[EmailDraftCandidate, list[EmailDraftCandidate]]:
        scored = [self.score_draft(candidate, prospect) for candidate in candidates]
        best = max(scored, key=lambda c: c.rubric_score)
        return best, scored

    def run_campaign(self, prospect: ProspectContext) -> CampaignDeliveryReceipt:
        draft_trace_id = f"draft-{uuid4().hex[:12]}"

        if prospect.campaign_id in self._seen_campaigns:
            return CampaignDeliveryReceipt(
                campaign_id=prospect.campaign_id,
                recipient_email=prospect.prospect_email,
                selected_draft=None,
                all_candidates=[],
                delivery_status="duplicate_skipped",
                draft_trace_id=draft_trace_id,
                delivery_trace_id=None,
                error_message="Duplicate campaign_id skipped by idempotency guard.",
            )

        raw_candidates = self.generate_drafts(prospect)
        best_draft, scored_candidates = self.select_best_draft(raw_candidates, prospect)

        if not self.is_recipient_approved(prospect.prospect_email):
            return CampaignDeliveryReceipt(
                campaign_id=prospect.campaign_id,
                recipient_email=prospect.prospect_email,
                selected_draft=best_draft,
                all_candidates=scored_candidates,
                delivery_status="blocked_unapproved_recipient",
                draft_trace_id=draft_trace_id,
                delivery_trace_id=None,
                error_message=(
                    f"Recipient '{prospect.prospect_email}' is not in the approved allowlist."
                ),
            )

        delivery_trace_id = f"deliv-{uuid4().hex[:12]}"
        try:
            provider_msg_id = self._mail_provider(
                prospect.prospect_email,
                best_draft.subject,
                best_draft.body,
            )
        except Exception as exc:
            return CampaignDeliveryReceipt(
                campaign_id=prospect.campaign_id,
                recipient_email=prospect.prospect_email,
                selected_draft=best_draft,
                all_candidates=scored_candidates,
                delivery_status="failed",
                draft_trace_id=draft_trace_id,
                delivery_trace_id=delivery_trace_id,
                provider_message_id=None,
                error_message=str(exc),
            )

        receipt = CampaignDeliveryReceipt(
            campaign_id=prospect.campaign_id,
            recipient_email=prospect.prospect_email,
            selected_draft=best_draft,
            all_candidates=scored_candidates,
            delivery_status="sent",
            draft_trace_id=draft_trace_id,
            delivery_trace_id=delivery_trace_id,
            provider_message_id=provider_msg_id,
            error_message=None,
        )
        self._seen_campaigns[prospect.campaign_id] = receipt
        return receipt

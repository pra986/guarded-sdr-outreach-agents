"""Pytest suite for GuardedSDREngine."""

from __future__ import annotations

from sdr_agents.engine import GuardedSDREngine
from sdr_agents.models import ProspectContext


def _make_prospect(
    campaign_id: str = "camp-001",
    email: str = "aarav@finvault.test",
) -> ProspectContext:
    return ProspectContext(
        campaign_id=campaign_id,
        prospect_name="Aarav Mehta",
        prospect_email=email,
        company="FinVault",
        role="VP of Risk Engineering",
        verified_facts=[
            "SOC 2 Type II certified in 2025",
            "42% YoY growth in automated KYC checks",
        ],
        value_proposition="reduce manual compliance review latency by 35%",
    )


def test_unapproved_recipient_blocked() -> None:
    calls: list[str] = []

    def fake_send(recipient: str, subject: str, body: str) -> str:
        calls.append(recipient)
        return "msg-should-not-send"

    engine = GuardedSDREngine(
        approved_recipients=["aarav@finvault.test"],
        mail_provider=fake_send,
    )
    receipt = engine.run_campaign(_make_prospect(email="intruder@other.test"))

    assert receipt.delivery_status == "blocked_unapproved_recipient"
    assert receipt.delivery_trace_id is None
    assert receipt.provider_message_id is None
    assert calls == []


def test_duplicate_campaign_id_deduplication() -> None:
    calls: list[str] = []

    def fake_send(recipient: str, subject: str, body: str) -> str:
        calls.append(recipient)
        return "msg-123"

    engine = GuardedSDREngine(
        approved_domains=["finvault.test"],
        mail_provider=fake_send,
    )
    prospect = _make_prospect(campaign_id="camp-dup-01")

    first = engine.run_campaign(prospect)
    second = engine.run_campaign(prospect)

    assert first.delivery_status == "sent"
    assert second.delivery_status == "duplicate_skipped"
    assert second.delivery_trace_id is None
    assert len(calls) == 1


def test_mail_provider_failure_trace_accuracy() -> None:
    def failing_send(recipient: str, subject: str, body: str) -> str:
        raise RuntimeError("SMTP 503 service unavailable")

    engine = GuardedSDREngine(
        approved_domains=["finvault.test"],
        mail_provider=failing_send,
    )
    receipt = engine.run_campaign(_make_prospect(campaign_id="camp-fail-01"))

    assert receipt.delivery_status == "failed"
    assert receipt.draft_trace_id.startswith("draft-")
    assert receipt.delivery_trace_id is not None
    assert receipt.delivery_trace_id.startswith("deliv-")
    assert receipt.provider_message_id is None
    assert "SMTP 503" in (receipt.error_message or "")


def test_factual_rubric_selection() -> None:
    engine = GuardedSDREngine(approved_domains=["finvault.test"])
    prospect = _make_prospect(campaign_id="camp-rubric-01")
    receipt = engine.run_campaign(prospect)

    assert receipt.delivery_status == "sent"
    assert len(receipt.all_candidates) == 3
    assert receipt.selected_draft is not None
    assert receipt.selected_draft.rubric_score == max(
        c.rubric_score for c in receipt.all_candidates
    )
    assert receipt.selected_draft.rubric_score > 0.8

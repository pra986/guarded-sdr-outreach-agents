"""Runnable CLI demo entrypoint for Guarded SDR Outreach Agents."""

from __future__ import annotations

import json

from sdr_agents.engine import GuardedSDREngine
from sdr_agents.models import ProspectContext


def main() -> None:
    engine = GuardedSDREngine(
        approved_recipients=["aarav.mehta@finvault.test"],
        approved_domains=["finvault.test"],
    )

    prospect = ProspectContext(
        campaign_id="camp-demo-001",
        prospect_name="Aarav Mehta",
        prospect_email="aarav.mehta@finvault.test",
        company="FinVault",
        role="VP of Risk Engineering",
        verified_facts=[
            "SOC 2 Type II certified in 2025",
            "42% YoY growth in automated KYC checks",
        ],
        value_proposition="reduce manual compliance review latency by 35% with deterministic audit trails.",
    )

    receipt = engine.run_campaign(prospect)
    print(json.dumps(receipt.model_dump(), indent=2))


if __name__ == "__main__":
    main()

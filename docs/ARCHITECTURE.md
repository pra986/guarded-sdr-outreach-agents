# Architecture — Guarded SDR Outreach Agents

## Overview

`guarded-sdr-outreach-agents` implements a deterministic, production-guarded Sales Development Representative (SDR) outreach pipeline. It separates **draft generation & scoring** from **guarded email delivery** so that failures or policy blocks are isolated and auditable.

## Pipeline Stages

1. **Context Validation (`ProspectContext`)**
   - Captures `campaign_id`, `prospect_name`, `prospect_email`, `company`, `role`, `verified_facts`, and `value_proposition`.
   - Normalizes recipient email addresses before allowlist verification.

2. **Multi-Writer Draft Generation (`GuardedSDREngine`)**
   - Generates 3 distinct style candidates (`EmailDraftCandidate`):
     - `professional`: Formal, ROI- and compliance-focused outreach.
     - `concise`: Brief, high-signal executive summary.
     - `consultative`: Hypothesis-driven, discovery-oriented outreach.

3. **Factual Rubric Scoring**
   - Each candidate is scored deterministically against a 4-part factual rubric:
     - Mentions prospect company & role.
     - Grounds claims in `verified_facts` without hallucinated metrics.
     - Includes clear value proposition & single call-to-action.
     - Respects length and tone guardrails.
   - Highest-scoring draft is selected with explicit rubric breakdown.

4. **Pre-Send Guardrails**
   - **Approved Recipient Allowlist**: Blocks delivery if `prospect_email` (or domain) is not in the configured allowlist, returning status `blocked_unapproved_recipient` without invoking the mail provider.
   - **Campaign Idempotency**: Tracks processed `campaign_id` keys (in-memory or SQLite-backed store) and returns `duplicate_skipped` on repeat submissions without double-sending.

5. **Trace Separation & Delivery Receipt (`CampaignDeliveryReceipt`)**
   - Maintains separate trace spans (`draft_trace_id` vs. `delivery_trace_id`).
   - If the mail provider raises an error or returns a failure, `delivery_status` is recorded as `failed` with the exact error reason—never falsely reported as sent.

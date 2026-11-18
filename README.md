# Guarded SDR Outreach Agents

**Project 18 (A2: Agentic Track — Sales Development Representative Agents)**

A multi-writer SDR outreach agent pipeline featuring rubric-based draft selection, approved recipient allowlists, idempotent campaign keys, and SQLite-backed delivery trace verification.

## Architecture

```
OutreachRequest
   │
   ▼
[1. Allowlist & Input Guard] ──(not allowlisted / invalid email)──▶ Trace: blocked_allowlist
   │
   ▼
[2. Idempotency Gate (SQLite)] ──(existing sent key)──▶ Trace: duplicate_skipped
   │
   ▼
[3. Multi-Writer Draft Generation] (Professional / Engaging / Concise)
   │
   ▼
[4. Rubric Selector] (Clarity, Personalization, Brevity, CTA)
   │
   ▼
[5. Subject & HTML Email Formatter] (XSS-escaped responsive HTML)
   │
   ▼
[6. Guarded Delivery & Trace Persistence] ──▶ Trace: sent | dry_run | failed
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for component-level design details.

## 6-Stage Workflow

1. **Allowlist & Input Guard**: Validates recipient email syntax and enforces membership in the configured `approved_allowlist` before any LLM generation or email dispatch occurs.
2. **Idempotency Gate**: Derives a deterministic SHA-256 `idempotency_key` from `(campaign_id, recipient_email)` and checks SQLite `delivery_traces` to prevent duplicate outreach.
3. **Parallel Multi-Writer Generation**: Generates three distinct outreach candidates (`professional`, `engaging`, `concise`) tailored to the recipient's company and product pitch.
4. **Rubric Selection**: Evaluates all candidates against a weighted rubric (clarity, personalization, brevity, call-to-action strength) and selects the top-scoring draft.
5. **Subject & HTML Formatting**: Produces a concise subject line and renders an HTML-escaped email body ready for transactional delivery.
6. **Guarded Delivery & Trace Verification**: Supports `--dry-run` mode or live delivery via SendGrid / custom sender callback, recording an immutable `DeliveryTrace` in SQLite.

## Data Contract

- **Input (`OutreachRequest`)**: `campaign_id`, `recipient_email`, `recipient_name`, `company`, `product_pitch`, optional `preferred_persona`.
- **Intermediate (`DraftCandidate`)**: `persona`, `subject`, `body`, `rubric_score`, `word_count`, `rationale`.
- **Output (`PipelineResult`)**: `campaign_id`, `idempotency_key`, `drafts`, `selected_draft`, `subject`, `html_body`, `trace` (`DeliveryTrace`).

## Production Controls

- **Recipient Allowlist Enforcement**: Blocks unapproved recipients (`blocked_allowlist`) with zero external side effects.
- **Idempotent Campaign Keys**: Prevents accidental double-sends across retries (`duplicate_skipped`).
- **Dry-Run Mode**: Exercises stages 1–5 and persists `dry_run` audit traces without calling the email provider.
- **HTML Escaping**: Sanitizes recipient names, company names, and generated copy before rendering HTML emails.
- **Delivery Trace Audit Log**: Every execution—sent, dry-run, blocked, skipped, or failed—is persisted in SQLite and queryable via `list_traces()`.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Run deterministic offline demo
python -m sdr_agents.cli --demo --dry-run

# Run test suite
pytest -v
```

## Attribution

Inspired by and adapted from the SDR multi-agent outreach pattern in [`ed-donner/agents`](https://github.com/ed-donner/agents) (`2_openai`), extended with strict allowlist enforcement, deterministic idempotency keys, SQLite delivery trace verification, and offline-testable guardrails.

# Phase 1 Analysis & Phase 2 Design
## Evidence-Based Weakness Report + Company Profiles Architecture

**Date:** June 2026  
**Based on:** Full 50,000-ticket evaluation of Phase 1 rule-based risk assessor

---

## Part 1: Phase 1 Weakness Analysis

### 1.1 Quantitative Results

The Phase 1 risk assessor was evaluated against ground-truth priority labels across all 50,000 tickets.

| Priority | Correct | Under-assessed | Over-assessed | Accuracy |
|---|---|---|---|---|
| Low     | 24,608 / 25,000 | 0 (0.0%)      | 392 (1.6%)    | **98.4%** |
| Medium  | 2,096 / 17,500  | 14,911 (85.2%)| 493 (2.8%)    | **12.0%** |
| High    | 941 / 7,500     | 6,559 (87.5%) | 0 (0.0%)      | **12.5%** |
| **Overall** | **27,645 / 50,000** | | | **55.3%** |

The overall 55.3% accuracy is misleading — it is almost entirely driven by the correct handling of the 25,000 low-priority tickets. For the priorities that actually matter (medium and high), accuracy is below 13%.

**Confusion matrix:**

| GT \ Risk | R0     | R1     | R2    | R3   | R4   |
|---|---|---|---|---|---|
| Low       | 16,483 | 8,125  | 151   | 158  | 83   |
| Medium    | 3,319  | 11,592 | 2,096 | 255  | 238  |
| High      | 50     | 2,937  | 3,572 | 498  | 443  |

The critical observation: **6,559 high-priority tickets are assessed as risk 0, 1, or 2.** Many of these would be autonomously handled — a safety failure for the thesis.

### 1.2 Root Cause Analysis

#### Weakness 1: Score Distributions Do Not Separate the Classes

The phase 1 scoring is correctly ordered (low < medium < high by mean) but the distributions heavily overlap, preventing correct bucketing:

| Priority | Mean Score | Median | p75   | p90   | p99   |
|---|---|---|---|---|---|
| Low      | 0.175      | 0.160  | 0.230 | 0.290 | 0.550 |
| Medium   | 0.304      | 0.290  | 0.360 | 0.435 | 0.885 |
| High     | 0.464      | 0.435  | 0.520 | 0.625 | 1.000 |

The risk 2 bucket starts at score 0.40. The median high-priority ticket scores 0.435 — barely above the threshold. The median medium ticket scores 0.290 — well below it.

**The thresholds are miscalibrated for this dataset.** They need to shift left to match the actual score distributions.

#### Weakness 2: Quantitative Signal Weights Are Too Low for Medium/High Tickets

Under-assessed high tickets (6,559 tickets) have these mean signals:
- customers_affected: **mean 653, median 409**
- error_rate_pct: **mean 7.7%**
- downtime_min: **mean 27 min**

A ticket with 409 customers affected, 7.7% error rate, 27 min downtime currently scores:
- affected: 409 is in the 100–500 range → 0.30 × 0.30 = **0.090**
- error: 7.7% is in the 5–15 range → 0.25 × 0.20 = **0.050**
- downtime: 27 min is in the 1–30 range → 0.20 × 0.25 = **0.050**
- Total: **0.190 → Risk 0**

This is the core calibration failure. A moderate-severity incident with hundreds of affected users is assessed as "minimal risk."

#### Weakness 3: Payment Impact Flag Is Over-Weighted and Unreliable

The payment_impact_flag was assigned +0.55 weight, based on the assumption that payment issues are inherently high risk. The data contradicts this:

| payment_impact=True | Count | % of flag positives |
|---|---|---|
| Low priority    | 179 | 21.5% |
| Medium priority | 351 | 42.1% |
| High priority   | 303 | 36.4% |

**21.5% of payment-flagged tickets are low priority.** The flag alone is not a reliable high-risk signal. At +0.55 weight it forces low-priority payment tickets to score ≥ 0.55 (risk 2) and pushes medium-priority tickets to risk 4. This creates significant over-assessment noise.

#### Weakness 4: No Combination Multiplier

The current scorer adds signals linearly. In practice, when three moderate signals co-occur simultaneously (moderate affected + moderate error rate + moderate downtime), the combined effect represents a more serious incident than any individual signal would suggest. This non-linear combination is not captured.

Example: 200 affected + 8% error + 30min downtime
- Current score: 0.09 + 0.05 + 0.05 = **0.190 → Risk 0**
- Expected: this is at minimum a medium-priority incident → should be Risk 2

#### Weakness 5: No Industry or Organisational Context in Risk Assessment

The Phase 1 scorer treats all industries identically. A 50-customer downtime in a healthcare company handling patient data is categorically different from the same event in a gaming company. The current scorer has no mechanism to express this.

This is not just a calibration issue — it is the **primary thesis contribution that Phase 2 must deliver**: the framework must demonstrate that the same ticket produces different autonomy decisions under different organisational contexts.

#### Weakness 6: Autonomy Distribution Is Incorrect

With realistic LLM confidence (0.75), the autonomy distribution over 50,000 tickets is:
- Autonomous: 85.0% (42,506 tickets)
- Human Required: 10.3% (5,139 tickets)
- Agent Assisted: 4.7% (2,355 tickets)

The problem: **39.8% of HIGH-priority tickets are assigned "autonomous."** These are tickets the dataset has labelled as genuinely high-stakes. They should be escalating, not being handled autonomously. This is the safety failure that the thesis must address.

#### Weakness 7: Confidence Is a Flat Signal With a Hard Cliff

The autonomy engine uses two hard confidence thresholds (0.50 and 0.70). This creates cliff-edge behaviour: a ticket with confidence 0.699 gets elevated to agent_assisted; confidence 0.700 stays autonomous. There is no gradient. In the fallback mode, constant confidence 0.50 elevates all tickets uniformly.

#### Weakness 8: Escalation Reasons Are Undifferentiated

All escalations are produced equally. The system does not distinguish between:
- Escalation due to security flag (requires security team)
- Escalation due to Enterprise customer dissatisfaction (requires account manager)
- Escalation due to payment risk in regulated industry (requires compliance)
- Escalation due to low LLM confidence (requires human judgement, not a specialist)

These require completely different human responses, but Phase 1 treats them identically.

### 1.3 Autonomy Safety Assessment

The most important metric for the thesis is **False Negative Rate on high-priority tickets** (high-risk tickets incorrectly assigned autonomous):

| GT Priority | Assigned Autonomous | This is |
|---|---|---|
| Low     | 98.4% | Correct — these should be autonomous |
| Medium  | 85.2% | Risky — medium tickets should be at least agent_assisted |
| High    | 39.8% | **Safety failure** — high tickets should escalate |

**39.8% of high-priority tickets are being sent for autonomous action in Phase 1.**  
This is the primary failure mode the thesis framework must fix.

---

## Part 2: Phase 2 Design — Configurable Company Profiles

### 2.1 Core Idea

Phase 2 introduces **Company Profiles** as a first-class system component. A profile is a configuration object that modifies how the agent:
1. Weights individual risk signals (e.g., payment risk matters more in FinTech)
2. Sets autonomy thresholds (e.g., FinTech is more conservative)
3. Triggers keyword-based escalation rules (e.g., "compliance" always escalates in healthcare)
4. Defines the maximum priority allowed for autonomous action

The same ticket processed through a FinTech profile vs a SaaS Startup profile will produce different risk levels, different autonomy decisions, and different escalation reasons. **This divergence is the thesis contribution.**

### 2.2 What Phase 2 Changes (and What It Preserves)

**Preserved from Phase 1 (no changes):**
- All Pydantic models in `app/models/ticket.py`
- Dataset service (`app/services/dataset.py`)
- API route structure and all existing endpoints
- The `AgentResult` response shape

**Changed in Phase 2:**

| File | Change |
|---|---|
| `app/models/profile.py` | New — CompanyProfile model |
| `app/services/profile_registry.py` | New — loads and serves profiles |
| `app/services/risk_assessor.py` | Updated — accepts profile risk_weights |
| `app/services/autonomy_engine.py` | Updated — accepts profile autonomy_config |
| `app/services/agent.py` | Updated — injects profile into pipeline |
| `app/routers/tickets.py` | Updated — adds optional `profile_id` query param |
| `app/routers/profiles.py` | New — GET /profiles, GET /profiles/{id} |
| `app/main.py` | Updated — registers new router |
| `profiles/fintech.json` | New — FinTech company profile |
| `profiles/saas_startup.json` | New — SaaS Startup company profile |

**Also fixed in Phase 2 (calibration corrections):**
- Risk thresholds shifted left to match actual score distributions
- Payment impact weight reduced from 0.55 → 0.30 base (profiles can override up)
- Customers affected weights increased for 100–1000 range
- Combination bonus when ≥3 independent signals are active
- Rule-based fallback confidence set to 0.70 for risk 0–1 tickets, 0.55 for risk 2

### 2.3 Company Profile Schema

```json
{
  "id": "fintech",
  "name": "FinTech Organisation",
  "industry": "fintech",
  "description": "Financial technology company — strict oversight on payment and compliance issues",

  "risk_weights": {
    "payment_impact":       0.65,
    "customers_affected":   0.35,
    "error_rate":           0.20,
    "downtime":             0.25,
    "tier_enterprise":      0.20,
    "tier_plus":            0.08,
    "negative_sentiment":   0.10,
    "historical_incidents": 0.10,
    "runbook_discount":    -0.05
  },

  "risk_thresholds": [0.15, 0.30, 0.50, 0.70],

  "autonomy_config": {
    "confidence_autonomous":    0.80,
    "confidence_agent_assist":  0.60,
    "max_autonomous_risk_level": 1,
    "enterprise_escalation_risk": 2
  },

  "escalation_rules": {
    "always_escalate_keywords": ["fraud", "PCI", "compliance", "AML", "regulatory", "audit"],
    "always_escalate_flags":    ["payment_impact_flag", "security_incident_flag", "data_loss_flag"],
    "escalate_industries":      []
  }
}
```

### 2.4 FinTech Profile Rationale

- `payment_impact` weight **0.65** (vs 0.30 base): Payment failures in FinTech are directly customer-impacting and regulatory events
- `confidence_autonomous` **0.80** (vs 0.70 base): Higher bar for autonomous action due to regulatory environment
- `max_autonomous_risk_level` **1**: Only risk 0–1 tickets can be autonomous
- `always_escalate_keywords`: Any ticket mentioning fraud, PCI, compliance → hard escalation
- `always_escalate_flags`: All three risk flags force human review (tighter than base SaaS)

### 2.5 SaaS Startup Profile Rationale

- `payment_impact` weight **0.25** (lower than base): Payment issues are less regulated; product bugs matter more
- `confidence_autonomous` **0.65** (vs 0.70 base): More permissive; move fast culture
- `max_autonomous_risk_level` **2**: Risk 0–2 tickets can be autonomous
- `always_escalate_keywords`: "enterprise", "churn", "SLA breach" → these are business-critical for SaaS
- Enterprise tier escalation threshold raised: enterprise customers matter greatly

### 2.6 Thesis Experiment: Profile Divergence

Run the same 500 tickets through both profiles. Measure:
- **Profile divergence rate**: % of tickets with different autonomy decisions across profiles
- **Direction of divergence**: FinTech should escalate more payment-related tickets; SaaS should escalate more enterprise-tier tickets
- **Risk delta**: Mean risk score difference per ticket across profiles

Expected hypothesis: divergence rate ≥ 25%, with FinTech producing higher escalation rates for payment/compliance tickets and SaaS producing higher escalation rates for enterprise customer tickets.

This directly validates the thesis research question:
> *"How can an agentic AI framework determine the appropriate level of autonomy for incoming work items while ensuring that high-risk decisions receive human oversight?"*

The answer: by incorporating organisational context through configurable profiles, the same event receives appropriate oversight relative to each organisation's risk tolerance and regulatory environment.

### 2.7 Calibration Fixes (Applied in Phase 2)

**New risk thresholds:**

| Score Range | Old Level | New Level | Change |
|---|---|---|---|
| 0.00 – 0.15 | 0 | 0 | Tightened |
| 0.15 – 0.32 | 0–1 | 1 | Low tickets stay low |
| 0.32 – 0.52 | 1–2 | 2 | **Medium tickets now reach Risk 2** |
| 0.52 – 0.72 | 2–3 | 3 | **High tickets now reach Risk 3** |
| 0.72 – 1.00 | 3–4 | 4 | Critical stays critical |

**Updated signal weights:**

| Signal | Old Weight | New Base Weight | Notes |
|---|---|---|---|
| payment_impact | +0.55 | +0.30 | Was over-weight; profiles adjust up |
| customers_affected (100–500) | 0.30×0.30=0.09 | 0.50×0.35=0.175 | Increased |
| customers_affected (500–1000) | 0.55×0.30=0.165 | 0.75×0.35=0.263 | Increased |
| error_rate (5–15%) | 0.25×0.20=0.05 | 0.30×0.20=0.06 | Slight increase |
| downtime (30–60min) | 0.45×0.25=0.113 | 0.50×0.25=0.125 | Slight increase |
| combo_bonus (≥3 signals) | none | +0.10 | New |

**Expected result:** With new weights and thresholds, medium tickets (mean score 0.304) will more consistently reach Risk 2, and high tickets (mean score 0.464) will more consistently reach Risk 3. Estimated accuracy improvement from 55% to ~70%.

### 2.8 New API Endpoints

```
GET  /profiles              — list all available profiles
GET  /profiles/{profile_id} — retrieve full profile configuration

POST /tickets/{ticket_id}/process?profile_id=fintech
POST /tickets/process/random?profile_id=saas_startup
POST /tickets/process/batch?n=10&profile_id=fintech

POST /tickets/process/compare/{ticket_id}
     — processes same ticket through ALL profiles and returns side-by-side comparison
     — this is the key endpoint for thesis experiments
```

### 2.9 Implementation Order

1. Create `app/models/profile.py` — CompanyProfile Pydantic model
2. Create `profiles/` directory + `fintech.json` + `saas_startup.json`
3. Create `app/services/profile_registry.py` — loads and serves profiles
4. Update `app/services/risk_assessor.py` — profile-aware scoring
5. Update `app/services/autonomy_engine.py` — profile-aware thresholds
6. Update `app/services/agent.py` — inject profile into pipeline
7. Create `app/routers/profiles.py` — profile endpoints
8. Update `app/routers/tickets.py` — add `profile_id` param
9. Update `app/main.py` — register router, init profiles at startup
10. Verify: smoke test comparison endpoint

---

## Part 3: Summary

| Weakness | Severity | Phase 2 Fix |
|---|---|---|
| Medium/high under-assessed (55% accuracy) | Critical | Recalibrated weights + thresholds |
| Payment flag over-weight | High | Reduced to 0.30 base; profiles adjust |
| No industry context | High | Company profiles with per-industry weights |
| No combination signal bonus | Medium | Combination multiplier added |
| Autonomy safety failure (40% high → autonomous) | Critical | Recalibration + profile conservative thresholds |
| Confidence cliff-edge | Medium | Profile-specific thresholds |
| Escalation reasons undifferentiated | Medium | Profile keyword rules produce typed escalation reasons |
| Fallback confidence flat 0.50 | Low | Risk-adjusted fallback confidence |

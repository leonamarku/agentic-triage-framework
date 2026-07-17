"""
Rule-based risk assessor — Phase 2.

Changes from Phase 1:
  - Now accepts an optional CompanyProfile for domain-specific signal weights.
  - Recalibrated base weights and thresholds (evidence-based, see PHASE1_ANALYSIS.md):
      * Reduced payment_impact weight (was over-weighted; unreliable across industries)
      * Increased customers_affected weight in 100–1000 range
      * Added combination bonus when ≥3 independent signals are non-zero
      * Shifted risk thresholds left to match actual score distributions
  - Hard overrides (security_incident, data_loss → Risk 4) remain unconditional
    and cannot be overridden by any profile — safety property must always hold.

Risk levels:
  0 — Minimal   : routine, no business impact
  1 — Low       : minor impact, known resolution path
  2 — Moderate  : some business impact, moderate uncertainty
  3 — High      : significant impact, complex or sensitive
  4 — Critical  : severe — security / data loss / financial risk
"""

from __future__ import annotations
from app.models.profile import CompanyProfile, DEFAULT_PROFILE, RiskWeights, RiskThresholds
from app.models.ticket import RiskAssessment, TicketInput


# ---------------------------------------------------------------------------
# Stepped score tables (shape of the response curves — weights applied after)
# ---------------------------------------------------------------------------

_AFFECTED_SCORE = [
    (0,     0.00),
    (10,    0.10),
    (100,   0.35),   # raised: 100 customers is genuinely significant
    (500,   0.60),   # raised: 500 is serious
    (1000,  0.80),   # raised: 1000+ is severe
    (float("inf"), 1.00),
]

_ERROR_RATE_SCORE = [
    (5,   0.00),
    (15,  0.30),
    (30,  0.55),
    (50,  0.75),
    (float("inf"), 0.95),
]

_DOWNTIME_SCORE = [
    (0,   0.00),
    (30,  0.25),
    (60,  0.50),
    (120, 0.75),
    (float("inf"), 0.95),
]


def _stepped(value: float, steps: list[tuple]) -> float:
    for threshold, score in steps:
        if value < threshold:
            return score
    return steps[-1][1]


def _bucket(score: float, t: RiskThresholds) -> int:
    """Map a continuous score to a risk level using profile-specific thresholds."""
    if score < t.t0: return 0
    if score < t.t1: return 1
    if score < t.t2: return 2
    if score < t.t3: return 3
    return 4


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def assess_risk(
    ticket: TicketInput,
    profile: CompanyProfile | None = None,
) -> RiskAssessment:
    """
    Compute a RiskAssessment from structured ticket fields.

    Args:
        ticket  : normalised ticket
        profile : company profile supplying domain-specific weights.
                  Falls back to DEFAULT_PROFILE if None.

    Returns:
        RiskAssessment with risk_level (0–4), risk_score (0.0–1.0),
        and a list of human-readable contributing factors.
    """
    if profile is None:
        profile = DEFAULT_PROFILE

    w: RiskWeights     = profile.risk_weights
    t: RiskThresholds  = profile.risk_thresholds
    factors: list[str] = []
    score: float       = 0.0
    active_signals     = 0   # count of non-trivial signals for combination bonus

    # ------------------------------------------------------------------
    # Hard overrides — always Risk 4, no profile can reduce these
    # ------------------------------------------------------------------
    if ticket.security_incident_flag:
        factors.append("Security incident flag — hard override to Risk 4")
        return RiskAssessment(risk_level=4, risk_score=1.0, risk_factors=factors, active_signal_count=1)

    if ticket.data_loss_flag:
        factors.append("Data loss flag — hard override to Risk 4")
        return RiskAssessment(risk_level=4, risk_score=1.0, risk_factors=factors, active_signal_count=1)

    # ------------------------------------------------------------------
    # Keyword-based escalation from profile (marks score up to threshold)
    # These don't force Risk 4 but ensure the ticket reaches at least Risk 3
    # ------------------------------------------------------------------
    ticket_context = " ".join([
        ticket.industry, ticket.product_area,
        ticket.reported_by_role, ticket.booking_channel,
    ]).lower()

    keyword_hit = False
    for kw in profile.escalation_rules.always_escalate_keywords:
        if kw.lower() in ticket_context:
            factors.append(f"Profile keyword match: '{kw}' (escalation rule)")
            keyword_hit = True
            break

    # ------------------------------------------------------------------
    # Payment impact flag (profile-weighted)
    # ------------------------------------------------------------------
    if ticket.payment_impact_flag:
        contrib = w.payment_impact
        score += contrib
        factors.append(f"Payment impact flag (+{contrib:.2f})")
        active_signals += 1

    # ------------------------------------------------------------------
    # Customers affected (profile-weighted stepped score)
    # ------------------------------------------------------------------
    aff_raw = _stepped(ticket.customers_affected, _AFFECTED_SCORE)
    aff_contrib = aff_raw * w.customers_affected
    if aff_contrib > 0.01:
        score += aff_contrib
        factors.append(
            f"{ticket.customers_affected} customers affected "
            f"(+{aff_contrib:.3f})"
        )
        active_signals += 1

    # ------------------------------------------------------------------
    # Error rate (profile-weighted)
    # ------------------------------------------------------------------
    err_raw = _stepped(ticket.error_rate_pct, _ERROR_RATE_SCORE)
    err_contrib = err_raw * w.error_rate
    if err_contrib > 0.01:
        score += err_contrib
        factors.append(
            f"Error rate {ticket.error_rate_pct:.1f}% "
            f"(+{err_contrib:.3f})"
        )
        active_signals += 1

    # ------------------------------------------------------------------
    # Downtime (profile-weighted)
    # ------------------------------------------------------------------
    down_raw = _stepped(ticket.downtime_min, _DOWNTIME_SCORE)
    down_contrib = down_raw * w.downtime
    if down_contrib > 0.01:
        score += down_contrib
        factors.append(
            f"{ticket.downtime_min} min downtime "
            f"(+{down_contrib:.3f})"
        )
        active_signals += 1

    # ------------------------------------------------------------------
    # Tier modifier (profile-weighted)
    # ------------------------------------------------------------------
    if ticket.customer_tier == "Enterprise":
        score += w.tier_enterprise
        factors.append(f"Enterprise customer tier (+{w.tier_enterprise:.2f})")
    elif ticket.customer_tier == "Plus":
        score += w.tier_plus
        factors.append(f"Plus customer tier (+{w.tier_plus:.2f})")

    # ------------------------------------------------------------------
    # Negative sentiment (profile-weighted)
    # ------------------------------------------------------------------
    if ticket.customer_sentiment == "negative":
        score += w.negative_sentiment
        factors.append(f"Negative customer sentiment (+{w.negative_sentiment:.2f})")
        active_signals += 1

    # ------------------------------------------------------------------
    # Historical incidents (profile-weighted)
    # ------------------------------------------------------------------
    if ticket.past_90d_incidents >= 5:
        score += w.historical_incidents
        factors.append(f"{ticket.past_90d_incidents} incidents in past 90 days (+{w.historical_incidents:.2f})")
        active_signals += 1
    elif ticket.past_90d_incidents >= 2:
        contrib = w.historical_incidents * 0.5
        score += contrib
        factors.append(f"{ticket.past_90d_incidents} incidents in past 90 days (+{contrib:.2f})")

    # ------------------------------------------------------------------
    # Runbook discount (profile-weighted)
    # ------------------------------------------------------------------
    if ticket.has_runbook:
        score += w.runbook_discount   # negative value
        factors.append(f"Runbook available ({w.runbook_discount:.2f})")

    # ------------------------------------------------------------------
    # Combination bonus — multiple co-occurring moderate signals indicate
    # a more complex incident than any single signal implies
    # ------------------------------------------------------------------
    if active_signals >= 3 and w.combination_bonus > 0:
        score += w.combination_bonus
        factors.append(
            f"{active_signals} co-occurring risk signals — combination bonus "
            f"(+{w.combination_bonus:.2f})"
        )

    # ------------------------------------------------------------------
    # Keyword rule: ensure at least Risk 3 when a keyword matched
    # ------------------------------------------------------------------
    if keyword_hit:
        score = max(score, t.t2 + 0.01)
        factors.append("Keyword rule: score raised to minimum Risk 3")

    # ------------------------------------------------------------------
    # Clamp and bucket using profile-specific thresholds
    # ------------------------------------------------------------------
    score = max(0.0, min(1.0, score))
    risk_level = _bucket(score, t)

    if not factors:
        factors.append("No significant risk signals detected — routine ticket")

    return RiskAssessment(
        risk_level=risk_level,
        risk_score=round(score, 4),
        risk_factors=factors,
        active_signal_count=active_signals,
    )

"""
Autonomy Engine — Phase 2 (patched).

Changes from Phase 1:
  - Now accepts a CompanyProfile for domain-specific thresholds.
  - Profile-specific max_autonomous_risk_level replaces the hard-coded value.
  - Profile escalation_rules.always_escalate_flags adds typed escalation reasons.
  - Profile-specific confidence thresholds replace the global constants.
  - Fallback confidence computed from active signal count (not flat per risk level).
  - Confidence-based escalation only applied at risk_level ≥ 2 to prevent
    over-escalation of genuinely routine tickets (fixes FinTech Scenario A).

The separation between risk assessment and autonomy decision is the core thesis
contribution: the same risk level produces different autonomy decisions under
different organisational profiles.
"""

from __future__ import annotations
from dataclasses import dataclass, field

from app.models.profile import CompanyProfile, DEFAULT_PROFILE
from app.models.ticket import RiskAssessment, TicketInput, AutonomyLevel


@dataclass
class AutonomyDecision:
    autonomy_level: AutonomyLevel
    confidence_score: float
    escalation_required: bool
    elevation_reasons: list[str] = field(default_factory=list)


def decide_autonomy(
    ticket: TicketInput,
    risk: RiskAssessment,
    llm_confidence: float,
    profile: CompanyProfile | None = None,
) -> AutonomyDecision:
    """
    Determine autonomy level from risk assessment + LLM confidence + company profile.

    Decision sequence:
      1. Base level from risk score vs profile's max_autonomous_risk_level
      2. Hard security/data_loss overrides (unconditional — no profile can remove these)
      3. Profile flag-based escalation rules
      4. Confidence-based elevation using profile thresholds
      5. Enterprise customer override using profile's enterprise_escalation_risk

    Args:
        ticket         : normalised ticket
        risk           : output of risk_assessor.assess_risk()
        llm_confidence : LLM-reported confidence (0.0–1.0).
                         Use risk-adjusted fallback if LLM unavailable.
        profile        : company profile; falls back to DEFAULT_PROFILE if None.
    """
    if profile is None:
        profile = DEFAULT_PROFILE

    ac = profile.autonomy_config
    er = profile.escalation_rules
    elevation_reasons: list[str] = []

    # ------------------------------------------------------------------
    # Step 1: Base level from risk vs profile's max autonomous threshold
    # ------------------------------------------------------------------
    max_auto = ac.max_autonomous_risk_level
    if risk.risk_level <= max_auto:
        level: AutonomyLevel = "autonomous"
    elif risk.risk_level <= max_auto + 1:
        level = "agent_assisted"
    else:
        level = "human_required"

    # ------------------------------------------------------------------
    # Step 2: Hard overrides — always human_required (no profile override)
    # ------------------------------------------------------------------
    if ticket.security_incident_flag:
        level = "human_required"
        elevation_reasons.append("Security incident flag — unconditional hard override")

    if ticket.data_loss_flag:
        level = "human_required"
        elevation_reasons.append("Data loss flag — unconditional hard override")

    # ------------------------------------------------------------------
    # Step 3: Profile-specific flag escalation rules
    # (e.g. FinTech escalates payment_impact_flag; default profile does not)
    # ------------------------------------------------------------------
    if level != "human_required":
        flag_map = {
            "payment_impact_flag":    ticket.payment_impact_flag,
            "security_incident_flag": ticket.security_incident_flag,
            "data_loss_flag":         ticket.data_loss_flag,
        }
        for flag_name in er.always_escalate_flags:
            if flag_map.get(flag_name, False):
                level = "human_required"
                elevation_reasons.append(
                    f"Profile rule: {flag_name} always escalates in {profile.name}"
                )
                break

    # ------------------------------------------------------------------
    # Step 4: Confidence-based elevation (profile-specific thresholds)
    # Only applied at risk_level >= 2: a genuinely routine ticket (risk 0–1)
    # should not be escalated purely because confidence is slightly below threshold.
    # Confidence uncertainty matters more as complexity and impact increase.
    # ------------------------------------------------------------------
    if level != "human_required" and risk.risk_level >= 2:
        if llm_confidence < ac.confidence_agent_assist:
            level = "human_required"
            elevation_reasons.append(
                f"LLM confidence {llm_confidence:.2f} below profile minimum "
                f"{ac.confidence_agent_assist:.2f} — elevated to human_required"
            )
        elif llm_confidence < ac.confidence_autonomous and level == "autonomous":
            level = "agent_assisted"
            elevation_reasons.append(
                f"LLM confidence {llm_confidence:.2f} below profile autonomous threshold "
                f"{ac.confidence_autonomous:.2f} — elevated to agent_assisted"
            )

    # ------------------------------------------------------------------
    # Step 5: Enterprise customer override (profile-specific threshold)
    # ------------------------------------------------------------------
    if (
        ticket.customer_tier == "Enterprise"
        and risk.risk_level >= ac.enterprise_escalation_risk
        and level != "human_required"
    ):
        level = "human_required"
        elevation_reasons.append(
            f"Enterprise customer with risk {risk.risk_level} ≥ "
            f"profile threshold {ac.enterprise_escalation_risk} "
            f"— elevated to human_required [{profile.name}]"
        )

    return AutonomyDecision(
        autonomy_level=level,
        confidence_score=round(llm_confidence, 4),
        escalation_required=(level == "human_required"),
        elevation_reasons=elevation_reasons,
    )


def fallback_confidence(risk_level: int, active_signal_count: int = 1) -> float:
    """
    Signal-diversity-adjusted fallback confidence for rule-based-only mode.

    Two axes:
      risk_level         : higher risk → lower base confidence (more uncertain)
      active_signal_count: more independent signals → higher confidence (better evidence)

    Formula: base + 0.04 * min(active_signal_count - 1, 4)
    Clamped to [0.30, 0.90].

    This replaces Phase 1's flat 0.50 and Phase 2's flat-per-risk-level approach.
    A Risk-2 ticket with 4 active signals is more confidently scored than one with 1 signal.
    """
    base = {0: 0.80, 1: 0.74, 2: 0.58, 3: 0.44, 4: 0.30}.get(risk_level, 0.55)
    diversity_bonus = 0.04 * min(max(active_signal_count - 1, 0), 4)
    return round(min(0.90, max(0.30, base + diversity_bonus)), 4)

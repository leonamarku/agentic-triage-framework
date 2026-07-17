"""
Company Profile model.

A profile captures an organisation's risk tolerance, domain-specific signal
weights, and autonomy thresholds. The same ticket processed through different
profiles will produce different risk levels and autonomy decisions — this
adaptability is a core thesis contribution.
"""

from __future__ import annotations
from pydantic import BaseModel, Field


class RiskWeights(BaseModel):
    """
    Per-signal scoring weights.
    Each weight is a float multiplier applied during risk scoring.
    Profiles can raise or lower any weight to reflect domain importance.
    """
    # Boolean flag weights (added to score when flag is True)
    payment_impact: float = Field(default=0.30, ge=0.0, le=1.0)
    # NOTE: security_incident and data_loss are always hard overrides (→ Risk 4)
    # and cannot be reduced by profile — safety property must hold across all contexts.

    # Quantitative signal multipliers (applied to the stepped score)
    customers_affected: float = Field(default=0.35, ge=0.0, le=1.0)
    error_rate: float = Field(default=0.20, ge=0.0, le=1.0)
    downtime: float = Field(default=0.25, ge=0.0, le=1.0)

    # Contextual modifiers
    tier_enterprise: float = Field(default=0.15, ge=0.0, le=0.50)
    tier_plus: float = Field(default=0.05, ge=0.0, le=0.30)
    negative_sentiment: float = Field(default=0.10, ge=0.0, le=0.30)
    historical_incidents: float = Field(default=0.10, ge=0.0, le=0.30)

    # Mitigation discount (negative — runbook reduces risk)
    runbook_discount: float = Field(default=-0.08, ge=-0.30, le=0.0)

    # Combination bonus — awarded when ≥3 independent signals are non-zero
    combination_bonus: float = Field(default=0.10, ge=0.0, le=0.30)


class RiskThresholds(BaseModel):
    """
    Score boundaries that separate risk levels.
    Profiles with stricter oversight lower these boundaries so more tickets
    reach higher risk levels and are more likely to be escalated.

    The four values define five buckets:
      score < t0            → Risk 0 (Minimal)
      t0 ≤ score < t1       → Risk 1 (Low)
      t1 ≤ score < t2       → Risk 2 (Moderate)
      t2 ≤ score < t3       → Risk 3 (High)
      t3 ≤ score            → Risk 4 (Critical)
    """
    t0: float = Field(default=0.15, ge=0.0, lt=1.0, description="Risk 0/1 boundary")
    t1: float = Field(default=0.32, ge=0.0, lt=1.0, description="Risk 1/2 boundary")
    t2: float = Field(default=0.52, ge=0.0, lt=1.0, description="Risk 2/3 boundary")
    t3: float = Field(default=0.72, ge=0.0, lt=1.0, description="Risk 3/4 boundary")


class AutonomyConfig(BaseModel):
    """
    Profile-specific autonomy thresholds and constraints.
    """
    # LLM confidence thresholds
    confidence_autonomous: float = Field(
        default=0.70, ge=0.0, le=1.0,
        description="Minimum LLM confidence to remain at 'autonomous' level"
    )
    confidence_agent_assist: float = Field(
        default=0.50, ge=0.0, le=1.0,
        description="Minimum LLM confidence to remain at 'agent_assisted' level; below forces human_required"
    )

    # Maximum risk level allowed for autonomous action
    max_autonomous_risk_level: int = Field(
        default=1, ge=0, le=2,
        description="Risk levels 0..max can be autonomous; above this → agent_assisted or higher"
    )

    # Enterprise customer escalation threshold
    enterprise_escalation_risk: int = Field(
        default=2, ge=1, le=4,
        description="Enterprise customers at this risk level or above are escalated"
    )


class EscalationRules(BaseModel):
    """
    Domain-specific escalation rules that override autonomy decisions.
    Any trigger here forces autonomy_level to human_required.
    """
    # Keywords in the ticket context that always force escalation
    always_escalate_keywords: list[str] = Field(
        default_factory=list,
        description="If any keyword is present in industry/product_area/role, force escalation"
    )

    # Flags that always force escalation (beyond the universal security/data_loss overrides)
    always_escalate_flags: list[str] = Field(
        default_factory=list,
        description="Ticket boolean field names that force escalation when True"
    )


class CompanyProfile(BaseModel):
    """
    Complete company profile configuration.
    Injected into the agent pipeline at processing time.
    """
    id: str = Field(description="Unique identifier used in API calls, e.g. 'fintech'")
    name: str = Field(description="Human-readable profile name")
    industry: str = Field(description="Primary industry context")
    description: str = Field(default="", description="Brief description of the profile's purpose")

    risk_weights: RiskWeights = Field(default_factory=RiskWeights)
    risk_thresholds: RiskThresholds = Field(default_factory=RiskThresholds)
    autonomy_config: AutonomyConfig = Field(default_factory=AutonomyConfig)
    escalation_rules: EscalationRules = Field(default_factory=EscalationRules)


# ---------------------------------------------------------------------------
# Built-in default profile (used when no profile_id is specified)
# ---------------------------------------------------------------------------

DEFAULT_PROFILE = CompanyProfile(
    id="default",
    name="Default Profile",
    industry="general",
    description=(
        "Balanced profile suitable for most organisations. "
        "Used when no specific profile is selected."
    ),
)

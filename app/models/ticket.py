"""
Pydantic models for the agentic triage framework.

Three layers:
  RawTicket    — mirrors the CSV row exactly (all strings, as loaded from pandas)
  TicketInput  — normalised, typed version used internally by all services
  AgentResult  — the final output returned by the API for every processed ticket
"""

from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Raw CSV row (all fields optional — CSV may have missing values)
# ---------------------------------------------------------------------------

class RawTicket(BaseModel):
    ticket_id: str
    day_of_week: str = ""
    company_id: str = ""
    company_size: str = ""
    industry: str = ""
    customer_tier: str = ""
    org_users: int = 0
    region: str = ""
    past_30d_tickets: int = 0
    past_90d_incidents: int = 0
    product_area: str = ""
    booking_channel: str = ""
    reported_by_role: str = ""
    customers_affected: int = 0
    error_rate_pct: float = 0.0
    downtime_min: int = 0
    payment_impact_flag: bool = False
    security_incident_flag: bool = False
    data_loss_flag: bool = False
    has_runbook: bool = False
    customer_sentiment: str = "neutral"
    description_length: int = 0
    # Ground truth — used for evaluation only, NOT fed to the agent
    ground_truth_priority: str = ""


# ---------------------------------------------------------------------------
# Normalised input used across all services
# ---------------------------------------------------------------------------

class TicketInput(BaseModel):
    """Clean, typed ticket fed into every service layer."""

    ticket_id: str
    industry: str
    customer_tier: Literal["Basic", "Plus", "Enterprise"]
    company_size: str
    region: str
    product_area: str
    reported_by_role: str
    booking_channel: str

    # Quantitative risk signals
    customers_affected: int = Field(ge=0)
    error_rate_pct: float = Field(ge=0.0, le=100.0)
    downtime_min: int = Field(ge=0)

    # Boolean risk flags
    payment_impact_flag: bool
    security_incident_flag: bool
    data_loss_flag: bool
    has_runbook: bool

    # Qualitative signals
    customer_sentiment: Literal["positive", "neutral", "negative"]
    description_length: int = Field(ge=0)

    # Historical context
    past_30d_tickets: int = Field(ge=0)
    past_90d_incidents: int = Field(ge=0)

    # Ground truth — available for evaluation, must NOT be used during processing
    ground_truth_priority: str = ""


# ---------------------------------------------------------------------------
# Risk assessment result (output of risk_assessor.py)
# ---------------------------------------------------------------------------

class RiskAssessment(BaseModel):
    risk_level: int = Field(ge=0, le=4, description="0=minimal … 4=critical")
    risk_score: float = Field(ge=0.0, le=1.0, description="Continuous score before level bucketing")
    risk_factors: list[str] = Field(description="Human-readable list of contributing signals")
    active_signal_count: int = Field(default=0, description="Number of independent non-trivial signals — used for fallback confidence")


# ---------------------------------------------------------------------------
# Final agent result — this is what the API returns
# ---------------------------------------------------------------------------

AutonomyLevel = Literal["autonomous", "agent_assisted", "human_required"]

class AgentResult(BaseModel):
    # Identifiers
    ticket_id: str
    industry: str
    customer_tier: str
    ground_truth_priority: str = Field(description="From dataset — for evaluation only")

    # Risk
    risk_level: int = Field(ge=0, le=4)
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_factors: list[str]

    # Autonomy decision
    autonomy_level: AutonomyLevel
    confidence_score: float = Field(ge=0.0, le=1.0)
    escalation_required: bool
    escalation_reason: str | None = Field(
        default=None,
        description="Primary reason for escalation (e.g. 'Security incident flag — hard override'). None if not escalated."
    )

    # LLM outputs
    reasoning: str = Field(description="Agent's chain-of-thought explanation")
    generated_output: str = Field(description="Draft response, brief, or investigation notes")
    recommended_action: str = Field(description="What a human or system should do next")

    # Meta
    profile_used: str = Field(description="Company profile ID used for this decision")
    llm_model_used: str
    processing_mode: Literal["full_llm", "rule_based_fallback"]

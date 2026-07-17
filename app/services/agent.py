"""
Agent service — Phase 2.

Changes from Phase 1:
  - Now accepts an optional CompanyProfile injected from the router.
  - Profile is passed through to risk_assessor and autonomy_engine.
  - Profile context is included in the LLM system prompt.
  - Fallback confidence is now risk-adjusted via autonomy_engine.fallback_confidence().
  - LLM prompt includes profile name/description for more context-aware outputs.
"""

import json
import logging

from groq import Groq, APIError, APIConnectionError, RateLimitError

from app.config import get_settings
from app.models.profile import CompanyProfile, DEFAULT_PROFILE
from app.models.ticket import AgentResult, TicketInput
from app.services.autonomy_engine import decide_autonomy, fallback_confidence
from app.services.risk_assessor import assess_risk

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an expert IT operations and support triage agent working for {company_name}.
Context: {company_description}

Your job is to analyse incoming work items and produce structured, actionable outputs
appropriate for the autonomy level already decided by the risk assessment engine.

You always respond with valid JSON only. No markdown, no prose outside the JSON.

Required schema:
{{
  "confidence_score": <float 0.0–1.0>,
  "reasoning": "<one concise paragraph explaining your analysis>",
  "generated_output": "<main work output — format depends on autonomy level>",
  "recommended_action": "<one clear sentence on what should happen next>"
}}"""

_USER_PROMPT_TEMPLATE = """\
TICKET DETAILS
==============
Ticket ID        : {ticket_id}
Industry         : {industry}
Customer Tier    : {customer_tier}
Company Size     : {company_size}
Region           : {region}
Product Area     : {product_area}
Reported By      : {reported_by_role}
Channel          : {booking_channel}
Description Length: {description_length} chars

IMPACT SIGNALS
==============
Customers Affected : {customers_affected}
Error Rate         : {error_rate_pct:.1f}%
Downtime           : {downtime_min} minutes
Payment Impact     : {payment_impact_flag}
Security Incident  : {security_incident_flag}
Data Loss          : {data_loss_flag}
Has Runbook        : {has_runbook}
Customer Sentiment : {customer_sentiment}
Past 30d Tickets   : {past_30d_tickets}
Past 90d Incidents : {past_90d_incidents}

RULE-BASED PRE-ASSESSMENT [{profile_name}]
==========================================
Risk Level  : {risk_level} / 4
Risk Score  : {risk_score:.3f}
Risk Factors: {risk_factors}

DECIDED AUTONOMY LEVEL: {autonomy_level}

{output_instructions}

Respond with valid JSON only."""

_OUTPUT_INSTRUCTIONS = {
    "autonomous": """\
OUTPUT INSTRUCTIONS (Autonomous — act independently)
=====================================================
Risk is low enough for autonomous handling.
For "generated_output", write a professional customer-facing response that:
  - Acknowledges the issue clearly
  - States what action is being taken
  - Gives a realistic resolution timeline based on severity
  - Ends with a follow-up contact line""",

    "agent_assisted": """\
OUTPUT INSTRUCTIONS (Agent-Assisted — prepare for human approval)
=================================================================
Risk requires human review before action.
For "generated_output", produce:
  1. ISSUE SUMMARY: One-sentence summary
  2. IMPACT ASSESSMENT: Who is affected and how severely
  3. DRAFT RESPONSE: Response draft the reviewer can edit and approve
  4. SUGGESTED NEXT STEPS: Numbered list of investigation/resolution steps""",

    "human_required": """\
OUTPUT INSTRUCTIONS (Human Required — escalate immediately)
===========================================================
This ticket requires immediate human decision-making.
For "generated_output", produce an escalation brief:
  1. ESCALATION SUMMARY: Why human intervention is required
  2. RISK BREAKDOWN: Key risk factors identified
  3. IMMEDIATE ACTIONS REQUIRED: Numbered urgent steps
  4. CONTEXT FOR REVIEWER: Relevant background
  5. DECISION OPTIONS: 2–3 options the human can choose from""",
}


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

def _call_llm(
    ticket: TicketInput,
    risk_level: int,
    risk_score: float,
    risk_factors: list[str],
    autonomy_level: str,
    profile: CompanyProfile,
) -> dict:
    settings = get_settings()
    client = Groq(api_key=settings.groq_api_key)

    system = _SYSTEM_PROMPT.format(
        company_name=profile.name,
        company_description=profile.description or f"A {profile.industry} organisation.",
    )

    user = _USER_PROMPT_TEMPLATE.format(
        ticket_id=ticket.ticket_id,
        industry=ticket.industry,
        customer_tier=ticket.customer_tier,
        company_size=ticket.company_size,
        region=ticket.region,
        product_area=ticket.product_area,
        reported_by_role=ticket.reported_by_role,
        booking_channel=ticket.booking_channel,
        description_length=ticket.description_length,
        customers_affected=ticket.customers_affected,
        error_rate_pct=ticket.error_rate_pct,
        downtime_min=ticket.downtime_min,
        payment_impact_flag=ticket.payment_impact_flag,
        security_incident_flag=ticket.security_incident_flag,
        data_loss_flag=ticket.data_loss_flag,
        has_runbook=ticket.has_runbook,
        customer_sentiment=ticket.customer_sentiment,
        past_30d_tickets=ticket.past_30d_tickets,
        past_90d_incidents=ticket.past_90d_incidents,
        profile_name=profile.name,
        risk_level=risk_level,
        risk_score=risk_score,
        risk_factors="; ".join(risk_factors),
        autonomy_level=autonomy_level,
        output_instructions=_OUTPUT_INSTRUCTIONS[autonomy_level],
    )

    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        temperature=0.2,
        max_tokens=1024,
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)


# ---------------------------------------------------------------------------
# Rule-based fallback
# ---------------------------------------------------------------------------

def _fallback_output(
    ticket: TicketInput,
    autonomy_level: str,
    risk_level: int,
    risk_factors: list[str],
    profile: CompanyProfile,
) -> dict:
    summaries = {
        "autonomous": (
            f"Ticket {ticket.ticket_id} ({ticket.industry}, {ticket.customer_tier} tier) "
            f"assessed as risk level {risk_level} under {profile.name}. "
            "Routine handling recommended — route to appropriate team."
        ),
        "agent_assisted": (
            f"ISSUE SUMMARY: Ticket {ticket.ticket_id} requires review under {profile.name} policy.\n"
            f"IMPACT: {ticket.customers_affected} customers affected, {ticket.downtime_min}min downtime.\n"
            f"RISK FACTORS: {'; '.join(risk_factors[:3])}\n"
            "DRAFT RESPONSE: [Pending human approval — LLM unavailable]\n"
            "NEXT STEPS: 1. Review ticket. 2. Confirm impact scope. 3. Approve or revise draft."
        ),
        "human_required": (
            f"ESCALATION BRIEF — Ticket {ticket.ticket_id} [{profile.name}]\n"
            f"Industry: {ticket.industry} | Tier: {ticket.customer_tier} | Risk: {risk_level}/4\n"
            f"RISK FACTORS: {'; '.join(risk_factors[:3])}\n"
            "ACTION: Human review required. LLM unavailable — manual assessment needed."
        ),
    }
    actions = {
        "autonomous":     "Route to support team for standard resolution.",
        "agent_assisted": "Route to human reviewer for approval before any action.",
        "human_required": "Escalate to senior support / engineering immediately.",
    }
    fb_conf = fallback_confidence(risk_level, active_signal_count=0)
    return {
        "confidence_score":   fb_conf,
        "reasoning":          f"Rule-based assessment only — LLM unavailable. [{profile.name}]",
        "generated_output":   summaries[autonomy_level],
        "recommended_action": actions[autonomy_level],
    }


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def process_ticket(
    ticket: TicketInput,
    profile: CompanyProfile | None = None,
) -> AgentResult:
    """
    Full pipeline: risk assessment → LLM → autonomy decision → result.

    Args:
        ticket  : normalised ticket
        profile : company profile; uses DEFAULT_PROFILE if None
    """
    if profile is None:
        profile = DEFAULT_PROFILE

    settings = get_settings()

    # Step 1: Risk assessment (profile-aware)
    risk = assess_risk(ticket, profile=profile)

    # Step 2: Preliminary autonomy (confidence=1.0 placeholder for prompt selection)
    preliminary = decide_autonomy(ticket, risk, llm_confidence=1.0, profile=profile)
    prelim_level = preliminary.autonomy_level

    # Step 3: LLM call
    processing_mode = "full_llm"
    try:
        llm_data = _call_llm(
            ticket=ticket,
            risk_level=risk.risk_level,
            risk_score=risk.risk_score,
            risk_factors=risk.risk_factors,
            autonomy_level=prelim_level,
            profile=profile,
        )
        llm_confidence   = float(llm_data.get("confidence_score", 0.70))
        reasoning        = str(llm_data.get("reasoning", ""))
        generated_output = str(llm_data.get("generated_output", ""))
        recommended_action = str(llm_data.get("recommended_action", ""))

    except (APIError, APIConnectionError, RateLimitError, json.JSONDecodeError, KeyError) as e:
        logger.warning("LLM call failed (%s: %s) — rule-based fallback", type(e).__name__, e)
        processing_mode = "rule_based_fallback"
        llm_confidence  = fallback_confidence(risk.risk_level, risk.active_signal_count)
        fb = _fallback_output(ticket, prelim_level, risk.risk_level, risk.risk_factors, profile)
        reasoning          = fb["reasoning"]
        generated_output   = fb["generated_output"]
        recommended_action = fb["recommended_action"]

    # Step 4: Final autonomy decision (real LLM confidence + profile)
    autonomy = decide_autonomy(ticket, risk, llm_confidence=llm_confidence, profile=profile)

    # Derive escalation_reason from first elevation reason (if escalated)
    escalation_reason: str | None = None
    if autonomy.escalation_required and autonomy.elevation_reasons:
        escalation_reason = autonomy.elevation_reasons[0]

    return AgentResult(
        ticket_id=ticket.ticket_id,
        industry=ticket.industry,
        customer_tier=ticket.customer_tier,
        ground_truth_priority=ticket.ground_truth_priority,

        risk_level=risk.risk_level,
        risk_score=risk.risk_score,
        risk_factors=risk.risk_factors,

        autonomy_level=autonomy.autonomy_level,
        confidence_score=autonomy.confidence_score,
        escalation_required=autonomy.escalation_required,
        escalation_reason=escalation_reason,

        reasoning=reasoning,
        generated_output=generated_output,
        recommended_action=recommended_action,

        profile_used=profile.id,
        llm_model_used=settings.groq_model,
        processing_mode=processing_mode,
    )

"""
Tickets router — Phase 2.

Changes from Phase 1:
  - All processing endpoints now accept an optional `profile_id` query parameter.
  - New /tickets/process/compare/{ticket_id} endpoint processes the same ticket
    through ALL registered profiles and returns a side-by-side comparison.
    This is the key endpoint for the thesis profile-divergence experiment.

Endpoints:
  GET  /tickets/info                                   — dataset statistics
  GET  /tickets/{ticket_id}                            — retrieve raw ticket
  POST /tickets/{ticket_id}/process?profile_id=...     — process with a specific profile
  POST /tickets/process/random?profile_id=...          — process a random ticket
  POST /tickets/process/batch?n=5&profile_id=...       — process N tickets
  POST /tickets/process/compare/{ticket_id}            — compare across all profiles
"""

import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.models.ticket import AgentResult, TicketInput
from app.services.agent import process_ticket
from app.services.dataset import get_dataset
from app.services.profile_registry import get_profile, list_profiles

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Dataset info
# ---------------------------------------------------------------------------

@router.get("/info")
def dataset_info():
    """Return statistics about the loaded dataset."""
    return get_dataset().get_stats()


# ---------------------------------------------------------------------------
# Retrieve a ticket (without processing)
# ---------------------------------------------------------------------------

@router.get("/{ticket_id}", response_model=TicketInput)
def get_ticket(ticket_id: str):
    """Return the normalised ticket for inspection without processing it."""
    ticket = get_dataset().get_by_id(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found.")
    return ticket


# ---------------------------------------------------------------------------
# Process a specific ticket
# ---------------------------------------------------------------------------

@router.post("/{ticket_id}/process", response_model=AgentResult)
def process_specific_ticket(
    ticket_id: str,
    profile_id: Annotated[
        str | None,
        Query(description="Company profile ID: 'default' | 'fintech' | 'saas_startup'")
    ] = None,
):
    """
    Run the full agent pipeline on a specific ticket.

    Optionally supply a profile_id to apply company-specific risk weights and
    autonomy thresholds. Uses the default profile if omitted.
    """
    ticket = get_dataset().get_by_id(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found.")

    try:
        profile = get_profile(profile_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    logger.info("Processing ticket %s with profile '%s'", ticket_id, profile.id)
    return process_ticket(ticket, profile=profile)


# ---------------------------------------------------------------------------
# Process a random ticket
# ---------------------------------------------------------------------------

@router.post("/process/random", response_model=AgentResult)
def process_random_ticket(
    profile_id: Annotated[str | None, Query(description="Profile ID")] = None,
):
    """Process a random ticket with the specified (or default) profile."""
    try:
        profile = get_profile(profile_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    ticket = get_dataset().get_random()
    logger.info("Processing random ticket %s with profile '%s'", ticket.ticket_id, profile.id)
    return process_ticket(ticket, profile=profile)


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

class BatchResponse(BaseModel):
    processed: int
    profile_used: str
    results: list[AgentResult]
    summary: dict


@router.post("/process/batch", response_model=BatchResponse)
def process_batch(
    n: Annotated[int, Query(ge=1, le=50)] = 5,
    priority_filter: Annotated[str | None, Query(description="low | medium | high")] = None,
    profile_id: Annotated[str | None, Query(description="Profile ID")] = None,
):
    """
    Process N tickets (max 50) with the specified profile.
    Optionally filter by ground-truth priority.
    """
    try:
        profile = get_profile(profile_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    tickets = get_dataset().get_sample(n, priority_filter=priority_filter)
    if not tickets:
        raise HTTPException(
            status_code=404,
            detail=f"No tickets found{f' with priority={priority_filter}' if priority_filter else ''}.",
        )

    results: list[AgentResult] = []
    for ticket in tickets:
        results.append(process_ticket(ticket, profile=profile))

    autonomy_counts: dict[str, int] = {"autonomous": 0, "agent_assisted": 0, "human_required": 0}
    escalated = 0
    risk_sum = 0.0
    for r in results:
        autonomy_counts[r.autonomy_level] = autonomy_counts.get(r.autonomy_level, 0) + 1
        if r.escalation_required:
            escalated += 1
        risk_sum += r.risk_score

    return BatchResponse(
        processed=len(results),
        profile_used=profile.id,
        results=results,
        summary={
            "autonomy_distribution": autonomy_counts,
            "escalation_rate": round(escalated / len(results), 3),
            "average_risk_score": round(risk_sum / len(results), 3),
            "priority_filter_applied": priority_filter,
        },
    )


# ---------------------------------------------------------------------------
# Profile comparison — THE THESIS EXPERIMENT ENDPOINT
# ---------------------------------------------------------------------------

class ProfileComparisonResult(BaseModel):
    ticket_id: str
    ticket_summary: dict
    results_by_profile: dict[str, AgentResult]
    divergence_summary: dict


@router.post("/process/compare/{ticket_id}", response_model=ProfileComparisonResult)
def compare_profiles(ticket_id: str):
    """
    Process the same ticket through ALL registered profiles and return a
    side-by-side comparison.

    This is the primary endpoint for the thesis profile-divergence experiment.
    The divergence_summary shows where and why profiles produced different
    autonomy decisions for the identical input ticket.
    """
    ticket = get_dataset().get_by_id(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found.")

    profiles = list_profiles()
    results_by_profile: dict[str, AgentResult] = {}

    for profile in profiles:
        logger.info("Comparing ticket %s — profile '%s'", ticket_id, profile.id)
        results_by_profile[profile.id] = process_ticket(ticket, profile=profile)

    # Build divergence summary
    autonomy_by_profile = {pid: r.autonomy_level for pid, r in results_by_profile.items()}
    risk_by_profile     = {pid: r.risk_level     for pid, r in results_by_profile.items()}
    score_by_profile    = {pid: r.risk_score      for pid, r in results_by_profile.items()}

    unique_autonomy = set(autonomy_by_profile.values())
    diverged = len(unique_autonomy) > 1

    ticket_summary = {
        "industry":            ticket.industry,
        "customer_tier":       ticket.customer_tier,
        "customers_affected":  ticket.customers_affected,
        "error_rate_pct":      ticket.error_rate_pct,
        "downtime_min":        ticket.downtime_min,
        "payment_impact_flag": ticket.payment_impact_flag,
        "security_incident_flag": ticket.security_incident_flag,
        "data_loss_flag":      ticket.data_loss_flag,
        "customer_sentiment":  ticket.customer_sentiment,
        "ground_truth_priority": ticket.ground_truth_priority,
    }

    divergence_summary = {
        "profiles_compared":   [p.id for p in profiles],
        "diverged":            diverged,
        "autonomy_by_profile": autonomy_by_profile,
        "risk_level_by_profile": risk_by_profile,
        "risk_score_by_profile": score_by_profile,
        "unique_autonomy_levels": list(unique_autonomy),
        "note": (
            "Profiles produced different autonomy decisions for the same ticket — "
            "demonstrating organisational context adaptability."
        ) if diverged else (
            "All profiles agreed on autonomy level for this ticket."
        ),
    }

    return ProfileComparisonResult(
        ticket_id=ticket_id,
        ticket_summary=ticket_summary,
        results_by_profile=results_by_profile,
        divergence_summary=divergence_summary,
    )

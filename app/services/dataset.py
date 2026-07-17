"""
Dataset service — loads and serves tickets from the 50K Support Ticket CSV.

Columns used and why:
  ticket_id             — unique identifier
  industry              — organisational context for LLM prompt
  customer_tier         — Basic/Plus/Enterprise (risk modifier)
  company_size          — Small/Medium/Large (context)
  region                — geographic context
  product_area          — which part of the product is affected
  reported_by_role      — support / devops / product_manager (context)
  booking_channel       — web / chat / phone (context)
  customers_affected    — quantitative impact signal
  error_rate_pct        — severity signal
  downtime_min          — severity/urgency signal
  payment_impact_flag   — boolean risk flag (financial risk)
  security_incident_flag— boolean risk flag (security risk)
  data_loss_flag        — boolean risk flag (data integrity risk)
  has_runbook           — mitigation availability (lowers risk)
  customer_sentiment    — positive/neutral/negative (urgency proxy)
  description_length    — proxy for ticket complexity
  past_30d_tickets      — recurrence signal
  past_90d_incidents    — historical incident rate
  priority              — ground truth label (evaluation only)

Columns intentionally excluded:
  *_cat columns         — numeric encodings; we use the string originals
  day_of_week_num       — numeric encoding; we use day_of_week string
  org_users             — not a direct risk signal in Phase 1
"""

import random
import logging
from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.models.ticket import TicketInput

logger = logging.getLogger(__name__)

# Sentinel value so callers can distinguish "not found" from errors
TICKET_NOT_FOUND = None

# Map raw CSV sentiment values to typed literals
_SENTIMENT_MAP = {
    "positive": "positive",
    "neutral": "neutral",
    "negative": "negative",
}

# Map raw tier values to typed literals
_TIER_MAP = {
    "basic": "Basic",
    "plus": "Plus",
    "enterprise": "Enterprise",
}


def _row_to_ticket(row: pd.Series) -> TicketInput:
    """Convert a DataFrame row to a typed TicketInput."""
    raw_sentiment = str(row.get("customer_sentiment", "neutral")).strip().lower()
    sentiment = _SENTIMENT_MAP.get(raw_sentiment, "neutral")

    raw_tier = str(row.get("customer_tier", "Basic")).strip().lower()
    tier = _TIER_MAP.get(raw_tier, "Basic")

    return TicketInput(
        ticket_id=str(row["ticket_id"]),
        industry=str(row.get("industry", "unknown")),
        customer_tier=tier,
        company_size=str(row.get("company_size", "unknown")),
        region=str(row.get("region", "unknown")),
        product_area=str(row.get("product_area", "unknown")),
        reported_by_role=str(row.get("reported_by_role", "unknown")),
        booking_channel=str(row.get("booking_channel", "unknown")),
        customers_affected=int(row.get("customers_affected", 0)),
        error_rate_pct=float(row.get("error_rate_pct", 0.0)),
        downtime_min=int(row.get("downtime_min", 0)),
        payment_impact_flag=bool(int(row.get("payment_impact_flag", 0))),
        security_incident_flag=bool(int(row.get("security_incident_flag", 0))),
        data_loss_flag=bool(int(row.get("data_loss_flag", 0))),
        has_runbook=bool(int(row.get("has_runbook", 0))),
        customer_sentiment=sentiment,
        description_length=int(row.get("description_length", 0)),
        past_30d_tickets=int(row.get("past_30d_tickets", 0)),
        past_90d_incidents=int(row.get("past_90d_incidents", 0)),
        ground_truth_priority=str(row.get("priority", "")),
    )


class DatasetService:
    """
    Loads the 50K support ticket CSV once at startup and provides
    lookup by ticket_id and random sampling.
    """

    def __init__(self, dataset_path: str) -> None:
        path = Path(dataset_path)
        if not path.exists():
            raise FileNotFoundError(
                f"Dataset not found at '{dataset_path}'. "
                "Make sure the CSV is in the data/ directory."
            )

        logger.info("Loading dataset from %s …", path)
        self._df = pd.read_csv(path, dtype={"ticket_id": str})
        self._df.set_index("ticket_id", inplace=True)
        logger.info("Dataset loaded: %d tickets", len(self._df))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def size(self) -> int:
        return len(self._df)

    @property
    def ticket_ids(self) -> list[str]:
        return self._df.index.tolist()

    def get_by_id(self, ticket_id: str) -> TicketInput | None:
        """Return a specific ticket or None if not found."""
        if ticket_id not in self._df.index:
            return TICKET_NOT_FOUND
        row = self._df.loc[ticket_id].copy()
        row["ticket_id"] = ticket_id   # restore index value as a column for _row_to_ticket
        return _row_to_ticket(row)

    def get_random(self) -> TicketInput:
        """Return one ticket chosen uniformly at random."""
        row = self._df.sample(1).iloc[0]
        row.name = self._df.sample(1).index[0]
        # Re-sample properly to include the index
        sample = self._df.sample(1)
        row = sample.iloc[0]
        ticket_id = sample.index[0]
        row = row.copy()
        row["ticket_id"] = ticket_id
        return _row_to_ticket(row)

    def get_sample(self, n: int, priority_filter: str | None = None) -> list[TicketInput]:
        """
        Return up to n tickets, optionally filtered by ground-truth priority.
        Useful for evaluation runs.
        """
        df = self._df
        if priority_filter:
            df = df[df["priority"].str.lower() == priority_filter.lower()]

        n = min(n, len(df))
        sample = df.sample(n)
        tickets = []
        for ticket_id, row in sample.iterrows():
            row = row.copy()
            row["ticket_id"] = ticket_id
            tickets.append(_row_to_ticket(row))
        return tickets

    def get_stats(self) -> dict:
        """Return basic dataset statistics for the /health or /info endpoint."""
        priority_dist = self._df["priority"].value_counts().to_dict()
        industry_dist = self._df["industry"].value_counts().to_dict()
        return {
            "total_tickets": len(self._df),
            "priority_distribution": priority_dist,
            "industry_distribution": industry_dist,
        }


# ---------------------------------------------------------------------------
# Application-level singleton (created once, reused across requests)
# ---------------------------------------------------------------------------
_dataset_service: DatasetService | None = None


def init_dataset(dataset_path: str) -> None:
    global _dataset_service
    _dataset_service = DatasetService(dataset_path)


def get_dataset() -> DatasetService:
    if _dataset_service is None:
        raise RuntimeError("Dataset not initialised. Call init_dataset() at startup.")
    return _dataset_service

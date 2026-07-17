# Thesis Architecture Design
## Agentic AI Framework for Autonomous Work Item Triage

**Version:** 1.0  
**Date:** June 2026  
**Status:** Pre-implementation — approved design baseline

---

## Part 1: Dataset Analysis & Sufficiency Assessment

### The Three Datasets

#### Dataset 1: `all_tickets_processed_improved_v3.csv`
- **Size:** 47,837 rows
- **Columns:** `Document` (ticket text), `Topic_group` (category label)
- **Categories:** Hardware (13,617), HR Support (10,915), Access (7,125), Miscellaneous (7,060), Storage (2,777), Purchase (2,464), Internal Project (2,119), Administrative rights (1,760)
- **Verdict:** Good source of real ticket text for category classification. **No priority or risk signal.** Text is preprocessed/cleaned (stopwords removed) — this weakens realism for LLM prompting but is fine for classification baselines.

#### Dataset 2: `customer_support_tickets.csv`
- **Size:** 8,469 rows
- **Columns:** Ticket ID, Customer Name/Email/Age/Gender, Product, Date, Ticket Type, Subject, Description, Status, Resolution, Priority, Channel, Response Time, Resolution Time, Satisfaction Rating
- **Priority distribution:** Low (2,063), Medium (2,192), High (2,085), Critical (2,129) — near-uniform, likely synthetic
- **Critical issue:** Ticket descriptions contain unfilled template placeholders (`{product_purchased}`). This confirms the dataset is **synthetic/generated**, not real customer data.
- **Verdict:** Useful for structural schema design and priority label benchmarking. Not suitable as primary LLM input due to synthetic descriptions. Use only for metadata fields (channel, status, response time).

#### Dataset 3: `Support_tickets.csv` (50K Priority Dataset)
- **Size:** 50,000 rows
- **Columns:** ticket_id, day_of_week, company metadata (size, industry, region, tier), operational signals (customers_affected, error_rate_pct, downtime_min), boolean risk flags (payment_impact_flag, security_incident_flag, data_loss_flag), has_runbook, customer_sentiment, priority label
- **Priority distribution:** Low (25,000), Medium (17,500), High (7,500) — realistic imbalanced distribution
- **Risk signals:** security_incident_flag (139 positive cases), payment_impact_flag (833), data_loss_flag (253)
- **Industry coverage:** SaaS B2B, Media, Ecommerce, Gaming, FinTech, Logistics, Healthcare
- **Verdict:** **The primary dataset.** Rich structured risk signals directly map onto the thesis autonomy framework. The imbalanced priority distribution is realistic and valuable for evaluation.

### Combined Assessment

| Requirement | Coverage | Source |
|---|---|---|
| Ticket text / NLP | ✅ Good | DS1 (47K real text) |
| Priority labels (ground truth) | ✅ Excellent | DS3 (50K, realistic imbalance) |
| Risk signals (structured) | ✅ Excellent | DS3 (security, payment, data loss, downtime) |
| Multi-industry context | ✅ Good | DS3 (7 industries) |
| Customer/org metadata | ✅ Good | DS3 (tier, size, region) |
| Ticket categories | ✅ Good | DS1 (8 IT categories) |
| Real ticket descriptions | ⚠️ Partial | DS1 (preprocessed), DS2 (synthetic) |
| Escalation ground truth | ❌ Missing | Must be derived/synthesized |
| Autonomy level labels | ❌ Missing | Must be rule-derived from DS3 signals |
| Resolution / actions taken | ⚠️ Partial | DS2 (but synthetic) |

### Sufficiency Verdict

**The datasets are sufficient for a master's thesis prototype.** The combination of DS1 (text) + DS3 (structured risk signals + priority labels) provides enough data to:
1. Train and evaluate a risk assessment module
2. Derive autonomy level labels via rule-based mapping (a defensible methodology)
3. Benchmark the agent's decisions against ground-truth priority labels
4. Simulate multi-industry organizational contexts

**Known limitations to declare in the thesis:**
- No real escalation ground truth — autonomy labels will be rule-derived, which must be acknowledged as a study design choice
- DS2 descriptions are synthetic — exclude from LLM prompting experiments
- DS1 text is preprocessed — use for category classification only, not for generative outputs

**Recommended data strategy:**
- **Primary evaluation dataset:** DS3 (50K) — use 80/20 train/test split
- **Text corpus:** DS1 (47K) — use for category labeling and ticket text generation in demo
- **Schema reference only:** DS2 — inform field design, do not use for LLM experiments

---

## Part 2: System Architecture

### Overview

The system is a three-tier web application with an embedded agentic layer. It is designed to sit between an incoming task stream (CSV upload simulating Jira/ServiceNow) and human reviewers.

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React + Tailwind)              │
│   Dashboard | Task Queue | Decision View | Config Panel         │
└─────────────────────────┬───────────────────────────────────────┘
                          │ REST + WebSocket (SSE for streaming)
┌─────────────────────────▼───────────────────────────────────────┐
│                        BACKEND (FastAPI)                        │
│   /tasks  /decisions  /profiles  /escalations  /evaluate        │
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │                  AGENT LAYER (LangGraph)                 │  │
│   │                                                          │  │
│   │  IntakeNode → AssessmentNode → AutonomyNode →            │  │
│   │  ActionNode → EscalationNode → OutputNode               │  │
│   └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│   ┌──────────────┐  ┌───────────────┐  ┌─────────────────────┐  │
│   │  LLM Client  │  │ CompanyProfile│  │  Evaluation Engine  │  │
│   │  (Groq API)  │  │   Registry    │  │  (metrics + logging)│  │
│   └──────────────┘  └───────────────┘  └─────────────────────┘  │
└─────────────────────────┬───────────────────────────────────────┘
                          │ SQLAlchemy ORM
┌─────────────────────────▼───────────────────────────────────────┐
│                     DATABASE (PostgreSQL / Supabase)            │
│   tickets | decisions | agent_outputs | company_profiles        │
│   escalations | evaluation_runs | audit_log                     │
└─────────────────────────────────────────────────────────────────┘
```

### Technology Stack (Confirmed)

| Layer | Technology | Justification |
|---|---|---|
| Frontend | React + Tailwind CSS | Component-based, rapid UI, widely supported |
| Backend | FastAPI (Python) | Async support, native Pydantic, easy LangGraph integration |
| Agent Framework | LangGraph | Stateful graph execution, conditional edges, supports human-in-the-loop |
| LLM | Groq API (llama-3.1-70b or mixtral-8x7b) | Free tier, low latency, OpenAI-compatible API |
| Database | PostgreSQL via Supabase | Managed, free tier, real-time subscriptions available |
| ORM | SQLAlchemy + Alembic | Migrations, type safety |
| Deployment | Railway or Render | Free tier, Docker support, environment variables |

### Component Responsibilities

**Frontend:**
- Ticket queue view (incoming tasks, status badges)
- Decision detail view (risk score, autonomy level, reasoning, generated outputs)
- Company profile configuration panel (risk thresholds, domain-specific overrides)
- Evaluation dashboard (accuracy metrics, confusion matrix, autonomy distribution)
- CSV upload interface (batch processing)

**Backend:**
- REST API for all CRUD operations
- Task ingestion pipeline (CSV parsing → normalization → queue)
- Agent invocation (async background tasks via FastAPI BackgroundTasks or Celery)
- Server-Sent Events (SSE) for real-time agent progress streaming
- Evaluation endpoints for running benchmark experiments

**Agent Layer:**
- Stateful LangGraph workflow (see Part 4)
- LLM calls via LangChain's ChatGroq wrapper
- Company profile injection at assessment time
- Structured output parsing (Pydantic models)

---

## Part 3: Database Schema

### Core Tables

```sql
-- Company profiles: configurable organizational contexts
CREATE TABLE company_profiles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL,
    industry        VARCHAR(50) NOT NULL,       -- fintech, saas, healthcare, etc.
    risk_config     JSONB NOT NULL,             -- domain-specific risk overrides
    autonomy_config JSONB NOT NULL,             -- autonomy threshold overrides
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- Example risk_config for FinTech:
-- {
--   "high_risk_keywords": ["payment", "fraud", "compliance", "PCI"],
--   "auto_escalate_categories": ["security_incident", "data_loss"],
--   "max_autonomous_priority": "low",
--   "require_human_for": ["payment_impact", "regulatory"]
-- }

-- Raw incoming tickets (before agent processing)
CREATE TABLE tickets (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id             VARCHAR(100),           -- original ID from dataset/source
    company_profile_id      UUID REFERENCES company_profiles(id),
    
    -- Ticket content
    title                   TEXT,
    description             TEXT,
    category                VARCHAR(100),
    ticket_type             VARCHAR(100),
    channel                 VARCHAR(50),            -- email, chat, phone, web
    
    -- Structured risk signals (mapped from DS3 fields)
    customers_affected      INTEGER DEFAULT 0,
    error_rate_pct          FLOAT DEFAULT 0.0,
    downtime_min            INTEGER DEFAULT 0,
    payment_impact_flag     BOOLEAN DEFAULT FALSE,
    security_incident_flag  BOOLEAN DEFAULT FALSE,
    data_loss_flag          BOOLEAN DEFAULT FALSE,
    has_runbook             BOOLEAN DEFAULT FALSE,
    customer_sentiment      VARCHAR(20),            -- positive, neutral, negative
    customer_tier           VARCHAR(20),            -- Basic, Plus, Enterprise
    industry                VARCHAR(50),
    region                  VARCHAR(20),
    
    -- Ground truth (from dataset, used for evaluation)
    ground_truth_priority   VARCHAR(20),            -- low, medium, high, critical
    
    -- Processing state
    status                  VARCHAR(30) DEFAULT 'pending',  -- pending, processing, completed, escalated
    created_at              TIMESTAMPTZ DEFAULT now(),
    processed_at            TIMESTAMPTZ
);

-- Agent decisions: the core output of the framework
CREATE TABLE decisions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id               UUID REFERENCES tickets(id) ON DELETE CASCADE,
    company_profile_id      UUID REFERENCES company_profiles(id),
    
    -- Risk assessment
    risk_level              INTEGER NOT NULL CHECK (risk_level BETWEEN 0 AND 4),
    risk_score              FLOAT NOT NULL,         -- 0.0 – 1.0 continuous score
    risk_factors            JSONB NOT NULL,         -- which signals contributed and why
    
    -- Autonomy decision
    autonomy_level          VARCHAR(30) NOT NULL,   -- autonomous, agent_assisted, human_required
    confidence_score        FLOAT NOT NULL,         -- 0.0 – 1.0
    
    -- Escalation
    is_escalated            BOOLEAN DEFAULT FALSE,
    escalation_reason       TEXT,
    escalation_triggers     JSONB,                  -- list of triggered rules
    
    -- LLM reasoning
    reasoning               TEXT NOT NULL,          -- full chain-of-thought from LLM
    recommended_action      TEXT,
    
    -- Timing
    processing_time_ms      INTEGER,
    llm_tokens_used         INTEGER,
    created_at              TIMESTAMPTZ DEFAULT now()
);

-- Agent-generated work outputs
CREATE TABLE agent_outputs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id         UUID REFERENCES decisions(id) ON DELETE CASCADE,
    ticket_id           UUID REFERENCES tickets(id) ON DELETE CASCADE,
    
    output_type         VARCHAR(50) NOT NULL,   -- response_draft, summary, routing_rec,
                                                 -- investigation_notes, escalation_brief, documentation
    content             TEXT NOT NULL,
    
    -- Human review tracking
    reviewed_by_human   BOOLEAN DEFAULT FALSE,
    human_approved      BOOLEAN,
    human_edited        BOOLEAN DEFAULT FALSE,
    human_feedback      TEXT,
    
    created_at          TIMESTAMPTZ DEFAULT now()
);

-- Escalations: formal escalation records
CREATE TABLE escalations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id           UUID REFERENCES tickets(id),
    decision_id         UUID REFERENCES decisions(id),
    
    escalation_type     VARCHAR(50),    -- risk_threshold, missing_info, policy_override, uncertainty
    severity            VARCHAR(20),    -- low, medium, high, critical
    brief               TEXT NOT NULL,  -- agent-generated escalation brief
    context_summary     TEXT,
    recommended_actions JSONB,
    
    -- Resolution
    resolved            BOOLEAN DEFAULT FALSE,
    resolved_by         VARCHAR(100),
    resolution_notes    TEXT,
    resolved_at         TIMESTAMPTZ,
    
    created_at          TIMESTAMPTZ DEFAULT now()
);

-- Evaluation runs: batch experiment records
CREATE TABLE evaluation_runs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_name                VARCHAR(100),
    company_profile_id      UUID REFERENCES company_profiles(id),
    dataset_name            VARCHAR(100),
    
    -- Run parameters
    sample_size             INTEGER,
    llm_model               VARCHAR(100),
    
    -- Aggregate metrics
    priority_accuracy       FLOAT,          -- agent risk vs ground truth priority
    escalation_rate         FLOAT,
    autonomous_rate         FLOAT,
    human_required_rate     FLOAT,
    avg_confidence          FLOAT,
    avg_processing_time_ms  FLOAT,
    
    -- Detailed results
    confusion_matrix        JSONB,          -- priority prediction confusion matrix
    autonomy_distribution   JSONB,          -- breakdown by autonomy level
    per_industry_metrics    JSONB,
    
    created_at              TIMESTAMPTZ DEFAULT now()
);

-- Audit log: immutable record of all agent actions
CREATE TABLE audit_log (
    id              BIGSERIAL PRIMARY KEY,
    ticket_id       UUID,
    decision_id     UUID,
    event_type      VARCHAR(50),    -- ticket_ingested, risk_assessed, action_taken, escalated, human_override
    event_data      JSONB,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_profile ON tickets(company_profile_id);
CREATE INDEX idx_decisions_ticket ON decisions(ticket_id);
CREATE INDEX idx_decisions_autonomy ON decisions(autonomy_level);
CREATE INDEX idx_decisions_risk ON decisions(risk_level);
CREATE INDEX idx_escalations_resolved ON escalations(resolved);
CREATE INDEX idx_audit_ticket ON audit_log(ticket_id);
```

---

## Part 4: Agent Workflow (LangGraph)

### State Schema

```python
class AgentState(TypedDict):
    # Input
    ticket: TicketModel
    company_profile: CompanyProfileModel
    
    # Assessment outputs
    risk_level: int                    # 0-4
    risk_score: float                  # 0.0-1.0
    risk_factors: list[str]            # contributing factors
    uncertainty_flags: list[str]       # missing info, ambiguity
    
    # Decision outputs
    autonomy_level: str                # autonomous | agent_assisted | human_required
    confidence_score: float
    reasoning: str
    
    # Action outputs
    generated_outputs: list[dict]      # list of {type, content}
    recommended_action: str
    
    # Escalation
    should_escalate: bool
    escalation_reason: str
    escalation_triggers: list[str]
    
    # Control
    error: str | None
    processing_steps: list[str]        # trace of nodes visited
```

### Node Definitions

```
┌─────────────┐
│  INTAKE     │  Parse & normalize ticket. Enrich with company profile context.
│  NODE       │  Validate required fields. Flag missing information.
└──────┬──────┘
       │
┌──────▼──────┐
│ ASSESSMENT  │  LLM call #1: Structured risk assessment.
│  NODE       │  Input: ticket fields + company risk_config
               │  Output: risk_level (0-4), risk_score, risk_factors[], uncertainty_flags[]
└──────┬──────┘
       │
┌──────▼──────┐
│  AUTONOMY   │  Rule-based + LLM validation: Map risk → autonomy level.
│  NODE       │  Apply company profile overrides.
               │  Output: autonomy_level, confidence_score
└──────┬──────┘
       │
   ┌───┴────────────────────────────┐
   │ conditional edge               │
   ▼                                ▼
┌──────────┐                ┌───────────────┐
│  ACTION  │                │  ESCALATION   │
│  NODE    │                │  NODE         │
│          │                │               │
│ LLM #2:  │                │ LLM #3:       │
│ Generate │                │ Generate      │
│ outputs  │                │ escalation    │
│ based on │                │ brief +       │
│ autonomy │                │ context       │
│ level    │                │ summary       │
└────┬─────┘                └───────┬───────┘
     │                              │
     └──────────────┬───────────────┘
                    │
             ┌──────▼──────┐
             │   OUTPUT    │  Persist decision + outputs to DB.
             │   NODE      │  Emit audit log entry. Return final state.
             └─────────────┘
```

### Node Logic Detail

**IntakeNode:**
- Normalize field names from CSV/API format to internal schema
- Inject company_profile into state
- Flag missing critical fields (description_length < 20, no category, etc.)
- Add `missing_info` to uncertainty_flags if applicable

**AssessmentNode (LLM Call #1):**
```
System prompt: You are a risk assessment engine for {company.name}, 
a {company.industry} company. Assess the following work item for risk level,
business impact, security implications, and compliance concerns.
Company risk configuration: {company.risk_config}

Output ONLY valid JSON matching this schema:
{
  "risk_level": 0-4,
  "risk_score": 0.0-1.0,
  "risk_factors": ["..."],
  "uncertainty_flags": ["..."],
  "reasoning": "..."
}
```
- Structured output forced via JSON mode
- Fallback: if LLM fails, use rule-based scoring from structured fields only
- Rule-based fallback scoring:
  - security_incident_flag = True → +2 risk levels
  - data_loss_flag = True → +2 risk levels  
  - payment_impact_flag = True → +1 risk level
  - customers_affected > 1000 → +1 risk level
  - downtime_min > 60 → +1 risk level
  - customer_tier = Enterprise → +0.5 (score only)

**AutonomyNode (Rule-based + override):**
```
Base mapping (before company overrides):
  Risk 0 → Autonomous (handle fully)
  Risk 1 → Autonomous (handle fully)
  Risk 2 → Agent-Assisted (prepare, require approval)
  Risk 3 → Human Required (escalate with brief)
  Risk 4 → Human Required (immediate escalation)

Modifiers that can elevate autonomy level:
  - confidence_score < 0.60 → elevate one level
  - uncertainty_flags non-empty → elevate one level
  - company_profile.require_human_for matches category → force Human Required
  - security_incident_flag = True → force Human Required (always)
  - data_loss_flag = True → force Human Required (always)
  - customer_tier = Enterprise AND risk >= 2 → elevate to Human Required
```

**ActionNode (LLM Call #2) — outputs by autonomy level:**

| Autonomy Level | Generated Outputs |
|---|---|
| Autonomous | response_draft, routing_recommendation, priority_assignment, documentation |
| Agent-Assisted | response_draft (pending approval), summary, routing_recommendation, suggested_actions |
| Human Required | escalation_brief, context_summary, risk_summary, recommended_actions |

**EscalationNode (LLM Call #3 — only when is_escalated=True):**
- Generate structured escalation brief
- Identify key risks
- Recommend immediate actions
- Notify human reviewer (via database flag, not email in prototype)

---

## Part 5: Autonomy Framework & Escalation Logic

### Risk Level Definitions

| Level | Name | Description | Example |
|---|---|---|---|
| 0 | Minimal | Routine, no business impact, fully understood | Password reset, FAQ inquiry |
| 1 | Low | Minor impact, known resolution path | Software install, standard account query |
| 2 | Moderate | Some business impact, moderate uncertainty | Service degradation, billing dispute |
| 3 | High | Significant impact, complex or sensitive | Outage affecting many users, data concern |
| 4 | Critical | Severe impact, security/compliance/financial risk | Security breach, data loss, payment fraud |

### Autonomy Levels

**Autonomous:**
- Agent acts independently, no human review before delivery
- All outputs are directly committed (response sent, ticket closed, routing applied)
- Criteria: Risk 0-1, confidence ≥ 0.75, no uncertainty flags, no company override

**Agent-Assisted:**
- Agent prepares all work but holds for human approval
- Human sees: draft response, routing suggestion, reasoning
- Human approves/edits/rejects before action
- Criteria: Risk 2, OR confidence 0.60-0.74, OR uncertainty flags present

**Human Required:**
- Agent escalates immediately with a brief
- Agent still generates context summary and recommended actions (reduces human effort)
- Human makes final decision
- Criteria: Risk 3-4, OR security/data_loss flags, OR company profile override, OR confidence < 0.60

### Key Design Principle: Risk ≠ Autonomy

A risk-2 ticket from a company with `max_autonomous_priority: low` gets escalated. A risk-2 ticket from a startup with permissive config stays agent-assisted. The company profile is the second dimension that separates risk assessment from autonomy decision — this is the thesis contribution.

### Escalation Triggers (Enumerated)

```python
ESCALATION_TRIGGERS = {
    "RISK_THRESHOLD":       "Risk level exceeds company maximum for autonomous action",
    "SECURITY_FLAG":        "Security incident flag is active",
    "DATA_LOSS_FLAG":       "Data loss flag is active",
    "PAYMENT_IMPACT":       "Payment impact flag active in regulated industry",
    "LOW_CONFIDENCE":       "Agent confidence below minimum threshold",
    "MISSING_INFORMATION":  "Critical fields missing, cannot assess reliably",
    "ENTERPRISE_CUSTOMER":  "Enterprise-tier customer with elevated risk",
    "POLICY_OVERRIDE":      "Company profile mandates human review for this category",
    "HIGH_USER_IMPACT":     "More than threshold customers affected",
    "COMPLIANCE_KEYWORD":   "Description contains compliance/regulatory keyword",
}
```

### Company Profile Examples

**FinTech Profile:**
```json
{
  "name": "FinTech Corp",
  "industry": "fintech",
  "risk_config": {
    "max_autonomous_risk": 1,
    "high_risk_keywords": ["payment", "fraud", "PCI", "compliance", "AML"],
    "auto_escalate_categories": ["security_incident", "data_loss", "payment_impact"],
    "require_human_for": ["payment_impact", "regulatory", "enterprise_customer"]
  },
  "autonomy_config": {
    "confidence_threshold": 0.80,
    "max_autonomous_priority": "low"
  }
}
```

**SaaS Startup Profile:**
```json
{
  "name": "SaaS Startup",
  "industry": "saas_b2b",
  "risk_config": {
    "max_autonomous_risk": 2,
    "high_risk_keywords": ["enterprise", "churn", "roadmap", "SLA breach"],
    "auto_escalate_categories": ["security_incident"],
    "require_human_for": ["strategic_roadmap", "enterprise_customer_complaint"]
  },
  "autonomy_config": {
    "confidence_threshold": 0.65,
    "max_autonomous_priority": "medium"
  }
}
```

**Healthcare Profile:**
```json
{
  "name": "Healthcare Org",
  "industry": "healthcare",
  "risk_config": {
    "max_autonomous_risk": 1,
    "high_risk_keywords": ["PHI", "patient", "HIPAA", "clinical", "medication"],
    "auto_escalate_categories": ["data_loss", "security_incident", "patient_data"],
    "require_human_for": ["patient_impact", "data_loss", "compliance"]
  },
  "autonomy_config": {
    "confidence_threshold": 0.85,
    "max_autonomous_priority": "low"
  }
}
```

---

## Part 6: Evaluation Methodology

### Research Question (Restated)
> How can an agentic AI framework determine the appropriate level of autonomy for incoming work items while ensuring that high-risk decisions receive human oversight?

### Evaluation Dimensions

The thesis evaluation must address three distinct questions:

1. **Risk Assessment Accuracy** — Does the agent correctly assess risk relative to ground truth?
2. **Autonomy Appropriateness** — Are autonomy decisions aligned with what humans would decide?
3. **Output Quality** — Are the agent's generated outputs (drafts, briefs) useful?

### Dimension 1: Risk Assessment Accuracy

**Method:** Compare agent `risk_level` against `ground_truth_priority` from DS3.

**Priority → Risk level mapping:**
```
low      → Risk 0-1  (expected)
medium   → Risk 2    (expected)
high     → Risk 3    (expected)
critical → Risk 4    (expected)
```

**Metrics:**
- Accuracy (exact match after mapping)
- Weighted F1-score (macro and per-class)
- Confusion matrix
- False Negative Rate for high-risk items (safety-critical metric — this is the most important one: agent must never under-assess critical tickets)

**Baselines:**
1. Random classifier
2. Rule-based classifier (pure structured signals, no LLM)
3. Fine-tuned BERT/RoBERTa on DS3 (optional, strong baseline)

**Test split:** 20% of DS3 (10,000 tickets), stratified by priority.

### Dimension 2: Autonomy Appropriateness

**Challenge:** No ground-truth autonomy labels exist. Two approaches:

**Approach A — Rule-derived labels (primary):**
Define the "correct" autonomy level from structured signals as a deterministic function:
```
if security_incident_flag or data_loss_flag → human_required
elif priority = critical → human_required
elif priority = high → agent_assisted
elif priority = medium → agent_assisted
elif priority = low → autonomous
```
Then measure how often the agent agrees with these derived labels. This is defensible as evaluating consistency with a specified policy, which is a research contribution in itself.

**Approach B — Human annotation study (for qualitative section):**
Select 100-200 tickets across the risk spectrum. Present to 3 human raters. Collect their autonomy judgments. Compute inter-rater agreement (Cohen's κ). Compare agent decisions to human consensus.

**Metrics:**
- Agreement rate with rule-derived labels (Approach A)
- Cohen's κ against human raters (Approach B)
- Escalation precision/recall (correctly escalating truly risky tickets)
- False escalation rate (autonomy "wasted" on low-risk items)
- Safety metric: Proportion of risk-3/4 tickets correctly assigned human_required

### Dimension 3: Output Quality

**Method:** LLM-as-judge evaluation (GPT-4 or Claude evaluator) + human spot-check

**For each output type, evaluate:**
- Relevance (1-5): Does the output address the ticket?
- Accuracy (1-5): Is the information correct?
- Actionability (1-5): Can a human act on this output?
- Conciseness (1-5): Is it appropriately brief?

**Sample:** 50-100 outputs per output type, sampled from across risk levels.

### Dimension 4: Cross-Profile Consistency

**Method:** Run the same 500 tickets through three company profiles (FinTech, SaaS, Healthcare).

**Expected finding:** Same ticket produces different autonomy decisions under different profiles.

**Metric:** Profile divergence rate — proportion of tickets where autonomy level differs across profiles. This directly validates the thesis contribution of configurable organizational context.

### Evaluation Summary Table

| Dimension | Method | Key Metric | Baseline |
|---|---|---|---|
| Risk accuracy | Ground truth comparison (DS3) | Weighted F1, FNR on high-risk | Rule-based scorer |
| Autonomy appropriateness | Rule-derived labels + human study | Agreement rate, Cohen's κ | Always-escalate, random |
| Output quality | LLM-as-judge + spot check | Mean quality score (1-5) | N/A |
| Cross-profile adaptability | Same tickets, 3 profiles | Profile divergence rate | Single-profile baseline |
| Safety | False negative on critical | FNR on risk ≥ 3 | Rule-based oracle |

### Threat to Validity (Acknowledge in Thesis)

- **Internal validity:** Autonomy labels are derived, not independently collected — annotator study mitigates this
- **External validity:** Kaggle datasets are synthetic/preprocessed — real-world performance may differ
- **LLM variability:** LLM outputs are non-deterministic — run evaluations with temperature=0 and report mean ± std over 3 runs
- **Confound:** Company profile is hand-authored — in production, it would be learned from company data

---

## Part 7: Identified Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| LLM hallucination in risk assessment | Medium | High | Rule-based fallback; structured JSON output mode; validation layer |
| Groq rate limits during batch eval | High | Medium | Implement exponential backoff; cache responses; use smaller model for bulk runs |
| Dataset labels are proxy, not ground truth | High | Medium | Explicitly declare in thesis; use multiple evaluation dimensions |
| LangGraph complexity delays implementation | Medium | High | Build linear pipeline first; add graph structure incrementally |
| Supabase free tier row limits | Low | Low | DS3 is 50K rows; Supabase free tier supports 500MB |
| LLM cost exceeds budget | Low | Medium | Use Groq free tier; cap evaluation samples; use rule-based for bulk |

---

## Part 8: Implementation Sequence

The following order minimizes risk and ensures a working prototype at each stage:

1. **Database + FastAPI skeleton** — Tables, basic CRUD endpoints, Pydantic models
2. **Data ingestion pipeline** — CSV upload → normalized tickets table
3. **Rule-based agent (no LLM)** — Risk scoring, autonomy decision, basic output — establishes baseline
4. **LangGraph workflow** — Replace rule-based with stateful graph, add LLM calls
5. **Company profile system** — Profile CRUD, injection into agent state, override logic
6. **Agent output generation** — LLM-generated drafts, summaries, escalation briefs
7. **Frontend dashboard** — Task queue, decision view, profile config
8. **Evaluation engine** — Batch runner, metrics, comparison views
9. **Thesis experiments** — Run all four evaluation dimensions, collect results

Each stage produces a committable, runnable artifact. Do not proceed to the next stage until the current one has a working test.

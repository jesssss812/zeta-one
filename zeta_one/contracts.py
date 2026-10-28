"""Types every module shares. The seams between modules are these types and the protocols below.

The evidence-record models follow docs/reference/demo-api.md, which is the contract with the site:
required keys are checked, extra keys are allowed. A change here is a change to that contract.
"""

import re
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from zeta_one.rho.models import Money

POLICY_VERSION = "2026-10-28.3"
SCHEMA_VERSION = 1
# The largest payment a proposal may name, in minor units: $10 billion, far inside SQLite's integer range.
MAX_PAYMENT_MINOR_UNITS = 10**12
CURRENCY_CODE = re.compile(r"^[A-Z]{3}$")
# Size caps on what an agent sends: its free text reaches the paid strong tier (security.md, S1).
MAX_ID_LENGTH = 128
MAX_MEMO_LENGTH = 1000
MAX_RATIONALE_LENGTH = 4000
MAX_SOURCE_DOCUMENTS = 20

RecordId = Annotated[str, Field(min_length=1, max_length=MAX_ID_LENGTH)]

Level = Literal["low", "elevated", "high"]
Decision = Literal["allow", "challenge", "block"]
TierName = Literal["tier0", "cheap", "strong"]
IdentityStatus = Literal[
    "verified", "unsigned", "unknown_agent", "revoked", "stale_timestamp", "replay", "invalid_signature"
]
ExecutionStatus = Literal["executed", "held", "blocked"]

LEVEL_ORDER: dict[str, int] = {"low": 0, "elevated": 1, "high": 2}


def max_level(a: Level, b: Level) -> Level:
    return a if LEVEL_ORDER[a] >= LEVEL_ORDER[b] else b


class ChallengeType(StrEnum):
    CONFIRM = "confirm"


class _Open(BaseModel):
    """Evidence and context models accept keys they don't name, so a newer record still loads."""

    model_config = ConfigDict(extra="allow")


# --- What an agent sends ---------------------------------------------------------------------------


class Proposal(BaseModel):
    """The body of POST /v1/actions/propose_payment (decision 0005)."""

    model_config = ConfigDict(extra="forbid")

    bill_id: RecordId | None = None
    counterparty_id: RecordId
    payment_method_id: RecordId
    source_account_id: RecordId
    amount: Money
    memo: str = Field(default="", max_length=MAX_MEMO_LENGTH)
    agent_rationale: str = Field(default="", max_length=MAX_RATIONALE_LENGTH)
    source_document_ids: list[RecordId] = Field(default_factory=list, max_length=MAX_SOURCE_DOCUMENTS)

    @field_validator("amount")
    @classmethod
    def positive_payment(cls, value: Money) -> Money:
        if value.amount <= 0:
            raise ValueError("payment amount must be positive")
        if value.amount > MAX_PAYMENT_MINOR_UNITS:
            raise ValueError("payment amount is too large")
        if not CURRENCY_CODE.match(value.currency):
            raise ValueError("currency must be an uppercase ISO 4217 code")
        return value


class SignedRequest(BaseModel):
    """A request as received, before parsing: identity is verified over these raw bytes."""

    method: str
    path: str
    headers: dict[str, str]
    body: bytes


# --- What the engine looked at (the scenario result's `context`) ----------------------------------


class PaymentMethodView(_Open):
    id: str
    type: str
    bank_name: str | None = None
    is_default: bool = False
    added_at: datetime | None = None


class CounterpartyView(_Open):
    id: str
    name: str
    status: str
    created_at: datetime
    payment_methods: list[PaymentMethodView] = Field(default_factory=list)


class PaymentMethodChange(_Open):
    id: str
    method_id: str
    change: str
    changed_at: datetime
    changed_by: str | None = None
    summary: str | None = None


class BillView(_Open):
    id: str
    counterparty_id: str
    counterparty_name: str
    invoice_number: str | None = None
    invoice_date: str | None = None
    due_date: str | None = None
    amount: Money
    memo: str | None = None
    document_excerpt: str | None = None
    status: str | None = None


class PaymentRecord(_Open):
    id: str
    posted_at: datetime
    amount: Money
    method_type: str | None = None


class PaymentHistory(_Open):
    """`recent` is a short summary (up to three payments in 90 days); `duplicate_candidates` is every
    payment in the duplicate window, so a matching payment can't hide behind three newer ones."""

    count: int = 0
    first_at: datetime | None = None
    last_at: datetime | None = None
    median_amount: Money | None = None
    recent: list[PaymentRecord] = Field(default_factory=list)
    duplicate_candidates: list[PaymentRecord] = Field(default_factory=list)


class BusinessView(_Open):
    id: str
    name: str


class Context(_Open):
    """Everything risk is assessed from. `counterparty` is always the proposed payee.

    `open_bills` holds the proposed counterparty's unpaid bills as the gateway found them itself,
    whatever the agent cited (security.md, S7). `gateway_payments` holds the simulated payments the
    gateway executed or holds for this payee in the last 30 days, which Rho's records don't show;
    each carries the `bill_id` it paid, if any.
    """

    business: BusinessView
    counterparty: CounterpartyView
    payment_method_history: list[PaymentMethodChange] = Field(default_factory=list)
    bill: BillView | None = None
    payment_history: PaymentHistory = Field(default_factory=PaymentHistory)
    bill_counterparty: CounterpartyView | None = None
    bill_counterparty_payment_history: PaymentHistory | None = None
    open_bills: list[BillView] = Field(default_factory=list)
    gateway_payments: list[PaymentRecord] = Field(default_factory=list)


# --- The evidence record ---------------------------------------------------------------------------


class IdentityEvidence(_Open):
    result: IdentityStatus
    claimed_agent_id: str | None = None
    business_id: str | None = None
    owner: str | None = None
    key_id: str | None = None
    timestamp: str | None = None
    nonce: str | None = None
    checked: list[str] = Field(default_factory=list)


class Violation(_Open):
    field: str
    kind: Literal["scope", "limit"]
    limit: Any = None
    observed: Any = None


class AuthorizationEvidence(_Open):
    authorization_id: str | None = None
    version: int | None = None
    violations: list[Violation] = Field(default_factory=list)
    snapshot: dict[str, Any] | None = None

    @classmethod
    def not_evaluated(cls) -> "AuthorizationEvidence":
        return cls()


class Feature(_Open):
    value: Any = None
    evidence: list[str] = Field(default_factory=list)


class Signal(_Open):
    name: str
    severity: Level
    evidence: list[str] = Field(default_factory=list)
    source: TierName


class Usage(_Open):
    """Token usage as the API reports it; `input_tokens` excludes the cache reads and writes."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


class TierResult(_Open):
    tier: TierName
    model: str | None = None
    level: Level | None = None
    confidence: float | None = None
    signals: list[str] = Field(default_factory=list)
    latency_ms: int | None = None
    usage: Usage | None = None
    error: str | None = None


class Floor(_Open):
    level: Level
    flags: list[str]


class Lowered(_Open):
    from_: Level = Field(alias="from")
    to: Level
    by: TierName
    signals: list[str]

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class RiskEvidence(_Open):
    level: Level | None = None
    level_set_by: TierName | None = None
    floor: Floor | None = None
    tiers_run: list[TierName] = Field(default_factory=list)
    features: dict[str, Feature] = Field(default_factory=dict)
    tier_results: list[TierResult] = Field(default_factory=list)
    signals: list[Signal] = Field(default_factory=list)
    lowered: Lowered | None = None
    reused_from: str | None = None
    # True when the models were skipped because this agent had already had MAX_FRESH_ASSESSMENTS
    # different proposals to the same payee and method assessed within the reuse window (S3).
    repeat_limit_reached: bool = False
    model_rationale: str | None = None

    @classmethod
    def not_evaluated(cls) -> "RiskEvidence":
        return cls()

    def has_signal(self, name: str) -> bool:
        return any(signal.name == name for signal in self.signals)

    def model_failed(self) -> bool:
        return any(result.error for result in self.tier_results if result.tier != "tier0")

    def tier0_failed(self) -> bool:
        return any(result.error for result in self.tier_results if result.tier == "tier0")


class Challenge(_Open):
    type: ChallengeType
    routed_to: str
    user_sees: str


class Execution(_Open):
    status: ExecutionStatus
    simulated: Literal[True] = True


class Cost(_Open):
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    usd: float = 0.0
    prices_used: dict[str, Any] = Field(default_factory=dict)
    # Models whose tokens are counted but had no price, so `usd` leaves them out.
    unpriced_models: list[str] = Field(default_factory=list)


class Configuration(_Open):
    """Which tiers run and how escalation decides (decision 0007)."""

    tiers: list[TierName] = Field(default_factory=lambda: ["tier0", "strong"])
    escalation: Literal["engineered", "jev", "always", "none"] = "engineered"
    # The Jev rule's thresholds, policy parameters recorded with every decision (decision 0007).
    jev_min_confidence: float = 0.8
    jev_min_finding_confidence: float = 0.9


class EvidenceRecord(_Open):
    schema_version: int = SCHEMA_VERSION
    decision_id: str
    created_at: datetime
    policy_version: str
    engine_version: str | None = None
    seed_version: str | None = None
    configuration: Configuration
    decision: Decision
    reasons: list[str]
    challenge: Challenge | None = None
    friction_rung: int
    identity: IdentityEvidence
    authorization: AuthorizationEvidence
    risk: RiskEvidence
    execution: Execution
    cost: Cost | None = None
    latency_ms: dict[str, int] | None = None
    review: dict[str, Any] | None = None
    # What was decided on, as it was then: the proposed payment (when the body parsed) and the context
    # the risk stage read (when it loaded). A reviewer reads these, not today's records.
    proposal: Proposal | None = None
    context: Context | None = None


class ScenarioInfo(_Open):
    name: str
    title: str
    summary: str
    expected: Decision


class ScenarioResult(_Open):
    """What POST /v1/scenarios/{name}/run returns, and what each fixture holds."""

    illustrative: bool = False
    scenario: ScenarioInfo
    context: Context
    proposal: Proposal
    decision_record: EvidenceRecord


# --- The authorization a business grants (decision 0006) ---------------------------------------------


class CounterpartyScope(_Open):
    mode: Literal["any", "allowlist", "denylist"] = "any"
    ids: list[str] = Field(default_factory=list)


class RollingLimit(_Open):
    # At least a day: a zero or negative window would count no earlier spend and switch the limit off.
    window_days: int = Field(ge=1)
    amount: Money


class Limits(_Open):
    per_payment: Money | None = None
    rolling: RollingLimit | None = None


class Authorization(_Open):
    authorization_id: str
    version: int
    policy_version: str
    business_id: str
    agent_id: str
    granted_by: str
    granted_at: datetime
    expires_at: datetime | None = None
    status: Literal["active", "revoked"] = "active"
    revoked_at: datetime | None = None
    actions: list[str] = Field(default_factory=lambda: ["propose_payment"])
    counterparties: CounterpartyScope = Field(default_factory=CounterpartyScope)
    allow_new_counterparties: bool = False
    limits: Limits = Field(default_factory=Limits)
    human_approval_above: Money | None = None


# --- Seams: the functions each module provides ------------------------------------------------------


class TierOutput(BaseModel):
    """What one risk tier returns. `result` goes into the evidence record as it is."""

    result: TierResult
    signals: list[Signal] = Field(default_factory=list)
    rationale: str | None = None


class Tier0Output(TierOutput):
    features: dict[str, Feature] = Field(default_factory=dict)


class RiskInput(BaseModel):
    """What a model tier may see: the proposal, its context and tier 0's findings.

    Never a case's category, setup, labels or name.
    """

    proposal: Proposal
    context: Context
    features: dict[str, Feature]
    tier0: TierResult


class IdentityVerifier(Protocol):
    def __call__(self, request: SignedRequest, now: datetime) -> IdentityEvidence: ...


class AuthorizationSource(Protocol):
    def __call__(self, business_id: str, agent_id: str) -> Authorization | None: ...


class AuthorizationChecker(Protocol):
    def __call__(
        self, proposal: Proposal, authorization: Authorization | None, identity: IdentityEvidence, now: datetime
    ) -> AuthorizationEvidence: ...


class ContextSource(Protocol):
    """Builds the context for a proposal from the data store. Raises InvalidProposal when the
    proposal refers to things that don't exist or don't belong together (unknown counterparty,
    payment method not on the counterparty, source account outside the business)."""

    def __call__(self, proposal: Proposal, business_id: str, now: datetime) -> Context: ...


class Tier0(Protocol):
    def __call__(self, proposal: Proposal, context: Context, now: datetime) -> Tier0Output: ...


class RiskTier(Protocol):
    """A model tier. Must not raise: a failure is returned as `result.error` (decision 0010)."""

    name: TierName

    def assess(self, risk_input: RiskInput) -> TierOutput: ...


class SpendSource(Protocol):
    """Executed and held payments by an agent since a time, in one currency: the rolling limit's input."""

    def __call__(self, agent_id: str, since: datetime, currency: str) -> int: ...


# --- Verified outcomes: what a person established after a decision (decision 0012) -----------------

Finding = Literal["legitimate", "payee_fraud", "manipulated_agent", "unauthorized"]
Verification = Literal[
    "callback_known_number", "vendor_portal", "bank_confirmation", "signed_customer_attestation",
    "customer_report", "none",
]
# Methods that establish a fact. A customer's report or no check at all records a claim, never a label.
VERIFYING_METHODS: frozenset[str] = frozenset(
    {"callback_known_number", "vendor_portal", "bank_confirmation", "signed_customer_attestation"}
)


class VerifiedOutcome(_Open):
    """What a person found about a decided payment, and how they know. Only a person records one."""

    finding: Finding
    verification: Verification
    by: str = Field(min_length=1, max_length=200)
    at: datetime
    note: str | None = Field(default=None, max_length=1000)
    source: Literal["resolve", "report"]

    @computed_field
    @property
    def verified(self) -> bool:
        return self.verification in VERIFYING_METHODS


# --- Evaluation cases (seam 6 in the implementation plan) -------------------------------------------


class SetupOp(BaseModel):
    """One change applied to a fresh copy of the seed before a case runs, e.g.
    {"op": "change_payment_method", "args": {"counterparty_id": "cp_0007", "days_ago": 3}}.
    The data workstream defines the ops; the evaluation only names them."""

    op: str
    args: dict[str, Any] = Field(default_factory=dict)


class LabelProvenance(BaseModel):
    sources: list[str] = Field(default_factory=list)
    agreed: bool | None = None
    adjudicated_by: str | None = None


class Case(BaseModel):
    """One evaluation case. Only `proposal` and the data its setup produces ever reach the engine."""

    id: str
    set: Literal["deterministic", "dev", "test", "hard", "feedback"]
    category: Literal["A", "B", "C", "D", "E", "F"]
    setup: list[SetupOp] = Field(default_factory=list)
    agent: str = "builtin:ap_assistant"
    proposal: Proposal
    truth: Literal["legitimate", "unauthorized", "payee_fraud", "manipulated_agent"]
    detectable: bool = True
    expected: Decision
    also_acceptable: list[Decision] = Field(default_factory=list)
    # For a deterministic case: a reason the decision must carry, so it can't pass for the wrong one.
    expected_reason: str | None = None
    label_provenance: LabelProvenance = Field(default_factory=LabelProvenance)
    provenance: str


class InvalidProposal(ValueError):
    """The request is malformed; it is rejected before risk runs and gets no decision."""

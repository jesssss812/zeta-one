# From the working demo to a fintech integration

Zeta One's decision engine runs in the local app. Each payment step submits a signed proposal
through the gateway's request handling and computes a new decision. With `ZETA_DEMO_LIVE=1`,
eligible risk assessments call Claude during that run; the page does not replay a stored model
answer. Deterministic checks can decide cases without a model. The records are synthetic and
payment execution is simulated: fresh computation does not mean live bank data.

The public Vercel site serves static explanatory pages and packaged artifacts. It does not run
the gateway, call models or connect to the laptop. The proposed platform integration below is
engineering work still to be done, not an available Rho integration.

## One engine, two operating environments

![Today’s signed demo proposals and a future fintech’s requests feed the same identity, authorization, risk, policy and evidence engine. The demo simulates payment handling; the future platform must enforce decisions before execution.](../../site/integration-flow.svg)

The shared component is the decision pipeline and its evidence contracts, not the demo controller
or the synthetic record store. Real integrations must validate the policy and risk configuration
against their own data and requirements; sharing the engine does not establish production readiness.

## What the demo actually runs

1. The browser calls `POST /v1/demo/next` on the local server.
2. For a payment step, the story controller creates and signs the proposal as its registered demo
   agent. It submits it to the gateway through an in-process HTTP test client; it is scripted
   orchestration, not a separate autonomous agent reasoning about which payment to make.
3. The gateway verifies identity, checks authorization, gathers synthetic business context, runs
   risk assessment and applies policy. Live mode uses engineered escalation, so routine cases and
   high floors can avoid model calls; an eligible case calls the configured strong tier then.
4. The sandbox records the evidence and simulated payment state. The page displays that result;
   the review view reads the same records. Human findings can create scoped adjustments used by
   subsequent assessments.

The sandbox has an in-memory database and a temporary agent key. Reset starts a new sandbox.
The regular gateway instead persists its state locally. See the
[demo API](demo-api.md#the-one-screen-demo) for routes and
[the README](../../README.md#quick-start) for launch commands.

For a recorded walkthrough, distinguish a successful live model call from a model failure or a
deterministic decision using the evidence record's tier results. Enabling live mode is not proof
that every step called a model. Inference can fail and leave a case held for review. No paid calls
are needed to open the public site.

## Engineering required for platform adoption

| Work | What the fintech and integration must establish |
| --- | --- |
| **Put checks before execution** | Add a mandatory check in the payment API or orchestrator. Enforce allow, hold and block server-side; agents must have no unrestricted alternative execution route. The fintech may retain execution credentials and execute only after a valid decision. |
| **Bind identity and delegated authority** | Map authenticated agents to customers and accountable owners. Connect registration, scoped grants, expiry and revocation to platform identity systems. Define request integrity, replay handling, key rotation and which authorization version applies. |
| **Connect current business context** | Replace the synthetic context source with authorized access to bills, vendor records, payment methods, change history and settled/held payments. Preserve source IDs, observation times and tenant boundaries. Define freshness and missing-data behavior; a recorded bank change is not proof it is legitimate. |
| **Make execution reliable** | Bind a decision to the exact customer, source account, recipient, destination, amount, currency and obligation. Recheck changed state before execution, reserve spend atomically, prevent duplicate execution, and reconcile retries and ambiguous provider timeouts. A risk-cache hit is not payment idempotency. |
| **Integrate human review and outcomes** | Route holds to authenticated staff with appropriate roles. Preserve the reviewed proposal and evidence; recheck when approval is acted on. Record what a person verified and how, separate complaints from findings, and support correction/revocation of adjustments. Selecting a verification method does not itself perform a bank check. |
| **Operate and validate the service** | Add durable tenant-isolated storage, protected secrets, monitoring, audit access, budgets/rate limits and explicit timeout/outage behavior. Load-test concurrency and review queues. Validate in shadow mode on representative customer data before a controlled enforcement rollout; measure missed fraud and legitimate review burden together. |

A check can run as a service called by the fintech's payment backend, or inside a customer-side
gateway that exclusively holds execution credentials. Either way, the enforcing system must bind
the response to the payment being executed and preserve deterministic authorization blocks. A
model cannot supply an override. Hosting a frontend alone does not create this enforcement boundary.

## The Rho boundary

The API available to this project provides no payment-write endpoint or pre-execution review hook;
approval actions and webhooks are also unavailable as documented in the
[Rho API reference](rho-api.md). The demo therefore does not send payments or approve them in Rho.
A platform integration would require Rho to expose or internally implement the enforcement and
context interfaces above. This is a proposed adoption path, not a claim of an existing partnership
or an API capability.

The underlying choices are recorded in
[the gateway decision](../decisions/0003-customer-side-gateway.md) and
[the deployment decision](../decisions/0011-deployment-and-hosting.md).

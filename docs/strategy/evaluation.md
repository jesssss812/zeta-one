# Evaluation: how Zeta One is measured

Written 2026-10-27, before any code. A change to how something is measured updates this doc in the
same change.

## Principle

Show more than a polished happy path. A credible evaluation runs a labelled set of proposed agent
actions through the system and reports where it is right, where it is wrong and what it costs. Use
synthetic examples openly, and never claim production fraud-detection accuracy without real labelled
data.

Zeta One's output is a decision (allow, challenge or block), so the main measurement is a classifier
evaluation: code compares each decision with a label, and no language model grades it. Language
models enter the evaluation where they write case text and help label, and both are checked. The
effort goes to risk; identity and authorization are deterministic and tested as such.

This doc separates what the submission needs from what comes after it. More evaluation is always
better; the line is drawn by what fits before the deadline and still holds up to a careful reader.

## Case categories

Every scenario set covers:

- known authorization violations
- legitimate, authorized payments
- authorized but suspicious payments
- unknown or unverifiable agents
- ambiguous cases that need human verification
- manipulated or adversarial inputs, such as prompt injection in invoices

Each case carries its expected decision (allow, challenge or block) and where its data came from
(Rho staging snapshot, or synthetic and how it was generated). The categories are listed in
[implementation-plan.md](implementation-plan.md#seed-data-and-scenarios).

## What to check

- Hard permissions are enforced correctly, every time.
- Legitimate actions are not challenged unnecessarily. Unnecessary challenges are a cost, as missed
  fraud is: this is the critical-damping trade-off.
- Meaningful risk signals are detected.
- Explanations are actionable.
- Evidence keeps its provenance.
- Latency and cost stay acceptable.

## For the submission

### Two labels per case

| Label | Means | Comes from |
| --- | --- | --- |
| `truth` | what is actually happening: `legitimate`, `unauthorized` (identity or authorization), `payee_fraud` (redirected or impersonated payee), `manipulated_agent` (the agent followed injected instructions) | the generator, by construction |
| `expected_decision` | what a good system should decide **from what it can observe**, with `also_acceptable` decisions | by construction for identity and authorization cases; for risk cases, an AI labeller checked by the owner |

They differ on purpose. A fraud that leaves no observable trace has `truth: payee_fraud` and
`expected_decision: allow`, and is marked `detectable: false`. Such cases are kept few, each one is
listed by name in the report, and they are counted apart from accuracy: what counts as observable
depends on which features exist today, so the list must not quietly excuse misses.
With today's features every generated fraud leaves a trace tier 0 flags, so the generator marks
none undetectable; such cases come from the `hard` set.

### Sets

| Set | Size | Rule |
| --- | --- | --- |
| Deterministic | 23 | One case per identity and authorization check, plus one per guardrail in [security.md](security.md) (self-approval refused, model failure challenged, a repeated proposal not re-rolled, a missing bill reference caught, split payments limited, approval after revocation blocked); labels by construction; every case must pass; no statistics |
| Risk `dev` | 51 | 48 generated legitimate, suspicious, adversarial and ambiguous cases, plus the three risk demo scenarios. Thresholds, prompts and rules are tuned here only |
| Risk `test` | 100 | 35 routine, 35 suspicious and 30 adversarial cases (51 legitimate and 49 fraud by their built-in truth); a different random seed and different wording from `dev`; frozen and hashed before the first scored run; never used for tuning. 15 of its combinations also appear in `dev`, because the routine class has too few to keep apart |
| Risk `hard` | 14, of 20 specs | Written outside the generator's templates, as prose drafted with Claude and approved by the owner with its labels: unfamiliar impersonation styles, instructions arriving through the real vendor's compromised channel, subtle injection, and legitimate urgent payments that look like fraud. Two are frauds marked undetectable, so 12 are scored |
| `feedback` | grows with use | Real decisions whose verified outcome (decision 0012) is a finding, labelled by it, exported by `eval/feedback.py`; claims are left out. Replayed on the seed, so the context is today's, not the decision's |

With about 30 cases in a class, a rate near 85% has a 95% interval of roughly ±12 points: enough to
tell configurations apart in aggregate, not to rank them within a category.

### Generating cases

Cases are generated from **dimensions**, each with a few values: vendor tenure, payment-method
change age, amount relative to the vendor's median, whether the proposal matches its bill, invoice
text (clean, urgency, redirect instruction, a legitimate notice of changed bank details), the
agent's stated rationale (plain, citing "updated instructions"), where the request came from (a
lookalike sender or the real vendor's compromised channel), and whether a change was verified with
the vendor.

1. Code builds the cross product of dimension values and drops impossible combinations: a
   payment-method change older than the vendor, or invoice text on a case with no bill, which the
   engine would never see. `truth` follows where the money goes: `payee_fraud` only when it would
   reach someone other than the real vendor (a bill for another payee, or bank details changed
   through a channel other than the vendor and never confirmed). A lookalike sender that leaves
   the vendor's bank details alone is a suspicious but `legitimate` case. Each case gets its own
   opaque record ids.
2. A Claude Code subagent on the owner's subscription turns each combination into invoice text and
   an agent rationale, from the committed prompt `eval/prompts/wording.md`, in batches of ~20.
3. Code applies each case's setup to a fresh copy of the seed.

The dimensions are close to tier 0's features, so the rules catch every generated fraud by
construction (they did, on `dev` and `test`), and generated cases flatter them. Against that:

- **Harmless look-alikes**: legitimate cases with a recent, confirmed change of bank details, or an
  urgent but honest invoice, so a flag alone is not the answer.
- **Frozen lexicon**: tier 0's instruction-pattern list is fixed before `test` is generated, and the
  call that writes `test` text never sees it.
- **Varied wording**: the wording call is asked for realistic and varied phrasing, including subtle
  versions, and is never given the label.
- **The `hard` set** is the check on the generator, because nothing in it came from it. It is
  small: 12 scored cases.

Wording, labelling and the strong tier all use Claude, with three different models: Claude Haiku
5.5 writes the wording, Claude Sonnet 5.5 labels, and Claude Opus 5.5 is the strong tier. The
report says that all three are from one family.

### Labelling

1. **The guide comes after reading.** The owner reads and notes ~20 generated `dev` cases, then
   writes a one-page labelling guide.
2. **One AI labeller, blind.** Claude Sonnet 5.5, sent each batch through the Anthropic API from
   the committed prompt `eval/prompts/label.md` (`python -m eval.label ai <set>`). It receives, inside
   its prompt, only what the system sees plus the guide; never `truth`, the category or the
   dimension values. No tools are offered, so it cannot open a file: the blindness holds by
   construction, and each batch's meta records the route. Its labels are committed; a rerun may
   label differently, which is why the committed file is the record.
3. **The owner labels** 40 suspicious, adversarial and ambiguous cases from `test`, stratified,
   without seeing the AI label, and approves the labels proposed with the `hard` set's specs (an
   approval, not a blind label).
4. **Agreement is reported on those 40**: raw agreement, and Cohen's κ with a bootstrap 95%
   interval (about ±0.15–0.2 at this size). Identity and authorization cases are left out, since
   agreeing on them is trivial and would inflate κ.
5. **Disagreements go to the owner**, whose label is final. The owner settles them after reading
   the AI's label and reason, in a separate file (`adjudicated.jsonl`), so κ stays the agreement of
   the blind labels. Each case records `label_provenance: {sources, agreed, adjudicated_by}`.

Labels are fixed before the system is scored on them.

### Comparisons

Run the same cases through seven configurations:

1. trivial baselines: `always_allow`, `always_challenge`
2. deterministic rules only: `rules`
3. rules, then the strong model only on engineered escalation: `engineered` (decisions 0009, 0017)
4. rules, then Jev, then the strong model on Jev's rule: `jev` (decisions 0007, 0016)
5. rules, then an open-weight model in the strong model's place on engineered escalation:
   `open_weight` (decisions 0014, 0018, 0019)
6. the strong model on every request: `strong`

Each runs once per set. The report names the models and prices that actually ran. The language-model tiers see only the
proposal and its context, never a case's category, setup, name or labels.

### Metrics

Reported **per category**, never as one headline number: the identity and authorization categories
must score 100%, so an overall accuracy would be inflated by them. Per configuration and category:

- n, accuracy against the expected decision, and separately accuracy counting also-acceptable
  decisions, each with a Wilson 95% interval
- detection: the share of detectable suspicious and adversarial cases not allowed
- challenge rate on legitimate cases, which is the review workload: detection is always reported
  next to the workload it took
- a confusion matrix
- lowerings: how often a model lowered soft-signal risk, split by legitimate cases (friction it
  saved) and fraudulent ones (risk it added)
- cost per evaluated action from reported token usage, and p50/p95 latency (a single run on one
  machine including network time, labelled so; no responses are cached, though the fixed system
  prompt is prompt-cached)

`dev`, `test` and `hard` results are shown side by side: a drop from `dev` to `test` or `hard` is
overfitting to the generator or the tuning, and is reported as found.

Configurations are compared with a table of discordant cases (where one configuration is right and
the other wrong). A McNemar p-value is given only pooled across the risk categories; per category
there are too few discordant cases for any p-value to mean anything.

Every report records the seed, the set hashes, the model ids, the prices used and the date.

### Invariants

AGENTS.md rule 7 is a property of the code, so it is tested as one. Property-based tests generate
thousands of cases and run them against a hostile model stub that always answers `low` and `allow`,
and assert that the merged risk level never falls below the tier-0 floor and that no identity or
authorization block is ever lifted. They run with the unit tests, pass 100% of the time and need no
labels.

### Error analysis

The evidence records are the traces. Every wrong decision on `dev` is read and tagged with the
**first stage that went wrong**: a feature missing or wrong, escalation not triggered, the model
wrong, the merge, or a policy row. The report includes the table of failures by stage and a short
list of failure kinds grouped from the notes.

### Limitations the report states

- The data is synthetic; no rate here is a production rate, and the sets say nothing about how
  often each case occurs.
- The generator's dimensions resemble tier 0's features; `hard` is the check on that.
- Generated cases vary in their dimension values and wording, but share one structure: every
  payment history is monthly at a steady amount, banks are a few synthetic labels, and no past
  payment or bank account carries an identifier that ties them together. The owner, labelling the
  `test` sample, found the cases too alike to say much beyond that structure. `dev` and `test`
  therefore measure overfitting to the tuning within one structure, not behaviour on unlike
  cases; `hard`, written outside the generator, is the check on that.
- Which model families wrote, labelled and decided the cases.
- The cases marked `detectable: false`, by name.
- Each configuration ran once per set.
- How many `test` labels are the AI labeller's alone, the agreement on the owner's blind labels, and
  how many disagreements the owner settled by taking the AI's label.
- That the open-weight model's prompt has a section written from its `dev` failures, which the
  strong tier's prompt lacks.
- That the open-weight cost is GPU rent per call's time, an upper bound.
- Any set scored under more than one policy version.

## If time allows, in order

1. **Repeat runs.** Each configuration that calls a model runs 3 times on the risk cases. Report
   the share of cases whose decision changed between runs, and pass^3 on detectable fraud: the share
   caught in all three runs. A 90% single-run rate is about 73% over three, and for money the
   consistent number is the one that matters.
2. **An attacking model.** The repository is public, so the attacker is assumed to know the policy
   and the features. Given both, a model writes invoice text and agent rationales aimed at getting a
   redirected payment **allowed**, about 20 attempts per configuration. It aims first at the path
   where a model may lower soft-signal risk (decision 0010), because that is where model judgement
   can turn into an allow. It is graded on the outcome:
   did the simulated payment execute to the attacker's account. Following NIST's lessons on agent
   hijacking evaluations ([NIST, 2025](https://www.nist.gov/news-events/news/2025/01/technical-blog-strengthening-ai-agent-hijacking-evaluations)):
   the attacker adapts to this system rather than replaying known attacks; results are reported per
   attack kind, not only in aggregate; and each attack is retried several times, because retrying
   raises success against a model. Here retries should gain nothing, since a repeated proposal
   reuses its risk result (decision 0010), and the report shows whether that holds. Reported as
   counts with intervals, never as a robustness claim. This is a capability measure: a rate above
   zero is expected and reported as it is.
3. **Expected cost.** A cost matrix weights each (expected, actual) pair: a missed detectable fraud
   costs most, blocking a legitimate payment less, and challenging one costs its friction weight.
   The weights are chosen, not derived, and recorded; the result is also shown with the missed-fraud
   weight halved and doubled. Reported as expected cost per 1,000 actions next to model spend. A
   dollar figure for missed fraud uses the synthetic amounts and states them; it is exposure on
   synthetic cases, never money saved.
4. **Friction score**, once more than one challenge type exists (decision 0008): each rung carries a
   weight (allow 0, notify 0.1, confirm 1, renew authorization 2, verify payee 3; chosen, not
   derived); the score is the mean weight over legitimate cases, reported with the share of
   legitimate actions that saw no prompt. With only `confirm`, it equals the challenge rate and adds
   nothing.

Jev's probabilities are reported raw and labelled as uncalibrated on our data: no reliability table
has been built from the cases that reached it.

The judges score "performance: did they optimize for speed or scale?"
([../reference/hackathon.md](../reference/hackathon.md)), so cost and latency are reported next to
accuracy.

## After the hackathon

- A second AI labeller from another model family, and agreement between the labellers.
- Structural variety in the generator: irregular schedules and amounts, payments tied to the
  bank account they went to, account endings and beneficiaries, more kinds of payee and history,
  and wording from another model family, labelled as such. More cases of one structure add no
  variety.
- Larger sets (about 100 `dev`, 200 `test`), so per-category comparisons have power.
- Jev's calibration against `truth`, as a reliability table, once enough cases reach it.
- A curve of expected cost against detection, by sweeping a threshold; engineered escalation is a
  rule, not a threshold, so this needs Jev or a scored tier.
- An LLM judge for whether explanations are actionable, checked against ~40 owner labels with its
  true-positive and true-negative rates stated before any of its numbers are reported.
- Automation detection as a risk signal only (rule 9), for example botscent's server-side header
  check (Web Bot Auth signature, user agent, the host's verified-bot field), tested against its
  published test vectors. Its browser-side checks don't apply to agents calling an API.
- A labelled set from real data, which is the only way to a production accuracy.
- **Feedback into evaluation.** Verified human outcomes (a reviewer confirms or clears a payment, a
  payee is confirmed as attacker-controlled) become evaluation cases with their provenance, and any
  proposed change to rules or models is re-evaluated against the baselines before a person approves
  it. A complaint alone is not a fraud label ([product.md](product.md)). Hard constraints apply
  whatever a model learns.

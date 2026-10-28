# How Zeta One is evaluated

Every configuration of the engine is scored on the same labelled cases, so the trade between fraud
caught, honest payments held up and model spend can be compared rather than argued. This page shows
how the cases are made, labelled, frozen, run and reported. It also shows who does each step: a
person, a model with a person checking, a model alone, or code. The full method is in
[../strategy/evaluation.md](../strategy/evaluation.md); the latest results are in
[../../data/eval/report.md](../../data/eval/report.md).

All cases are synthetic. No rate in the report is a production rate, and payments are simulated.
The same overview as a page, in the same colours, is [site/evaluation.html](../../site/evaluation.html).

## The flow

```mermaid
flowchart LR
  subgraph make["1 · Make cases"]
    direction TB
    sample["Sample combinations<br/>seeded, reproducible"]:::code
    word["Write invoice text + agent rationale<br/>Claude Haiku 5.5, sees no labels"]:::model
    assemble["Assemble cases<br/>dev 48 · test 100"]:::code
    hard["Hard set, written by hand<br/>15–20 cases outside the generator"]:::human
    convert["Hard set as case files<br/>drafted with Claude, checked by a person"]:::assisted
    fixed["Identity + authorization cases<br/>23, labelled by construction"]:::code
    feedback["Feedback cases<br/>labelled by verified findings"]:::code
    sample --> word --> assemble
    hard --> convert
  end

  subgraph label["2 · Label"]
    direction TB
    guide["Labelling guide<br/>drafted with Claude, decided by a person"]:::assisted
    ai["AI labels on every case, blind<br/>Claude Sonnet 5.5"]:::model
    person["Human labels on 40 test cases<br/>without seeing the AI's labels"]:::human
    agree["Agreement<br/>Cohen's κ with a 95% interval"]:::code
    settle["Disagreements settled<br/>the human label is final"]:::human
    guide --> ai --> agree
    person --> agree --> settle
  end

  freeze["3 · Freeze<br/>every set hashed; the rule lexicon<br/>fixed before test was written"]:::code

  subgraph run["4 · Run"]
    direction TB
    runner["Each case in a fresh sandbox<br/>7 configurations, spend cap"]:::code
    tiers["Risk tiers under test<br/>Claude Opus 5.5 · Jev 1.14 · Qwen3 235B"]:::model
    runner -- "uncertain cases only,<br/>except strong" --> tiers
  end

  report["5 · Report<br/>rates with intervals, confusion matrices,<br/>cost per 1,000 decisions"]:::code

  assemble --> ai
  assemble -- "40 sampled" --> person
  convert --> freeze
  settle --> freeze
  freeze --> runner
  fixed --> runner
  feedback --> runner
  runner --> report

  classDef human fill:#f6dca0,stroke:#7a4d00,color:#17221f
  classDef assisted fill:#dcedb0,stroke:#3c5a12,color:#17221f
  classDef model fill:#d3e0f4,stroke:#24456b,color:#17221f
  classDef code fill:#eceee8,stroke:#58665f,color:#17221f
```

| Colour | Who | Used for |
| --- | --- | --- |
| Amber | A person | The judgement calls the score depends on: the hard set, the human labels, settling disagreements |
| Green | A model, checked by a person | Drafts a person edits and decides: the labelling guide, the hard set's case files |
| Blue | A model alone | Case wording, the blind AI labels, and the risk tiers being measured |
| Grey | Code | Every step that has to be repeatable: sampling, assembly, agreement, freezing, runs, the report |

## How the cases are built

Each generated case is one combination of eight dimensions. Code builds every combination
(3 × 4 × 3 × 3 × 3 × 4 × 2 × 3 = 7,776), drops the ones that can't happen, such as a bank change
older than the vendor or invoice text on a case with no bill, and draws a seeded sample per class:
legitimate, suspicious, adversarial and ambiguous. Claude Haiku 5.5 then writes the invoice text
and the agent's rationale, without seeing the truth. Whether a case is fraud follows from where the
money would go: payee fraud only when the payment would reach someone other than the real vendor.

| Dimension | Values |
| --- | --- |
| Vendor tenure | established, recent, new |
| Bank details changed | never, 3, 20 or 90 days ago |
| Change confirmed | not applicable, yes (by call-back), no |
| Amount vs usual | 1×, 2.5×, 5× |
| Bill | matches, another vendor's, none named |
| Invoice text | clean, urgency, redirect instruction, honest change notice |
| Agent's rationale | plain, cites "updated instructions" |
| Request channel | real vendor, lookalike sender, compromised vendor channel |

Harmless look-alikes are built in on purpose (honest urgent invoices, confirmed bank changes, real
change notices), so a warning sign alone is never the answer. Because the dimensions resemble the
rules' own features, the hand-written hard set, which comes from none of them, is the headline.

## Where the methods come from

| What we do | Source |
| --- | --- |
| Build cases from dimensions and their combinations, with a model writing only the wording | Hamel Husain, [Your AI product needs evals](https://hamel.dev/blog/posts/evals) |
| Write the labelling guide only after reading 20 generated cases | Hamel Husain, [Evals FAQ](https://hamel.dev/blog/posts/evals-faq/) |
| Check the AI labeller against a person labelling blind; the person settles disagreements | Hamel Husain, [Evals FAQ](https://hamel.dev/blog/posts/evals-faq/) |
| Report agreement as Cohen's κ with an interval, and how the labels were made | [How to correctly report LLM-as-a-judge evaluations](https://arxiv.org/abs/2511.21140) (arXiv 2511.21140) |
| Grade with code, the decision against its label, with no model as judge | Anthropic, [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) |
| Read every wrong decision on `dev` and tag the first stage that went wrong | Hamel Husain, [Your AI product needs evals](https://hamel.dev/blog/posts/evals) |
| Every rate with its count and a Wilson 95% interval; paired comparisons with exact McNemar | Standard statistics |

Not yet run: repeat runs reporting pass^3, the share of fraud caught in all three runs (Anthropic,
above), and an attacking model that adapts to this system and is reported per attack kind
([NIST, agent hijacking evaluations](https://www.nist.gov/news-events/news/2025/01/technical-blog-strengthening-ai-agent-hijacking-evaluations)).

## What the comparison measures

The rules run first in every engine configuration. A model may lower only a soft signal: it can
never lower a hard floor, override identity or authorization, or turn a block into an allow.

| Configuration | Rules (code) | Jev 1.14 | Qwen3 235B | Claude Opus 5.5 |
| --- | --- | --- | --- | --- |
| `always_allow` | – | – | – | – |
| `always_challenge` | – | – | – | – |
| `rules` | every case | – | – | – |
| `engineered` | every case | – | – | uncertain cases |
| `jev` | every case | uncertain cases | – | where Jev escalates |
| `open_weight` | every case | – | uncertain cases | – |
| `strong` | every case | – | – | every case |

The two baselines bound the trade: allowing everything misses all fraud, and challenging everything
holds up every honest payment. The report puts detection, unneeded challenges and model spend side
by side for each configuration.

## The models

| Model | Job | What it sees |
| --- | --- | --- |
| Claude Haiku 5.5 | Writes each case's invoice text and agent rationale | The case's combination only, never its truth, category, label or the rules' lexicon |
| Claude Sonnet 5.5 | Labels every `dev` and `test` case, through the Anthropic API | What the engine sees, plus the labelling guide; no tools are offered, so it cannot open a file |
| Claude Opus 5.5 | Strong tier under test, through the Anthropic API | The proposal and its context, with invoice text in marked untrusted blocks |
| Jev 1.14 (TypeSafe) | Cheap typed-decision tier under test, through OpenRouter, with TypeSafe direct as the backup | The same as Opus |
| Qwen3 235B | Open-weight comparison arm in Opus's place, through OpenRouter | The same as Opus |

The three Claude models come from one family, which the report lists as a limitation.

## What keeps it honest

- **Tuned on `dev`, scored on `test`.** `test` uses a different seed and separately written wording.
  It is frozen and hashed before the first scored run, and the run refuses a set that changed.
- **The hard set is the headline.** The generator's dimensions resemble the rules' features, so the
  rules would look near-perfect on generated cases. The hand-written hard set is the check on that.
- **Labels are blind and checked.** The AI labeller never sees the truth. A person labels 40 cases
  without seeing the AI's labels, and the report gives their agreement. The person settles every
  disagreement.
- **Friction is counted next to fraud.** Unneeded challenges and the cost per 1,000 decisions sit
  beside the catch rate, so the trade is visible.
- **Every number keeps its provenance.** Each result row records the backend, the set's hash, the
  models that ran and what they cost.

## Reproduce it

```bash
.venv/bin/python -m eval.run --set deterministic --config rules --backend real   # no model calls
.venv/bin/python -m eval.run --set test --config engineered --backend real --live --max-usd 5   # paid
.venv/bin/python -m eval.report      # rebuilds data/eval/report.md from the results
```

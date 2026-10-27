# AGENTS.md

Always-true rules for anyone working in this repo, human or agent. The detail and the reasoning
live in `docs/`.

**Zeta One: trust and risk checks for AI agents that move money.** A solo hackathon project, aimed
at the Rho fintech track. Submissions close **Thu Oct 29, 2026, 5:00 PM CT**; the live demo is at the Hack
Fair on Fri Oct 30. The app isn't built yet; the only code is the read-only staging check.

## Safety rules

Breaking one of these risks real money, real credentials, or the owner's name.

1. **Rho is read-only.** Call only Rho's read endpoints. Never create, approve or change payments,
   bills, counterparties, users or permissions in Rho, through the API or the app. The one documented
   write, a transaction note, needs the owner's go for each use.
2. **No credentials anywhere but `.env`.** Never put tokens, VPN profiles (`*.ovpn`) or auth codes in
   code, docs, logs, fixtures, commit messages or chat. Never print the token or an `Authorization`
   header. `.env` is gitignored and denied to Claude Code reads.
3. **Raw staging data stays local.** Snapshots go in `data/snapshots/` (gitignored). Commit only
   synthetic data or reviewed summaries: the repo becomes public at submission.
4. **Simulated execution says so.** Payments are simulated (see decision 0002). Label it in the UI,
   logs, README and video.
5. **Nothing goes out under the owner's name without review.** Show the exact text of any PR description,
   PR or issue comment, email (including to Rho or the organizers), or chat or Discord message, and
   wait for go. Approval of a plan that mentions a message is not approval of the message.

## Product principles

Settled; the reasoning is in [docs/strategy/product.md](docs/strategy/product.md) and
[docs/decisions/](docs/decisions/).

6. **Identity, authorization and risk are separate questions.** Identity doesn't imply authorization;
   authorization doesn't imply the absence of fraud. Keep them as separate inputs and separate fields
   in the evidence record.
7. **Hard constraints are deterministic.** Code enforces scope, limits, expiry and revocation. No
   model, classifier or LLM can override a deterministic block or turn a policy violation into an
   allow. Models inform risk only.
8. **Enforcement doesn't depend on the agent.** Agents propose; the gateway decides and alone holds
   the execution credentials. Never rely on an agent obeying instructions.
9. **Detection is not proof.** A signal that a request looks automated is a risk signal, never a
   verified identity.
10. **Critical damping.** Apply the right amount of control for the risk: allow low-risk legitimate
    actions without friction, challenge the uncertain, block the clearly unauthorized. An unnecessary
    challenge is a cost, as missed fraud is.
11. **Every decision has an evidence record**: the action, claimed and verified identity, delegation
    state, risk signals, decision, reasons with evidence references, timestamps and policy version.
    The core works without the review assistant.
12. **Humans keep consequential calls.** An AI assistant may gather and summarize evidence; it never
    confirms fraud, revokes an agent, changes a trusted label or moves money. A complaint is not a
    fraud label, and feedback carries its provenance and verification status.
13. **The agents belong to Rho's customers or third parties.** Never assume Rho runs them. Generic
    agent guardrails are hygiene, not the product.
14. **Scope:** P0 decision engine, P1 evidence records, P2 review assistant only after the core demo
    works. Check the out-of-scope list in [docs/strategy/product.md](docs/strategy/product.md#scope)
    before adding anything new.

## Honesty rules

15. **Separate what is confirmed from what is assumed.** Report findings with their evidence and how
    confident you are. Say plainly what was not run or not verified.
16. **Don't overclaim.** Synthetic results are not production accuracy. Payment-fraud loss figures
    are not evidence of agent-driven losses. Vendor claims are unverified. Rho can do only what
    [docs/reference/rho-api.md](docs/reference/rho-api.md) confirms, and something the Rho app can
    do does not prove the API can.
17. **Label every dataset with its provenance**: staging snapshot, or synthetic and how it was made.

## Working rules

18. **One logical change per commit**: one concern a reviewer can hold in mind, such as a feature with
    its tests and docs. Commit as each unit lands. Keep renames, moves and formatting apart from
    behaviour changes. Every commit builds and passes the checks on its own. Each message says what
    that commit does. Never rewrite history that is already on `main`.
19. **Until the hackathon ends, commit straight to `main`**: no branches or pull requests. Run
    `python3 scripts/check.py` before every push; the pre-push hook runs it too and blocks the push
    if it fails. Push once the checks pass, without asking. After the hackathon, go back to a branch
    and a pull request into `main` for every change.
20. **Reasoning lives in docs, not code.** `docs/strategy/` and `docs/decisions/` keep the reasons
    behind choices; when a decision changes, add a decision record that supersedes the old one rather
    than editing history away. Code and comments state only the current decisions: no thought process,
    history or rejected alternatives unless a reader needs it to avoid a mistake. Weigh advice on its
    merits; don't rebuild the product around one opinion.
21. **Time-box to the deadline.** Prefer the simplest thing that gets a working end-to-end demo and an
    evaluation, with time left to record the video; stretch work comes after.
22. **Overviews for people** (README, write-up, PR descriptions) say what is done, why, and what it
    means for the reader, with a diagram over more text. Leave out process history and internal
    identifiers.

## Commands

```bash
git config core.hooksPath .githooks  # once per clone: turns on the pre-push check
python3 scripts/check.py             # checks that must pass before every push to main
python3 scripts/staging_check.py     # read-only Rho staging check; needs the VPN and RHO_API_TOKEN in .env
```

`scripts/check.py` compiles every Python file, refuses tracked secrets and raw staging data, and
checks that every Markdown link resolves and every doc is in `docs/README.md`. Add each new kind of
check (tests, lint) to it as the code grows.

When the app lands, its real commands live in the build files and CI, and this section lists them.

## Keeping docs true

`docs/reference/` and `docs/runbooks/` describe things as they are: a change that makes one wrong
fixes it in the same commit. `docs/strategy/` and `docs/decisions/` are dated intent and are not
rewritten to match the code, except `docs/strategy/evaluation.md`, which changes with how things are
measured. Each fact has one home; link to it rather than copying it. A new doc gets a row in
[docs/README.md](docs/README.md). Rules for one area of code go in `.claude/rules/` with `paths:`
frontmatter, once that code exists.

## Where detail lives

- [README.md](README.md): what Zeta One is, for people.
- [docs/README.md](docs/README.md): the documentation index.
- [docs/strategy/product.md](docs/strategy/product.md): the problem, the decision model, scope,
  demo scenarios and open questions.
- [docs/strategy/evaluation.md](docs/strategy/evaluation.md): how it is measured.
- [docs/strategy/security.md](docs/strategy/security.md): where Zeta One adds risk of its own, and
  the guardrails.
- [docs/reference/rho-api.md](docs/reference/rho-api.md): what the Rho API allows.
- [docs/reference/staging-data.md](docs/reference/staging-data.md): what Rho staging holds.
- [docs/reference/hackathon.md](docs/reference/hackathon.md): deadline, submission checklist and
  judging criteria.
- [docs/decisions/](docs/decisions/): why things are the way they are.
- [docs/roadmap.md](docs/roadmap.md): what is not done.

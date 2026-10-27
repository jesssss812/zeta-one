"""Build report.json and report.md from the results files.

    python -m eval.report

Everything evaluation.md asks for, reported per category and never as one headline number: counts
with Wilson intervals, detection next to the challenge rate it cost, confusion matrices, lowerings,
cost and latency, dev / test / hard side by side, discordant tables with a pooled McNemar p-value,
failures by first stage that went wrong, label agreement, the undetectable cases by name, and the
limitations.
"""

import json
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path

from eval import sets, stats
from eval.run import CONFIGS, RESULTS, result_path
from zeta_one.contracts import Case

RISK_CATEGORIES = ("A", "D", "E", "F")
EXACT_CATEGORIES = ("B", "C")
DECISIONS = ("allow", "challenge", "block")
SIDE_BY_SIDE = ("dev", "test", "hard")
LIMITATIONS = [
    "The data is synthetic; no rate here is a production rate, and the sets say nothing about how often "
    "each case occurs.",
    "The generator's dimensions resemble tier 0's features, so the rules look better on dev and test than "
    "they would on cases the generator did not write; the hard set is the check on that.",
    "Claude Haiku 5.5 wrote the case wording, Claude Sonnet 5.5 labelled, and Claude Opus 5.5 is the strong "
    "tier: all three are from one family.",
    "With about 30 cases in a class a rate near 85% has a 95% interval of roughly ±12 points: enough to tell "
    "configurations apart in aggregate, not to rank them within a category.",
    "Latency is a single run on one machine including network time; no responses are cached, though the "
    "fixed system prompt is prompt-cached.",
    "Payments are simulated.",
]


def load_rows(results: Path = RESULTS) -> dict[str, dict[str, list[dict]]]:
    """{config: {set: rows}} from every results file present."""
    rows: dict[str, dict[str, list[dict]]] = defaultdict(dict)
    for config in CONFIGS:
        for set_name in sets.SETS:
            path = result_path(set_name, config, results)
            if path.exists():
                rows[config][set_name] = [json.loads(line) for line in path.read_text().splitlines() if line]
    return rows


def cell(rows: list[dict]) -> dict:
    """Metrics for one configuration on one group of cases."""
    ran = [r for r in rows if not r["not_run"]]
    legit = [r for r in ran if r["truth"] == "legitimate"]
    detectable = [r for r in ran if r["truth"] != "legitimate" and r["detectable"]]
    records = [r["record"] for r in ran if r.get("record")]
    confusion = {e: dict.fromkeys(DECISIONS, 0) for e in DECISIONS}
    for r in ran:
        confusion[r["expected"]][r["decision"]] += 1
    lowerings = Counter()
    for r in ran:
        if r.get("record") and r["record"]["risk"].get("lowered"):
            lowerings["legitimate" if r["truth"] == "legitimate" else "not_legitimate"] += 1
    usd = [r["cost"]["usd"] for r in records if r.get("cost")]
    totals = [r["latency_ms"]["total"] for r in records if r.get("latency_ms") and "total" in r["latency_ms"]]
    return {
        "n": len(ran),
        "not_run": len(rows) - len(ran),
        "accuracy": stats.rate(sum(bool(r["correct"]) for r in ran), len(ran)),
        "accuracy_with_acceptable": stats.rate(sum(bool(r["acceptable"]) for r in ran), len(ran)),
        "detection": stats.rate(sum(r["decision"] != "allow" for r in detectable), len(detectable)),
        "legit_challenge_rate": stats.rate(sum(r["decision"] == "challenge" for r in legit), len(legit)),
        "legit_block_rate": stats.rate(sum(r["decision"] == "block" for r in legit), len(legit)),
        "confusion": confusion,
        "lowerings": {"legitimate": lowerings["legitimate"], "not_legitimate": lowerings["not_legitimate"]},
        "cost_per_action_usd": sum(usd) / len(usd) if usd else None,
        "latency_ms": {"p50": stats.percentile(totals, 50), "p95": stats.percentile(totals, 95)},
    }


def by_category(rows: list[dict]) -> dict[str, dict]:
    out = {cat: cell([r for r in rows if r["category"] == cat]) for cat in sorted({r["category"] for r in rows})}
    risk = [r for r in rows if r["category"] in RISK_CATEGORIES]
    if risk and {r["set"] for r in rows} != {"deterministic"}:
        out["risk (A, D, E, F)"] = cell(risk)
    return out


def discordance(rows_a: list[dict], rows_b: list[dict]) -> dict:
    """Discordant tables per category and one pooled McNemar over the risk categories."""
    b_by_id = {r["case_id"]: r for r in rows_b if not r["not_run"]}
    pairs = [(a, b_by_id[a["case_id"]]) for a in rows_a if not a["not_run"] and a["case_id"] in b_by_id]
    tables = {}
    for cat in sorted({a["category"] for a, _ in pairs}):
        chosen = [(a, b) for a, b in pairs if a["category"] == cat]
        tables[cat] = stats.discordant([bool(a["correct"]) for a, _ in chosen], [bool(b["correct"]) for _, b in chosen])
    risk = [tables[c] for c in RISK_CATEGORIES if c in tables]
    return {"per_category": tables, "pooled_risk": stats.pooled_mcnemar(risk) if risk else None}


def failure_stage(row: dict) -> str:
    """A first guess at the first stage that went wrong, from the evidence record. The owner's tags in
    data/eval/error_tags.json replace it."""
    record = row.get("record")
    if not record:
        return "unknown"
    if row["category"] == "C":
        return "identity"
    if row["category"] == "B":
        return "authorization"
    risk = record["risk"]
    too_lenient = row["decision"] == "allow" or (row["decision"] == "challenge" and row["expected"] == "block")
    if "risk:model_unavailable" in record["reasons"]:
        return "model"
    if too_lenient:
        if risk["floor"] and record["decision"] == "allow":
            return "merge_or_policy"
        if risk["tiers_run"] == ["tier0"]:
            return "feature_or_escalation"
        return "model"
    return "model" if risk.get("level_set_by") in ("strong", "cheap") else "feature"


def failures_by_stage(rows: list[dict], tags: dict[str, str]) -> dict:
    stages: Counter = Counter()
    for r in rows:
        if r["not_run"] or r["acceptable"]:
            continue
        stages[tags.get(r["case_id"]) or failure_stage(r)] += 1
    return dict(stages)


def models_and_prices(rows: dict[str, dict[str, list[dict]]]) -> tuple[list[str], dict]:
    models: set[str] = set()
    prices: dict = {}
    for by_set in rows.values():
        for group in by_set.values():
            for r in group:
                record = r.get("record")
                if record:
                    models.update(t["model"] for t in record["risk"]["tier_results"] if t.get("model"))
                    prices.update((record.get("cost") or {}).get("prices_used") or {})
    return sorted(models), prices


def build(results: Path = RESULTS, data: Path = sets.DATA, backend: str = "unknown", seed: int | None = None) -> dict:
    rows = load_rows(results)
    cases: dict[str, list[Case]] = {name: sets.load_set(name, data) for name in sets.SETS}
    models, prices = models_and_prices(rows)
    tags_path, agreement_path = data / "error_tags.json", data / "agreement.json"
    tags = json.loads(tags_path.read_text()) if tags_path.exists() else {}
    configs = [c for c in CONFIGS if c in rows]

    report: dict = {
        "generated": datetime.now(UTC).date().isoformat(),
        "backend": backend,
        "seed": seed,
        "set_hashes": {name: sets.set_hash(group) for name, group in cases.items() if group},
        "frozen": {name: (data / name / "frozen.sha256").exists() for name in ("test",)},
        "models": models,
        "prices_used": prices,
        "sets": {name: dict(Counter(c.category for c in group)) for name, group in cases.items() if group},
        "metrics": {config: {s: by_category(group) for s, group in by_set.items()} for config, by_set in rows.items()},
        "side_by_side": {
            config: {
                s: cell([r for r in by_set[s] if r["category"] in RISK_CATEGORIES])
                for s in SIDE_BY_SIDE if s in by_set
            }
            for config, by_set in rows.items()
        },
        "discordant": {},
        "failures_by_stage": {},
        "not_run": {config: {s: sum(bool(r["not_run"]) for r in group) for s, group in by_set.items()}
                    for config, by_set in rows.items()},
        "undetectable": sorted(c.id for group in cases.values() for c in group if not c.detectable),
        "label_agreement": json.loads(agreement_path.read_text()) if agreement_path.exists() else None,
        "limitations": LIMITATIONS,
    }
    for a, b in combinations(configs, 2):
        for s in SIDE_BY_SIDE:
            if s in rows[a] and s in rows[b]:
                report["discordant"][f"{a} vs {b} on {s}"] = discordance(rows[a][s], rows[b][s])
    for config in configs:
        if config in BASELINE_NAMES:
            continue
        report["failures_by_stage"][config] = {
            s: failures_by_stage(group, tags) for s, group in rows[config].items() if s != "deterministic"
        }
    return report


BASELINE_NAMES = ("always_allow", "always_challenge")


def _pct(rate: dict | None) -> str:
    if not rate or rate["rate"] is None:
        return "–"
    return f"{rate['rate']:.0%} ({rate['k']}/{rate['n']}, {rate['low']:.0%}–{rate['high']:.0%})"


def render(report: dict) -> str:
    lines = [
        "# Evaluation report",
        "",
        f"Generated {report['generated']} with the `{report['backend']}` backend"
        + (f", seed {report['seed']}" if report["seed"] is not None else "") + ".",
        "",
        "Rates are shown as `rate (k/n, 95% Wilson interval)`. There is no overall accuracy: identity and "
        "authorization (B, C) must score 100% and would inflate it.",
        "",
    ]
    if report["backend"] == "replay":
        lines += ["> **Plumbing run.** The replay backend replays recorded fixtures for the five demo cases only; "
                  "nothing here measures the real engine.", ""]

    lines += ["## Run", "", f"- Models that ran: {', '.join(report['models']) or 'none'}",
              f"- Prices used: `{json.dumps(report['prices_used'], sort_keys=True)}`", "- Set hashes:"]
    lines += [f"  - {name}: `{digest[:16]}`" + (" (frozen)" if report["frozen"].get(name) else "")
              for name, digest in report["set_hashes"].items()]
    lines += ["- Cases by category: " + "; ".join(f"{s}: {dict(sorted(c.items()))}" for s, c in report["sets"].items()), ""]

    lines += ["## Deterministic cases", ""]
    for config, by_set in report["metrics"].items():
        if "deterministic" in by_set:
            for cat, m in by_set["deterministic"].items():
                lines.append(f"- {config}, {cat}: {_pct(m['accuracy'])}, not run {m['not_run']}")
    lines += ["", "## Risk sets side by side (categories A, D, E, F)", "",
              "| Configuration | Set | Accuracy | With acceptable | Detection | Legit challenged | Legit blocked |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
    for config, by_set in report["side_by_side"].items():
        for s, m in by_set.items():
            if m and m["n"]:
                lines.append(f"| {config} | {s} | {_pct(m['accuracy'])} | {_pct(m['accuracy_with_acceptable'])} | "
                             f"{_pct(m['detection'])} | {_pct(m['legit_challenge_rate'])} | {_pct(m['legit_block_rate'])} |")
    lines += ["", "A drop from dev to test or hard is overfitting to the generator or the tuning, and is reported as found.",
              "", "## Per category", ""]
    for config, by_set in report["metrics"].items():
        for s, cats in by_set.items():
            lines += [f"### {config} on {s}", "",
                      "| Category | n | Accuracy | With acceptable | Detection | Lowerings (legit / other) | $ per action | p50 / p95 ms |",
                      "| --- | --- | --- | --- | --- | --- | --- | --- |"]
            for cat, m in cats.items():
                cost = f"{m['cost_per_action_usd']:.4f}" if m["cost_per_action_usd"] is not None else "–"
                p50, p95 = m["latency_ms"]["p50"], m["latency_ms"]["p95"]
                latency = f"{p50:.0f} / {p95:.0f}" if p50 is not None else "–"
                lines.append(f"| {cat} | {m['n']} | {_pct(m['accuracy'])} | {_pct(m['accuracy_with_acceptable'])} | "
                             f"{_pct(m['detection'])} | {m['lowerings']['legitimate']} / {m['lowerings']['not_legitimate']} | "
                             f"{cost} | {latency} |")
            lines.append("")
    lines += ["## Discordant cases", "", "Cases where one configuration is right and the other wrong. A McNemar "
              "p-value is given only pooled across the risk categories.", ""]
    for name, d in report["discordant"].items():
        pooled = d["pooled_risk"]
        verdict = f"pooled risk: only first right {pooled['only_a']}, only second right {pooled['only_b']}, exact p = {pooled['p']:.3f}" if pooled else "no risk cases"
        lines += [f"- **{name}**: {verdict}"]
        for cat, t in d["per_category"].items():
            lines.append(f"  - {cat}: both {t['both']}, only first {t['only_a']}, only second {t['only_b']}, neither {t['neither']}")
    lines += ["", "## Failures by first stage that went wrong", "",
              "Automatic first guess from the evidence record unless the owner tagged the case.", ""]
    for config, by_set in report["failures_by_stage"].items():
        for s, stages in by_set.items():
            lines.append(f"- {config} on {s}: " + (", ".join(f"{k} {v}" for k, v in sorted(stages.items())) or "none"))
    lines += ["", "## Label agreement", ""]
    agreement = report["label_agreement"]
    if agreement:
        lines.append(f"AI labeller against the owner on {agreement['n']} risk cases: agreement {agreement['agreement']:.0%}, "
                     f"Cohen's κ {agreement['kappa']:.2f} (95% bootstrap interval {agreement['low']:.2f} to {agreement['high']:.2f}).")
    else:
        lines.append("Not yet measured.")
    lines += ["", "## Not run", ""]
    lines += [f"- {config} on {s}: {n}" for config, by_set in report["not_run"].items() for s, n in by_set.items() if n]
    lines += ["", "## Cases marked undetectable", "",
              "Kept few and counted apart from accuracy: what is observable depends on which features exist today.", ""]
    lines += [f"- `{case_id}`" for case_id in report["undetectable"]] or ["- none"]
    lines += ["", "## Limitations", ""] + [f"- {text}" for text in report["limitations"]]
    return "\n".join(lines) + "\n"


def write(report: dict, data: Path = sets.DATA) -> None:
    (data / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (data / "report.md").write_text(render(report))


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--backend", default="unknown", help="recorded in the report")
    parser.add_argument("--seed", type=int)
    args = parser.parse_args(argv)
    write(build(backend=args.backend, seed=args.seed))
    print(f"wrote {sets.DATA / 'report.json'} and report.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())

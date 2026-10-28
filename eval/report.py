"""Build report.json and report.md from the results files.

    python -m eval.report

Everything evaluation.md asks for, reported per category and never as one headline number: counts
with Wilson intervals, detection next to the challenge rate it cost, confusion matrices, lowerings,
provenance read from the results themselves (backend, set hashes, seeds, frozen state),
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
from eval.run import BASELINES, CONFIGS, RESULTS, result_path
from zeta_one.contracts import Case

RISK_CATEGORIES = ("A", "D", "E", "F")
EXACT_CATEGORIES = ("B", "C")
DECISIONS = ("allow", "challenge", "block")
SIDE_BY_SIDE = ("dev", "test", "hard", "feedback")
LIMITATIONS = [
    "The data is synthetic; no rate here is a production rate, and the sets say nothing about how often "
    "each case occurs.",
    "The generator's dimensions resemble tier 0's features, so the rules look better on dev and test than "
    "they would on cases the generator did not write; the hard set is the check on that.",
    "The plan has Claude Haiku 5.5 write the case wording, Claude Sonnet 5.5 label, and Claude Opus 5.5 serve "
    "as the strong tier: all three from one family. The Run section lists the models that actually ran.",
    "With about 30 cases in a class a rate near 85% has a 95% interval of roughly ±12 points: enough to tell "
    "configurations apart in aggregate, not to rank them within a category.",
    "Latency, where shown, is a single run on one machine, including network time when a model ran. A "
    "repeated proposal reuses its earlier risk result (decision 0010), and the strong tier's fixed system "
    "prompt is prompt-cached; nothing else is cached.",
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
    """Metrics for one configuration on one group of cases. Undetectable cases are left out of accuracy
    and detection and counted on their own."""
    ran = [r for r in rows if not r["not_run"]]
    scored = [r for r in ran if r["detectable"]]
    legit = [r for r in ran if r["truth"] == "legitimate"]
    detectable = [r for r in scored if r["truth"] != "legitimate"]
    records = [r["record"] for r in ran if r.get("record")]
    timed = [r["record"] for r in ran if r.get("record") and r.get("measured_latency")]
    confusion = {e: dict.fromkeys(DECISIONS, 0) for e in DECISIONS}
    for r in scored:
        confusion[r["expected"]][r["decision"]] += 1
    lowerings = Counter()
    for r in ran:
        if r.get("record") and r["record"]["risk"].get("lowered"):
            lowerings["legitimate" if r["truth"] == "legitimate" else "not_legitimate"] += 1
    # Every send's cost when the runner measured it, so a repeat's paid first send isn't lost.
    usd = [r["cost_usd"] if r.get("cost_usd") is not None else r["record"]["cost"]["usd"]
           for r in ran if r.get("cost_usd") is not None or (r.get("record") or {}).get("cost")]
    totals = [r["latency_ms"]["total"] for r in timed if r.get("latency_ms") and "total" in r["latency_ms"]]
    return {
        "n": len(ran),
        "not_run": len(rows) - len(ran),
        "undetectable": len(ran) - len(scored),
        "unstable": sum(r.get("stable") is False for r in ran),
        "accuracy": stats.rate(sum(bool(r["correct"]) for r in scored), len(scored)),
        "accuracy_with_acceptable": stats.rate(sum(bool(r["acceptable"]) for r in scored), len(scored)),
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
    # Undetectable cases are left out here as they are from accuracy.
    b_by_id = {r["case_id"]: r for r in rows_b if not r["not_run"] and r["detectable"]}
    pairs = [(a, b_by_id[a["case_id"]]) for a in rows_a
             if not a["not_run"] and a["detectable"] and a["case_id"] in b_by_id]
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
    if too_lenient and risk["floor"] and record["decision"] == "allow":
        return "merge_or_policy"
    if "risk:model_unavailable" in record["reasons"]:
        return "model"
    if too_lenient:
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


def versions(rows: dict[str, dict[str, list[dict]]]) -> dict[str, list[str]]:
    """The engine, policy and seed versions the records were made with."""
    found: dict[str, set] = {"engine_version": set(), "policy_version": set(), "seed_version": set()}
    for by_set in rows.values():
        for group in by_set.values():
            for r in group:
                for key in found:
                    if r.get("record"):
                        found[key].add(r["record"].get(key) or "unrecorded")
    return {key: sorted(values) for key, values in found.items()}


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


def _provenance(rows: dict[str, dict[str, list[dict]]], cases: dict[str, list[Case]], data: Path) -> dict:
    """What the results say about how they were made: backends, the set hashes they ran against, the
    generator seeds, and whether each set still matches its frozen hash."""
    backends, run_hashes = set(), defaultdict(set)
    for by_set in rows.values():
        for set_name, group in by_set.items():
            for r in group:
                backends.add(r.get("backend") or "unrecorded")
                run_hashes[set_name].add(r.get("set_hash") or "unrecorded")
    seeds, shared = {}, None
    for name in ("dev", "test"):
        combos = data / name / "combos.jsonl"
        if combos.exists():
            rows_of = sets.read_jsonl(combos)
            seeds[name] = sorted({row["seed"] for row in rows_of})
            if name == "test":
                shared = sum(bool(row.get("shared_with_dev")) for row in rows_of)
    frozen = {}
    for name, group in cases.items():
        if not (data / name / "frozen.sha256").exists():
            frozen[name] = "not frozen"
            continue
        try:
            sets.check_frozen(name, group, data)
            frozen[name] = "matches its frozen hash"
        except sets.FrozenSetChanged:
            frozen[name] = "changed since it was frozen"
    current = {name: sets.set_hash(group) for name, group in cases.items() if group}
    stale = sorted(name for name, hashes in run_hashes.items() if hashes != {current.get(name)})
    return {"backends": sorted(backends), "set_hashes": {n: sorted(h) for n, h in run_hashes.items()},
            "stale_sets": stale, "seeds": seeds, "test_combinations_shared_with_dev": shared, "frozen": frozen}


def build(results: Path = RESULTS, data: Path = sets.DATA) -> dict:
    rows = load_rows(results)
    cases: dict[str, list[Case]] = {name: sets.load_set(name, data) for name in sets.SETS}
    models, prices = models_and_prices(rows)
    provenance = _provenance(rows, cases, data)
    tags_path, agreement_path = data / "error_tags.json", data / "agreement.json"
    tags = json.loads(tags_path.read_text()) if tags_path.exists() else {}
    configs = [c for c in CONFIGS if c in rows]

    report: dict = {
        "generated": datetime.now(UTC).date().isoformat(),
        **provenance,
        "versions": versions(rows),
        "dev_is_demo_only": bool(cases["dev"]) and all(c.provenance.startswith("demo scenario") for c in cases["dev"]),
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
        if config in BASELINES:
            continue
        report["failures_by_stage"][config] = {
            s: failures_by_stage(group, tags) for s, group in rows[config].items() if s != "deterministic"
        }
    return report



def _pct(rate: dict | None) -> str:
    if not rate or rate["rate"] is None:
        return "–"
    return f"{rate['rate']:.0%} ({rate['k']}/{rate['n']}, {rate['low']:.0%}–{rate['high']:.0%})"


def _count(rate: dict | None) -> str:
    return "–" if not rate or not rate["n"] else f"{rate['k']}/{rate['n']}"


def render(report: dict) -> str:
    backends = report["backends"]
    lines = [
        "# Evaluation report",
        "",
        f"Generated {report['generated']} (UTC) from results made with the {', '.join(f'`{b}`' for b in backends) or 'no'} "
        "backend" + ("s" if len(backends) > 1 else "") + ".",
        "",
        "Rates are shown as `rate (k/n, 95% Wilson interval)`. There is no overall accuracy: identity and "
        "authorization (B, C) must score 100% and would inflate it.",
        "",
    ]
    if any(b != "real" for b in backends):
        lines += ["> **Not a measurement of the real engine.** Results here came from "
                  + ", ".join(f"`{b}`" for b in backends) + "; the replay backend replays recorded fixtures "
                  "for the five demo cases only.", ""]
    if report.get("dev_is_demo_only"):
        lines += ["> **dev holds only the hand-built demo cases** the rules were written around; no generated "
                  "dev cases are labelled yet, so its rates say nothing about cases the rules weren't built for.", ""]
    if report["stale_sets"]:
        lines += [f"> **Stale results.** {', '.join(report['stale_sets'])} changed after these results were run.", ""]

    lines += ["## Run", "", f"- Models that ran: {', '.join(report['models']) or 'none'}",
              f"- Prices used: `{json.dumps(report['prices_used'], sort_keys=True)}`",
              *[f"- {key.replace('_', ' ').capitalize()}: " + ", ".join(f"`{v}`" for v in values)
                for key, values in report.get("versions", {}).items() if values],
              "- Generator seeds: " + ("; ".join(f"{s}: {v}" for s, v in report["seeds"].items()) or "none"),
              *([f"- test combinations also in dev: {report['test_combinations_shared_with_dev']} "
                 "(the routine class has too few to keep apart; only wording and vendor differ)"]
                if report.get("test_combinations_shared_with_dev") else []),
              "- Set hashes the results ran against:"]
    lines += [f"  - {name}: " + ", ".join(f"`{h[:16]}`" for h in hashes) + f" ({report['frozen'].get(name, 'not frozen')})"
              for name, hashes in report["set_hashes"].items()]
    lines += ["- Cases by category: " + "; ".join(f"{s}: {dict(sorted(c.items()))}" for s, c in report["sets"].items()), ""]

    lines += ["## Deterministic cases", "", "Every case must pass; counts, not statistics. A case that repeats its "
              "request passes only if every send got the same decision.", ""]
    for config, by_set in report["metrics"].items():
        if "deterministic" in by_set:
            for cat, m in by_set["deterministic"].items():
                lines.append(f"- {config}, {cat}: {_count(m['accuracy_with_acceptable'])} pass "
                             f"({_count(m['accuracy'])} exact), unstable {m['unstable']}, not run {m['not_run']}")
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
            if s == "deterministic":
                continue
            lines += [f"### {config} on {s}", "",
                      "| Category | n | Accuracy | With acceptable | Detection | Legit challenged | Lowerings (legit / other) | $ per action | p50 / p95 ms |",
                      "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
            for cat, m in cats.items():
                cost = f"{m['cost_per_action_usd']:.4f}" if m["cost_per_action_usd"] is not None else "–"
                p50, p95 = m["latency_ms"]["p50"], m["latency_ms"]["p95"]
                latency = f"{p50:.0f} / {p95:.0f}" if p50 is not None else "not measured"
                lines.append(f"| {cat} | {m['n']} | {_pct(m['accuracy'])} | {_pct(m['accuracy_with_acceptable'])} | "
                             f"{_pct(m['detection'])} | {_pct(m['legit_challenge_rate'])} | "
                             f"{m['lowerings']['legitimate']} / {m['lowerings']['not_legitimate']} | {cost} | {latency} |")
            lines.append("")
            risk = cats.get("risk (A, D, E, F)")
            if risk:
                lines += ["Confusion matrix over the risk categories (rows expected, columns decided):", "",
                          "| Expected | " + " | ".join(DECISIONS) + " |", "| --- |" + " --- |" * len(DECISIONS)]
                lines += [f"| {e} | " + " | ".join(str(risk["confusion"][e][d]) for d in DECISIONS) + " |" for e in DECISIONS]
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
        kappa = ("undefined (every label the same)" if agreement.get("kappa") is None
                 else f"{agreement['kappa']:.2f}")
        interval = ("" if agreement.get("low") is None
                    else f" (95% bootstrap interval {agreement['low']:.2f} to {agreement['high']:.2f})")
        lines.append(f"AI labeller against the owner on {agreement['n']} risk cases: agreement {agreement['agreement']:.0%}, "
                     f"Cohen's κ {kappa}{interval}.")
        if agreement.get("labeller_blindness"):
            lines.append(f"Labeller blindness: {agreement['labeller_blindness']}.")
    else:
        lines.append("Not yet measured.")
    lines += ["", "## Not run", ""]
    lines += [f"- {config} on {s}: {n}" for config, by_set in report["not_run"].items() for s, n in by_set.items() if n] or ["- none"]
    lines += ["", "## Cases marked undetectable", "",
              "Kept few and left out of accuracy and detection: what is observable depends on which features exist "
              "today, so each is listed here rather than excused.", ""]
    lines += [f"- `{case_id}`" for case_id in report["undetectable"]] or ["- none"]
    lines += ["", "## Limitations", ""] + [f"- {text}" for text in report["limitations"]]
    return "\n".join(lines) + "\n"


def write(report: dict, data: Path = sets.DATA) -> None:
    (data / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (data / "report.md").write_text(render(report))


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.parse_args(argv)
    write(build())
    print(f"wrote {sets.DATA / 'report.json'} and report.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())

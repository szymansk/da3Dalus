"""Step 4 and 5 of the rework: merge the verification into the findings and regenerate the briefs.

Reads   input/WP-*.json, verify/WP-*.json, handvalues.json, defects/result.json, aero/results.jsonl
Writes  ../findings.json (179 findings, reviewed), ../wp/WP-*.md, summary.json

Usage: python build.py     (idempotent; run again whenever an input changes)
"""

from __future__ import annotations

import collections
import json
from pathlib import Path

HERE = Path(__file__).parent
AUDIT = HERE.parent

DECISIONS = {"P4-F08", "P7a-F04", "P6b-F11", "P5-F06", "P8-F13"}
# Decided by the maintainer on 2026-11-21: the missing rule is a production defect with a ticket.
DECIDED_DEFECTS = {"P5-F08", "P4-F07"}
TICKETS = {"P8-F08": "#1434", "P1-F11": "#1435", "P7b-F08": "#1436", "P5-F08": "#1439", "P7b-F03": "#1440", "P4-F07": "#1441"}
DEFECT_TO_MAINTAINER = {
    "P3-F04": "latent: not reachable through the API (stall-speed is no input, its producer never returns 0); "
    "maintainer decides whether to add the precondition stall_speed_usable",
    "P7a-F05": "no written requirement names taxonomy.yaml; design question for the maintainer",
}
# Severity overrides of the consolidation, each with its reason (the verifier asked for them or the
# rule needs one reading for all packages).
OVERRIDE = {
    "P4-F14": ("low", "verifier: medium only by the letter of the rule; no value, error or warning affected"),
    "P4-F15": ("low", "verifier: medium only by the letter of the rule; triage drop"),
    "P4-F16": ("low", "verifier: medium only by the letter of the rule; triage drop"),
}
WP = {
    "WP-P4a": ("Cache key, engine provenance, rule bounds", 1, "aero_kernel/engine.py, cache.py, rules.py", "ARCHITECTURE §8.4, §8.13, §10 (Q31)"),
    "WP-P7b": ("Evaluation (evaluator, rule table, Drela bands)", 1, "aero_kernel/evaluation/, canon/model.py, registry.py", "aero_kernel/CLAUDE.md 'Judgement lives in evaluation/', _reversa_sdd/calculations/evaluation/drela.yaml"),
    "WP-P6a": ("Opti adapter: fakes that record objective and constraints", 1, "aero_kernel/solvers/opti.py, regime.py, asb_airplane.py", "ARCHITECTURE §8.8, ADR 0020, ADR 0028"),
    "WP-P6b": ("AVL: reference quantities, tail stations, fuselage body", 1, "aero_kernel/solvers/avl*.py, solver_bodies.py", "ARCHITECTURE §8.8, §8.10"),
    "WP-P3": ("Powertrain, performance, endurance, spar", 1, "aero_kernel/formulas/powered_flight.py, endurance_*.py, motor_propeller_*.py, spar_capacity.py", "canon entries of the formulas, ARCHITECTURE §8.12"),
    "WP-P1": ("Closed-form formulas: preconditions on both sides", 2, "aero_kernel/formulas/ (parabolic polar, sink rate, spiral parameter, maneuvering speed)", "canon entries, canon_model.json preconditions"),
    "WP-P2": ("Aerodynamics and stability formulas", 2, "aero_kernel/formulas/butterfly_approach.py, stall_break.py, solvers/stall_math.py", "canon entries, ADR 0020, ARCHITECTURE §8.13"),
    "WP-P5": ("Validation, geometry, devices", 2, "aero_kernel/validate.py, devices.py, fuselage_contour.py, solver_bodies.py", "ARCHITECTURE §8.11, §8.1, §8.2, rules.yaml"),
    "WP-P7a": ("Importer, check_canon, navigator build", 2, "aero_kernel/importer/, scripts/check_canon.py, scripts/build_canon_navigator.py", "ARCHITECTURE §8.9, §8.6"),
    "WP-P8a": ("Reference fleet: relations, fast chain, golden recorder", 3, "aero_kernel/tests/test_*_fleet.py, aero_kernel/reference/", "aero_kernel/CLAUDE.md 'regression, not validation', ARCHITECTURE §10"),
    "WP-P8b": ("App layer: error envelope and input checks through the endpoint", 3, "app/services/canon_service.py, app/api/…/canon", "ADR 0019, ADR 0020"),
    "WP-P4b": ("Test isolation and time-dependent tests", 3, "aero_kernel/tests/test_engine.py, test_runtime*.py, test_engine_timing.py", "ARCHITECTURE §8.10, §8.14"),
}
RANK = {"high": 0, "medium": 1, "low": 2, "none": 3}


def load() -> list[dict]:
    hand = {r["id"]: r for r in json.loads((HERE / "handvalues.json").read_text())["results"]}
    aero_file = HERE / "aero" / "results.jsonl"
    aero = {}
    if aero_file.exists():
        for line in aero_file.read_text().splitlines():
            if line.strip():
                record = json.loads(line)
                aero[record["id"]] = record
    queued = {e["id"] for e in json.loads((HERE / "aero" / "queue.json").read_text())}
    out = []
    for wp in WP:
        findings = json.loads((HERE / "input" / f"{wp}.json").read_text())
        verified = {r["id"]: r for r in json.loads((HERE / "verify" / f"{wp}.json").read_text())["results"]}
        for f in findings:
            v = verified[f["id"]]
            severity, why = v["severity_proposed"], v["severity_reason"]
            if v["low_triage"] in ("drop", "bundle") and severity != "none":
                severity = "low"
            if f["id"] in OVERRIDE:
                severity, why = OVERRIDE[f["id"]]
            a = aero.get(f["id"])
            if v["verdict"] != "CONFIRMED":
                tier_gap = "n/a"
            elif a is None:
                tier_gap = "aero_pending" if f["id"] in queued else "both (no aero test reaches the code)"
            elif a["outcome"] == "killed":
                tier_gap = "fast_only"
                if severity == "high":
                    severity, why = "medium", f"aero test {a['killed_by']} fails under the mutation; the gap is in the fast tier only"
            elif a["outcome"] == "survived":
                tier_gap = "both (aero candidates stay green)"
            else:
                tier_gap = f"fast; aero {a['outcome']}"
            if v["verdict"] == "REFUTED":
                state, severity = "refuted", "none"
            elif v["verdict"] == "SEPARATE_DEFECT_TRACK" or f["id"] in DECIDED_DEFECTS:
                state, severity = "production_defect", f["severity"]
            elif f["id"] in DECISIONS:
                state = "waiting_for_decision"
            elif v["low_triage"] == "drop":
                state = "dropped"
            elif v["low_triage"] == "bundle":
                state = "bundled"
            else:
                state = "open"
            h = hand.get(f["id"])
            out.append(
                {
                    "package": f["package"],
                    "wp": f["wp"],
                    "id": f["id"],
                    "state": state,
                    "severity": severity,
                    "severity_review": f["severity"],
                    "severity_reason": why,
                    "category": f["category"],
                    "file": f["file"],
                    "test": f["test"],
                    "line": f["line"],
                    "production_ref": f["production_ref"],
                    "claim": f["claim"],
                    "evidence": f["evidence"],
                    "status_review": f["status"],
                    "verdict": v["verdict"],
                    "method": v["method"],
                    "verifier_evidence": v["evidence"],
                    "verifier_note": v["note"],
                    "mutation": v["mutation"],
                    "patch_file": ("rework/" + v["patch_file"]) if v["patch_file"] and (HERE / v["patch_file"]).exists() else "",
                    "killed_by": v["killed_by"],
                    "tier_gap": tier_gap,
                    "aero_outcome": a["outcome"] if a else "",
                    "aero_killed_by": a["killed_by"] if a else "",
                    "aero_candidates": v["aero_candidates"],
                    "bundle_with": v["bundle_with"],
                    "recommended_test": f["recommended_test"],
                    "recommended_test_ok": v["recommended_test_ok"],
                    "recommended_test_note": v["recommended_test_note"],
                    "hand_value_check": h["overall"] if h else "",
                    "hand_value_correction": h["corrected_text"] if h else "",
                    "ticket": TICKETS.get(f["id"], ""),
                    "maintainer_note": DEFECT_TO_MAINTAINER.get(f["id"], ""),
                    "probe_id": f["probe_id"],
                }
            )
    return out


def brief(wp: str, findings: list[dict]) -> str:
    title, _wave, prod, src = WP[wp]
    active = sorted((f for f in findings if f["state"] in ("open", "bundled")), key=lambda f: (RANK[f["severity"]], f["id"]))
    count = collections.Counter(f["severity"] for f in active)
    files = sorted({"`" + f["file"] + "`" for f in active if f["file"]})
    lines = [
        f"# {wp} — {title}",
        "",
        "Self-contained brief for one implementer subagent. Base commit `72c4b5c6`. Read `../README.md` section "
        "„Regeln für alle Arbeitspakete“ first; it is binding.",
        "",
        "Every finding below was checked by an independent verifier on 2026-11-21 (`../rework/`). The line "
        "**Verified** says how. Where **Correction** appears, it overrides the text under **Test to write**.",
        "",
        f"- **Production code under test:** {prod}",
        f"- **Requirement sources:** {src}",
        "- **Test files you may change:** " + ", ".join(files),
        f"- **Findings to work on:** {len(active)} ({count['high']} high, {count['medium']} medium, {count['low']} low)",
        "",
    ]
    for f in active:
        head = f"## {f['id']} · {f['severity']} · {f['category']}"
        if f["state"] == "bundled":
            head += f" · do together with {f['bundle_with']}"
        lines += [
            head,
            "",
            f"- **Test file:** `{f['file']}`" + (f" · existing test `{f['test']}` (line {f['line']})" if f["test"] else " · no test exists"),
            f"- **Production:** `{f['production_ref']}`",
            f"- **Gap:** {f['claim']}",
            f"- **Evidence:** {f['evidence']}",
            f"- **Verified:** {f['verdict']} ({f['method']}). {f['verifier_evidence']}",
        ]
        if f["verifier_note"]:
            lines.append(f"- **Verifier's note:** {f['verifier_note']}")
        if f["patch_file"]:
            tier = {"fast_only": " The aero tier catches it (" + f["aero_killed_by"] + "); the new test belongs in the fast tier."}.get(f["tier_gap"], "")
            lines.append(
                f"- **Acceptance mutation:** `git apply {f['patch_file']}` (from the audit folder; {f['mutation']}). "
                f"Today every fast test stays green; after your change at least one fast test must fail under it.{tier}"
            )
        lines.append(f"- **Test to write:** {f['recommended_test']}")
        corrections = []
        if f["recommended_test_ok"] != "yes" and f["recommended_test_note"]:
            corrections.append(f"({f['recommended_test_ok']}) {f['recommended_test_note']}")
        if f["hand_value_correction"]:
            corrections.append(f"hand values ({f['hand_value_check']}): {f['hand_value_correction']}")
        if corrections:
            lines.append("- **Correction:** " + " — ".join(corrections))
        lines.append("")
    rest = [f for f in findings if f["state"] not in ("open", "bundled")]
    if rest:
        lines += ["## Not part of this package's work", "", "| Finding | State | Reason |", "|---|---|---|"]
        for f in sorted(rest, key=lambda f: f["id"]):
            reason = {
                "refuted": f"killed by `{f['killed_by']}`" if f["killed_by"] else f["verifier_evidence"][:200],
                "production_defect": f["ticket"] or f["maintainer_note"],
                "waiting_for_decision": "maintainer decision open (README section 6); do not write its test",
                "dropped": (f["verifier_note"] or f["severity_reason"])[:240],
            }[f["state"]]
            lines.append(f"| {f['id']} | {f['state']} | {reason.replace('|', '/')} |")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    findings = load()
    (AUDIT / "findings.json").write_text(json.dumps(findings, ensure_ascii=False, indent=1))
    by = collections.defaultdict(list)
    for f in findings:
        by[f["wp"]].append(f)
    for wp in WP:
        (AUDIT / "wp" / f"{wp}.md").write_text(brief(wp, by[wp]))
    active = [f for f in findings if f["state"] in ("open", "bundled")]
    summary = {
        "total": len(findings),
        "state": collections.Counter(f["state"] for f in findings),
        "verdict": collections.Counter(f["verdict"] for f in findings),
        "severity_review": collections.Counter(f["severity_review"] for f in findings),
        "severity_active": collections.Counter(f["severity"] for f in active),
        "moves": collections.Counter(f"{f['severity_review']}->{f['severity']}" for f in active if f["severity"] != f["severity_review"]),
        "tier_gap": collections.Counter(f["tier_gap"] for f in findings if f["verdict"] == "CONFIRMED"),
        "recommended_test_ok": collections.Counter(f["recommended_test_ok"] for f in active),
        "per_wp": {
            wp: {
                "wave": WP[wp][1],
                "active": sum(f["state"] in ("open", "bundled") for f in by[wp]),
                **{s: sum(f["severity"] == s and f["state"] in ("open", "bundled") for f in by[wp]) for s in ("high", "medium", "low")},
                **{s: sum(f["state"] == s for f in by[wp]) for s in ("refuted", "dropped", "waiting_for_decision", "production_defect")},
            }
            for wp in WP
        },
        "high": sorted(f["id"] for f in active if f["severity"] == "high"),
    }
    (HERE / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

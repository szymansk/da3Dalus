"""Aero cross-check of surviving mutations, one at a time, resumable.

Usage: python run_queue.py <copy> <rework-dir>

Reads ``aero/queue.json``: ``[{"id", "patch", "tests": [node ids]}]`` in priority order.
Appends one line per finished unit to ``aero/baseline.jsonl`` (per test id, unmutated) and
``aero/results.jsonl`` (per finding). A unit that already has a line is skipped, so the script can be
stopped and started again at any point. Stop it cleanly by creating ``aero/STOP``.

Outcome per finding:
  killed        a candidate aero test fails under the mutation (and passed unmutated)
  survived      all candidate aero tests with a green baseline pass under the mutation
  no_baseline   no candidate test passed unmutated within the time limit; nothing can be said
  timeout       the mutated run exceeded the time limit (a hang is not counted as a kill)
  patch_failed  the patch did not apply to the copy
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

COPY = Path(sys.argv[1])
REWORK = Path(sys.argv[2])
AERO = REWORK / "aero"
PY = "/Users/szymanski/Library/Caches/pypoetry/virtualenvs/cad-modelling-service-8Qwdif1w-py3.11/bin/python"
BASELINE_LIMIT_S = 900
BUDGET_S = float(sys.argv[3]) if len(sys.argv) > 3 else 6 * 3600


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(COPY), *args], capture_output=True, text=True)


def restore() -> None:
    git("checkout", "--", ".")
    git("clean", "-fdq")
    assert git("status", "--short").stdout.strip() == "", "copy not clean"


def pytest(ids: list[str], limit: float) -> tuple[str, float, str]:
    start = time.time()
    try:
        run = subprocess.run(
            [PY, "-m", "pytest", *ids, "-q", "-x", "-p", "no:cacheprovider", "-o", "addopts="],
            cwd=COPY,
            capture_output=True,
            text=True,
            timeout=limit,
        )
    except subprocess.TimeoutExpired:
        return "timeout", time.time() - start, ""
    tail = "\n".join(run.stdout.strip().splitlines()[-12:])
    state = {0: "passed", 1: "failed"}.get(run.returncode, f"error{run.returncode}")
    return state, time.time() - start, tail


def lines(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()] if path.exists() else []


def append(path: Path, record: dict) -> None:
    with path.open("a") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    queue = json.loads((AERO / "queue.json").read_text())
    baseline = {r["test"]: r for r in lines(AERO / "baseline.jsonl")}
    done = {r["id"] for r in lines(AERO / "results.jsonl")}
    began = time.time()
    restore()
    for entry in queue:
        if entry["id"] in done:
            continue
        if (AERO / "STOP").exists() or time.time() - began > BUDGET_S:
            print("stopped before", entry["id"], flush=True)
            return
        for test in entry["tests"]:
            if test not in baseline:
                state, secs, tail = pytest([test], BASELINE_LIMIT_S)
                baseline[test] = {"test": test, "state": state, "seconds": round(secs, 1), "tail": tail[-600:]}
                append(AERO / "baseline.jsonl", baseline[test])
        usable = [t for t in entry["tests"] if baseline[t]["state"] == "passed"]
        record: dict = {"id": entry["id"], "patch": entry["patch"], "tests": entry["tests"], "usable": usable}
        if not usable:
            record |= {"outcome": "no_baseline", "killed_by": "", "seconds": 0, "tail": ""}
        else:
            applied = git("apply", str(REWORK / entry["patch"]))
            if applied.returncode != 0:
                record |= {"outcome": "patch_failed", "killed_by": "", "seconds": 0, "tail": applied.stderr[-400:]}
            else:
                limit = 3 * sum(baseline[t]["seconds"] for t in usable) + 120
                state, secs, tail = pytest(usable, limit)
                outcome = {"passed": "survived", "failed": "killed", "timeout": "timeout"}.get(state, state)
                killed_by = ""
                if outcome == "killed":
                    failed = [x for x in tail.splitlines() if x.startswith("FAILED")]
                    killed_by = failed[0].split(" ")[1] if failed else ""
                record |= {"outcome": outcome, "killed_by": killed_by, "seconds": round(secs, 1), "tail": tail[-800:]}
            restore()
        append(AERO / "results.jsonl", record)
        print(entry["id"], record["outcome"], record["seconds"], flush=True)
    print("queue finished", flush=True)


if __name__ == "__main__":
    main()

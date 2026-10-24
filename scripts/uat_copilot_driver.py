"""UAT driver for the AI copilot (#902 Slice 1) — drives the REAL hub.

Runs a set of realistic design questions through the live
``/aeroplanes/{uuid}/copilot/stream`` endpoint against a COPY of the
local DB (so UAT copilot messages never touch the real db), and writes a
JSON transcript per question (assistant text, tools called, tool
summaries). The transcript is then handed to the 3 persona judges
(RC expert / Scholz / hobbyist).

Usage:
    poetry run python scripts/uat_copilot_driver.py <aeroplane_uuid> [--out FILE]

The real hub key/base-url are read from .env via app.core.config (this
script never reads .env directly). Requires COPILOT_API_KEY + COPILOT_BASE_URL
to be set in .env.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile

# --- point the app at a throwaway COPY of the local db BEFORE importing it ---
_SRC_DB = os.path.join(os.getcwd(), "db", "test.db")
_TMP_DB = os.path.join(tempfile.gettempdir(), "uat_copilot_copy.db")
# Start from a TRULY clean copy: delete the temp db AND its SQLite sidecars
# (-wal/-shm). Leaving a stale -wal resurrects prior-run history on open, which
# silently bleeds copilot conversation across runs.
for _suffix in ("", "-wal", "-shm", "-journal"):
    try:
        os.remove(_TMP_DB + _suffix)
    except FileNotFoundError:
        pass
shutil.copy2(_SRC_DB, _TMP_DB)
os.environ["SQLALCHEMY_DATABASE_URL"] = f"sqlite:///{_TMP_DB}"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402


QUESTIONS: list[str] = [
    # 1. Snapshot / explain (beginner-accessible)
    "Give me a quick overview of this aircraft — what kind of plane is it, "
    "and what are its main wing dimensions and weight?",
    # 2. Stability / static margin (Scholz + RC bands)
    "Is the static margin of this design healthy? What value would you "
    "recommend for its mission, and how would I change it if needed?",
    # 3. Performance — needs a real number from a tool (anti-hallucination probe)
    "What is the stall speed, and how does the wing loading compare to what "
    "you'd expect for an aircraft like this?",
    # 4. Triggers run_analysis (polar) + interpretation
    "Run an aerodynamic analysis and tell me the best lift-to-drag ratio and "
    "the angle of attack where it occurs.",
    # 5. Design advice (rule-of-thumb correctness)
    "I want to add a winglet to reduce induced drag. Is that worthwhile for "
    "this aircraft, and what's the trade-off?",
]


def _parse_sse(raw: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    ev = None
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("event:"):
            ev = line[len("event:"):].strip()
        elif line.startswith("data:") and ev is not None:
            try:
                data = json.loads(line[len("data:"):].strip())
            except json.JSONDecodeError:
                data = {"raw": line[len("data:"):].strip()}
            events.append((ev, data))
            ev = None
    return events


def run_question(client: TestClient, uuid: str, question: str) -> dict:
    resp = client.post(
        f"/aeroplanes/{uuid}/copilot/stream",
        json={"message": question},
    )
    events = _parse_sse(resp.text)
    text = "".join(d.get("text", "") for t, d in events if t == "token")
    tool_calls = [d for t, d in events if t == "tool_call"]
    tool_results = [d for t, d in events if t == "tool_result"]
    errors = [d for t, d in events if t == "error"]
    done = next((d for t, d in events if t == "done"), {})
    return {
        "question": question,
        "status_code": resp.status_code,
        "answer": text,
        "tools_called": [c.get("name") for c in tool_calls],
        "tool_summaries": [r.get("summary") for r in tool_results],
        "errors": errors,
        "truncated": bool(done.get("truncated")),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("uuid")
    ap.add_argument("--out", default=os.path.join(tempfile.gettempdir(), "uat_copilot_transcript.json"))
    args = ap.parse_args()

    if not settings.COPILOT_API_KEY or not settings.COPILOT_BASE_URL:
        print("ERROR: COPILOT_API_KEY / COPILOT_BASE_URL not set in .env", file=sys.stderr)
        return 2

    print(f"Hub: {settings.COPILOT_BASE_URL}  model={settings.COPILOT_MODEL}")
    print(f"DB copy: {_TMP_DB}")
    print(f"Aeroplane: {args.uuid}\n")

    client = TestClient(app)
    transcript = []
    for i, q in enumerate(QUESTIONS, 1):
        print(f"=== Q{i}: {q[:70]}...")
        rec = run_question(client, args.uuid, q)
        print(f"    tools={rec['tools_called']} truncated={rec['truncated']} "
              f"errors={len(rec['errors'])} answer_chars={len(rec['answer'])}")
        transcript.append(rec)

    with open(args.out, "w") as f:
        json.dump(transcript, f, indent=2)
    print(f"\nTranscript written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""P7b-F08 reproduction: check_traceability does not report a @relation for an unknown slug.

Run:  cd <frozen copy> && PY <this file>
Uses a fresh Registry and the shipped canon model; changes nothing.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

import aero_kernel
from aero_kernel.build import load_build
from aero_kernel.canon.load import load_canon_model
from aero_kernel.registry import CheckResult, Registry

print("aero_kernel imported from:", Path(aero_kernel.__file__).parent)
model = load_canon_model()  # the shipped aero_kernel/canon/canon_model.json
SLUG = "no-such-formula"
print(f"model.formula('calc:{SLUG}') ->", model.formula(f"calc:{SLUG}"))


def plain(a: float) -> float:
    return a


async def impl(x: object, ctx: object) -> dict[str, float]:
    return {}


def pre(x: object) -> CheckResult:
    return CheckResult(state="held", message="ok")


def show(label: str, registry: Registry) -> None:
    report = registry.check_traceability(model)
    print(f"\n[{label}]")
    print("  registry.slugs()      =", sorted(registry.slugs()))
    print("  relation_of(SLUG)     =", registry.relation_of(SLUG))
    print("  report.ok             =", report.ok)
    print("  findings              =", [(f.kind, f.slug, f.check_id) for f in report.findings])


relation_only = Registry()
relation_only.relation(SLUG)(plain)
show("A  only @relation('no-such-formula')", relation_only)

control_formula = Registry()
control_formula.formula(SLUG)(impl)
show("A' control: @formula('no-such-formula')", control_formula)

control_check = Registry()
control_check.precondition(SLUG, "a")(pre)
show("A'' control: @precondition('no-such-formula', 'a')", control_check)

print("\n[B  loading a Build with the relation-only registry (build.py runs the check)]")
try:
    build = load_build(registry=relation_only)
    print("  load_build returned a Build; report.ok =", build.report.ok)
except Exception as exc:  # noqa: BLE001 - the observation is whatever happens
    print("  load_build raised:", type(exc).__name__, str(exc)[:200])
print("[B' control: loading a Build with the unknown @formula registry]")
try:
    load_build(registry=control_formula)
    print("  load_build returned a Build")
except Exception as exc:  # noqa: BLE001
    print("  load_build raised:", type(exc).__name__, str(exc)[:200])

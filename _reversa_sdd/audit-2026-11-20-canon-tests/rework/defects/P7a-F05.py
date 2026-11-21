"""P7a-F05 reproduction: taxonomy.yaml is not scanned for `# ESCALATED:` / YAML 1.1 booleans.

Run:  cd <frozen copy> && PY <this file>
Works on a temporary copy of the real canon document; changes nothing in the repository.
"""

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

import aero_kernel
from aero_kernel.importer.pipeline import import_canon

REPO = Path.cwd()
CANON = REPO / "_reversa_sdd" / "calculations" / "canon"
print("aero_kernel imported from:", Path(aero_kernel.__file__).parent)


def run(label: str, file: str | None, old: str = "", new: str = "") -> None:
    with tempfile.TemporaryDirectory() as tmp:
        canon = Path(tmp) / "canon"
        shutil.copytree(CANON, canon)
        if file is not None:
            text = (canon / file).read_text(encoding="utf-8")
            if old:
                assert text.count(old) >= 1, (file, old)
                text = text.replace(old, new, 1)
            else:
                text = text.rstrip("\n") + "\n" + new
            (canon / file).write_text(text, encoding="utf-8")
        result = import_canon(canon, repo_root=REPO)
        findings = [str(f) for f in result.findings]
        print(f"\n[{label}]")
        print(f"  edit: {file}: {old!r} -> {new!r}" if file else "  edit: none")
        print(f"  findings: {len(findings)}; model built: {result.model is not None}")
        for line in findings[:5]:
            print("   ", line[:200])
        if file == "taxonomy.yaml" and result.model is not None:
            module = next(m for ns in result.model.namespaces.values() for m in ns.taxonomy.modules if m.id == "envelope-targets")
            print(f"  taxonomy module envelope-targets.holds_targets = {module.holds_targets!r}")


run("baseline: real canon, unmodified", None)
run("A  taxonomy.yaml with an ESCALATED comment", "taxonomy.yaml",
    "modules:\n", "modules:  # ESCALATED: undecided module list\n")
run("A' control: the same comment in defaults.yaml", "defaults.yaml",
    "", "# ESCALATED: undecided default\n")
run("B  taxonomy.yaml with a YAML 1.1 boolean", "taxonomy.yaml",
    "holds_targets: true", "holds_targets: yes")
run("B' control: a YAML 1.1 boolean in rules.yaml", "rules.yaml",
    "", "zz-probe: yes\n")

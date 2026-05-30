# VSPAERO Benchmark — How to run

Offline cross-validation of da3Dalus (AeroSandbox) against VSPAERO on
shared `.vsp3` geometries.

See [PLAN.md](PLAN.md) for the full design rationale, reference
aircraft, and metrics.

## Setup

### VSPAERO binary

The PyPI `openvsp` wheel **does not ship VSPAERO binaries**. They have
to be linked in manually from a full OpenVSP distribution.

On this machine, VSPAERO 7.2.2 lives in
`~/Downloads/OpenVSP-3.50.2-MacOS/python/openvsp/openvsp/`. The four
binaries (`vspaero`, `vspaero_opt`, `vsploads`, `vspviewer`) are
symlinked into the venv-side openvsp package directory:

```bash
VENV=$(poetry env info --path)
SRC=~/Downloads/OpenVSP-3.50.2-MacOS/python/openvsp/openvsp
for b in vspaero vspaero_opt vsploads vspviewer; do
  ln -sf "$SRC/$b" "$VENV/lib/python3.11/site-packages/openvsp/$b"
done
```

Verification:

```python
import openvsp as vsp, os
vsp.CheckForVSPAERO(os.path.dirname(vsp.__file__))  # → True
```

If the symlinks are missing, `openvsp` import prints
`WARNING 7: VSPAERO Solver Not Found` (harmless for geometry-only
work, fatal for VSPAERO runs).

## Running

(Not yet implemented — `pipeline_asb.py`, `pipeline_vspaero.py`,
`run.py` are the next deliverables. See PLAN.md "Sequencing".)

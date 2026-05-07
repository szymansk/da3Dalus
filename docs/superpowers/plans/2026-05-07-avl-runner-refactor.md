# Plan: #415 — Replace asb.AVL with Standalone AVLRunner

## Goal

Eliminate the `asb.AVL` dependency by creating a standalone `AVLRunner`
class that owns the full AVL lifecycle: geometry file handling, keystroke
generation, subprocess execution, output parsing, and result
post-processing.

## Current State

| Component | Location | Uses asb.AVL? |
|---|---|---|
| `_run_avl()` | `app/api/utils.py:48` | Yes — `asb.AVL(...)` + `.run()` |
| `AVLWithStripForces` | `app/services/avl_strip_forces.py:182` | Yes — subclasses `asb.AVL` |
| `_build_control_run_command()` | `app/api/utils.py:37` | Indirect (calls `build_control_deflection_commands`) |
| `build_control_deflection_commands()` | `app/services/avl_strip_forces.py:156` | No — standalone |
| `parse_strip_forces_output()` | `app/services/avl_strip_forces.py:133` | No — standalone |

## Target State

| Component | Location | asb.AVL? |
|---|---|---|
| `AVLRunner` | `app/services/avl_runner.py` (NEW) | No |
| `parse_stability_output()` | `app/services/avl_runner.py` (NEW) | No |
| `_run_avl()` | `app/api/utils.py` | Uses `AVLRunner` |
| `analyze_*_strip_forces()` | `app/services/analysis_service.py` | Uses `AVLRunner` |
| `AVLWithStripForces` | DELETED | — |
| `_build_control_run_command()` | DELETED | — |
| `build_control_deflection_commands()` | `app/services/avl_strip_forces.py` | Unchanged |
| `parse_strip_forces_output()` | `app/services/avl_strip_forces.py` | Unchanged |

## Architecture

```python
class AVLRunner:
    """Standalone AVL runner — replaces asb.AVL for all AVL operations."""
    
    def __init__(
        self,
        airplane: asb.Airplane,
        op_point: asb.OperatingPoint,
        xyz_ref: list[float],
        avl_command: str | None = None,
        timeout: float = 30,
        working_directory: str | None = None,
    ): ...
    
    def run(
        self,
        avl_file_content: str,
        control_overrides: dict[str, float] | None = None,
        include_strip_forces: bool = False,
    ) -> dict:
        """Full AVL run cycle.
        
        1. Write geometry file to working directory
        2. Build keystroke sequence (OPER, control deflections, x, st, [fs], quit)
        3. Run AVL subprocess with stdin keystrokes
        4. Parse stability output file
        5. Optionally parse strip forces from stdout
        6. Post-process: lowercase keys, strip "tot" suffix, compute derived quantities
        """
```

### Key Design Decisions

1. **Single `run()` method** with `include_strip_forces` flag — simpler API than separate methods.
2. **Geometry file is always provided as string** — caller is responsible for building it (via `build_avl_geometry_file()` or user-provided content). AVLRunner never calls `asb.AVL.write_avl()`.
3. **Reimplements `parse_unformatted_data_output`** as `parse_stability_output()` — eliminates the last `asb.AVL` dependency. Same logic: scan for ` = ` identifiers, extract key-value pairs.
4. **Post-processing moved into AVLRunner** — the `_post_process_results()` logic from `AVLWithStripForces` becomes a private method on AVLRunner.
5. **Prepared for trim (#418)** — accepts optional `extra_keystrokes` for future indirect constraint support, but doesn't implement trim logic.

### Keystroke Sequence

```
# Standard analysis:
OPER                           # Enter OPER mode
d1 d1 <deflection>            # Control deflection commands (one per surface)
...
x                              # Execute analysis
st                             # Write stability output to file
<output_filename>
o                              # Overwrite if exists

# If include_strip_forces:
fs                             # Print strip forces to stdout

                               # Empty lines to clear prompts
quit                           # Exit AVL
```

## TDD Task Breakdown

### Task 1: Stability output parser
**Files:** `app/services/avl_runner.py`, `app/tests/test_avl_runner.py`

RED: Test `parse_stability_output()` with sample AVL output text.
GREEN: Implement parser — scan for ` = `, extract key-value pairs.
REFACTOR: Clean up.

### Task 2: AVLRunner keystroke generation  
**Files:** `app/services/avl_runner.py`, `app/tests/test_avl_runner.py`

RED: Test `_build_keystrokes()` — correct sequence for airplane with control surfaces.
GREEN: Implement keystroke builder using `build_control_deflection_commands()`.
REFACTOR: Clean up.

### Task 3: AVLRunner post-processing
**Files:** `app/services/avl_runner.py`, `app/tests/test_avl_runner.py`

RED: Test `_post_process_results()` — lowercase, "tot" stripping, derived quantities.
GREEN: Move post-processing from `AVLWithStripForces` into AVLRunner.
REFACTOR: Clean up.

### Task 4: AVLRunner.run() integration (mocked subprocess)
**Files:** `app/services/avl_runner.py`, `app/tests/test_avl_runner.py`

RED: Test full `run()` cycle with mocked subprocess.
GREEN: Wire together: write geometry, build keystrokes, run subprocess, parse, post-process.
REFACTOR: Clean up.

### Task 5: Replace _run_avl() in utils.py
**Files:** `app/api/utils.py`

RED: Existing tests should still pass.
GREEN: Replace `_run_avl()` implementation to use `AVLRunner`.
REFACTOR: Remove `_build_control_run_command()`.

### Task 6: Replace AVLWithStripForces in analysis_service.py
**Files:** `app/services/analysis_service.py`

RED: Existing tests should still pass.
GREEN: Update `analyze_airplane_strip_forces()` and `analyze_wing_strip_forces()` to use AVLRunner.
REFACTOR: Clean up.

### Task 7: Remove AVLWithStripForces class
**Files:** `app/services/avl_strip_forces.py`

Remove the `AVLWithStripForces` class. Keep `build_control_deflection_commands()` and `parse_strip_forces_output()` — both are still used by AVLRunner.

### Task 8: Verify all existing tests pass
Run full test suite to ensure no regressions.

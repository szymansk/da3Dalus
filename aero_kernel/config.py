"""The kernel configuration: the numeric tolerances of the kernel's own self-checks (gh-1299).

The source is ``config.yaml`` in the canon root (maintainer, 2026-10-26: "eine config.yaml, die aber
nicht vom Anwender überschrieben werden kann"). The importer carries it into the canon model
(``namespaces.calc.config``) as one closed set of keys, validated by
:class:`aero_kernel.canon.model.KernelConfig`: a missing or an unknown key is a finding of the import.
Because it lives in ``canon_model.json`` it is part of the content hash and of the build digest, so a
changed value invalidates every cache entry, and the kernel runs without reading YAML (Q12).

Nothing a caller supplies reaches it: it is no ``AircraftInput`` field, no rule parameter and no
value slug. The adapters report the values as solver settings of their tool.
"""

from aero_kernel.canon.model import ConfigValue, KernelConfig

__all__ = ["ConfigValue", "KernelConfig", "config"]


def config() -> KernelConfig:
    """The configuration of the shipped canon model.

    Returns:
        The tolerances; shared with the build, so a call is a lookup.

    Raises:
        RuntimeError: If the shipped model states none (a defect of the import).
    """
    from aero_kernel.build import shipped_build  # build imports the formulas

    found = shipped_build().model.namespaces["calc"].config
    if found is None:
        msg = "the canon model states no kernel configuration (config.yaml)"
        raise RuntimeError(msg)
    return found

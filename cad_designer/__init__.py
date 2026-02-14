import warnings

try:
    from pyparsing import PyparsingDeprecationWarning
except Exception:  # pragma: no cover - fallback when pyparsing is unavailable
    PyparsingDeprecationWarning = None

if PyparsingDeprecationWarning is not None:
    warnings.filterwarnings(
        "ignore",
        category=PyparsingDeprecationWarning,
        module=r"cadquery\..*",
    )
    warnings.filterwarnings(
        "ignore",
        category=PyparsingDeprecationWarning,
        module=r"ezdxf\.queryparser",
    )

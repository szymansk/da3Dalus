---
paths:
  - "**/*.py"
  - "**/*.sh"
---

# Security Rules

## Never Access Sensitive Files

Do NOT read, write, or edit:
- `.env` files
- `*.pem`, `*.key` files
- `*secret*`, `*credential*`, `*password*` files
- Cloud credentials (`.azure/`, `~/.aws/credentials`, `~/.config/gcloud/`)
- API keys or tokens

Use `.env.example` for documenting required environment variables with
placeholder values.

## Command Execution Safety

When shelling out from Python, never pass unsanitized user input through
a shell:

```python
import subprocess

# GOOD — arguments are separate, no shell interpretation
subprocess.run(["git", "clone", repo_url], check=True)

# BAD — shell=True with interpolation allows command injection
subprocess.run(f"git clone {repo_url}", shell=True, check=True)
```

Rules:
- Pass `args` as a list. Never interpolate untrusted values into a string.
- Avoid `shell=True`. If you must use it, whitelist inputs.
- Validate paths before file operations (see below).
- External binaries in this repo (e.g. `Avl/bin/avl`) should be invoked
  with explicit absolute paths from config, not from `PATH` lookup on
  user input.

## Path Safety

- Always normalise user-supplied paths with `pathlib.Path().resolve()`
  or `os.path.realpath()`.
- Reject any path that escapes the allowed base directory.
- Do not trust filenames that come from request bodies or query strings.

```python
from pathlib import Path

BASE_DIR = Path("/app/exports").resolve()

def safe_join(user_path: str) -> Path:
    candidate = (BASE_DIR / user_path).resolve()
    if BASE_DIR not in candidate.parents and candidate != BASE_DIR:
        raise ValueError("path outside allowed directory")
    return candidate
```

`os.path.commonpath([base, candidate])` is an acceptable alternative for
the containment check.

## Credential Storage

- Secrets live in `.env` (gitignored) and are read via
  `pydantic-settings` in `app/core/config.py`.
- Never log credentials, connection strings, or request bodies that may
  contain them.
- Clear sensitive values after use; do not store them on long-lived
  objects unless necessary.
- For Azure resources, prefer managed identity / Azure SDK credential
  providers over embedding SAS tokens or shared-access keys in code.

## Output Sanitization

- Mask secrets in logs and error messages (never echo the full value of
  an env var in a stack trace).
- Avoid returning raw filesystem paths in error responses for sensitive
  files.
- Sanitize any user input before rendering it in HTML, JSON error
  messages, or log lines (control characters, newlines).
- FastAPI endpoints should return structured Pydantic error responses
  from `app/core/exceptions.py`, not raw exception text.

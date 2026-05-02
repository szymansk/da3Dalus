# eslint-plugin-sonarjs + Pre-commit Hook

**Issue:** #377
**Date:** 2026-05-02

## Goal

Catch SonarQube-style issues locally before they reach the server by
integrating `eslint-plugin-sonarjs` into the frontend ESLint config
and enforcing it via a Husky pre-commit hook.

## Acceptance Criteria

- [ ] `eslint-plugin-sonarjs` is a devDependency in `frontend/package.json`
- [ ] `eslint.config.mjs` includes the sonarjs `recommended` preset
- [ ] All sonarjs rules run as errors (recommended default)
- [ ] `sonarjs/no-clear-text-protocols` is disabled (localhost URLs are intentional)
- [ ] `sonarjs/publicly-writable-directories` is disabled (/tmp refs are harmless)
- [ ] `coverage/` directory is added to globalIgnores
- [ ] All existing violations (~31) are fixed
- [ ] `husky` and `lint-staged` are devDependencies
- [ ] `.husky/pre-commit` hook runs lint-staged
- [ ] `prepare` script in package.json installs Husky on `npm install`
- [ ] lint-staged runs `eslint --max-warnings=0` on staged `*.{ts,tsx,js,jsx}` files
- [ ] `npm run lint` passes with zero errors

## Design

### 1. ESLint Configuration

**File:** `frontend/eslint.config.mjs`

Add `eslint-plugin-sonarjs` using its flat-config recommended preset:

```javascript
import sonarjs from "eslint-plugin-sonarjs";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  sonarjs.configs.recommended,
  {
    rules: {
      "sonarjs/no-clear-text-protocols": "off",
      "sonarjs/publicly-writable-directories": "off",
    },
  },
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    "coverage/**",
  ]),
]);
```

### 2. Fix Existing Violations

48 total violations detected during audit. After disabling the two
false-positive rules (~17 hits) and ignoring `coverage/` (~1 hit),
~31 genuine violations remain:

| Rule | Count | Fix |
|------|-------|-----|
| `no-nested-conditional` | 8 | Extract nested ternaries into variables or early returns |
| `no-unused-vars` / `no-dead-store` | 12 | Remove unused variables and dead assignments |
| `cognitive-complexity` | 3 | Extract helpers to reduce function complexity |
| `public-static-readonly` | 3 | Add `readonly` modifier to public static properties |
| `slow-regex` | 2 | Rewrite regexes to avoid catastrophic backtracking |
| `unused-import` / `void-use` | 2 | Remove unused import, replace void operator |

### 3. Husky + lint-staged

**New devDependencies:**
- `husky` (latest)
- `lint-staged` (latest)

**package.json changes:**

```json
{
  "scripts": {
    "prepare": "cd .. && husky frontend/.husky"
  },
  "lint-staged": {
    "*.{ts,tsx,js,jsx}": "eslint --max-warnings=0"
  }
}
```

The `cd ..` is required because `frontend/` is a subdirectory of the
git root. Husky must install the git hook from the repo root, pointing
to `frontend/.husky/` for the hook scripts.

**New file:** `frontend/.husky/pre-commit`

```sh
cd frontend && npx lint-staged
```

The `cd frontend` ensures lint-staged runs in the correct directory
where `node_modules` and the ESLint config live.

`--max-warnings=0` ensures even warnings block commits.
`prepare` script auto-installs hooks on `npm install`.

### 4. Ignored / Suppressed Rules

| Rule | Disposition | Rationale |
|------|------------|-----------|
| `sonarjs/no-clear-text-protocols` | Disabled globally | Frontend uses `http://localhost` for local dev API calls; HTTPS is enforced in deployment |
| `sonarjs/publicly-writable-directories` | Disabled globally | References are in coverage tooling, not application code |

### 5. Out of Scope

- Python/backend pre-commit hooks (separate concern)
- Root-level hook orchestration
- Custom sonarjs rule tuning beyond the two suppressions

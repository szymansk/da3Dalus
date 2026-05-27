#!/usr/bin/env node
/**
 * gh-564: List every Gherkin step phrase in ``e2e/features/*.feature`` that
 * has no matching ``Given/When/Then("phrase", …)`` in
 * ``e2e/steps/**\/*.ts``. ``bddgen`` itself only prints the first 10
 * snippets (then says "...and N more"), so we cannot drive a CI gate
 * off its stdout — this script walks the same inputs and prints the
 * full list grouped by feature, plus an exit code of 1 when there is at
 * least one missing step.
 *
 * Usage:
 *
 *     npm run bdd:missing             # human-readable report
 *     npm run bdd:missing -- --json   # machine-readable (CI gate)
 *
 * Why grep + regex and not the playwright-bdd Node API: the API
 * surface for "give me a structured list" isn't documented, the
 * cli's ``--format json`` is also undocumented in v8.5.0, and the
 * regex pass below is robust enough for the project's modest step
 * library (~60 steps).
 */

import { promises as fs } from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND_ROOT = path.resolve(__dirname, "..", "..");
const STEPS_DIR = path.join(FRONTEND_ROOT, "e2e", "steps");
const FEATURES_DIR = path.join(FRONTEND_ROOT, "e2e", "features");

// ------------------------------------------------------------------
// Phrase normalization — ``"foo"`` → ``{string}``, ``42`` → ``{int}``,
// ``0.162`` → ``{float}``. Matches the cucumber-expression placeholders
// the project's existing steps already use.
// ------------------------------------------------------------------
const STRING_RE = /"[^"]*"/g;
const FLOAT_RE = /\b\d+\.\d+\b/g;
const INT_RE = /\b\d+\b/g;

function normalize(phrase) {
  return phrase
    .replace(STRING_RE, "{string}")
    .replace(FLOAT_RE, "{float}")
    .replace(INT_RE, "{int}");
}

// ------------------------------------------------------------------
// Step-definition discovery — match ``Given("...", ...)`` /
// ``When(...)`` / ``Then(...)`` literals in step .ts files. Backticks
// not supported by playwright-bdd but accepted here for robustness.
// ------------------------------------------------------------------
const STEP_DEF_RE = /(?:Given|When|Then)\(\s*([`'"])((?:[^\\]|\\.)*?)\1/g;

async function collectExistingSteps() {
  const out = new Set();
  const files = await fs.readdir(STEPS_DIR);
  for (const fn of files) {
    if (!fn.endsWith(".ts")) continue;
    const txt = await fs.readFile(path.join(STEPS_DIR, fn), "utf8");
    let m;
    while ((m = STEP_DEF_RE.exec(txt)) !== null) {
      out.add(m[2]);
    }
  }
  return out;
}

// ------------------------------------------------------------------
// Feature-file walker — yield (file, lineNumber, phrase) for every
// Gherkin step line. The regex uses a possessive-style ``\S`` lead +
// greedy ``.*`` (instead of lazy ``.+?\s*$``) to avoid the
// super-linear backtracking sonarjs flags on lazy-quantifier-then-
// trailing-whitespace patterns.
// ------------------------------------------------------------------
const GHERKIN_STEP_RE = /^\s+(?:Given|When|Then|And|But)\s+(\S.*)$/;

async function* iterFeatureSteps() {
  const files = await fs.readdir(FEATURES_DIR);
  for (const fn of files) {
    if (!fn.endsWith(".feature")) continue;
    const txt = await fs.readFile(path.join(FEATURES_DIR, fn), "utf8");
    const lines = txt.split("\n");
    for (let i = 0; i < lines.length; i++) {
      const m = lines[i].match(GHERKIN_STEP_RE);
      if (m) yield { file: fn, line: i + 1, phrase: m[1].trimEnd() };
    }
  }
}

async function collectMissing() {
  const existing = await collectExistingSteps();
  const existingNormalized = new Set();
  for (const p of existing) existingNormalized.add(normalize(p));

  const byFile = new Map();
  for await (const { file, line, phrase } of iterFeatureSteps()) {
    if (existing.has(phrase) || existingNormalized.has(normalize(phrase))) continue;
    if (!byFile.has(file)) byFile.set(file, []);
    byFile.get(file).push({ line, phrase });
  }
  return byFile;
}

function totalCount(byFile) {
  let total = 0;
  for (const arr of byFile.values()) total += arr.length;
  return total;
}

function printJson(byFile, total) {
  const payload = {
    total,
    by_file: Object.fromEntries(
      [...byFile.entries()].map(([f, arr]) => [f, arr]),
    ),
  };
  process.stdout.write(JSON.stringify(payload, null, 2) + "\n");
}

function printHuman(byFile, total) {
  if (total === 0) {
    console.log("✓ all feature steps have implementations");
    return;
  }
  console.log(`✗ ${total} missing step definitions across ${byFile.size} feature(s):\n`);
  for (const [f, arr] of [...byFile.entries()].sort()) {
    console.log(`  ${f}: ${arr.length} missing`);
    for (const { line, phrase } of arr) {
      console.log(`    line ${line}: ${phrase}`);
    }
    console.log("");
  }
  console.log(
    `Run \`npx -p playwright-bdd bddgen\` to get the implementation snippets.\n` +
      `See #564 + its sub-issues for the per-feature breakdown.`,
  );
}

async function main() {
  const asJson = process.argv.includes("--json");
  const byFile = await collectMissing();
  const total = totalCount(byFile);

  if (asJson) {
    printJson(byFile, total);
  } else {
    printHuman(byFile, total);
  }

  process.exit(total === 0 ? 0 : 1);
}

main().catch((err) => {
  console.error(err);
  process.exit(2);
});

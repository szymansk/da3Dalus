---
name: supercycle-ticket
description: "Ticket intake: brainstorm with user, explore codebase, create refined GH Issue — read-only, no code changes"
argument-hint: "<free-form description of the idea, feature, bug, or task>"
---

# /supercycle-ticket — Ticket Creation & Refinement

Argument: **$ARGUMENTS**

Brainstorm an idea into a refined GH Issue. This skill is
**read-only on the repository** — the only external writes are
to GitHub Issues via `gh`.

For implementation after ticket creation, use:
- `/supercycle-work` — brainstorm + implement + merge
- `/supercycle-implement` — skip brainstorming, start coding

---

<gather>

<step name="ask-issue-type">
Present a selector — do NOT auto-detect:

> **What type of issue is this?**
> 1. **Feature** — new capability or enhancement
> 2. **Bug** — something is broken
> 3. **Task** — infra, docs, CI/CD, refactoring, tooling

Map the choice to:

| Choice | Label | Template |
|--------|-------|----------|
| Feature | `enhancement` | `.github/ISSUE_TEMPLATE/feature.md` |
| Bug | `bug` | `.github/ISSUE_TEMPLATE/bug.md` |
| Task | `task` | `.github/ISSUE_TEMPLATE/task.md` |
</step>

<step name="ask-brainstorming-depth">
> **How deep should we go?**
> 1. **Light** — analyze codebase, draft ticket, ask your approval
> 2. **Medium** — + propose 2-3 approaches with trade-offs
> 3. **Full** — + multiple clarifying questions, iterative refinement
</step>

<step name="question-protocol">
Any question from agent to user — including clarifying questions
during brainstorming — MUST be posted to the GH Issue first using
`post-question-comment` from `../supercycle-common/tracking.md`.
Post to GH, then ask in conversation. Remove `has-question` label
after answer.

Note: If no GH Issue exists yet (free-text input), questions are
asked in conversation only until the issue is created in TRACK.
</step>

</gather>

---

<delegate>

<phase name="brainstorming" order="1">
<description>Explore the problem space and produce a design spec.</description>

<step name="download-linked-assets">
If the user provided images (wireframes, screenshots, diagrams) or
documents (PDFs, design files) as part of their input, use `WebFetch`
to download each, then `Read` to view them. These visual assets are
critical context for brainstorming.
</step>

<step name="invoke-brainstorming">
Invoke `/brainstorming` with:
- The user's full description text from `$ARGUMENTS`
- Downloaded images/documents as visual context
- The chosen issue type and brainstorming depth
- Instruction that output is for a GH Issue, not implementation
</step>

The brainstorming skill handles:
- Codebase exploration *Invoke agent `@code-base-explorer`* (uses Serena LSP tools)
- Clarifying questions (one at a time)
- 2-3 approaches with trade-offs and recommendation
- Design presentation in sections with user approval
- Spec writing to `docs/superpowers/specs/`
</phase>

</delegate>

---

<track>

After brainstorming produces a spec:

<step name="create-gh-issue">
Use the spec output to fill the chosen GH Issue template:
```bash
gh issue create \
  --title "<type-prefix>: <concise title>" \
  --body "<spec formatted as issue template>" \
  --label "<type-label>"
```
</step>

<step name="post-step-comment-and-labels">
Commit and push the spec file before posting the comment.
Use `post-step-comment` from `../supercycle-common/tracking.md`:
- **Label:** `has-spec`
- **Body:** Full spec / acceptance criteria from brainstorming output,
  with a `github-blob-link` to the spec file on the current branch
</step>

<step name="set-status">
Use `rotate-status` from `../supercycle-common/tracking.md`:
- **New status:** `status:ready`
</step>

<step name="report">
> "Created issue #N: <title> — <url>"
>
> **Next steps:**
> - `/supercycle-work #N` — brainstorm implementation + build
> - `/supercycle-implement #N` — skip brainstorming, start coding
</step>

</track>

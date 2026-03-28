---
name: document-changes
description: Document completed work across all relevant project files. Use when the user says "document this", "make sure this is documented", "update the docs", or after completing a task/feature that touches multiple areas. Ensures nothing is missed.
user-invocable: true
argument-hint: task-file-or-description
---

# Document Changes

You are documenting completed work for DevPulse. Your job is to ensure every relevant documentation surface is updated accurately and completely.

## Documentation Targets

These are the files and locations that may need updating. **Check every one** — skip only if genuinely unaffected.

| Target | Path | What goes here |
|--------|------|----------------|
| **Task file** | `.claude/tasks/**/*.md` | Mark status `completed`, check off deliverables, add Files Created/Modified, note any deviations from original spec |
| **CLAUDE.md** | `CLAUDE.md` (root) | Architecture docs, file tree, patterns/conventions, env vars, API endpoint tables. This is the primary codebase reference. |
| **API reference** | `docs/API.md` | Full request/response contracts for any new or changed endpoints |
| **Spec docs** | `DEVPULSE_SPEC.md`, `DEVPULSE_MANAGEMENT_FEATURES.md` | Only if the implementation diverged from spec or spec needs correction |
| **README** | `README.md` | Only if setup steps, env vars, or user-facing features changed |
| **Env example** | `.env.example` | Any new environment variables |

## Process

### Step 1: Assess scope

Determine if this is a **small change** (1-3 files, single concern) or a **large change** (4+ files, multiple concerns, new patterns, new API endpoints, new packages).

- **Small change**: Proceed directly — you can evaluate all targets yourself.
- **Large change**: Launch subagents in parallel to ensure thorough coverage:

```
Agent 1 (Explore): "Identify all files created or modified in the current working state
  that relate to [feature]. List each file with a one-line summary of what changed."

Agent 2 (Explore): "Check CLAUDE.md, docs/API.md, and DEVPULSE_SPEC.md — identify any
  sections that reference [affected area] and may need updating."
```

Wait for agent results before writing documentation.

### Step 2: Gather context

Read the current state of each documentation target to understand what's already documented. Don't duplicate. Don't contradict.

Key things to capture:
- **What was built** — components, endpoints, services, models
- **What was added** — new packages, new files, new patterns
- **What changed** — modified behavior, updated conventions
- **What was decided** — design choices, trade-offs, deviations from spec

### Step 3: Update each target

Work through the targets in this order:

#### 1. Task file (if one exists for this work)
- Set `## Status` to `completed`
- Convert deliverables to checkboxes and check them off: `- [x]`
- Add `## Files Created` and `## Files Modified` sections with paths
- Add `## Packages Added` if any new dependencies
- Note any deliverables that were skipped or changed from the original spec, with rationale

#### 2. CLAUDE.md
This is the most critical target. It's the source of truth for how the codebase works.

Update these sections as needed:
- **File tree** (`### Frontend Layout` / `### Backend Layout`): Add new files/directories with one-line descriptions
- **Patterns and Conventions** (`### Frontend patterns` / `### Backend patterns`): Document new patterns so future work follows them
- **API Structure** tables: Add new endpoint groups or endpoints
- **Environment Variables** table: Add new env vars with defaults and purpose
- **Tech Stack**: Only if a significant new dependency was added (not minor utils)

Rules:
- Match the existing style — terse, factual, no marketing language
- One bullet per pattern, starting with bold label
- File tree entries use comments like `# one-line description`

#### 3. docs/API.md
Only if API endpoints were added or changed:
- Add full request/response contracts
- Include query parameters, path parameters, request body schema
- Include example responses
- Match the existing format in the file

#### 4. Other targets
- `.env.example` — add new vars with placeholder values and comments
- `README.md` — only for user-facing changes (new setup steps, new features in the feature list)
- Spec docs — only to correct inaccuracies, not to add implementation details

### Step 4: Verify

After all updates, do a final scan:
- Grep for any "TODO" or "TBD" you may have left
- Confirm no contradictions between CLAUDE.md and the actual code
- Confirm task file status is `completed` if applicable

## What NOT to document

- Implementation details that are obvious from reading the code
- Git history (commit messages already capture this)
- Temporary debugging steps or workarounds
- Anything already covered by inline code comments

## Tone

- Factual, terse, no filler
- Present tense ("Uses sonner for toasts" not "We added sonner for toasts")
- Match the style of the existing documentation in each file

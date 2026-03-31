# N1-02: "Ask About Your Team" Conversational AI

> Priority: Notion-inspired | Effort: Medium | Impact: High (Differentiation)
> Origin: Notion analysis — Notion AI lets users ask questions about their workspace in natural language

## Context

DevPulse has structured AI analysis (predefined types: developer analysis, team health, 1:1 prep) but no freeform query capability. Notion AI popularized the pattern of asking natural language questions and getting synthesized answers from your own data.

A conversational "Ask about your team" feature where a manager types a question and gets an answer grounded in actual DevPulse metrics would be genuinely unique in the self-hosted engineering intelligence market. No competitor offers this.

## Requirements

### Backend
1. New endpoint: `POST /ai/ask` accepting `{ question: string, scope?: { team?: string, developer_id?: int, repo_id?: int } }`
2. Query pipeline:
   - Parse the question to determine which metrics are relevant (cycle time, workload, collaboration, DORA, etc.)
   - Fetch the relevant metrics using existing service functions (stats.py, collaboration.py, etc.)
   - Compose a Claude prompt with the question + structured metrics context
   - Return the AI response as `{ answer: string, metrics_used: string[], scope: object }`
3. Respect existing AI guards: feature toggle check, budget check, cooldown
4. Store in `ai_analyses` with `analysis_type="question"` for audit/caching
5. Rate limit: reuse existing AI cooldown mechanism

### Frontend
1. New component: `TeamAskBox` — a text input with submit button, placed on:
   - Executive Dashboard (scoped to org)
   - Developer Detail page (scoped to that developer)
   - Optionally: a standalone `/admin/ai/ask` page
2. Response rendered as Markdown (use existing Markdown renderer or simple `prose` styling)
3. Show which metrics were consulted (chips/tags below the answer)
4. Loading state with streaming feel (typing indicator or skeleton)
5. History of recent questions (from `ai_analyses` where `type="question"`)

### Example Questions & Expected Behavior
- "Why is cycle time increasing on the platform team?" → Fetches team cycle time trends, identifies outlier PRs, checks workload distribution
- "Who should I pair with Alex for the next project?" → Fetches collaboration scores, works-with data, complementary skills
- "Are there any bus factor risks right now?" → Fetches collaboration matrix, identifies single-reviewer repos
- "How is the backend team doing on DORA metrics?" → Fetches DORA for backend team, compares to thresholds

## Implementation Notes

- The metric-gathering step is the core challenge. Start simple: include a broad set of team/developer stats as context rather than trying to parse which specific metrics the question needs. Claude can ignore irrelevant context.
- Context window budget: gather summary stats (not raw PR lists). The existing service functions already return aggregated data.
- Consider a two-phase approach: v1 sends all available summary stats as context (brute force but works), v2 adds intelligent metric selection.

## Acceptance Criteria

- [ ] Manager can type a natural language question and get a data-grounded answer
- [ ] Answer references actual metrics from the system (not hallucinated numbers)
- [ ] AI guards respected (feature toggle, budget, cooldown)
- [ ] Question and answer stored in ai_analyses for audit
- [ ] Scope filtering works (team, developer, repo)
- [ ] Recent question history visible

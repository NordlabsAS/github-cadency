# N1-01: Markdown/Clipboard Export for AI Briefs

> Priority: Notion-inspired | Effort: Low | Impact: High
> Origin: Notion analysis — managers paste 1:1 prep into Notion/Google Docs for meetings

## Context

DevPulse generates AI-powered 1:1 prep briefs and team health analyses via the Claude API. These results are rendered in structured views (`AnalysisResultRenderer`, `OneOnOnePrepView`) but are trapped inside the app. Managers typically take notes in Notion, Google Docs, or similar — they need a way to get DevPulse data out.

Notion's lesson: the best analytics tool is the one that fits into existing workflows. A "Copy as Markdown" button is the lowest-friction bridge.

## Requirements

### Backend
- No backend changes needed. The AI analysis result is already stored as JSONB and returned via the API.

### Frontend
1. Add a "Copy as Markdown" button to:
   - `OneOnOnePrepView` (1:1 prep brief renderer)
   - `AnalysisResultRenderer` (general AI analysis results)
   - Team health check view
2. Button copies a well-formatted Markdown string to the clipboard:
   - Headings for each section
   - Bullet points for insights, action items, risks
   - Metrics formatted as inline code or tables
   - Developer names, date range, and generation timestamp included
3. Use `navigator.clipboard.writeText()` with a sonner toast on success
4. Optional: "Download as .md" variant for longer reports

### UX
- Small icon button (ClipboardCopy from Lucide) in the top-right of each result card
- Tooltip: "Copy as Markdown"
- Toast: "Copied to clipboard" (success) / "Failed to copy" (error)

## Implementation Notes

- Create a `formatAnalysisAsMarkdown(result, analysisType)` utility function that switches on analysis type and produces clean Markdown
- The JSONB structure varies by `analysis_type` — inspect existing result shapes in `ai_analysis.py` and the frontend renderers
- Keep formatting simple — no HTML, no custom syntax. Plain Markdown that pastes cleanly into Notion, GitHub, or any editor.

## Acceptance Criteria

- [ ] 1:1 prep brief can be copied as Markdown with one click
- [ ] Team health analysis can be copied as Markdown
- [ ] General AI analysis results can be copied as Markdown
- [ ] Markdown output is clean and readable when pasted into Notion or GitHub
- [ ] Toast notification confirms copy success

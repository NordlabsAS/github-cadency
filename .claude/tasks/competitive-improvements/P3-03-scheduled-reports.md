# P3-03: Scheduled Report Exports

> Priority: 3 (Enterprise Readiness) | Effort: Medium | Impact: Medium
> Competitive gap: No PDF export, shareable links, email digests, or Slack summaries.

## Context

DevPulse has no way to distribute insights outside the dashboard. Managers can't attach engineering reports to board decks, share weekly summaries with stakeholders who don't have DevPulse access, or receive automated digests.

## What to Build

### Report Types

1. **Executive Summary** — key metrics, DORA status, investment allocation, team health
2. **Team Weekly Digest** — cycle time, PR throughput, review quality, workload balance, notable items
3. **Developer Summary** — individual metrics for 1:1 prep (extends existing AI 1:1 prep)
4. **Custom Report** — admin picks which sections/metrics to include

### Export Formats

- **PDF** — for board decks, email attachments, archival
- **HTML email** — for scheduled email delivery
- **Slack message** — formatted summary (if P1-02 Slack integration exists)
- **JSON** — for external system consumption

### Scheduling

- Configurable schedule per report (daily, weekly on Monday, biweekly, monthly)
- Delivery channel: email, Slack channel, or just store for download
- Report history: keep generated reports for download/review

## Backend Changes

### New Model: `report_configs` table
```
id, name, report_type ("executive" | "team_weekly" | "developer" | "custom"),
schedule_cron (str — cron expression),
sections (JSONB — which sections to include for custom),
scope_type ("org" | "team" | "developer"), scope_value (str | int),
format ("pdf" | "html" | "json"),
delivery_type ("email" | "slack" | "store_only"),
delivery_target (str — email address or Slack channel),
enabled (bool), last_generated_at, created_by (FK), created_at
```

### New Model: `generated_reports` table
```
id, config_id (FK), generated_at, period_start, period_end,
format (str), file_path (str — local storage path),
file_size_bytes (int), status ("generating" | "completed" | "failed"),
error (str, nullable)
```

### New Service: `backend/app/services/reports.py`
- `generate_report(config)` — orchestrate data fetch + render
- `render_executive_pdf(data)` — build PDF with charts
- `render_team_weekly_html(data)` — HTML email template
- `render_custom_report(data, sections)` — flexible section composition
- Report data assembled from existing stats/DORA/workload/collaboration services

### PDF Generation
- Use `weasyprint` or `reportlab` for PDF rendering
- HTML template → PDF conversion (reuse React-like layouts in server-side HTML)
- Embed charts as SVG or PNG (pre-rendered server-side)

### Email Delivery
- SMTP integration (standard library `smtplib` + `email`)
- Config: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`
- HTML email with inline CSS (email-safe styling)

### Scheduler Integration
- Parse cron expressions from `report_configs`
- Add report generation jobs to APScheduler
- Dynamically update schedule when config changes

### New Router: `backend/app/api/reports.py`
- `POST /api/reports/configs` — create report schedule (admin)
- `GET /api/reports/configs` — list configured reports
- `PATCH /api/reports/configs/{id}` — update config
- `DELETE /api/reports/configs/{id}` — delete config
- `POST /api/reports/configs/{id}/generate` — trigger immediate generation
- `GET /api/reports/history` — list generated reports
- `GET /api/reports/{id}/download` — download generated report file
- `POST /api/reports/preview` — preview report without saving

## Frontend Changes

### Reports Admin Page (`/admin/reports`)
- Report config list with schedule, last generated, status
- Create/edit report dialog: type, sections, schedule, delivery
- Generate now button
- Report history with download links

### Report Preview
- In-browser preview of report (HTML render)
- PDF download button

### Quick Export Buttons
- Add "Export PDF" button to Executive Dashboard, Team Weekly views
- On-demand report generation (no schedule needed)

## Dependencies
- `weasyprint` for HTML→PDF (requires system deps: cairo, pango, gdk-pixbuf)
- OR `reportlab` for pure-Python PDF (no system deps, but less HTML-friendly)
- `jinja2` for HTML email templates (already a FastAPI dependency)

## Testing
- Unit test report data assembly for each report type
- Unit test PDF generation (verify output is valid PDF)
- Unit test email HTML rendering
- Unit test cron schedule parsing
- Test report generation with empty data (graceful handling)

## Acceptance Criteria
- [ ] Executive summary report generates as PDF
- [ ] Team weekly digest generates as HTML email
- [ ] Reports schedulable via cron (daily/weekly/monthly)
- [ ] Email delivery works via SMTP
- [ ] Slack delivery works (if Slack integrated)
- [ ] Report history with download links
- [ ] On-demand "Export PDF" from dashboard pages
- [ ] Custom report with selectable sections
- [ ] Admin-only configuration

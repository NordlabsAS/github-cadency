# P2-03: Industry Benchmark Data

> Priority: 2 (Differentiate) | Effort: Medium | Impact: Medium
> Competitive gap: LinearB has 8M+ PR benchmark dataset. Swarmia, Jellyfish, DX offer industry benchmarks. DevPulse has team-relative only.

## Context

DevPulse currently computes team-relative percentiles (how does developer X compare to the team). Managers also ask "how do we compare to the industry?" LinearB's benchmark dataset (8M+ PRs) is a major selling point.

Since DevPulse is self-hosted, it can't automatically aggregate data across instances. Two approaches: (1) ship curated industry benchmark data from published research, (2) opt-in anonymous benchmark sharing.

## What to Build

### Phase 1: Curated Industry Benchmarks (Ship with DevPulse)

**Embed published benchmark data from DORA reports, LinearB studies, and academic research:**

| Metric | P25 (Low) | P50 (Median) | P75 (High) | P90 (Elite) | Source |
|--------|-----------|--------------|------------|-------------|--------|
| PR cycle time | >7 days | 3-7 days | 1-3 days | <1 day | DORA/LinearB |
| Time to first review | >24h | 8-24h | 2-8h | <2h | LinearB |
| PR size (lines) | >1000 | 400-1000 | 100-400 | <100 | Google research |
| Review depth (comments/PR) | <0.5 | 0.5-1.5 | 1.5-3 | >3 | Industry avg |
| Deploy frequency | <1/month | 1-4/month | 1-4/week | Daily+ | DORA |
| Lead time | >6 months | 1-6 months | 1 week-1 month | <1 day | DORA |
| Change failure rate | >45% | 16-45% | 1-15% | 0-5% | DORA |
| MTTR | >6 months | 1-6 months | <1 day | <1 hour | DORA |

**Display:** Show team's position on industry benchmark bands alongside existing team-relative percentiles.

### Phase 2: Anonymous Opt-In Benchmark Sharing

**Optional feature where self-hosted instances contribute anonymized aggregate metrics:**

- Strictly opt-in (off by default, admin enables)
- Only aggregates shared (never raw data, developer names, repo names, or code)
- Data sent: team size, median cycle time, median review time, deploy frequency, etc.
- Central benchmark API (optional, community-run) aggregates and returns percentiles
- Instances can participate without exposing any identifying information

## Backend Changes

### Industry Benchmark Data (`backend/app/services/benchmarks.py`)
- `INDUSTRY_BENCHMARKS` dict with metric → percentile bands
- `get_industry_placement(metric, value)` — returns industry percentile band
- `get_team_industry_comparison(team_stats)` — compare all team metrics against industry
- Benchmark data versioned with source attribution and last-updated date
- Easy to update as new research is published

### Extend Stats Service (`backend/app/services/stats.py`)
- `get_benchmarks()` already returns team-relative percentiles
- Add `industry_placement` field to each metric in response
- New endpoint or extend existing: `/api/stats/benchmarks` includes industry data

### Schemas (`backend/app/schemas/schemas.py`)
- Add to `PercentilePlacement`:
  - `industry_band: str | None` — "elite", "high", "medium", "low"
  - `industry_percentile_approx: int | None` — approximate industry percentile
- New `IndustryBenchmarkInfo` schema with source, last_updated, bands per metric

### Phase 2: Anonymous Sharing (optional)
- New config: `BENCHMARK_OPT_IN: bool = False`
- `backend/app/services/benchmark_sharing.py`:
  - `compute_shareable_aggregates()` — compute anonymized team-level aggregates
  - `submit_to_benchmark_api(aggregates)` — POST to community benchmark endpoint
  - `fetch_community_benchmarks()` — GET latest community percentiles
- Scheduled job: monthly submission if opted in

## Frontend Changes

### Benchmarks Page Enhancement (`frontend/src/pages/insights/Benchmarks.tsx`)
- Add "Industry" tab alongside existing team-relative view
- For each metric: show team value, team percentile, **and** industry band
- Visual: horizontal bar with industry bands (colored zones) + team marker
- Tooltip: "Your team's median cycle time of 2.3 days places you in the 'High' band (industry P75)"
- Source attribution: "Based on DORA 2024 State of DevOps Report"

### Executive Dashboard Integration
- Add industry context to key metrics: "Cycle time: 2.3d (Industry: High performer)"
- DORA metrics with industry band comparison

### New Chart Component: `IndustryBenchmarkBar`
- Horizontal bar divided into 4 colored zones (low/medium/high/elite)
- Team's value shown as a marker/arrow on the bar
- Responsive, themed with CSS variables

## Data Sourcing Strategy
- Initial data from DORA State of DevOps Report (2024)
- Supplement with LinearB published benchmarks, Google Engineering Productivity research
- Clearly attribute all sources in UI
- Version benchmark data so it can be updated with new research
- All benchmark data ships with the application (no external API required for Phase 1)

## Testing
- Unit test industry placement calculation for each metric
- Unit test edge cases (value exactly on band boundary)
- Unit test benchmark data integrity (all metrics have valid bands)
- Unit test Phase 2 anonymization (ensure no PII in shared data)

## Acceptance Criteria
- [ ] Industry benchmark bands for all key metrics (cycle time, review time, PR size, DORA)
- [ ] Team values shown alongside industry bands on Benchmarks page
- [ ] Industry context added to Executive Dashboard
- [ ] Sources clearly attributed in UI
- [ ] Benchmark data versioned and easy to update
- [ ] Phase 2 opt-in sharing is strictly optional and anonymized

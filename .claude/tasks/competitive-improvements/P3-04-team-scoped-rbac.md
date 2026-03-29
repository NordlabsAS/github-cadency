# P3-04: Team-Scoped RBAC

> Priority: 3 (Enterprise Readiness) | Effort: Medium | Impact: Medium
> Competitive gap: DevPulse has binary admin/developer roles. Enterprises need team-scoped access control.

## Context

Current RBAC is two-tier: `admin` (full access) and `developer` (own data only). This doesn't scale. In a 100+ person org, you need:
- Engineering managers who see their team's data but not other teams'
- Tech leads who can manage their team's goals and working agreements
- Directors who see multiple teams but can't change system config

## What to Build

### Role Hierarchy

| Role | Scope | Can See | Can Modify |
|------|-------|---------|------------|
| `super_admin` | Org | Everything | System config, integrations, all teams |
| `admin` | Org | Everything | Team config, goals, reports (not system config) |
| `team_lead` | Team(s) | Own team(s) + org-level aggregates | Team goals, agreements, reports for own team |
| `developer` | Self | Own data + team aggregates (anonymized) | Own goals |
| `viewer` | Configurable | Read-only access to assigned teams/org | Nothing |

### Scope Model

```
Role + Scope = Permission
- super_admin + org → full access
- team_lead + [Team A, Team B] → full access for those teams
- viewer + org → read-only for everything
- viewer + [Team A] → read-only for Team A only
```

### Key Access Rules

- **Org-level stats** (executive dashboard, DORA): visible to admin+ and team_leads (for their teams' contribution)
- **Team-level stats**: visible to team members + team_lead + admin+
- **Developer detail**: visible to the developer themselves + their team_lead + admin+
- **AI analysis**: triggerable by team_lead+ for their team, admin+ for any
- **Configuration** (sync, integrations, SSO): super_admin only
- **Working agreements**: createable by team_lead for their team, admin+ for any
- **Reports**: team_lead can create for their team, admin+ for any

## Backend Changes

### Model Changes

**`developers` table updates:**
- Rename `app_role` → `role` with expanded enum: `super_admin`, `admin`, `team_lead`, `developer`, `viewer`
- Migration: existing `admin` → `super_admin`, existing `developer` → `developer`

**New Model: `role_scopes` table:**
```
id, developer_id (FK), scope_type ("org" | "team"),
scope_value (str, nullable — team name for team scope),
granted_by (FK developers), granted_at
```

### Auth Updates (`backend/app/api/auth.py`)
- `get_current_user()` returns user with resolved scopes
- New helpers:
  - `require_role(min_role)` — check role hierarchy
  - `require_team_access(team_name)` — check user has access to specific team
  - `can_view_developer(viewer, target_developer)` — permission check
  - `can_modify_team(user, team_name)` — write access check

### API Route Updates
- All stat endpoints: filter results by user's scope
- Team endpoints: return 403 if user doesn't have team access
- Developer detail: return 403 if not self/team_lead/admin
- Config endpoints: require super_admin
- Goals/agreements: scope-aware creation and viewing

### Schemas
- `AuthUser` extended with `scopes: list[RoleScope]`
- New `RoleScopeCreate`, `RoleAssignment` schemas

### New Router: `backend/app/api/roles.py`
- `GET /api/roles/assignments` — list role assignments (admin+)
- `POST /api/roles/assign` — assign role + scope (admin+)
- `DELETE /api/roles/assignments/{id}` — revoke role scope (admin+)
- `GET /api/roles/my-scopes` — current user's role and scopes

## Frontend Changes

### Role-Aware UI
- Nav items visible based on role (team_leads see team management, not system config)
- Stats pages filter to user's accessible teams
- Admin pages gated by role (super_admin for system config)
- Team picker dropdown only shows accessible teams

### Role Management Page (`/admin/roles`)
- User list with current role and scopes
- Assign/revoke roles
- Scope configuration (org-wide or specific teams)
- Bulk role assignment

### User Role Context
- Extend `AuthUser` type with role and scopes
- `useAuth()` hook exposes role-checking helpers
- Route guards based on role

## Migration Strategy
1. Add new `role` column alongside existing `app_role`
2. Migrate data: admin → super_admin, developer → developer
3. Create `role_scopes` table
4. Add scope checks to API routes (progressive, defaulting to permissive for backward compat)
5. Drop old `app_role` column

## Testing
- Unit test role hierarchy checking
- Unit test scope-based data filtering
- Unit test permission combinations (team_lead with 2 teams, viewer with org scope)
- Test backward compatibility (existing admin users become super_admin)
- Test 403 responses for unauthorized access

## Acceptance Criteria
- [ ] 5-tier role hierarchy (super_admin, admin, team_lead, developer, viewer)
- [ ] Team-scoped access (team_leads see only their teams)
- [ ] Stats/developer data filtered by scope
- [ ] Config pages gated to super_admin
- [ ] Role management admin page
- [ ] Backward-compatible migration (existing roles preserved)
- [ ] Frontend nav adapts to user's role
- [ ] API returns 403 for unauthorized cross-team access

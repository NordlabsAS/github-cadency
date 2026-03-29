# P3-01: SSO/SAML Support

> Priority: 3 (Enterprise Readiness) | Effort: Large | Impact: High (for enterprise adoption)
> Competitive gap: All major competitors offer SSO/SAML. DevPulse has GitHub OAuth only.

## Context

Enterprise security teams require SSO/SAML for any internal tool. GitHub OAuth alone won't pass procurement at most companies with 100+ engineers. This is a hard blocker for enterprise adoption.

## What to Build

### Authentication Methods (in addition to existing GitHub OAuth)

1. **SAML 2.0 SP** — for Okta, Azure AD, OneLogin, Google Workspace
2. **OIDC (OpenID Connect)** — for Okta, Azure AD, Auth0, Keycloak
3. **SCIM provisioning** — automatic user creation/deactivation from IdP

### SAML 2.0 Flow
```
User → DevPulse Login → Redirect to IdP → IdP authenticates →
SAML assertion POST to DevPulse ACS endpoint → DevPulse validates →
JWT issued → User logged in
```

### User Mapping
- Map IdP user to DevPulse developer via email address
- Auto-create developer record on first SSO login (configurable)
- Map IdP groups to DevPulse roles (admin group → admin role)
- GitHub username linkage: prompt on first login or map via IdP attribute

## Backend Changes

### New Model: `sso_config` table
```
id, provider_type ("saml" | "oidc"),
entity_id (str), metadata_url (str, nullable), metadata_xml (text, nullable),
acs_url (str), slo_url (str, nullable),
certificate (text), private_key (text, encrypted),
attribute_mapping (JSONB — email, name, groups fields),
admin_group (str, nullable), default_role (str, default "developer"),
auto_create_users (bool, default true),
enforce_sso (bool, default false — when true, disable password/OAuth login),
created_at, updated_at
```

### New Router: `backend/app/api/sso.py`
- `GET /api/sso/metadata` — SP metadata XML for IdP configuration
- `POST /api/sso/acs` — SAML Assertion Consumer Service endpoint
- `GET /api/sso/login` — initiate SAML/OIDC login redirect
- `GET /api/sso/callback` — OIDC callback endpoint
- `GET /api/sso/config` — current SSO config (admin)
- `PUT /api/sso/config` — configure SSO (admin)
- `POST /api/sso/test` — test SSO configuration
- `GET /api/sso/slo` — Single Logout endpoint

### Auth Flow Updates (`backend/app/api/auth.py`)
- If SSO configured and `enforce_sso=True`, redirect all login to SSO
- JWT token issued after SSO validation (reuse existing JWT infrastructure)
- Add `auth_method: "github_oauth" | "saml" | "oidc"` to JWT claims

### SCIM Endpoint (`backend/app/api/scim.py`)
- SCIM 2.0 `/Users` endpoint for IdP-driven provisioning
- Create/update/deactivate developers based on IdP SCIM events
- Map SCIM groups to DevPulse teams/roles

### Config
- `SSO_ENABLED: bool = False`
- `SSO_ENFORCE: bool = False` (require SSO, disable other login methods)

## Frontend Changes

### Login Page Update
- If SSO configured: show "Sign in with SSO" button alongside GitHub OAuth
- If SSO enforced: only show SSO button
- SSO redirect flow (no password form needed)

### SSO Admin Page (`/admin/settings/sso`)
- SSO provider configuration form
- Upload IdP metadata or enter manually
- Attribute mapping configuration
- Group → role mapping
- Test SSO configuration button
- Enforce SSO toggle (with warning)
- SP metadata download for IdP setup

## Dependencies
- `python3-saml` or `pysaml2` for SAML 2.0
- `authlib` for OIDC
- `cryptography` for certificate handling

## Security Considerations
- SAML assertion signature validation (reject unsigned/tampered assertions)
- Replay attack prevention (assertion validity window, one-time use IDs)
- Certificate rotation support
- Private key encrypted at rest
- SCIM endpoint authenticated via bearer token (not public)

## Testing
- Unit test SAML assertion parsing and validation
- Unit test OIDC token verification
- Unit test user mapping (IdP → developer)
- Unit test group → role mapping
- Unit test enforce SSO mode (blocks other auth methods)
- Integration test with mock IdP

## Acceptance Criteria
- [ ] SAML 2.0 login flow works with major IdPs (Okta, Azure AD)
- [ ] OIDC login flow works
- [ ] User auto-creation on first SSO login
- [ ] IdP group → DevPulse role mapping
- [ ] Enforce SSO mode (disable other auth methods)
- [ ] SCIM user provisioning/deprovisioning
- [ ] SSO admin configuration page
- [ ] SP metadata available for IdP setup

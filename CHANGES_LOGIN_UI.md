# SIMBA Portal UI update

This package is based on the supplied Flask project and retains its existing data-source, snapshot, masking, and Databricks integration code.

## UI changes

- Added a responsive split-screen login page: SIMBA brand/tagline and feature highlights on the left; username/password and Google SSO entry point on the right.
- Added subtle motion, hover states, animated background rings, responsive layouts, and reduced-motion accessibility support.
- Removed Sample Data from the sidebar and from the Overview page. Approved sample previews are now opened from a selected dataset's detail panel inside Data Layers.
- Simplified the sidebar to Overview, Data Layers, Kafka Events, and Security & Governance.
- Added demo-only session gating, CSRF token validation, password reveal, and sign-out.

## Configure demo sign-in

Set these values in the server-side environment file (never in HTML or JavaScript):

```dotenv
SIMBA_DEMO_MODE=true
SIMBA_AUTH_MODE=none
SIMBA_DEMO_LOGIN_REQUIRED=true
SIMBA_DEMO_USERNAME=your-demo-user
SIMBA_DEMO_PASSWORD=choose-a-unique-demo-password
SIMBA_SESSION_SECRET=generate-a-long-random-secret
SIMBA_COOKIE_SECURE=false
```

Generate the session secret on the server with:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

For HTTPS set `SIMBA_COOKIE_SECURE=true`. Keep this demo-only login behind private networking and never reuse company passwords.

## Google / company SSO

The Google button is a UI entry point in demo mode and intentionally does not pretend to authenticate users. For real sign-in, configure the approved Google Workspace or company identity provider through AWS ALB OIDC (or an approved SSO solution), set `SIMBA_AUTH_MODE=alb-oidc`, and configure `SIMBA_ALB_ARN` and the ALB listener rules. Do not deploy this demo form as production authentication.

## Data warning

The app remains in demo mode until the real Databricks workspace and approved tables are configured and verified. Displayed demo figures are not live metrics.

# SIMBA Data Lake Admin Portal — refreshed branded build

Flask-based SIMBA data lake POC portal. The current focused sidebar contains Overview, Data Layers,
Kafka Events, and Security & Governance. Sample row preview is accessed from a selected table inside
Data Layers rather than through a separate sidebar item. The login page is split into a SIMBA brand/tagline
panel and a sign-in panel, with responsive layouts and reduced-motion support.

## Login behavior (read this before deploying)

* For a **private demo only**, keep `SIMBA_DEMO_MODE=true` and `SIMBA_AUTH_MODE=none`, set
  `SIMBA_DEMO_LOGIN_REQUIRED=true`, and configure `SIMBA_DEMO_USERNAME`, `SIMBA_DEMO_PASSWORD`, and
  `SIMBA_SESSION_SECRET` in the server-side environment file. Generate the session secret with:
  `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`. Do not use the example values in a shared environment.
* The demo username/password form is a prototype gate for UI review, **not production-grade identity management**.
  Keep the instance on a private network. Do not reuse corporate passwords.
* The “Continue with Google” button is a visual entry point only in demo mode. Real Google/company SSO is not
  implemented by a button in Flask: configure the approved company identity provider and AWS Application Load
  Balancer OIDC authentication first. In `SIMBA_AUTH_MODE=alb-oidc`, the ALB must authenticate requests and
  the Flask app validates its signed identity header. Do not claim Google sign-in works until this is configured.
* `SIMBA_SESSION_SECRET` must be a long random secret shared by all Gunicorn workers and must not be committed.

## How live updates work

```
Plumery Kafka/MSK ──► Databricks Structured Streaming ──► simba_data_poc.bronze.kafka_events (Delta)
                       (databricks/01_kafka_to_bronze.py)            │
                                                                     ▼
Browser ◄── SSE push (/api/stream) ◄── Flask poller ◄── Databricks SQL Warehouse (OAuth service principal)
```

* The portal never connects to Kafka directly. Databricks is the single source of truth, and the
  browser never sees a credential.
* **Fast refresh** (default 30 s) covers Kafka topic activity and Databricks job runs. **Slow refresh**
  (default 10 min) covers the table inventory, row counts, lineage and grants.
* A change is pushed to every open browser over Server-Sent Events. If SSE is blocked, the page
  falls back to polling.
* End-to-end latency is the stream trigger interval plus the fast refresh interval. For example, a
  1-minute trigger plus 30 s polling means new events show up in about 1.5 minutes.
* **Cost control:** polling keeps the SQL Warehouse awake. The poller pauses after
  `SIMBA_IDLE_PAUSE_SECONDS` with no viewers (default 15 min), so the warehouse can auto-stop.

### What the portal shows, and where it comes from

| Page | Source (live mode) |
|---|---|
| Datasets, schema, owner | `simba_data_poc.information_schema.tables / columns` |
| Row counts | `COUNT(*)` per table (views skipped; disable with `SIMBA_ROW_COUNTS=false`) |
| Last processed | `DESCRIBE HISTORY … LIMIT 1` |
| Kafka events | `simba_data_poc.bronze.kafka_events` |
| Job runs | Databricks Jobs API for `SIMBA_DATABRICKS_JOB_IDS` |
| Lineage, downstream consumers | `system.access.table_lineage`, `system.access.column_lineage` |
| Grants | `information_schema.catalog_privileges / schema_privileges / table_privileges` |
| Sample rows | Only the tables listed in `SIMBA_SAMPLE_TABLES`, max 10 rows, with column masking as a backstop |
| Descriptive text, roadmap, statuses | `content/portal.json`, maintained by the team |

In **demo mode** (`SIMBA_DEMO_MODE=true`, the default) every number is simulated and every page
says so. Keep demo mode on until a real query against the approved workspace has been verified.

## ⚠ Blockers to clear before launching anything

These are carried over from the project handover and are **not** resolved by this code:

1. **The AWS account's status.** Account `835090871452` was shown as "simba (marked to delete)".
   Confirm with the AWS administrator that it is approved before creating EC2 or ALB resources.
2. **Network.** You need an approved VPC and **private** subnet, the internal or VPN CIDR allowed to
   reach the portal, and SSM vs SSH. The private subnet also needs **outbound** access, through a NAT
   gateway or VPC endpoints, to: Ubuntu/PyPI mirrors (install only), the Databricks workspace,
   Secrets Manager, SSM, and `public-keys.auth.elb.eu-west-1.amazonaws.com`.
3. **Sign-in.** The company IdP (e.g. Entra ID) needs an OIDC app registration for the ALB, plus an
   ACM certificate for the portal hostname.
4. **Databricks.** You need the workspace URL, a SQL Warehouse, a service principal, and the grants
   in `databricks/02_portal_service_principal_grants.sql`.
5. **Kafka.** You need a network path from Databricks to MSK, confirmation of the auth mode, and
   credentials. On MSK, port 9096 is SCRAM and 9098 is IAM; the earlier "9098 + SCRAM" pairing
   needs confirming.

---

## 1. Launch the EC2 instance (console, field by field)

| Field | Value |
|---|---|
| Name | `simba-data-lake-portal-dev` |
| AMI | **Ubuntu Server 24.04 LTS** (HVM, SSD, 64-bit x86), *not* Ubuntu Pro |
| Instance type | `t3.small` (2 vCPU, 2 GiB) |
| Key pair | **Proceed without a key pair** if SSM is approved (preferred). Otherwise create `simba-portal-dev-key`, RSA, `.pem` |
| VPC | The approved VPC (confirm `vpc-0ee5ac1f60599c807` with the admin) |
| Subnet | The approved **private** subnet. Do not choose "No preference" |
| Auto-assign public IP | **Disable** |
| Firewall | **Select existing security group** → `simba-portal-ec2-sg` (below). Do **not** accept `launch-wizard-1` |
| Storage | 30 GiB, `gp3`, **Encrypted: Yes** (default KMS key unless the admin specifies one) |
| Advanced → IAM instance profile | `simba-portal-ec2-role` (below) |
| Advanced → Metadata version | **V2 only (token required)** |
| Advanced → User data | Leave blank |

### Security groups

Create these first (EC2 → Security Groups):

* **`simba-portal-alb-sg`**: inbound TCP 443 from the **approved internal/VPN CIDR only**.
* **`simba-portal-ec2-sg`**: inbound TCP 80 **from `simba-portal-alb-sg` only** (choose the security
  group as the source, not a CIDR). Add **no SSH rule** if you use SSM. If SSH is approved, allow
  TCP 22 from the admin/VPN CIDR only, **never `0.0.0.0/0`**.

### IAM role for the instance: `simba-portal-ec2-role`

* Trusted entity: EC2.
* Attach `AmazonSSMManagedInstanceCore` if you use Session Manager.
* Add this inline policy. Replace `<ACCOUNT_ID>` and use the real secret name:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "ReadPortalDatabricksSecret",
    "Effect": "Allow",
    "Action": "secretsmanager:GetSecretValue",
    "Resource": "arn:aws:secretsmanager:eu-west-1:<ACCOUNT_ID>:secret:simba/portal/databricks-*"
  }]
}
```

If the secret uses a customer-managed KMS key, also allow `kms:Decrypt` on **that key ARN only**.

### Store the Databricks service-principal secret

Run this from your own machine, logged in with SSO. **Type the secret into the console instead if
your shell history is shared.**

```bash
aws secretsmanager create-secret --region eu-west-1 --profile <your-profile> \
  --name simba/portal/databricks \
  --secret-string '{"client_id":"<application-id>","client_secret":"<oauth-secret>"}'
```

## 2. Internal ALB with sign-in (HTTPS)

1. **Target group:** type Instances, HTTP port 80, health check path `/api/health`. Register the instance.
2. **Load balancer:** Application, scheme **Internal**, the approved private subnets (two AZs),
   security group `simba-portal-alb-sg`.
3. **Listener HTTPS:443:** use the ACM certificate for the portal hostname.
   * Action 1 is **Authenticate (OIDC)**, using the IdP's issuer, authorization endpoint, token
     endpoint, user-info endpoint, client id and client secret. Scope: `openid email profile`.
   * Action 2 is **Forward** to the target group.
4. Set the **idle timeout** to 120 s. The portal sends SSE heartbeats every 15 s, so 60 s also works.
5. Add an internal DNS record for the hostname, pointing at the ALB.
6. Copy the ALB ARN into `SIMBA_ALB_ARN`. The app verifies that each request was signed by *this*
   ALB, so traffic that bypasses it is rejected.

## 3. Deploy the code onto the instance

Connect with **EC2 → Instance → Connect → Session Manager** (or SSH over VPN). Then get the
project onto the box. The usual approach is to upload the zip to an approved S3 location and pull it:

```bash
# on your machine
aws s3 cp simba-portal.zip s3://<approved-bucket>/deploy/simba-portal.zip --profile <your-profile>
```

```bash
# on the instance (the role then also needs s3:GetObject on that one object)
sudo apt-get update && sudo apt-get install -y unzip awscli || sudo snap install aws-cli --classic
cd /tmp && aws s3 cp s3://<approved-bucket>/deploy/simba-portal.zip . && unzip -o simba-portal.zip -d simba-portal
cd /tmp/simba-portal
sed -i 's/\r$//' deploy/install.sh        # in case the zip was built on Windows
sudo bash deploy/install.sh
```

The script installs Python and Nginx and creates a `simba` system user. It copies the code to
`/opt/simba-portal` read-only and creates `/etc/simba-portal/simba-portal.env` (mode 640, demo mode,
auth disabled). It then starts `simba-portal.service` and Nginx and checks `/api/health`.

Optionally, run the tests on the instance:

```bash
cd /opt/simba-portal && sudo python3 -m venv /tmp/t && sudo /tmp/t/bin/pip install -q -r requirements-dev.txt && sudo /tmp/t/bin/pytest -q
```

## 4. Databricks setup for live mode

1. **SQL Warehouse:** a Serverless or Pro warehouse, size 2X-Small, **auto-stop 10 min**. Copy the
   *Server hostname* and *HTTP path* from Connection details.
2. **Service principal and grants:** follow `databricks/02_portal_service_principal_grants.sql`.
   Also ask an account admin to enable the `system.access` schema, which is needed for lineage.
3. **Kafka → Bronze:** create the checkpoint volume once:
   `CREATE VOLUME IF NOT EXISTS simba_data_poc.bronze.checkpoints;`
   Then import `databricks/01_kafka_to_bronze.py` as a notebook and fill in the widgets.
   * Run once with trigger `availableNow` and starting offsets `earliest`. This is the initial replay of
     whatever Kafka still retains, and is **not** a full history unless Plumery confirms the retention.
   * Then create a **Job** that runs it continuously with trigger `1 minute`, or on a schedule with
     `availableNow`. Put the job id in `SIMBA_DATABRICKS_JOB_IDS`.
   * SCRAM credentials go in a secret scope (`kafka-username`, `kafka-password`):
     `databricks secrets create-scope simba-kafka`, then `databricks secrets put-secret simba-kafka kafka-username`.

## 5. Switch to live mode and turn on sign-in

```bash
sudo nano /etc/simba-portal/simba-portal.env
```

```ini
SIMBA_DEMO_MODE=false
SIMBA_AUTH_MODE=alb-oidc
SIMBA_ALB_ARN=arn:aws:elasticloadbalancing:eu-west-1:<account>:loadbalancer/app/<name>/<id>
DATABRICKS_SERVER_HOSTNAME=<workspace-host-without-https>
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/<id>
DATABRICKS_AUTH_TYPE=oauth-m2m
SIMBA_DATABRICKS_SECRET_ID=simba/portal/databricks
SIMBA_SAMPLE_TABLES=                       # only approved masked views
SIMBA_LINK_SERVICE_PORTAL=<UBA service portal URL>
SIMBA_SUPPORT_EMAIL=<support mailbox>
```

```bash
sudo systemctl restart simba-portal
journalctl -u simba-portal -n 50 --no-pager      # look for "starting in live mode"
curl -s http://127.0.0.1/api/ready                # {"ready": true, ...} once all sections load
```

If the configuration is incomplete, the service **refuses to start** and the journal lists each missing setting.

### Go-live checklist

- [ ] AWS account confirmed active and approved
- [ ] Instance in a private subnet, no public IP, SG port 80 only from the ALB SG, no SSH from `0.0.0.0/0`
- [ ] ALB internal, HTTPS, OIDC sign-in works, `SIMBA_AUTH_MODE=alb-oidc`
- [ ] `/api/ready` returns `ready: true` in live mode, and the values match Databricks when spot-checked
- [ ] `SIMBA_SAMPLE_TABLES` contains only approved masked views
- [ ] Request links and support email filled in
- [ ] `pip freeze > requirements.lock` saved, so dependency versions are reproducible

## Operations

| Task | Command |
|---|---|
| Status / logs | `systemctl status simba-portal` · `journalctl -u simba-portal -f` |
| Nginx logs | `/var/log/nginx/simba-portal.*.log` |
| Restart after an env change | `sudo systemctl restart simba-portal` |
| Update the code | Unpack the new zip, then `sudo bash deploy/install.sh` (keeps the env file) |
| Edit wording or the roadmap | `/opt/simba-portal/content/portal.json`, then restart |

## Troubleshooting

| Symptom | Meaning / fix |
|---|---|
| Service won't start: "Invalid SIMBA portal configuration" | A required setting is missing; the journal names it. |
| Header says "Polling" instead of "Live" | SSE is blocked or capped (`SIMBA_MAX_STREAMS`). Check the Nginx `/api/stream` block and the ALB idle timeout. |
| Every request returns 401 behind the ALB | `SIMBA_ALB_ARN` doesn't match the ALB, or the instance can't reach `public-keys.auth.elb.eu-west-1.amazonaws.com` (needs NAT or egress). |
| Section shows "Could not load … PERMISSION_DENIED" | Grant is missing for the service principal; see the grants SQL. |
| `TABLE_OR_VIEW_NOT_FOUND … kafka_events` | The Kafka → Bronze notebook hasn't run yet. |
| Lineage empty | Either `system.access` is not enabled, or no pipeline has written through Unity Catalog yet. |
| Governance list looks incomplete | Expected without MANAGE: information_schema only shows grants the principal can see. |
| `NoCredentialsError` / `AccessDenied` on the secret | Instance profile missing, or the secret ARN in the policy doesn't match. |

## Quick local start (Windows)

This package includes a `.env` configured for **local demo use only**, so the login page is available at `/login` and the root route redirects to sign-in until you authenticate. Do not use the bundled demo credentials on a public/shared deployment.

1. Use Python 3.13 for the dependencies in `requirements.txt`.
2. In PowerShell, from this extracted folder, create/install once:
   ```powershell
   py -3.13 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
3. Start with `./START_LOCAL.ps1`, or run:
   ```powershell
   .\.venv\Scripts\python.exe -m flask --app wsgi run --host 127.0.0.1 --port 5000
   ```
4. Browse to **http://127.0.0.1:5000/login** (not only `/`).

Demo credentials: `simba-demo` / `SimbaDemo2026!`. The Google button is a placeholder until a real company identity provider / ALB OIDC is configured.


## Refreshed branded build
This package retains the original portal routes, Kafka Events, Databricks live/demo source integration, lineage, security/governance, roadmap, request access, data dictionary, help/support, content JSON, and the Databricks ingestion scripts. It adds SIMBA and UBA logo assets and a Microsoft sign-in entry point. Microsoft sign-in remains a placeholder until the approved Entra ID / ALB OIDC flow is configured. No `.env` file or virtual environment is included in this distribution; configure secrets using your approved environment or secret manager.

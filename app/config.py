"""Runtime settings, read once from environment variables (see .env.example)."""
import os
import re
from dataclasses import dataclass, field

IDENT_RE = re.compile(r"^[A-Za-z0-9_]+$")
FQN_RE = re.compile(r"^[A-Za-z0-9_]+\.[A-Za-z0-9_]+\.[A-Za-z0-9_]+$")


def _bool(name, default):
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _int(name, default, minimum=1):
    value = os.getenv(name, "").strip()
    try:
        return max(minimum, int(value)) if value else default
    except ValueError:
        return default


def _str(name, default=""):
    return os.getenv(name, default).strip()


def _list(name, default=""):
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    demo_mode: bool = True
    environment_label: str = "NON-PRODUCTION"

    # Unity Catalog scope
    catalog: str = "simba_data_poc"
    layer_schemas: tuple = ("bronze", "silver", "gold")
    kafka_events_table: str = "simba_data_poc.bronze.kafka_events"
    sample_tables: tuple = ()
    sample_row_limit: int = 10
    mask_patterns: tuple = ()
    row_counts_enabled: bool = True
    row_count_max_tables: int = 50
    history_max_tables: int = 50
    lineage_lookback_days: int = 90
    job_ids: tuple = ()

    # Refresh behaviour
    fast_refresh_seconds: int = 30
    slow_refresh_seconds: int = 600
    idle_pause_seconds: int = 900
    max_streams: int = 24

    # Databricks connection (server-side only; never sent to the browser)
    databricks_host: str = ""
    databricks_http_path: str = ""
    databricks_auth_type: str = "oauth-m2m"
    databricks_client_id: str = field(default="", repr=False)
    databricks_client_secret: str = field(default="", repr=False)
    databricks_token: str = field(default="", repr=False)
    secrets_manager_secret_id: str = ""
    aws_region: str = "eu-west-1"

    # Authentication
    auth_mode: str = "alb-oidc"
    alb_arn: str = ""
    allowed_email_domains: tuple = ()
    demo_login_required: bool = False
    demo_username: str = field(default="", repr=False)
    demo_password: str = field(default="", repr=False)

    # Request / support links shown on the portal
    links: dict = field(default_factory=dict)

    @classmethod
    def from_env(cls):
        return cls(
            demo_mode=_bool("SIMBA_DEMO_MODE", True),
            environment_label=_str("SIMBA_ENVIRONMENT_LABEL", "NON-PRODUCTION"),
            catalog=_str("SIMBA_CATALOG", "simba_data_poc"),
            layer_schemas=tuple(_list("SIMBA_LAYER_SCHEMAS", "bronze,silver,gold")),
            kafka_events_table=_str("SIMBA_KAFKA_EVENTS_TABLE", "simba_data_poc.bronze.kafka_events"),
            sample_tables=tuple(_list("SIMBA_SAMPLE_TABLES")),
            sample_row_limit=min(_int("SIMBA_SAMPLE_ROW_LIMIT", 10), 50),
            mask_patterns=tuple(p.lower() for p in _list(
                "SIMBA_MASK_COLUMN_PATTERNS",
                "email,phone,mobile,msisdn,bvn,nin,name,address,account_number,acct,dob,birth,"
                "password,pin,token,secret,card,iban,ip_address",
            )),
            row_counts_enabled=_bool("SIMBA_ROW_COUNTS", True),
            row_count_max_tables=_int("SIMBA_ROW_COUNT_MAX_TABLES", 50),
            history_max_tables=_int("SIMBA_HISTORY_MAX_TABLES", 50),
            lineage_lookback_days=_int("SIMBA_LINEAGE_LOOKBACK_DAYS", 90),
            job_ids=tuple(_list("SIMBA_DATABRICKS_JOB_IDS")),
            fast_refresh_seconds=_int("SIMBA_FAST_REFRESH_SECONDS", 30, minimum=5),
            slow_refresh_seconds=_int("SIMBA_SLOW_REFRESH_SECONDS", 600, minimum=60),
            idle_pause_seconds=_int("SIMBA_IDLE_PAUSE_SECONDS", 900, minimum=60),
            max_streams=_int("SIMBA_MAX_STREAMS", 24),
            databricks_host=_str("DATABRICKS_SERVER_HOSTNAME").removeprefix("https://").rstrip("/"),
            databricks_http_path=_str("DATABRICKS_HTTP_PATH"),
            databricks_auth_type=_str("DATABRICKS_AUTH_TYPE", "oauth-m2m").lower(),
            databricks_client_id=_str("DATABRICKS_CLIENT_ID"),
            databricks_client_secret=_str("DATABRICKS_CLIENT_SECRET"),
            databricks_token=_str("DATABRICKS_TOKEN"),
            secrets_manager_secret_id=_str("SIMBA_DATABRICKS_SECRET_ID"),
            aws_region=_str("AWS_REGION", "eu-west-1"),
            auth_mode=_str("SIMBA_AUTH_MODE", "alb-oidc").lower(),
            alb_arn=_str("SIMBA_ALB_ARN"),
            allowed_email_domains=tuple(d.lower().lstrip("@") for d in _list("SIMBA_ALLOWED_EMAIL_DOMAINS")),
            demo_login_required=_bool("SIMBA_DEMO_LOGIN_REQUIRED", True),
            demo_username=_str("SIMBA_DEMO_USERNAME"),
            demo_password=_str("SIMBA_DEMO_PASSWORD"),
            links={
                "service_portal": _str("SIMBA_LINK_SERVICE_PORTAL"),
                "request_access": _str("SIMBA_LINK_REQUEST_ACCESS"),
                "request_dataset": _str("SIMBA_LINK_REQUEST_DATASET"),
                "support_email": _str("SIMBA_SUPPORT_EMAIL"),
            },
        )

    def validate(self):
        """Return a list of configuration problems. Live mode refuses to start if any exist."""
        problems = []
        if not IDENT_RE.match(self.catalog):
            problems.append("SIMBA_CATALOG must contain only letters, digits and underscores")
        for schema in self.layer_schemas:
            if not IDENT_RE.match(schema):
                problems.append(f"Invalid schema name in SIMBA_LAYER_SCHEMAS: {schema!r}")
        if self.kafka_events_table and not FQN_RE.match(self.kafka_events_table):
            problems.append("SIMBA_KAFKA_EVENTS_TABLE must be catalog.schema.table")
        for table in self.sample_tables:
            if not FQN_RE.match(table):
                problems.append(f"Invalid entry in SIMBA_SAMPLE_TABLES: {table!r}")
        for job_id in self.job_ids:
            if not job_id.isdigit():
                problems.append(f"Invalid job id in SIMBA_DATABRICKS_JOB_IDS: {job_id!r}")
        if self.auth_mode not in ("alb-oidc", "none"):
            problems.append("SIMBA_AUTH_MODE must be 'alb-oidc' or 'none'")
        if self.auth_mode == "alb-oidc" and not self.alb_arn:
            problems.append("SIMBA_ALB_ARN is required when SIMBA_AUTH_MODE=alb-oidc")
        if self.demo_mode and self.auth_mode == "none" and self.demo_login_required:
            if not self.demo_username or not self.demo_password:
                problems.append("Set SIMBA_DEMO_USERNAME and SIMBA_DEMO_PASSWORD for demo sign-in")
            session_secret = os.getenv("SIMBA_SESSION_SECRET", "")
            if len(session_secret) < 32 or "replace" in session_secret.lower():
                problems.append("Set SIMBA_SESSION_SECRET to a random value of at least 32 characters")

        if not self.demo_mode:
            if not self.databricks_host:
                problems.append("DATABRICKS_SERVER_HOSTNAME is required in live mode")
            if not self.databricks_http_path:
                problems.append("DATABRICKS_HTTP_PATH is required in live mode")
            if self.databricks_auth_type not in ("oauth-m2m", "pat"):
                problems.append("DATABRICKS_AUTH_TYPE must be 'oauth-m2m' or 'pat'")
            if not self.secrets_manager_secret_id:
                if self.databricks_auth_type == "oauth-m2m" and not (
                    self.databricks_client_id and self.databricks_client_secret
                ):
                    problems.append("Set SIMBA_DATABRICKS_SECRET_ID or DATABRICKS_CLIENT_ID/DATABRICKS_CLIENT_SECRET")
                if self.databricks_auth_type == "pat" and not self.databricks_token:
                    problems.append("Set SIMBA_DATABRICKS_SECRET_ID or DATABRICKS_TOKEN")
        return problems

    def public_config(self):
        """Settings that are safe to expose to the browser."""
        return {
            "demo_mode": self.demo_mode,
            "environment_label": self.environment_label,
            "catalog": self.catalog,
            "layer_schemas": list(self.layer_schemas),
            "kafka_events_table": self.kafka_events_table,
            "sample_tables": list(self.sample_tables),
            "sample_row_limit": self.sample_row_limit,
            "fast_refresh_seconds": self.fast_refresh_seconds,
            "slow_refresh_seconds": self.slow_refresh_seconds,
            "auth_mode": self.auth_mode,
            "links": self.links,
        }

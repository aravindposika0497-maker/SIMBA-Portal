"""Thin, thread-safe wrapper around the Databricks SQL connector and SDK.

Credentials are resolved server-side only (AWS Secrets Manager or environment
variables) and are never returned to callers or logged.
"""
import json
import logging
import threading

log = logging.getLogger(__name__)


class DatabricksClient:
    def __init__(self, settings):
        self.settings = settings
        self._lock = threading.Lock()
        self._conn = None
        self._creds = None
        self._workspace = None

    # ------------------------------------------------------------------ credentials
    def _credentials(self):
        if self._creds is not None:
            return self._creds
        s = self.settings
        creds = {
            "client_id": s.databricks_client_id,
            "client_secret": s.databricks_client_secret,
            "token": s.databricks_token,
        }
        if s.secrets_manager_secret_id:
            import boto3  # imported lazily so demo mode does not need AWS libraries configured

            client = boto3.client("secretsmanager", region_name=s.aws_region)
            secret = json.loads(client.get_secret_value(SecretId=s.secrets_manager_secret_id)["SecretString"])
            for key in creds:
                if secret.get(key):
                    creds[key] = secret[key]
        self._creds = creds
        return creds

    def _sdk_config(self):
        from databricks.sdk.core import Config

        c = self._credentials()
        host = f"https://{self.settings.databricks_host}"
        if self.settings.databricks_auth_type == "oauth-m2m":
            return Config(host=host, client_id=c["client_id"], client_secret=c["client_secret"])
        return Config(host=host, token=c["token"])

    # ------------------------------------------------------------------ SQL
    def _connect(self):
        from databricks import sql

        kwargs = {
            "server_hostname": self.settings.databricks_host,
            "http_path": self.settings.databricks_http_path,
        }
        if self.settings.databricks_auth_type == "oauth-m2m":
            from databricks.sdk.core import oauth_service_principal

            config = self._sdk_config()
            kwargs["credentials_provider"] = lambda: oauth_service_principal(config)
        else:
            kwargs["access_token"] = self._credentials()["token"]
        return sql.connect(**kwargs)

    def _close(self):
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:  # noqa: BLE001 - closing a broken connection may itself fail
                pass
        self._conn = None

    def query(self, statement, params=None):
        """Run a statement and return a list of dicts. Reconnects once on failure."""
        with self._lock:
            for attempt in (1, 2):
                try:
                    if self._conn is None:
                        self._conn = self._connect()
                    with self._conn.cursor() as cursor:
                        cursor.execute(statement, params or None)
                        if not cursor.description:
                            return []
                        columns = [d[0] for d in cursor.description]
                        return [dict(zip(columns, row)) for row in cursor.fetchall()]
                except Exception:
                    self._close()
                    if attempt == 2:
                        raise
                    log.warning("Databricks query failed; reconnecting and retrying once")
        return []

    # ------------------------------------------------------------------ REST (Jobs)
    def workspace(self):
        if self._workspace is None:
            from databricks.sdk import WorkspaceClient

            self._workspace = WorkspaceClient(config=self._sdk_config())
        return self._workspace

    def close(self):
        with self._lock:
            self._close()

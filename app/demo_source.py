"""Demo data source (SIMBA_DEMO_MODE=true).

EVERYTHING here is fabricated so the interface can be reviewed before Databricks
access is approved. The UI labels this mode on every page. Kafka counts tick
upwards over time so the live-update path (poller -> SSE -> browser) can be
tested end to end without a real cluster.
"""
import time
from datetime import datetime, timedelta, timezone

from .masking import mask_rows

_START = time.time()


def _now():
    return datetime.now(timezone.utc)


def _ago(**kwargs):
    return (_now() - timedelta(**kwargs)).isoformat()


_TABLES = [
    ("bronze", "demo_user", "Demo user records (synthetic)", [("user_id", "string"), ("country_code", "string"), ("registration_status", "string"), ("created_at", "timestamp")], 4821),
    ("bronze", "demo_device", "Demo device records (synthetic)", [("device_id", "string"), ("user_id", "string"), ("platform", "string"), ("registered_at", "timestamp")], 3160),
    ("bronze", "demo_transaction", "Demo transaction records (synthetic)", [("transaction_id", "string"), ("user_id", "string"), ("amount", "decimal(18,2)"), ("currency", "string"), ("status", "string")], 2875),
    ("bronze", "kafka_events", "Raw Kafka events (demo)", [("topic", "string"), ("partition", "int"), ("offset", "bigint"), ("kafka_timestamp", "timestamp"), ("key", "string"), ("value", "string"), ("_ingested_at", "timestamp"), ("event_date", "date")], 18420),
    ("silver", "demo_customer_activity", "Demo conformed activity (synthetic)", [("user_id", "string"), ("activity_date", "date"), ("login_count", "int"), ("session_count", "int")], 5210),
    ("gold", "demo_digital_channel_kpis", "Demo daily KPIs (synthetic)", [("kpi_date", "date"), ("country_code", "string"), ("active_users", "int"), ("success_rate_pct", "decimal(5,2)")], 1051),
]

_TOPICS = [
    ("authentication.event.user-logged-in", 6.0),
    ("accounts.event.account-opened", 2.5),
    ("notifications.event.sms-notification-delivered", 3.0),
    ("transfers.event.funds-transfer-initiated", 1.2),
    ("payments.event.payment-order-initiated", 0.9),
    ("transfers.event.funds-transfer-failed", 0.2),
    ("payments.event.payment-order-completed", 0.6),
    ("authentication.event.device-logged-out", 0.4),
]


class DemoSource:
    mode = "demo"

    def __init__(self, settings):
        self.s = settings

    def layers(self):
        cat = self.s.catalog
        tables = []
        for i, (schema, name, comment, cols, rows) in enumerate(_TABLES):
            tables.append(
                {
                    "full_name": f"{cat}.{schema}.{name}",
                    "schema": schema,
                    "name": name,
                    "type": "MANAGED",
                    "format": "DELTA",
                    "owner": "demo-owner",
                    "comment": comment,
                    "created_at": _ago(days=30),
                    "last_altered_at": _ago(minutes=12 + i),
                    "columns": [{"name": c, "type": t, "nullable": True, "comment": None} for c, t in cols],
                    "row_count": rows + (int((time.time() - _START) / 10) if name == "kafka_events" else 0),
                    "last_write": {"timestamp": _ago(minutes=12 + i), "operation": "WRITE", "user": "demo", "metrics": {}},
                }
            )
        return {"catalog": cat, "schemas": list(self.s.layer_schemas), "tables": tables}

    def kafka(self):
        elapsed = time.time() - _START
        topics = []
        for i, (topic, rate) in enumerate(_TOPICS):
            ticked = int(elapsed * rate / 10)
            topics.append(
                {
                    "topic": topic,
                    "events_total": 500 * (8 - i) + ticked,
                    "events_24h": 40 * (8 - i) + ticked,
                    "first_event_at": _ago(days=20),
                    "last_event_at": _ago(seconds=5 + i * 40),
                    "partitions": 3,
                }
            )
        return {
            "source_table": self.s.kafka_events_table,
            "topics": topics,
            "last_ingested_at": _ago(seconds=8),
            "last_event_at": _ago(seconds=5),
            "note": "Demo values. Counts tick upward to exercise the live-update path.",
        }

    def pipelines(self):
        return {
            "runs": [
                {"job_id": "0", "run_name": "demo_kafka_to_bronze", "life_cycle_state": "RUNNING", "result_state": None, "state_message": "", "start_time": _ago(hours=2), "end_time": None, "url": None},
                {"job_id": "0", "run_name": "demo_silver_customer_activity", "life_cycle_state": "TERMINATED", "result_state": "SUCCESS", "state_message": "", "start_time": _ago(minutes=40), "end_time": _ago(minutes=35), "url": None},
                {"job_id": "0", "run_name": "demo_gold_kpis", "life_cycle_state": "TERMINATED", "result_state": "SUCCESS", "state_message": "", "start_time": _ago(minutes=30), "end_time": _ago(minutes=28), "url": None},
            ]
        }

    def lineage(self):
        c = self.s.catalog
        edges = [
            (f"{c}.bronze.demo_user", f"{c}.silver.demo_customer_activity"),
            (f"{c}.bronze.kafka_events", f"{c}.silver.demo_customer_activity"),
            (f"{c}.bronze.demo_device", f"{c}.silver.demo_customer_activity"),
            (f"{c}.silver.demo_customer_activity", f"{c}.gold.demo_digital_channel_kpis"),
            (f"{c}.bronze.demo_transaction", f"{c}.gold.demo_digital_channel_kpis"),
        ]
        return {
            "lookback_days": self.s.lineage_lookback_days,
            "edges": [{"source": s, "target": t, "entity_type": "NOTEBOOK", "events": 10, "last_seen": _ago(hours=1)} for s, t in edges],
        }

    def column_lineage(self, full_name):
        c = self.s.catalog
        rows = [
            {"source_table_full_name": f"{c}.bronze.demo_user", "source_column_name": "user_id", "target_table_full_name": f"{c}.silver.demo_customer_activity", "target_column_name": "user_id", "last_seen": _ago(hours=1)},
            {"source_table_full_name": f"{c}.silver.demo_customer_activity", "source_column_name": "user_id", "target_table_full_name": f"{c}.gold.demo_digital_channel_kpis", "target_column_name": "active_users", "last_seen": _ago(hours=1)},
        ]
        return {"table": full_name, "columns": [r for r in rows if full_name in (r["source_table_full_name"], r["target_table_full_name"])]}

    def governance(self):
        return {
            "grants": [],
            "errors": {},
            "note": "Demo mode does not show grants. Permissions are only displayed when read from Unity Catalog.",
        }

    def sample(self, full_name):
        rows = [
            {"user_id": f"U-***{1001 + i}", "country_code": ["NGA", "GHA", "KEN"][i % 3], "registration_status": ["Completed", "Pending"][i % 2], "email": f"demo{i}@example.com"}
            for i in range(min(8, self.s.sample_row_limit))
        ]
        masked, masked_columns = mask_rows(rows, self.s.mask_patterns)
        return {"table": full_name, "columns": list(rows[0].keys()), "rows": masked, "masked_columns": masked_columns}

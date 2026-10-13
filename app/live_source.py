"""Live data source: every value here comes from a real query against Databricks.

Each public method returns one portal section. Methods raise on failure; the
snapshot service isolates failures per section and keeps the last good value.
"""
import logging
from datetime import datetime, timezone
from itertools import islice

from .config import FQN_RE, IDENT_RE
from .masking import mask_rows

log = logging.getLogger(__name__)


def _q(identifier):
    """Backtick-quote a validated identifier."""
    if not IDENT_RE.match(identifier):
        raise ValueError(f"Unsafe identifier: {identifier!r}")
    return f"`{identifier}`"


def _fqn(full_name):
    if not FQN_RE.match(full_name):
        raise ValueError(f"Unsafe table name: {full_name!r}")
    return ".".join(_q(part) for part in full_name.split("."))


def _ms_to_iso(ms):
    if not ms:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


class LiveSource:
    mode = "live"

    def __init__(self, settings, client):
        self.s = settings
        self.db = client

    # ------------------------------------------------------------------ layers
    def layers(self):
        cat = _q(self.s.catalog)
        schema_list = ", ".join(f"'{schema}'" for schema in self.s.layer_schemas)  # validated in Settings
        tables = self.db.query(
            f"""
            SELECT table_schema, table_name, table_type, table_owner, comment,
                   created, last_altered, data_source_format
            FROM {cat}.information_schema.tables
            WHERE table_schema IN ({schema_list})
            ORDER BY table_schema, table_name
            """
        )
        columns = self.db.query(
            f"""
            SELECT table_schema, table_name, column_name, full_data_type AS data_type,
                   is_nullable, comment, ordinal_position
            FROM {cat}.information_schema.columns
            WHERE table_schema IN ({schema_list})
            ORDER BY table_schema, table_name, ordinal_position
            """
        )
        by_table = {}
        for col in columns:
            by_table.setdefault((col["table_schema"], col["table_name"]), []).append(
                {
                    "name": col["column_name"],
                    "type": col["data_type"],
                    "nullable": col["is_nullable"] == "YES",
                    "comment": col["comment"],
                }
            )

        result = []
        for t in tables:
            key = (t["table_schema"], t["table_name"])
            result.append(
                {
                    "full_name": f"{self.s.catalog}.{key[0]}.{key[1]}",
                    "schema": key[0],
                    "name": key[1],
                    "type": t["table_type"],
                    "format": t["data_source_format"],
                    "owner": t["table_owner"],
                    "comment": t["comment"],
                    "created_at": t["created"],
                    "last_altered_at": t["last_altered"],
                    "columns": by_table.get(key, []),
                    "row_count": None,
                    "last_write": None,
                }
            )

        self._attach_row_counts(result)
        self._attach_history(result)
        return {"catalog": self.s.catalog, "schemas": list(self.s.layer_schemas), "tables": result}

    def _attach_row_counts(self, tables):
        if not self.s.row_counts_enabled:
            return
        countable = [t for t in tables if t["type"] != "VIEW"][: self.s.row_count_max_tables]
        if not countable:
            return
        union = " UNION ALL ".join(
            f"SELECT '{t['full_name']}' AS full_name, COUNT(*) AS n FROM {_fqn(t['full_name'])}" for t in countable
        )
        try:
            counts = {row["full_name"]: row["n"] for row in self.db.query(union)}
        except Exception:
            log.exception("Row count query failed")
            return
        for t in countable:
            t["row_count"] = counts.get(t["full_name"])

    def _attach_history(self, tables):
        delta_tables = [t for t in tables if (t["format"] or "").upper() == "DELTA"][: self.s.history_max_tables]
        for t in delta_tables:
            try:
                rows = self.db.query(f"DESCRIBE HISTORY {_fqn(t['full_name'])} LIMIT 1")
            except Exception:
                log.warning("DESCRIBE HISTORY failed for %s", t["full_name"])
                continue
            if rows:
                last = rows[0]
                t["last_write"] = {
                    "timestamp": last.get("timestamp"),
                    "operation": last.get("operation"),
                    "user": last.get("userName"),
                    "metrics": last.get("operationMetrics") or {},
                }

    # ------------------------------------------------------------------ Kafka
    def kafka(self):
        table = _fqn(self.s.kafka_events_table)
        recent = self.db.query(
            f"""
            SELECT topic, COUNT(*) AS events_24h,
                   MAX(kafka_timestamp) AS last_event_at, MAX(_ingested_at) AS last_ingested_at
            FROM {table}
            WHERE event_date >= date_sub(current_date(), 1)
              AND kafka_timestamp >= current_timestamp() - INTERVAL 24 HOURS
            GROUP BY topic
            """
        )
        totals = self.db.query(
            f"""
            SELECT topic, COUNT(*) AS events_total, MIN(kafka_timestamp) AS first_event_at,
                   MAX(kafka_timestamp) AS last_event_at, COUNT(DISTINCT `partition`) AS partitions
            FROM {table}
            GROUP BY topic
            """
        )
        ingest = self.db.query(f"SELECT MAX(_ingested_at) AS last_ingested_at, MAX(kafka_timestamp) AS last_event_at FROM {table}")
        recent_by_topic = {row["topic"]: row for row in recent}
        topics = []
        for row in totals:
            r = recent_by_topic.get(row["topic"], {})
            topics.append(
                {
                    "topic": row["topic"],
                    "events_total": row["events_total"],
                    "events_24h": r.get("events_24h", 0),
                    "first_event_at": row["first_event_at"],
                    "last_event_at": row["last_event_at"],
                    "partitions": row["partitions"],
                }
            )
        topics.sort(key=lambda t: (-(t["events_24h"] or 0), t["topic"]))
        return {
            "source_table": self.s.kafka_events_table,
            "topics": topics,
            "last_ingested_at": ingest[0]["last_ingested_at"] if ingest else None,
            "last_event_at": ingest[0]["last_event_at"] if ingest else None,
            "note": "Only topics that have delivered at least one event to the Bronze table are listed.",
        }

    # ------------------------------------------------------------------ pipelines
    def pipelines(self):
        if not self.s.job_ids:
            return {"runs": [], "note": "No Databricks job ids configured (SIMBA_DATABRICKS_JOB_IDS)."}
        workspace = self.db.workspace()
        runs = []
        for job_id in self.s.job_ids:
            for run in islice(workspace.jobs.list_runs(job_id=int(job_id), limit=3), 3):
                state = run.state
                runs.append(
                    {
                        "job_id": job_id,
                        "run_name": run.run_name,
                        "life_cycle_state": getattr(getattr(state, "life_cycle_state", None), "value", None),
                        "result_state": getattr(getattr(state, "result_state", None), "value", None),
                        "state_message": getattr(state, "state_message", None),
                        "start_time": _ms_to_iso(run.start_time),
                        "end_time": _ms_to_iso(run.end_time),
                        "url": run.run_page_url,
                    }
                )
        runs.sort(key=lambda r: r["start_time"] or "", reverse=True)
        return {"runs": runs}

    # ------------------------------------------------------------------ lineage
    def lineage(self):
        rows = self.db.query(
            """
            SELECT source_table_full_name, target_table_full_name, entity_type,
                   COUNT(*) AS events, MAX(event_time) AS last_seen
            FROM system.access.table_lineage
            WHERE event_date >= date_sub(current_date(), :days)
              AND (source_table_catalog = :catalog OR target_table_catalog = :catalog)
              AND source_table_full_name IS NOT NULL
            GROUP BY source_table_full_name, target_table_full_name, entity_type
            ORDER BY last_seen DESC
            LIMIT 2000
            """,
            {"days": self.s.lineage_lookback_days, "catalog": self.s.catalog},
        )
        edges = [
            {
                "source": r["source_table_full_name"],
                "target": r["target_table_full_name"],
                "entity_type": r["entity_type"],
                "events": r["events"],
                "last_seen": r["last_seen"],
            }
            for r in rows
        ]
        return {"lookback_days": self.s.lineage_lookback_days, "edges": edges}

    def column_lineage(self, full_name):
        if not FQN_RE.match(full_name):
            raise ValueError("Invalid table name")
        rows = self.db.query(
            """
            SELECT source_table_full_name, source_column_name, target_table_full_name, target_column_name,
                   MAX(event_time) AS last_seen
            FROM system.access.column_lineage
            WHERE event_date >= date_sub(current_date(), :days)
              AND (target_table_full_name = :t OR source_table_full_name = :t)
            GROUP BY source_table_full_name, source_column_name, target_table_full_name, target_column_name
            ORDER BY target_table_full_name, target_column_name
            LIMIT 1000
            """,
            {"days": self.s.lineage_lookback_days, "t": full_name},
        )
        return {"table": full_name, "columns": rows}

    # ------------------------------------------------------------------ governance
    def governance(self):
        cat = _q(self.s.catalog)
        grants = []
        queries = {
            "CATALOG": f"""SELECT grantee, grantor, privilege_type, is_grantable, inherited_from,
                                  catalog_name AS securable
                           FROM {cat}.information_schema.catalog_privileges""",
            "SCHEMA": f"""SELECT grantee, grantor, privilege_type, is_grantable, inherited_from,
                                 concat(catalog_name, '.', schema_name) AS securable
                          FROM {cat}.information_schema.schema_privileges""",
            "TABLE": f"""SELECT grantee, grantor, privilege_type, is_grantable, inherited_from,
                                concat(table_catalog, '.', table_schema, '.', table_name) AS securable
                         FROM {cat}.information_schema.table_privileges""",
        }
        errors = {}
        for securable_type, sql in queries.items():
            try:
                for row in self.db.query(sql):
                    inherited = row.get("inherited_from")
                    grants.append(
                        {
                            "grantee": row["grantee"],
                            "grantee_type": _guess_principal_type(row["grantee"]),
                            "securable_type": securable_type,
                            "securable": row["securable"],
                            "privilege": row["privilege_type"],
                            "path": "Direct grant" if not inherited or inherited == "NONE" else f"Inherited from {inherited.lower()}",
                            "grantor": row["grantor"],
                            "grantable": row["is_grantable"] == "YES",
                        }
                    )
            except Exception as exc:  # noqa: BLE001
                log.warning("Grant query for %s failed", securable_type)
                errors[securable_type] = type(exc).__name__
        return {
            "grants": grants,
            "errors": errors,
            "note": (
                "Rows are limited to grants visible to the portal's service principal. Group membership is not "
                "expanded, so a user's effective access may also come through groups listed here."
            ),
        }

    # ------------------------------------------------------------------ samples
    def sample(self, full_name):
        if full_name not in self.s.sample_tables:
            raise PermissionError("Table is not on the sample allowlist")
        rows = self.db.query(f"SELECT * FROM {_fqn(full_name)} LIMIT {int(self.s.sample_row_limit)}")
        columns = list(rows[0].keys()) if rows else []
        masked_rows, masked_columns = mask_rows(rows, self.s.mask_patterns)
        return {"table": full_name, "columns": columns, "rows": masked_rows, "masked_columns": masked_columns}


def _guess_principal_type(grantee):
    """Best-effort label only; Unity Catalog does not return the principal type here."""
    if "@" in grantee:
        return "User"
    if len(grantee) == 36 and grantee.count("-") == 4:
        return "Service principal"
    return "Group"

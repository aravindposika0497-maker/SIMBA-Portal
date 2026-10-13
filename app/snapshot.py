"""Background poller + Server-Sent Events broker.

Flow: Kafka -> Databricks streaming job -> Delta tables -> this poller (SQL
Warehouse) -> in-memory snapshot -> SSE push to every open browser.

* Fast sections (Kafka activity, job runs) refresh every SIMBA_FAST_REFRESH_SECONDS.
* Slow sections (inventory, lineage, grants) refresh every SIMBA_SLOW_REFRESH_SECONDS.
* Polling pauses when nobody has used the portal for SIMBA_IDLE_PAUSE_SECONDS,
  so the SQL Warehouse can auto-stop instead of running all night.
* A failing section keeps its last good value and is flagged as stale.
"""
import hashlib
import json
import logging
import threading
import time
from datetime import date, datetime, timezone
from decimal import Decimal

log = logging.getLogger(__name__)

FAST_SECTIONS = ("kafka", "pipelines")
SLOW_SECTIONS = ("layers", "lineage", "governance")
ALL_SECTIONS = SLOW_SECTIONS + FAST_SECTIONS


def json_default(value):
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, (set, tuple)):
        return list(value)
    return str(value)


def to_jsonable(value):
    """Round-trip through JSON so payloads contain only plain types."""
    return json.loads(json.dumps(value, default=json_default))


def _utcnow():
    return datetime.now(timezone.utc).isoformat()


class StreamLimitReached(Exception):
    pass


class SnapshotService:
    def __init__(self, settings, source):
        self.settings = settings
        self.source = source
        self._cond = threading.Condition()
        self._data = {name: None for name in ALL_SECTIONS}
        self._hash = {name: None for name in ALL_SECTIONS}
        self._section_version = {name: 0 for name in ALL_SECTIONS}
        self._meta = {name: {"ok": None, "updated_at": None, "checked_at": None, "error": None} for name in ALL_SECTIONS}
        self._version = 0
        self._streams = 0
        self._last_activity = time.monotonic()
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread = None

    # ------------------------------------------------------------------ lifecycle
    def start(self):
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name="snapshot-poller", daemon=True)
            self._thread.start()

    def stop(self):
        self._stop.set()
        self._wake.set()

    def touch(self):
        """Record user activity; wakes the poller immediately if it was paused."""
        was_idle = self._idle()
        self._last_activity = time.monotonic()
        if was_idle:
            self._wake.set()

    def _idle(self):
        return self._streams == 0 and time.monotonic() - self._last_activity > self.settings.idle_pause_seconds

    def _run(self):
        next_fast = next_slow = 0.0
        while not self._stop.is_set():
            if self._idle():
                # Nobody is looking: stop querying so the warehouse can auto-stop.
                self._wake.wait(30)
                self._wake.clear()
                if not self._idle():
                    next_fast = next_slow = 0.0  # refresh straight away on return
                continue
            now = time.monotonic()
            if now >= next_slow:
                self.refresh(SLOW_SECTIONS)
                next_slow = time.monotonic() + self.settings.slow_refresh_seconds
            if now >= next_fast:
                self.refresh(FAST_SECTIONS)
                next_fast = time.monotonic() + self.settings.fast_refresh_seconds
            self._wake.wait(1)
            self._wake.clear()

    # ------------------------------------------------------------------ refresh
    def refresh(self, sections):
        changed = False
        for name in sections:
            checked_at = _utcnow()
            try:
                payload = to_jsonable(getattr(self.source, name)())
                digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
                with self._cond:
                    meta = self._meta[name]
                    status_changed = meta["ok"] is not True
                    meta.update(ok=True, checked_at=checked_at, error=None)
                    if digest != self._hash[name]:
                        self._data[name] = payload
                        self._hash[name] = digest
                        meta["updated_at"] = checked_at
                        status_changed = True
                    if status_changed:
                        self._bump(name)
                        changed = True
            except Exception as exc:  # noqa: BLE001 - one bad section must not stop the others
                log.exception("Refreshing section %s failed", name)
                message = f"{type(exc).__name__}: {str(exc)[:240]}"
                with self._cond:
                    meta = self._meta[name]
                    status_changed = meta["ok"] is not False or meta["error"] != message
                    meta.update(ok=False, checked_at=checked_at, error=message)
                    if status_changed:
                        self._bump(name)
                        changed = True
        if changed:
            with self._cond:
                self._cond.notify_all()

    def _bump(self, name):
        self._version += 1
        self._section_version[name] = self._version

    # ------------------------------------------------------------------ read
    def _meta_payload(self):
        return {
            "mode": self.source.mode,
            "version": self._version,
            "server_time": _utcnow(),
            "sections": {k: dict(v) for k, v in self._meta.items()},
        }

    def snapshot(self):
        with self._cond:
            return {"version": self._version, "meta": self._meta_payload(), "sections": dict(self._data)}

    def status(self):
        with self._cond:
            return self._meta_payload()

    # ------------------------------------------------------------------ SSE
    def acquire_stream(self):
        with self._cond:
            if self._streams >= self.settings.max_streams:
                raise StreamLimitReached()
            self._streams += 1
        self.touch()

    def release_stream(self):
        with self._cond:
            self._streams = max(0, self._streams - 1)
            self._last_activity = time.monotonic()

    def stream(self, since_version):
        """Generator of SSE frames. Call acquire_stream() first; release happens in finally."""
        last = since_version
        try:
            yield "retry: 5000\n\n"
            while not self._stop.is_set():
                with self._cond:
                    self._cond.wait_for(lambda: self._version > last or self._stop.is_set(), timeout=15)
                    if self._version > last:
                        sections = {k: self._data[k] for k, v in self._section_version.items() if v > last}
                        payload = {"version": self._version, "meta": self._meta_payload(), "sections": sections}
                        last = self._version
                        event = "update"
                    else:
                        payload = {"meta": self._meta_payload()}
                        event = "heartbeat"
                yield f"event: {event}\ndata: {json.dumps(payload, default=json_default)}\n\n"
        finally:
            self.release_stream()

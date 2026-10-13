import os

bind = "127.0.0.1:8000"  # Nginx is the only thing that should talk to Gunicorn

# Exactly ONE worker: the snapshot poller lives in-process, and a second worker
# would double the queries sent to the SQL Warehouse. Threads serve concurrent
# requests; each open live-update (SSE) connection holds one thread, so keep
# SIMBA_MAX_STREAMS comfortably below this number.
workers = 1
worker_class = "gthread"
threads = int(os.getenv("SIMBA_GUNICORN_THREADS", "32"))

timeout = 120
graceful_timeout = 20
keepalive = 5
preload_app = False

accesslog = "-"
errorlog = "-"
loglevel = "info"

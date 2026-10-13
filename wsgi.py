"""Gunicorn entry point: `gunicorn -c gunicorn.conf.py wsgi:app`."""
from dotenv import load_dotenv

load_dotenv()  # local development only; on EC2 systemd provides the environment and this is a no-op

from app import create_app  # noqa: E402

app = create_app()

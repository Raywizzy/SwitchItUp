"""Vercel serverless entrypoint for the Switch It Up API."""

from __future__ import annotations

import os


os.environ.setdefault("SWITCHITUP_DATA_PATH", "/tmp/switchitup_app_state.json")
os.environ.setdefault("SWITCHITUP_CORS_ORIGIN", "*")

from server import SwitchItUpHandler  # noqa: E402


class handler(SwitchItUpHandler):
    """Expose the local HTTP handler as a Vercel Python function."""


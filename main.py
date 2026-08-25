"""Entry point -- imports every module so its @chat.function/@ext.panel
decorators register, then exposes `ext` for the Imperal runtime. Purges
stale sys.modules cache first (same defensive pattern as Databricks/
BigQuery Connector's main.py) so a hot-reload never serves stale bytecode.
"""
from __future__ import annotations

import sys

_MODULES = [
    "app", "schemas", "aws_sigv4", "redshift_client",
    "handlers_connection", "handlers_clusters", "handlers_serverless",
    "handlers_dataapi", "handlers_analytics",
    "panels", "panels_settings",
]
for _m in _MODULES:
    sys.modules.pop(_m, None)

from app import ext  # noqa: E402
import handlers_connection  # noqa: E402,F401
import handlers_clusters  # noqa: E402,F401
import handlers_serverless  # noqa: E402,F401
import handlers_dataapi  # noqa: E402,F401
import handlers_analytics  # noqa: E402,F401
import panels  # noqa: E402,F401
import panels_settings  # noqa: E402,F401

__all__ = ["ext"]

"""Extension declaration, secrets, lifecycle hooks.

WHY BYOK VIA RAW AWS ACCESS KEYS, SAME REASONING AS AWS CONNECTOR.

Redshift is the user's OWN AWS account -- Imperal cannot and should not
broker access to someone else's data warehouse centrally. The user
provides their own IAM Access Key ID + Secret Access Key (optionally a
session token for temporary/SSO credentials), and every call is signed
with AWS SigV4 (see aws_sigv4.py, copied verbatim from AWS Connector --
same signing algorithm, no reason to reimplement it) and sent directly to
AWS's own regional endpoints.

WHY THE REDSHIFT DATA API, NOT A JDBC/PSQL DRIVER.

The extension runtime has no PostgreSQL wire-protocol driver available
(same class of constraint as every other *_client.py -- no boto3, no
psycopg2). AWS's own Redshift Data API solves exactly this: it lets you
run SQL against a cluster or Serverless workgroup over a plain HTTPS/JSON
call (execute-statement / describe-statement / get-statement-result),
with AWS handling the actual database connection on your behalf. This is
the officially recommended way to query Redshift without a database
driver.

CONNECTIONS ARE STORED AS ONE JSON ARRAY, SAME AS OTHER BYOK CONNECTORS.

`redshift_connections` holds a JSON array of
`{id, label, access_key_id, secret_access_key, session_token, region}`
objects, and every tool's `connection_id` parameter addresses one entry.
"""
from __future__ import annotations

from imperal_sdk import ChatExtension, Extension

ext = Extension(
    "redshift-connector",
    version="0.1.0",
    display_name="Amazon Redshift",
    description=(
        "Connect your own AWS account to manage Redshift provisioned "
        "clusters, Redshift Serverless workgroups, databases, and run SQL "
        "via the Redshift Data API, and audit warehouse cost and health "
        "-- from Imperal. Uses your own IAM Access Key -- nothing is "
        "hosted or proxied by Imperal beyond the request itself."
    ),
    icon="icon.svg",
    capabilities=[
        "redshift:read",
        "redshift:write",
    ],
    actions_explicit=True,
    system=False,
)

chat = ChatExtension(
    ext,
    tool_name="redshift",
    description=(
        "Amazon Redshift Connector -- connect your own AWS account via IAM "
        "Access Key, then manage provisioned clusters/Serverless "
        "workgroups/databases and run SQL through the Redshift Data API, "
        "and audit warehouse health and cost."
    ),
)

ext.secret(
    "redshift_connections",
    (
        "Your connected AWS accounts for Redshift -- stored as a JSON "
        "array, one entry per account, each with its own IAM Access Key "
        "ID/Secret Access Key/session token and region. Managed through "
        "connect_redshift / disconnect_redshift -- you should not need to "
        "edit this directly."
    ),
    required=True,
    write_mode="both",
    max_bytes=65536,
    rotation_hint_days=90,
)(lambda: None)


@ext.health_check
async def health_check(ctx) -> dict:
    """Fast configuration health; no third-party call -- just confirms at
    least one AWS account connection is stored, same shape as Databricks
    Connector's / Google BigQuery Connector's health_check."""
    import json as _json
    raw = await ctx.secrets.get("redshift_connections")
    try:
        count = len(_json.loads(raw)) if raw else 0
    except Exception:
        count = 0
    return {
        "healthy": True,
        "detail": (
            f"{count} AWS account(s) connected for Redshift."
            if count else "No AWS account connected yet."
        ),
    }

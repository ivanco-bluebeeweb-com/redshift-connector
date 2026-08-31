"""Connection management: connect/disconnect Redshift accounts. Same
shape as Databricks/BigQuery Connector's handlers_connection.py.
"""
from __future__ import annotations

import json
import uuid

from imperal_sdk import ActionResult

import redshift_client as rsc
from app import ext, chat
from schemas import (
    NoParams,
    ConnectRedshiftParams, ProviderConnection, ProviderConnectionList,
    DisconnectRedshiftParams, DeleteResult,
)

_CONN_SECRET = "redshift_connections"


async def _load_connections(ctx) -> list[dict]:
    raw = await ctx.secrets.get(_CONN_SECRET)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return data if isinstance(data, list) else []


async def _save_connections(ctx, items: list[dict]) -> None:
    await ctx.secrets.set(_CONN_SECRET, json.dumps(items))


async def _resolve_connection(ctx, connection_id: str):
    conns = await _load_connections(ctx)
    if not conns:
        return ActionResult.error("No AWS account connected yet.")
    if connection_id:
        for c in conns:
            if c.get("id") == connection_id:
                return c
        return ActionResult.error(f"No Redshift connection with id '{connection_id}'.")
    if len(conns) == 1:
        return conns[0]
    return ActionResult.error(
        "Multiple accounts are connected -- pass connection_id to pick one."
    )


def _to_entity(c: dict) -> ProviderConnection:
    return ProviderConnection(
        id=c.get("id", ""),
        title=c.get("label") or c.get("access_key_id", "")[:8] + "...",
        connected=True,
        detail=c.get("access_key_id", ""),
        region=c.get("region", ""),
    )


@chat.function(
    "connect_redshift",
    "Connect your own AWS account by saving an IAM Access Key ID + Secret Access Key, after checking it actually works against Redshift.",
    action_type="write",
    chain_callable=True,
    data_model=ProviderConnection,
    effects=["create:resource"],
    event="redshift-connector.connect_redshift",
)
async def connect_redshift(ctx, params: ConnectRedshiftParams) -> ActionResult:
    """Connect a new AWS account for Redshift access."""
    if not params.access_key_id or not params.secret_access_key:
        return ActionResult.error("Both access_key_id and secret_access_key are required.")
    conn = {
        "id": str(uuid.uuid4()),
        "label": params.label,
        "access_key_id": params.access_key_id,
        "secret_access_key": params.secret_access_key,
        "session_token": params.session_token,
        "region": params.region or "us-east-1",
    }
    try:
        await rsc.list_clusters(ctx, conn)
    except rsc.ClientFail as exc:
        if exc.status == 403 or "AccessDenied" in str(exc) or "not authorized" in str(exc).lower():
            return ActionResult.error(
                "AWS accepted the keys but denied Redshift access -- attach a policy granting "
                "redshift:Describe*, redshift-serverless:List*/Get*, and redshift-data:* to this IAM user, then reconnect."
            )
        return ActionResult.error(f"Could not verify the connection: {exc}")
    conns = await _load_connections(ctx)
    conns.append(conn)
    await _save_connections(ctx, conns)
    return ActionResult.success(data=_to_entity(conn), summary="Redshift connected.")


@chat.function(
    "list_connections",
    "List the connected AWS accounts (for Redshift access).",
    action_type="read",
    chain_callable=True,
    data_model=ProviderConnectionList,
    event="redshift-connector.list_connections",
)
async def list_connections(ctx, params: NoParams) -> ActionResult:
    """List connections."""
    conns = await _load_connections(ctx)
    return ActionResult.success(data=ProviderConnectionList(items=[_to_entity(c) for c in conns]), summary="Connections listed.")


@chat.function(
    "disconnect_redshift",
    "Disconnect an AWS account: deletes the saved Access Key. Nothing in AWS itself is changed.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    effects=["delete:resource"],
    event="redshift-connector.disconnect_redshift",
)
async def disconnect_redshift(ctx, params: DisconnectRedshiftParams) -> ActionResult:
    """Disconnect an AWS account."""
    conns = await _load_connections(ctx)
    remaining = [c for c in conns if c.get("id") != params.connection_id]
    if len(remaining) == len(conns):
        return ActionResult.error(f"No Redshift connection with id '{params.connection_id}'.")
    await _save_connections(ctx, remaining)
    return ActionResult.success(data=DeleteResult(ok=True, detail="Disconnected."), summary="Redshift disconnected.")

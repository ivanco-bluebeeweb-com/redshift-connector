"""Serverless (workgroups/namespaces) + databases handlers. Same shape
as Databricks Connector's handlers_catalog.py.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import redshift_client as rsc
from app import ext, chat
from handlers_connection import _resolve_connection
from schemas import (
    ListWorkgroupsParams, WorkgroupList, RedshiftWorkgroup,
    GetWorkgroupParams, ListNamespacesParams, NamespaceList, RedshiftNamespace,
    ListDatabasesParams, DatabaseList, RedshiftDatabase,
)


def _to_workgroup(w: dict) -> RedshiftWorkgroup:
    return RedshiftWorkgroup(
        workgroup_name=w.get("workgroupName", ""),
        namespace_name=w.get("namespaceName", ""),
        status=w.get("status", ""),
        base_capacity=int(w.get("baseCapacity", 0) or 0),
    )


def _to_namespace(n: dict) -> RedshiftNamespace:
    return RedshiftNamespace(
        namespace_name=n.get("namespaceName", ""),
        namespace_id=n.get("namespaceId", ""),
        status=n.get("status", ""),
        db_name=n.get("dbName", ""),
    )


@chat.function(
    "list_workgroups",
    "List Redshift Serverless workgroups in the connected AWS account/region.",
    action_type="read",
    chain_callable=True,
    data_model=WorkgroupList,
    event="redshift-connector.list_workgroups",
)
async def list_workgroups(ctx, params: ListWorkgroupsParams) -> ActionResult:
    """List workgroups."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    try:
        rows = await rsc.list_workgroups(ctx, conn)
    except rsc.ClientFail as exc:
        return ActionResult.error(str(exc))
    return ActionResult.success(data=WorkgroupList(items=[_to_workgroup(w) for w in rows]))


@chat.function(
    "get_workgroup",
    "Read one Redshift Serverless workgroup in full by its name.",
    action_type="read",
    chain_callable=True,
    data_model=RedshiftWorkgroup,
    event="redshift-connector.get_workgroup",
)
async def get_workgroup(ctx, params: GetWorkgroupParams) -> ActionResult:
    """Read one workgroup."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    try:
        w = await rsc.get_workgroup(ctx, conn, params.workgroup_name)
    except rsc.ClientFail as exc:
        return ActionResult.error(str(exc))
    if not w:
        return ActionResult.error(f"No workgroup '{params.workgroup_name}'.")
    return ActionResult.success(data=_to_workgroup(w))


@chat.function(
    "list_namespaces",
    "List Redshift Serverless namespaces in the connected AWS account/region.",
    action_type="read",
    chain_callable=True,
    data_model=NamespaceList,
    event="redshift-connector.list_namespaces",
)
async def list_namespaces(ctx, params: ListNamespacesParams) -> ActionResult:
    """List namespaces."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    try:
        rows = await rsc.list_namespaces(ctx, conn)
    except rsc.ClientFail as exc:
        return ActionResult.error(str(exc))
    return ActionResult.success(data=NamespaceList(items=[_to_namespace(n) for n in rows]))


@chat.function(
    "list_databases",
    "List databases available on a Redshift cluster or Serverless workgroup, via the Data API.",
    action_type="read",
    chain_callable=True,
    data_model=DatabaseList,
    event="redshift-connector.list_databases",
)
async def list_databases(ctx, params: ListDatabasesParams) -> ActionResult:
    """List databases."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    if not params.cluster_identifier and not params.workgroup_name:
        return ActionResult.error("Either cluster_identifier or workgroup_name is required.")
    try:
        rows = await rsc.list_databases(
            ctx, conn, params.cluster_identifier, params.workgroup_name, params.db_user,
        )
    except rsc.ClientFail as exc:
        return ActionResult.error(str(exc))
    return ActionResult.success(data=DatabaseList(items=[RedshiftDatabase(**d) for d in rows]))

"""Cluster (provisioned) handlers -- list/get/delete/reboot/resize +
snapshots. Same shape as Databricks Connector's handlers_clusters.py.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import redshift_client as rsc
from app import ext, chat
from handlers_connection import _resolve_connection
from schemas import (
    ListClustersParams, ClusterList, RedshiftCluster,
    GetClusterParams, DeleteClusterParams, DeleteResult,
    RebootClusterParams, ResizeClusterParams,
    ListSnapshotsParams, SnapshotList, RedshiftSnapshot,
)


def _to_cluster(c: dict) -> RedshiftCluster:
    return RedshiftCluster(
        cluster_identifier=c.get("ClusterIdentifier", ""),
        node_type=c.get("NodeType", ""),
        cluster_status=c.get("ClusterStatus", ""),
        number_of_nodes=int(c.get("NumberOfNodes", 1) or 1),
        publicly_accessible=(c.get("PubliclyAccessible", "false") == "true"),
        db_name=c.get("DBName", ""),
    )


@chat.function(
    "list_clusters",
    "List Redshift provisioned clusters in the connected AWS account/region.",
    action_type="read",
    chain_callable=True,
    data_model=ClusterList,
    event="redshift-connector.list_clusters",
)
async def list_clusters(ctx, params: ListClustersParams) -> ActionResult:
    """List clusters."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    try:
        rows = await rsc.list_clusters(ctx, conn)
    except rsc.ClientFail as exc:
        return ActionResult.error(str(exc))
    return ActionResult.success(data=ClusterList(items=[_to_cluster(c) for c in rows]), summary="Clusters listed.")


@chat.function(
    "get_cluster",
    "Read one Redshift provisioned cluster in full by its identifier.",
    action_type="read",
    chain_callable=True,
    data_model=RedshiftCluster,
    event="redshift-connector.get_cluster",
)
async def get_cluster(ctx, params: GetClusterParams) -> ActionResult:
    """Read one cluster."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    try:
        c = await rsc.get_cluster(ctx, conn, params.cluster_identifier)
    except rsc.ClientFail as exc:
        return ActionResult.error(str(exc))
    if not c:
        return ActionResult.error(f"No cluster '{params.cluster_identifier}'.")
    return ActionResult.success(data=_to_cluster(c), summary="Cluster retrieved.")


@chat.function(
    "delete_cluster",
    "Permanently delete a Redshift provisioned cluster. Cannot be undone unless a final snapshot is taken.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    effects=["delete:resource"],
    event="redshift-connector.delete_cluster",
)
async def delete_cluster(ctx, params: DeleteClusterParams) -> ActionResult:
    """Delete a cluster."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    try:
        await rsc.delete_cluster(ctx, conn, params.cluster_identifier, params.skip_final_snapshot)
    except rsc.ClientFail as exc:
        return ActionResult.error(str(exc))
    return ActionResult.success(data=DeleteResult(ok=True, detail=f"Cluster '{params.cluster_identifier}' deletion initiated."), summary="Cluster deleted.")


@chat.function(
    "reboot_cluster",
    "Reboot a Redshift provisioned cluster.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    effects=["update:resource"],
    event="redshift-connector.reboot_cluster",
)
async def reboot_cluster(ctx, params: RebootClusterParams) -> ActionResult:
    """Reboot a cluster."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    try:
        await rsc.reboot_cluster(ctx, conn, params.cluster_identifier)
    except rsc.ClientFail as exc:
        return ActionResult.error(str(exc))
    return ActionResult.success(data=DeleteResult(ok=True, detail="Reboot initiated."), summary="Reboot cluster done.")


@chat.function(
    "resize_cluster",
    "Resize a Redshift provisioned cluster -- change its node type and/or node count.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    effects=["update:resource"],
    event="redshift-connector.resize_cluster",
)
async def resize_cluster(ctx, params: ResizeClusterParams) -> ActionResult:
    """Resize a cluster."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    try:
        await rsc.resize_cluster(ctx, conn, params.cluster_identifier, params.node_type, params.number_of_nodes)
    except rsc.ClientFail as exc:
        return ActionResult.error(str(exc))
    return ActionResult.success(data=DeleteResult(ok=True, detail="Resize initiated."), summary="Resize cluster done.")


@chat.function(
    "list_snapshots",
    "List snapshots for a Redshift provisioned cluster, or across the account if no cluster is given.",
    action_type="read",
    chain_callable=True,
    data_model=SnapshotList,
    event="redshift-connector.list_snapshots",
)
async def list_snapshots(ctx, params: ListSnapshotsParams) -> ActionResult:
    """List snapshots."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    try:
        rows = await rsc.list_snapshots(ctx, conn, params.cluster_identifier)
    except rsc.ClientFail as exc:
        return ActionResult.error(str(exc))
    items = [
        RedshiftSnapshot(
            snapshot_identifier=s.get("SnapshotIdentifier", ""),
            cluster_identifier=s.get("ClusterIdentifier", ""),
            snapshot_type=s.get("SnapshotType", ""),
            status=s.get("Status", ""),
        )
        for s in rows
    ]
    return ActionResult.success(data=SnapshotList(items=items), summary="Snapshots listed.")

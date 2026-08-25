"""Audit -- aggregated health report. Same shape as BigQuery/Databricks
Connector's handlers_analytics.py.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import redshift_client as rsc
from app import ext, chat
from handlers_connection import _resolve_connection
from schemas import AuditRedshiftParams, AuditReport, AuditFinding


@chat.function(
    "audit_redshift",
    "Build one aggregated health report across the connected AWS account: publicly accessible clusters, clusters/workgroups with default settings that may indicate weak security posture.",
    action_type="read",
    chain_callable=True,
    data_model=AuditReport,
    event="redshift-connector.audit_redshift",
)
async def audit_redshift(ctx, params: AuditRedshiftParams) -> ActionResult:
    """Audit the connected AWS account's Redshift footprint."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    findings: list[AuditFinding] = []

    try:
        clusters = await rsc.list_clusters(ctx, conn)
    except rsc.ClientFail as exc:
        return ActionResult.error(str(exc))
    for c in clusters:
        ident = c.get("ClusterIdentifier", "")
        if c.get("PubliclyAccessible", "false") == "true":
            findings.append(AuditFinding(
                kind="cluster_publicly_accessible",
                detail=f"Cluster '{ident}' is publicly accessible -- confirm this is intentional, otherwise restrict it to a VPC.",
                severity="high",
            ))
        if not c.get("AutomatedSnapshotRetentionPeriod") or c.get("AutomatedSnapshotRetentionPeriod") == "0":
            findings.append(AuditFinding(
                kind="cluster_no_automated_snapshots",
                detail=f"Cluster '{ident}' has automated snapshots disabled -- no point-in-time recovery.",
                severity="medium",
            ))

    try:
        workgroups = await rsc.list_workgroups(ctx, conn)
    except rsc.ClientFail:
        workgroups = []
    for w in workgroups:
        if w.get("publiclyAccessible"):
            findings.append(AuditFinding(
                kind="workgroup_publicly_accessible",
                detail=f"Workgroup '{w.get('workgroupName', '')}' is publicly accessible -- confirm this is intentional.",
                severity="high",
            ))

    return ActionResult.success(data=AuditReport(
        findings=findings,
        clusters_scanned=len(clusters),
        workgroups_scanned=len(workgroups),
    ))

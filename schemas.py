"""Pydantic params models + SDL entity contracts for Amazon Redshift
Connector. Module-scope (V17 federal invariant). Organized by domain:
connection, clusters, serverless, databases, data-api, audit.
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from imperal_sdk import sdl


class NoParams(BaseModel):
    """Explicit empty params model -- V17 disallows untyped handlers."""
    pass


# ── Connection ──────────────────────────────────────────────────────────

class ConnectRedshiftParams(BaseModel):
    access_key_id: str = Field("", description="Your AWS IAM Access Key ID, e.g. AKIAIOSFODNN7EXAMPLE.")
    secret_access_key: str = Field("", description="Your AWS IAM Secret Access Key.")
    session_token: str = Field("", description="Optional session token for temporary/SSO credentials. Leave empty for a permanent access key.")
    region: str = Field("us-east-1", description="AWS region your Redshift clusters/workgroups live in, e.g. us-east-1.")
    label: str = Field("", description="Optional friendly name for this connection.")


class ProviderConnection(sdl.Entity):
    id: str = ""
    title: str = ""
    connected: bool = False
    detail: str = ""
    region: str = ""


class ProviderConnectionList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[ProviderConnection] = []


class DisconnectRedshiftParams(BaseModel):
    connection_id: str = Field(..., description="Connection id from list_connections.")


class DeleteResult(sdl.Entity):
    id: str = ""
    title: str = ""
    ok: bool = True
    detail: str = ""


# ── Clusters (provisioned) ─────────────────────────────────────────────

class ListClustersParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected account.")


class RedshiftCluster(sdl.Entity):
    id: str = ""
    title: str = ""
    cluster_identifier: str = ""
    node_type: str = ""
    cluster_status: str = ""
    number_of_nodes: int = 0
    publicly_accessible: bool = False
    db_name: str = ""


class ClusterList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[RedshiftCluster] = []


class GetClusterParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected account.")
    cluster_identifier: str = Field(..., description="Cluster identifier, e.g. 'my-cluster'.")


class DeleteClusterParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected account.")
    cluster_identifier: str = Field(..., description="Cluster identifier to delete.")
    skip_final_snapshot: bool = Field(False, description="If false (default), a final snapshot is taken before deletion.")
    final_snapshot_identifier: str = Field("", description="Name for the final snapshot, required unless skip_final_snapshot is true.")


class RebootClusterParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected account.")
    cluster_identifier: str = Field(..., description="Cluster identifier to reboot.")


class ResizeClusterParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected account.")
    cluster_identifier: str = Field(..., description="Cluster identifier to resize.")
    node_type: str = Field(..., description="New node type, e.g. 'ra3.xlplus'.")
    number_of_nodes: int = Field(..., description="New node count.")


class ListSnapshotsParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected account.")
    cluster_identifier: str = Field("", description="Optional: filter to snapshots of one cluster.")


class RedshiftSnapshot(sdl.Entity):
    id: str = ""
    title: str = ""
    snapshot_identifier: str = ""
    cluster_identifier: str = ""
    status: str = ""
    snapshot_type: str = ""
    node_type: str = ""


class SnapshotList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[RedshiftSnapshot] = []


# ── Serverless ──────────────────────────────────────────────────────────

class ListWorkgroupsParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected account.")


class RedshiftWorkgroup(sdl.Entity):
    id: str = ""
    title: str = ""
    workgroup_name: str = ""
    namespace_name: str = ""
    status: str = ""
    base_capacity: int = 0
    publicly_accessible: bool = False


class WorkgroupList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[RedshiftWorkgroup] = []


class GetWorkgroupParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected account.")
    workgroup_name: str = Field(..., description="Workgroup name.")


class ListNamespacesParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected account.")


class RedshiftNamespace(sdl.Entity):
    id: str = ""
    title: str = ""
    namespace_name: str = ""
    namespace_id: str = ""
    status: str = ""
    db_name: str = ""
    admin_username: str = ""


class NamespaceList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[RedshiftNamespace] = []


# ── Databases ───────────────────────────────────────────────────────────

class ListDatabasesParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected account.")
    cluster_identifier: str = Field("", description="Provisioned cluster identifier (set this OR workgroup_name).")
    workgroup_name: str = Field("", description="Serverless workgroup name (set this OR cluster_identifier).")
    database: str = Field("dev", description="Database to connect through for listing, e.g. 'dev'.")
    db_user: str = Field("", description="Database user for provisioned clusters using temporary credentials (IAM auth).")
    secret_arn: str = Field("", description="Secrets Manager secret ARN holding DB credentials, alternative to db_user.")


class RedshiftDatabase(sdl.Entity):
    id: str = ""
    title: str = ""
    database_name: str = ""


class DatabaseList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[RedshiftDatabase] = []


# ── Data API (SQL execution) ────────────────────────────────────────────

class ExecuteSqlParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected account.")
    cluster_identifier: str = Field("", description="Provisioned cluster identifier (set this OR workgroup_name).")
    workgroup_name: str = Field("", description="Serverless workgroup name (set this OR cluster_identifier).")
    database: str = Field(..., description="Database to run the query against, e.g. 'dev'.")
    db_user: str = Field("", description="Database user for provisioned clusters using temporary credentials (IAM auth).")
    secret_arn: str = Field("", description="Secrets Manager secret ARN holding DB credentials, alternative to db_user.")
    sql: str = Field(..., description="SQL statement to run, e.g. SELECT * FROM public.users LIMIT 100.")


class StatementSubmitResult(sdl.Entity):
    id: str = ""
    title: str = ""
    statement_id: str = ""
    status: str = ""
    created_at: str = ""


class GetStatementStatusParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected account.")
    statement_id: str = Field(..., description="Statement id returned by execute_sql.")


class StatementStatus(sdl.Entity):
    id: str = ""
    title: str = ""
    statement_id: str = ""
    status: str = ""
    error: str = ""
    has_result_set: bool = False
    error_message: str = ""
    result_rows: int = 0
    duration_ns: int = 0


class GetStatementResultParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected account.")
    statement_id: str = Field(..., description="Statement id returned by execute_sql, once its status is FINISHED.")


class StatementResult(sdl.Entity):
    id: str = ""
    title: str = ""
    columns: list[str] = []
    rows: list[list[str]] = []
    total_rows: int = 0


class CancelStatementParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected account.")
    statement_id: str = Field(..., description="Statement id to cancel.")


class ListStatementsParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected account.")


class StatementSummary(sdl.Entity):
    id: str = ""
    title: str = ""
    statement_id: str = ""
    status: str = ""
    query_string: str = ""
    created_at: str = ""


class StatementList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[StatementSummary] = []


# ── Audit ───────────────────────────────────────────────────────────────

class AuditRedshiftParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected account.")


class AuditFinding(sdl.Entity):
    id: str = ""
    title: str = ""
    kind: str = ""
    detail: str = ""
    severity: str = ""


class AuditReport(sdl.Entity):
    id: str = ""
    title: str = ""
    findings: list[AuditFinding] = []
    clusters_scanned: int = 0
    workgroups_scanned: int = 0

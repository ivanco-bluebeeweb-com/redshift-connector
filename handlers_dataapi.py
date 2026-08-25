"""Data API handlers -- execute SQL, get statement status/result, cancel,
list statements. Same shape as BigQuery Connector's handlers_jobs.py.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import redshift_client as rsc
from app import ext, chat
from handlers_connection import _resolve_connection
from schemas import (
    ExecuteSqlParams, StatementSubmitResult,
    GetStatementStatusParams, StatementStatus,
    GetStatementResultParams, StatementResult,
    CancelStatementParams, DeleteResult,
    ListStatementsParams, StatementList, StatementSummary,
)


@chat.function(
    "execute_sql",
    "Run a SQL statement against Redshift (provisioned cluster or Serverless workgroup) via the Data API. Returns a statement id -- poll get_statement_status, then get_statement_result.",
    action_type="write",
    chain_callable=True,
    data_model=StatementSubmitResult,
    effects=["create:resource"],
    event="redshift-connector.execute_sql",
)
async def execute_sql(ctx, params: ExecuteSqlParams) -> ActionResult:
    """Execute a SQL statement."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    if not params.cluster_identifier and not params.workgroup_name:
        return ActionResult.error("Either cluster_identifier or workgroup_name is required.")
    try:
        data = await rsc.execute_statement(
            ctx, conn, params.sql, params.cluster_identifier,
            params.workgroup_name, params.database, params.db_user,
        )
    except rsc.ClientFail as exc:
        return ActionResult.error(str(exc))
    return ActionResult.success(data=StatementSubmitResult(
        statement_id=data.get("Id", ""),
        created_at=str(data.get("CreatedAt", "")),
    ))


@chat.function(
    "get_statement_status",
    "Read a SQL statement's current status by id from execute_sql -- whether it's done, and row/duration info.",
    action_type="read",
    chain_callable=True,
    data_model=StatementStatus,
    event="redshift-connector.get_statement_status",
)
async def get_statement_status(ctx, params: GetStatementStatusParams) -> ActionResult:
    """Read statement status."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    try:
        data = await rsc.describe_statement(ctx, conn, params.statement_id)
    except rsc.ClientFail as exc:
        return ActionResult.error(str(exc))
    return ActionResult.success(data=StatementStatus(
        statement_id=data.get("Id", ""),
        status=data.get("Status", ""),
        error_message=data.get("Error", "") or "",
        result_rows=int(data.get("ResultRows", 0) or 0),
        duration_ns=int(data.get("Duration", 0) or 0),
    ))


@chat.function(
    "get_statement_result",
    "Read the result rows of a completed SQL statement by id from execute_sql.",
    action_type="read",
    chain_callable=True,
    data_model=StatementResult,
    event="redshift-connector.get_statement_result",
)
async def get_statement_result(ctx, params: GetStatementResultParams) -> ActionResult:
    """Read statement result."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    try:
        data = await rsc.get_statement_result(ctx, conn, params.statement_id)
    except rsc.ClientFail as exc:
        return ActionResult.error(str(exc))
    columns = [m.get("name", "") for m in data.get("ColumnMetadata", []) or []]
    rows = []
    for record in data.get("Records", []) or []:
        row = {}
        for i, field in enumerate(record):
            col = columns[i] if i < len(columns) else f"col_{i}"
            row[col] = next(iter(field.values()), None) if isinstance(field, dict) else field
        rows.append(row)
    return ActionResult.success(data=StatementResult(columns=columns, rows=rows))


@chat.function(
    "cancel_statement",
    "Cancel a running SQL statement.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    effects=["update:resource"],
    event="redshift-connector.cancel_statement",
)
async def cancel_statement(ctx, params: CancelStatementParams) -> ActionResult:
    """Cancel a statement."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    try:
        await rsc.cancel_statement(ctx, conn, params.statement_id)
    except rsc.ClientFail as exc:
        return ActionResult.error(str(exc))
    return ActionResult.success(data=DeleteResult(ok=True, detail="Cancel requested."))


@chat.function(
    "list_statements",
    "List recent SQL statements run via the Data API in the connected AWS account/region.",
    action_type="read",
    chain_callable=True,
    data_model=StatementList,
    event="redshift-connector.list_statements",
)
async def list_statements(ctx, params: ListStatementsParams) -> ActionResult:
    """List statements."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    try:
        rows = await rsc.list_statements(ctx, conn, params.max_results)
    except rsc.ClientFail as exc:
        return ActionResult.error(str(exc))
    items = [
        StatementSummary(
            statement_id=s.get("Id", ""),
            query_string=(s.get("QueryString", "") or "")[:300],
            status=s.get("Status", ""),
            created_at=str(s.get("CreatedAt", "")),
        )
        for s in rows
    ]
    return ActionResult.success(data=StatementList(items=items))

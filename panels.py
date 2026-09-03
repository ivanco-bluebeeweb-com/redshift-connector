"""Panel UI -- connections list/connect form + clusters / serverless /
databases / query editor in the left sidebar and main center panel.

SIDEBAR CONTENT -- NO CARDS ANYWHERE, per ~/UI_INTERFACE_STANDARD.md's
"left sidebar, no decorated cards" rule (same convention as Databricks/
BigQuery Connector's panels.py).

Form container is stretched full-width (align="stretch") and every field
carries its own visible label via the _field() wrapper below plus a
contextually specific placeholder. No setup instructions are duplicated
here that already exist in "App settings" (panels_settings.py).
"""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
from handlers_connection import _load_connections


def _field(label: str, node: ui.UINode) -> ui.UINode:
    return ui.Stack(direction="v", gap=1, align="stretch", children=[
        ui.Text(label, variant="caption"),
        node,
    ])


def _settings_button() -> ui.UINode:
    return ui.Button(
        "App settings", variant="secondary", on_click=ui.Call("__panel__redshift_settings"),
    )


def _connect_form() -> ui.UINode:
    return ui.Stack(direction="v", gap=1, align="stretch", children=[
        ui.Empty(
            message="Connect your own AWS account to manage Redshift clusters, Serverless workgroups, and run SQL. Create an Access Key under IAM > Users > Security credentials.",
            icon="database",
        ),
        ui.Form(
            action="connect_redshift", submit_label="Подключить",
            children=[
              ui.Stack(direction="v", gap=3, align="stretch", children=[
                _field("Access Key ID", ui.Input(
                    param_name="access_key_id",
                    placeholder="AKIAIOSFODNN7EXAMPLE",
                )),
                _field("Secret Access Key", ui.Password(
                    param_name="secret_access_key",
                    placeholder="Ваш AWS Secret Access Key",
                )),
                _field("Session Token (опционально)", ui.Password(
                    param_name="session_token",
                    placeholder="Только для временных/SSO-креденшлов",
                )),
                _field("Регион", ui.Select(
                    param_name="region",
                    options=[
                        {"label": "US East (N. Virginia)", "value": "us-east-1"},
                        {"label": "US East (Ohio)", "value": "us-east-2"},
                        {"label": "US West (Oregon)", "value": "us-west-2"},
                        {"label": "EU (Ireland)", "value": "eu-west-1"},
                        {"label": "EU (Frankfurt)", "value": "eu-central-1"},
                        {"label": "EU (Stockholm)", "value": "eu-north-1"},
                        {"label": "Asia Pacific (Singapore)", "value": "ap-southeast-1"},
                    ],
                )),
                _field("Имя подключения (опционально)", ui.Input(
                    param_name="label",
                    placeholder="Мой AWS-аккаунт",
                )),
              ]),
            ],
        ),
    ])


@ext.panel("redshift_sidebar", slot="left")
async def redshift_sidebar(ctx) -> ui.UINode:
    connections = await _load_connections(ctx)
    if not connections:
        return ui.Stack(direction="v", gap=3, align="stretch", children=[
            _connect_form(),
        ])
    label = connections[0].get("label") or connections[0].get("access_key_id", "")
    nav = [
        ("Clusters", "redshift_clusters"),
        ("Serverless", "redshift_serverless"),
        ("Databases", "redshift_databases"),
        ("Query Editor", "redshift_query"),
    ]
    return ui.Stack(direction="v", gap=1, align="start", children=[
        ui.Text(label, variant="body"),
        ui.Divider(),
        *[ui.ListItem(id=target, title=lbl, on_click=ui.Call(f"__panel__{target}")) for lbl, target in nav],
        ui.Divider(),
        _settings_button(),
    ])


@ext.panel("redshift_clusters", slot="center", center_overlay=True)
async def redshift_clusters_panel(ctx) -> ui.UINode:
    connections = await _load_connections(ctx)
    if not connections:
        return ui.Empty(message="Connect an AWS account first.", icon="database")
    from handlers_clusters import list_clusters
    from schemas import ListClustersParams
    result = await list_clusters(ctx, ListClustersParams(connection_id=""))
    items = result.data.items if result.ok and result.data else []
    if not items:
        return ui.Empty(message="No Redshift clusters found in this region.", icon="database")
    return ui.DataTable(
        columns=[
            {"key": "cluster_identifier", "label": "Cluster"},
            {"key": "node_type", "label": "Node type"},
            {"key": "cluster_status", "label": "Status"},
            {"key": "number_of_nodes", "label": "Nodes"},
            {"key": "publicly_accessible", "label": "Public"},
            {"key": "db_name", "label": "DB name"},
        ],
        rows=[i.model_dump() for i in items],
    )


@ext.panel("redshift_serverless", slot="center", center_overlay=True)
async def redshift_serverless_panel(ctx) -> ui.UINode:
    connections = await _load_connections(ctx)
    if not connections:
        return ui.Empty(message="Connect an AWS account first.", icon="database")
    from handlers_serverless import list_workgroups
    from schemas import ListWorkgroupsParams
    result = await list_workgroups(ctx, ListWorkgroupsParams(connection_id=""))
    items = result.data.items if result.ok and result.data else []
    if not items:
        return ui.Empty(message="No Redshift Serverless workgroups found in this region.", icon="database")
    return ui.DataTable(
        columns=[
            {"key": "workgroup_name", "label": "Workgroup"},
            {"key": "namespace_name", "label": "Namespace"},
            {"key": "status", "label": "Status"},
            {"key": "base_capacity", "label": "Base capacity (RPU)"},
        ],
        rows=[i.model_dump() for i in items],
    )


@ext.panel("redshift_databases", slot="center", center_overlay=True)
async def redshift_databases_panel(ctx) -> ui.UINode:
    connections = await _load_connections(ctx)
    if not connections:
        return ui.Empty(message="Connect an AWS account first.", icon="database")
    return ui.Empty(
        message="Use the Query Editor to pick a cluster or workgroup and list its databases.",
        icon="database",
    )


@ext.panel("redshift_query", slot="center", center_overlay=True)
async def redshift_query_panel(ctx) -> ui.UINode:
    connections = await _load_connections(ctx)
    if not connections:
        return ui.Empty(message="Connect an AWS account first.", icon="database")
    from handlers_dataapi import list_statements
    from schemas import ListStatementsParams
    result = await list_statements(ctx, ListStatementsParams(connection_id="", max_results=25))
    items = result.data.items if result.ok and result.data else []
    table = ui.Empty(message="No recent queries.", icon="activity") if not items else ui.DataTable(
        columns=[
            {"key": "statement_id", "label": "Statement"},
            {"key": "status", "label": "Status"},
            {"key": "query_string", "label": "Query"},
            {"key": "created_at", "label": "Created"},
        ],
        rows=[i.model_dump() for i in items],
    )
    return ui.Stack(direction="v", gap=2, align="stretch", children=[
        ui.Form(
            action="execute_sql", submit_label="Выполнить запрос",
            children=[
              ui.Stack(direction="v", gap=3, align="stretch", children=[
                _field("Кластер (опционально)", ui.Input(
                    param_name="cluster_identifier",
                    placeholder="my-cluster (оставьте пустым для Serverless)",
                )),
                _field("Workgroup (опционально)", ui.Input(
                    param_name="workgroup_name",
                    placeholder="default (оставьте пустым для provisioned-кластера)",
                )),
                _field("База данных", ui.Input(
                    param_name="database",
                    placeholder="dev",
                )),
                _field("SQL-запрос", ui.Input(
                    param_name="sql",
                    placeholder="SELECT * FROM public.table LIMIT 100",
                )),
              ]),
            ],
        ),
        ui.Divider(),
        table,
    ])

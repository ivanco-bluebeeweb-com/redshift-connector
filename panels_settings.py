"""App settings panel -- connection management (disconnect rows) plus the
one-time onboarding instructions. Nothing here duplicates the sidebar.
"""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
from handlers_connection import _load_connections


@ext.panel("redshift_settings", slot="center", center_overlay=True)
async def redshift_settings(ctx) -> ui.UINode:
    connections = await _load_connections(ctx)
    rows = []
    for c in connections:
        rows.append(ui.Stack(direction="h", gap=2, align="center", children=[
            ui.Text(c.get("label") or c.get("access_key_id", ""), variant="body"),
            ui.Text(c.get("region", ""), variant="caption"),
            ui.Button(
                "Отключить", variant="destructive",
                on_click=ui.Call("disconnect_redshift", params={"connection_id": c.get("id", "")}),
            ),
        ]))
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Text("Как получить AWS-ключ доступа", variant="subtitle"),
        ui.Text(
            "В AWS Console откройте IAM > Users > (ваш пользователь) > "
            "Security credentials > Create access key. Убедитесь, что "
            "политике назначены права redshift-data:* и "
            "redshift:GetClusterCredentials (или "
            "redshift-serverless:GetCredentials) -- без них запросы через "
            "Data API будут падать с AccessDenied даже с рабочим ключом.",
            variant="body",
        ),
        ui.Divider(),
        ui.Text("Подключённые аккаунты", variant="subtitle"),
        *(rows if rows else [ui.Empty(message="Нет подключённых аккаунтов.", icon="database")]),
    ])

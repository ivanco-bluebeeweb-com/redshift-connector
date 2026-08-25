"""Amazon Redshift API client -- SigV4-signed requests over ctx.http,
across three AWS services: redshift (provisioned clusters + snapshots,
Query protocol/XML), redshift-serverless (workgroups/namespaces, JSON),
and redshift-data (the Data API that actually runs SQL, JSON).

WHY THREE DIFFERENT SERVICE HOSTS/PROTOCOLS, SAME REASONING AS AWS
CONNECTOR'S MULTI-SERVICE DISPATCH.

Redshift's control plane (`redshift.<region>.amazonaws.com`) is one of
AWS's older services and speaks the "Query" protocol: form-encoded
Action=/Version= parameters, XML responses -- same shape as AWS
Connector's EC2 calls. Redshift Serverless
(`redshift-serverless.<region>.amazonaws.com`) and the Redshift Data API
(`redshift-data.<region>.amazonaws.com`) are both modern JSON
request/response services identified by an X-Amz-Target header, same
shape as AWS Connector's Lambda calls. Reusing one dispatch style for all
three would mean force-fitting XML into a JSON client or vice versa --
so each gets its own small request builder, same principle as
aws_client.py's per-service functions.
"""
from __future__ import annotations

import json as _json
import xml.etree.ElementTree as ET

from aws_sigv4 import sign_request


class ClientFail(Exception):
    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        self.message = message
        self.status = status


def fail(message: str, status: int = 0):
    raise ClientFail(message, status)


def _redshift_host(region: str) -> str:
    return f"redshift.{region}.amazonaws.com"


def _serverless_host(region: str) -> str:
    return f"redshift-serverless.{region}.amazonaws.com"


def _data_api_host(region: str) -> str:
    return f"redshift-data.{region}.amazonaws.com"


def _creds(conn: dict) -> dict:
    return {
        "access_key_id": conn.get("access_key_id", ""),
        "secret_access_key": conn.get("secret_access_key", ""),
        "session_token": conn.get("session_token", "") or None,
        "region": conn.get("region", "us-east-1"),
    }


async def _query_request(ctx, conn: dict, action: str, version: str, params: dict) -> ET.Element:
    """POST a form-encoded 'Query protocol' request to the redshift
    control-plane service, and parse the XML response."""
    region = conn.get("region", "us-east-1")
    host = _redshift_host(region)
    body_params = {"Action": action, "Version": version}
    for k, v in params.items():
        if v is not None and v != "":
            body_params[k] = str(v)
    from urllib.parse import urlencode
    body = urlencode(body_params)
    headers = sign_request(
        method="POST", host=host, path="/", query="", body=body,
        service="redshift", extra_headers={"Content-Type": "application/x-www-form-urlencoded"},
        **_creds(conn),
    )
    resp = await ctx.http.post(f"https://{host}/", data=body, headers=headers)
    text = resp.text if hasattr(resp, "text") else str(resp.content)
    if resp.status_code >= 400:
        detail = _xml_error_detail(text) or text[:300]
        fail(f"Redshift API error ({resp.status_code}): {detail}", resp.status_code)
    try:
        return ET.fromstring(text)
    except ET.ParseError:
        fail(f"Redshift API returned unparsable XML: {text[:300]}")


def _xml_error_detail(text: str) -> str:
    try:
        root = ET.fromstring(text)
        for tag in (".//Message", ".//message"):
            el = root.find(tag)
            if el is not None and el.text:
                return el.text
    except ET.ParseError:
        pass
    return ""


def _ns_strip(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _xml_to_dicts(root: ET.Element, item_tag_suffix: str) -> list[dict]:
    """Flatten a Query-protocol XML response's repeated child elements
    (e.g. <Clusters><Cluster>...) into plain dicts."""
    out: list[dict] = []
    for el in root.iter():
        if _ns_strip(el.tag) == item_tag_suffix:
            d = {}
            for child in el:
                d[_ns_strip(child.tag)] = child.text
            out.append(d)
    return out


async def _json_request(ctx, conn: dict, service: str, host: str, target: str, payload: dict) -> dict:
    """POST a JSON request to a modern (redshift-serverless / redshift-data)
    AWS service, identified by X-Amz-Target."""
    body = _json.dumps(payload)
    headers = sign_request(
        method="POST", host=host, path="/", query="", body=body,
        service=service, extra_headers={
            "Content-Type": "application/x-amz-json-1.1",
            "X-Amz-Target": target,
        },
        **_creds(conn),
    )
    resp = await ctx.http.post(f"https://{host}/", data=body, headers=headers)
    try:
        data = resp.json() if hasattr(resp, "json") else _json.loads(resp.content)
    except Exception:
        data = {}
    if resp.status_code >= 400:
        detail = data.get("message") or data.get("Message") or str(data)
        fail(f"{service} API error ({resp.status_code}): {detail}", resp.status_code)
    return data or {}


# ── Clusters (provisioned) ─────────────────────────────────────────────

async def list_clusters(ctx, conn: dict) -> list[dict]:
    root = await _query_request(ctx, conn, "DescribeClusters", "2012-12-01", {})
    return _xml_to_dicts(root, "Cluster")


async def get_cluster(ctx, conn: dict, cluster_identifier: str) -> dict:
    root = await _query_request(ctx, conn, "DescribeClusters", "2012-12-01",
                                 {"ClusterIdentifier": cluster_identifier})
    rows = _xml_to_dicts(root, "Cluster")
    if not rows:
        fail(f"Cluster '{cluster_identifier}' not found.", 404)
    return rows[0]


async def delete_cluster(ctx, conn: dict, cluster_identifier: str, skip_final_snapshot: bool) -> None:
    params = {
        "ClusterIdentifier": cluster_identifier,
        "SkipFinalClusterSnapshot": "true" if skip_final_snapshot else "false",
    }
    await _query_request(ctx, conn, "DeleteCluster", "2012-12-01", params)


async def reboot_cluster(ctx, conn: dict, cluster_identifier: str) -> None:
    await _query_request(ctx, conn, "RebootCluster", "2012-12-01",
                          {"ClusterIdentifier": cluster_identifier})


async def resize_cluster(ctx, conn: dict, cluster_identifier: str, node_type: str,
                          number_of_nodes: int) -> None:
    params = {"ClusterIdentifier": cluster_identifier}
    if node_type:
        params["NodeType"] = node_type
    if number_of_nodes:
        params["NumberOfNodes"] = number_of_nodes
    await _query_request(ctx, conn, "ResizeCluster", "2012-12-01", params)


async def list_snapshots(ctx, conn: dict, cluster_identifier: str) -> list[dict]:
    params = {}
    if cluster_identifier:
        params["ClusterIdentifier"] = cluster_identifier
    root = await _query_request(ctx, conn, "DescribeClusterSnapshots", "2012-12-01", params)
    return _xml_to_dicts(root, "Snapshot")


# ── Redshift Serverless ─────────────────────────────────────────────────

async def list_workgroups(ctx, conn: dict) -> list[dict]:
    region = conn.get("region", "us-east-1")
    data = await _json_request(
        ctx, conn, "redshift-serverless", _serverless_host(region),
        "RedshiftServerless.ListWorkgroups", {},
    )
    return data.get("workgroups", [])


async def get_workgroup(ctx, conn: dict, workgroup_name: str) -> dict:
    region = conn.get("region", "us-east-1")
    data = await _json_request(
        ctx, conn, "redshift-serverless", _serverless_host(region),
        "RedshiftServerless.GetWorkgroup", {"workgroupName": workgroup_name},
    )
    wg = data.get("workgroup")
    if not wg:
        fail(f"Workgroup '{workgroup_name}' not found.", 404)
    return wg


async def list_namespaces(ctx, conn: dict) -> list[dict]:
    region = conn.get("region", "us-east-1")
    data = await _json_request(
        ctx, conn, "redshift-serverless", _serverless_host(region),
        "RedshiftServerless.ListNamespaces", {},
    )
    return data.get("namespaces", [])


# ── Data API (databases + SQL execution) ────────────────────────────────

async def list_databases(ctx, conn: dict, cluster_identifier: str, workgroup_name: str,
                          database: str, db_user: str) -> list[dict]:
    region = conn.get("region", "us-east-1")
    payload: dict = {"Database": database or "dev"}
    if cluster_identifier:
        payload["ClusterIdentifier"] = cluster_identifier
        if db_user:
            payload["DbUser"] = db_user
    elif workgroup_name:
        payload["WorkgroupName"] = workgroup_name
    else:
        fail("Either cluster_identifier or workgroup_name is required.")
    data = await _json_request(
        ctx, conn, "redshift-data", _data_api_host(region),
        "RedshiftData.ListDatabases", payload,
    )
    return [{"database_name": n} for n in data.get("Databases", [])]


async def execute_statement(ctx, conn: dict, sql: str, cluster_identifier: str,
                             workgroup_name: str, database: str, db_user: str) -> dict:
    region = conn.get("region", "us-east-1")
    payload: dict = {"Sql": sql, "Database": database or "dev"}
    if cluster_identifier:
        payload["ClusterIdentifier"] = cluster_identifier
        if db_user:
            payload["DbUser"] = db_user
    elif workgroup_name:
        payload["WorkgroupName"] = workgroup_name
    else:
        fail("Either cluster_identifier or workgroup_name is required.")
    return await _json_request(
        ctx, conn, "redshift-data", _data_api_host(region),
        "RedshiftData.ExecuteStatement", payload,
    )


async def describe_statement(ctx, conn: dict, statement_id: str) -> dict:
    region = conn.get("region", "us-east-1")
    return await _json_request(
        ctx, conn, "redshift-data", _data_api_host(region),
        "RedshiftData.DescribeStatement", {"Id": statement_id},
    )


async def get_statement_result(ctx, conn: dict, statement_id: str) -> dict:
    region = conn.get("region", "us-east-1")
    return await _json_request(
        ctx, conn, "redshift-data", _data_api_host(region),
        "RedshiftData.GetStatementResult", {"Id": statement_id},
    )


async def cancel_statement(ctx, conn: dict, statement_id: str) -> dict:
    region = conn.get("region", "us-east-1")
    return await _json_request(
        ctx, conn, "redshift-data", _data_api_host(region),
        "RedshiftData.CancelStatement", {"Id": statement_id},
    )


async def list_statements(ctx, conn: dict, max_results: int) -> list[dict]:
    region = conn.get("region", "us-east-1")
    data = await _json_request(
        ctx, conn, "redshift-data", _data_api_host(region),
        "RedshiftData.ListStatements", {"MaxResults": max_results or 20},
    )
    return data.get("Statements", [])

from typing import Any
from urllib.parse import quote, urlencode
from uuid import UUID

from clients.http_client import api_client
from config import oauth_required_scopes
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

"""
Registers governance approval-request operations with the MCP server.

Approval requests are the governed alternative to direct topic creation:
users without kafka:CreateTopic submit a topic-creation request, which a
governance admin then approves or rejects in Lenses. The agent hosts the
API (/api/v1/approvals) and enforces the governance:* IAM actions; HQ
proxies the calls per environment.

Approve/reject are deliberately not exposed. The agent's PUT
/approvals/{id}/approve performs no IAM check (login only), so a tool for it
would let any authenticated model approve its own request.
"""

APPROVAL_STATUSES = ["Pending", "Approved", "Rejected", "Failed"]
SORT_FIELDS = ["entityName", "createdBy", "createdAt"]
SORT_ORDERS = ["asc", "desc"]


def register_approvals(mcp: FastMCP):

    @mcp.tool(auth=oauth_required_scopes("write"))
    async def request_topic_creation(
        environment: str,
        topic_name: str,
        reason: str,
        partitions: int = 1,
        replication: int = 1,
        configs: dict[str, str] | None = None,
        tags: list[str] | None = None,
        records_size: int | None = None,
        data_produced_per_day: int | None = None,
        consumers: int | None = None,
    ) -> dict[str, Any]:
        """
        Submit a topic-creation approval request (the governed alternative to create_topic).

        Use this when the caller lacks the kafka:CreateTopic permission and topic
        creation must go through governance approval. The topic is only created
        once a governance admin approves the request in Lenses.

        Args:
            environment: The environment name.
            topic_name: Name of the topic to request.
            reason: Why the topic is needed (shown to the approver).
            partitions: Number of partitions (default: 1).
            replication: Replication factor (default: 1). Must not exceed the
                number of brokers in the cluster.
            configs: Topic configurations, e.g. {"retention.ms": "86400000"}.
            tags: Tags describing the topic.
            records_size: Expected record size (capacity planning, optional).
            data_produced_per_day: Expected data produced per day (optional).
            consumers: Expected number of consumers (optional).

        Returns:
            The created request, e.g. {"id": "<uuid>"}. Track it with
            get_approval_request.
        """
        settings: dict[str, Any] = {
            "replication": replication,
            "partitions": partitions,
            "capacity": {
                "recordsSize": records_size,
                "dataProducedPerDay": data_produced_per_day,
                "consumers": consumers,
            },
        }
        # Omitted rather than sent as null when empty: the agent reads a missing
        # key as None, and the omission shape is what was verified against 6.2.5.
        if configs:
            settings["topicConfig"] = configs

        payload = {
            # The discriminator is required -- the agent's NewRequest is a circe
            # union, and it rejects the body without it with an opaque decode error.
            "type": "CreateNewEntity",
            "entityName": topic_name,
            "entityType": "KafkaTopic",
            "settings": settings,
            "metadata": {"reason": reason, "tags": tags or []},
        }

        endpoint = f"/api/v1/environments/{environment}/proxy/api/v1/approvals"
        try:
            return await api_client._make_request("POST", endpoint, payload)
        except Exception as e:
            # ToolError so the agent's own validation ("Topic X already exists",
            # "replication exceeds broker count") survives mask_error_details.
            raise ToolError(f"Topic creation request failed: {e}") from e

    @mcp.tool(auth=oauth_required_scopes("read"))
    async def list_approval_requests(
        environment: str,
        statuses: list[str] | None = None,
        entity_name: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_field: str | None = None,
        sort_order: str | None = None,
    ) -> dict[str, Any]:
        """
        List topic-creation approval requests.

        Note: a caller without the governance:ListRequests permission gets an
        empty page, not an error.

        Args:
            environment: The environment name.
            statuses: Filter by status: "Pending", "Approved", "Rejected", "Failed".
            entity_name: Filter by matching topic name (substring).
            page: Page number (default: 1).
            page_size: Items per page (default: 25).
            sort_field: Field to sort by: "entityName", "createdBy", "createdAt"
                (default: "createdAt", newest first).
            sort_order: Sorting order - "asc" or "desc".

        Returns:
            Paginated requests: {"values": [...], "pagesAmount": N, "totalCount": N}.
        """
        # Validated here, and raised as ToolError, because the agent's own error
        # for a bad enum is circe decode noise -- and because anything that is not
        # a ToolError is replaced with "Error calling tool" before the model sees
        # it (the server runs with mask_error_details=True).
        if statuses:
            invalid = [s for s in statuses if s not in APPROVAL_STATUSES]
            if invalid:
                raise ToolError(f"Invalid statuses {invalid}. Must be one of: {', '.join(APPROVAL_STATUSES)}")
        if sort_field and sort_field not in SORT_FIELDS:
            raise ToolError(f"sort_field must be one of: {', '.join(SORT_FIELDS)}")
        if sort_order and sort_order not in SORT_ORDERS:
            raise ToolError(f"sort_order must be one of: {', '.join(SORT_ORDERS)}")

        # pageSize is required by the agent API -- it has no server-side default.
        query_params = [("page", str(page)), ("pageSize", str(page_size))]
        for status in statuses or []:
            query_params.append(("approvalStatus", status))
        if entity_name:
            query_params.append(("entityName", entity_name))
        if sort_field:
            query_params.append(("sortField", sort_field))
        if sort_order:
            query_params.append(("sortOrder", sort_order))

        # urlencode, not f-strings: entity_name is model-supplied, and httpx2
        # percent-encodes spaces in a raw query string but leaves "&" and "="
        # alone -- so an unencoded value could inject extra query parameters.
        query_string = urlencode(query_params, quote_via=quote)
        endpoint = f"/api/v1/environments/{environment}/proxy/api/v1/approvals?{query_string}"
        return await api_client._make_request("GET", endpoint)

    @mcp.tool(auth=oauth_required_scopes("read"))
    async def get_approval_request(environment: str, request_id: str) -> dict[str, Any]:
        """
        Get the details of an approval request.

        Args:
            environment: The environment name.
            request_id: The request id (UUID) returned by request_topic_creation.

        Returns:
            Request details including entityName, settings, metadata,
            approvalStatus ("Pending", "Approved", "Rejected" or "Failed"),
            createdBy/createdAt, reviewedBy/reviewedAt, rejectionReason,
            failureReason, and the defaultTopicConfig that will apply where
            the request didn't set a value.
        """
        # request_id lands in the URL path, and httpx2 resolves dot segments
        # before the request goes out ("/approvals/../x" becomes "/x"), so a
        # malformed id would quietly retarget the call at another HQ endpoint
        # using our credentials. A UUID is also a clearer error than a 404.
        try:
            UUID(request_id)
        except ValueError as e:
            raise ToolError(f"request_id must be a UUID, got {request_id!r}") from e

        endpoint = f"/api/v1/environments/{environment}/proxy/api/v1/approvals/{request_id}"
        return await api_client._make_request("GET", endpoint)

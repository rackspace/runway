"""Tests for runway.cfngin.hooks.ecs."""

# pyright: basic
from __future__ import annotations

from typing import TYPE_CHECKING

from runway._logging import LogLevels
from runway.cfngin.hooks.ecs import create_clusters

if TYPE_CHECKING:
    from mypy_boto3_ecs.type_defs import ClusterTypeDef
    from pytest import LogCaptureFixture

    from ...factories import MockCFNginContext

MODULE = "runway.cfngin.hooks.ecs"


def test_create_clusters(caplog: LogCaptureFixture, cfngin_context: MockCFNginContext) -> None:
    """Test create_clusters."""
    caplog.set_level(LogLevels.DEBUG, MODULE)
    stub = cfngin_context.add_stubber("ecs")
    clusters: dict[str, ClusterTypeDef] = {
        "foo": {"clusterName": "foo"},
        "bar": {"clusterName": "bar"},
    }

    stub.add_response("create_cluster", {"cluster": clusters["foo"]}, {"clusterName": "foo"})
    stub.add_response("create_cluster", {"cluster": clusters["bar"]}, {"clusterName": "bar"})

    with stub:
        assert create_clusters(cfngin_context, clusters=list(clusters)) == {
            "clusters": {k: {"cluster": v} for k, v in clusters.items()}
        }
    stub.assert_no_pending_responses()

    for cluster in clusters:
        assert f"creating ECS cluster: {cluster}" in caplog.messages


def test_create_clusters_str(cfngin_context: MockCFNginContext) -> None:
    """Test create_clusters with ``clusters`` provided as str."""
    stub = cfngin_context.add_stubber("ecs")
    cluster_name = "foo"

    stub.add_response(
        "create_cluster",
        {"cluster": {"clusterName": cluster_name}},
        {"clusterName": cluster_name},
    )

    with stub:
        assert create_clusters(cfngin_context, clusters=cluster_name) == {
            "clusters": {cluster_name: {"cluster": {"clusterName": cluster_name}}}
        }
    stub.assert_no_pending_responses()

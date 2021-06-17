"""AWS ECS hook.

A lot of this code exists to deal w/ the broken ECS connect_to_region
function, and will be removed once this pull request is accepted:
https://github.com/boto/boto/pull/3143

"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Union

from typing_extensions import TypedDict

if TYPE_CHECKING:
    from mypy_boto3_ecs.type_defs import CreateClusterResponseTypeDef

    from ...context import CfnginContext

LOGGER = logging.getLogger(__name__)


class CreateClustersResponseTypeDef(TypedDict):
    """Response from create_clusters."""

    clusters: Dict[str, CreateClusterResponseTypeDef]


def create_clusters(
    context: CfnginContext, *, clusters: Union[List[str], str], **_: Any
) -> CreateClustersResponseTypeDef:
    """Create ECS clusters.

    Args:
        context: CFNgin context object.
        clusters: Names of clusters to create.

    """
    conn = context.get_session().client("ecs")
    if isinstance(clusters, str):
        clusters = [clusters]

    cluster_info: Dict[str, Any] = {}
    for cluster in clusters:
        LOGGER.debug("creating ECS cluster: %s", cluster)
        response = conn.create_cluster(clusterName=cluster)
        cluster_info[response.get("cluster", {}).get("clusterName", "")] = response
    return {"clusters": cluster_info}

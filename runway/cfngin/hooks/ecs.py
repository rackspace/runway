"""AWS ECS hook."""
# pylint: disable=no-self-argument,no-self-use
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Union

from pydantic import validator
from typing_extensions import TypedDict

from ...utils import BaseModel

if TYPE_CHECKING:
    from mypy_boto3_ecs.type_defs import CreateClusterResponseTypeDef

    from ...context import CfnginContext

LOGGER = logging.getLogger(__name__)


class CreateClustersHookArgs(BaseModel):
    """Hook arguments for ``create_clusters``."""

    clusters: List[str]
    """List of cluster names to create."""

    @validator("clusters", allow_reuse=True, pre=True)
    def _convert_clusters(cls, v: Union[List[str], str]) -> List[str]:
        """Convert value of ``clusters`` from str to list."""
        if isinstance(v, str):
            return [v]
        return v


class CreateClustersResponseTypeDef(TypedDict):
    """Response from create_clusters."""

    clusters: Dict[str, CreateClusterResponseTypeDef]


def create_clusters(
    context: CfnginContext, *__args: Any, **kwargs: Any
) -> CreateClustersResponseTypeDef:
    """Create ECS clusters.

    Args:
        context: CFNgin context object.

    """
    args = CreateClustersHookArgs.parse_obj(kwargs)
    ecs_client = context.get_session().client("ecs")

    cluster_info: Dict[str, Any] = {}
    for cluster in args.clusters:
        LOGGER.debug("creating ECS cluster: %s", cluster)
        response = ecs_client.create_cluster(clusterName=cluster)
        cluster_info[response.get("cluster", {}).get("clusterName", "")] = response
    return {"clusters": cluster_info}

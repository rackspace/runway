"""AWS ECS hook."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, List  # noqa: UP035

from pydantic import validator
from typing_extensions import TypedDict

from ...utils import BaseModel

if TYPE_CHECKING:
    from mypy_boto3_ecs.type_defs import CreateClusterResponseTypeDef

    from ...context import CfnginContext

LOGGER = logging.getLogger(__name__)


class CreateClustersHookArgs(BaseModel):
    """Hook arguments for ``create_clusters``."""

    clusters: List[str]  # noqa: UP006
    """List of cluster names to create."""

    @validator("clusters", allow_reuse=True, pre=True)  # type: ignore
    def _convert_clusters(cls, v: list[str] | str) -> list[str]:  # noqa: N805
        """Convert value of ``clusters`` from str to list."""
        if isinstance(v, str):
            return [v]
        return v


class CreateClustersResponseTypeDef(TypedDict):
    """Response from create_clusters."""

    clusters: dict[str, CreateClusterResponseTypeDef]


def create_clusters(
    context: CfnginContext, *_args: Any, **kwargs: Any
) -> CreateClustersResponseTypeDef:
    """Create ECS clusters.

    Args:
        context: CFNgin context object.
        **kwargs: Arbitrary keyword arguments.

    """
    args = CreateClustersHookArgs.parse_obj(kwargs)
    ecs_client = context.get_session().client("ecs")

    cluster_info: dict[str, Any] = {}
    for cluster in args.clusters:
        LOGGER.debug("creating ECS cluster: %s", cluster)
        response = ecs_client.create_cluster(clusterName=cluster)
        cluster_info[response.get("cluster", {}).get("clusterName", "")] = response
    return {"clusters": cluster_info}

"""AWS ECS hook.

A lot of this code exists to deal w/ the broken ECS connect_to_region
function, and will be removed once this pull request is accepted:
https://github.com/boto/boto/pull/3143

"""
# pylint: disable=unused-argument
import logging

from six import string_types

from ..session_cache import get_session

LOGGER = logging.getLogger(__name__)


def create_clusters(provider, context, **kwargs):
    """Create ECS clusters.

    Expects a "clusters" argument, which should contain a list of cluster
    names to create.

    Args:
        provider (:class:`runway.cfngin.providers.base.BaseProvider`): Provider
            instance.
        context (:class:`runway.cfngin.context.Context`): Context instance.

    Returns:
        bool: Whether or not the hook succeeded.

    """
    conn = get_session(provider.region).client('ecs')

    try:
        clusters = kwargs["clusters"]
    except KeyError:
        LOGGER.error("setup_clusters hook missing \"clusters\" argument")
        return False

    if isinstance(clusters, string_types):
        clusters = [clusters]

    cluster_info = {}
    for cluster in clusters:
        LOGGER.debug("Creating ECS cluster: %s", cluster)
        response = conn.create_cluster(clusterName=cluster)
        cluster_info[response["cluster"]["clusterName"]] = response
    return {"clusters": cluster_info}

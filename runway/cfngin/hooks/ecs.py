"""AWS ECS hook.

A lot of this code exists to deal w/ the broken ECS connect_to_region
function, and will be removed once this pull request is accepted:
https://github.com/boto/boto/pull/3143

"""
import logging

LOGGER = logging.getLogger(__name__)


def create_clusters(context, *_, **kwargs):
    """Create ECS clusters.

    Args:
        context (:class:`runway.cfngin.context.Context`): Context instance.
            (passed in by CFNgin)

    Keyword Args:
        clusters (List[str]): Names of clusters to create.


    Returns:
        bool: Whether or not the hook succeeded.

    """
    conn = context.get_session().client("ecs")

    try:
        clusters = kwargs["clusters"]
    except KeyError:
        LOGGER.error("clusters argument required but not provided")
        return False

    if isinstance(clusters, str):
        clusters = [clusters]

    cluster_info = {}
    for cluster in clusters:
        LOGGER.debug("creating ECS cluster: %s", cluster)
        response = conn.create_cluster(clusterName=cluster)
        cluster_info[response["cluster"]["clusterName"]] = response
    return {"clusters": cluster_info}

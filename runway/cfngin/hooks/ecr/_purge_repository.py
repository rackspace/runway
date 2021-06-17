"""Purge all images from an ECR repository."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from mypy_boto3_ecr.client import ECRClient
    from mypy_boto3_ecr.type_defs import ImageIdentifierTypeDef

    from ....context import CfnginContext

LOGGER = logging.getLogger(__name__.replace("._", "."))


def delete_ecr_images(
    client: ECRClient,
    image_ids: List[ImageIdentifierTypeDef],
    repository_name: str,
) -> None:
    """Delete images from an ECR repository."""
    response = client.batch_delete_image(
        repositoryName=repository_name, imageIds=image_ids
    )
    if "failures" in response and response["failures"]:
        for msg in response["failures"]:
            LOGGER.info(
                "failed to delete image %s: (%s) %s",
                msg.get("imageId", {}).get("imageDigest")
                or msg.get("imageId", {}).get("imageTag"),
                msg.get("failureCode"),
                msg.get("failureReason"),
            )
        raise ValueError("failures present in response")


def list_ecr_images(
    client: ECRClient, repository_name: str
) -> List[ImageIdentifierTypeDef]:
    """List all images in an ECR repository."""
    image_ids: List[ImageIdentifierTypeDef] = []
    try:
        response = client.list_images(
            repositoryName=repository_name, filter={"tagStatus": "ANY"}
        )
        image_ids.extend(response["imageIds"])
        while response.get("nextToken"):
            response = client.list_images(
                filter={"tagStatus": "ANY"},
                nextToken=response["nextToken"],
                repositoryName=repository_name,
            )
            image_ids.extend(response["imageIds"])
        return [
            {"imageDigest": digest}
            for digest in {
                image["imageDigest"] for image in image_ids if image.get("imageDigest")
            }
        ]
    except client.exceptions.RepositoryNotFoundException:
        LOGGER.info("repository %s does not exist", repository_name)
        return []


def purge_repository(
    context: CfnginContext,
    repository_name: str,
    **_: Any,
) -> Dict[str, str]:
    """Purge all images from an ECR repository.

    Args:
        context: CFNgin context object.
        repository_name: Name of the repository to purge.

    """
    client = context.get_session().client("ecr")
    image_ids = list_ecr_images(client, repository_name=repository_name)
    if not image_ids:
        LOGGER.info("no images found in repository %s", repository_name)
        return {"status": "skipped"}
    delete_ecr_images(client, image_ids=image_ids, repository_name=repository_name)
    LOGGER.info("purged all images from repository")
    return {"status": "success"}

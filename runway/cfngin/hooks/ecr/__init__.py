"""AWS Elastic Container Registry (ECR) hook."""
from ._purge_repository import purge_repository

__all__ = ["purge_repository"]

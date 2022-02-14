"""Docker login hook."""
# pylint: disable=no-self-argument,no-self-use
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

from pydantic import Field, validator

from ....utils import BaseModel
from .data_models import ElasticContainerRegistry
from .hook_data import DockerHookData

if TYPE_CHECKING:
    from ....context import CfnginContext

LOGGER = logging.getLogger(__name__.replace("._", "."))


class LoginArgs(BaseModel):
    """Args passed to the docker.login hook."""

    _ctx: Optional[CfnginContext] = Field(default=None, alias="context", exclude=True)

    dockercfg_path: Optional[str] = None
    """Path to a non-default Docker config file."""

    ecr: Optional[ElasticContainerRegistry] = Field(default=None, exclude=True)
    """Information describing an ECR registry."""

    email: Optional[str] = None
    """The email for the registry account."""

    password: str
    """The plaintext password for the registry account."""

    registry: Optional[str] = None
    """URI of the registry to login to."""

    username: str = "AWS"
    """The registry username."""

    @validator("ecr", pre=True, allow_reuse=True)
    def _set_ecr(cls, v: Any, values: Dict[str, Any]) -> Any:
        """Set the value of ``ecr``."""
        if v and isinstance(v, dict):
            return ElasticContainerRegistry.parse_obj(
                {"context": values.get("context"), **v}
            )
        return v

    @validator("registry", pre=True, always=True, allow_reuse=True)
    def _set_registry(cls, v: Any, values: Dict[str, Any]) -> Any:
        """Set the value of ``registry``."""
        if v:
            return v

        ecr: Optional[ElasticContainerRegistry] = values.get("ecr")
        if ecr:
            return ecr.fqn

        return None


def login(*, context: CfnginContext, **kwargs: Any) -> DockerHookData:
    """Docker login hook.

    Replicates the functionality of ``docker login`` cli command.

    kwargs are parsed by :class:`~runway.cfngin.hooks.docker.LoginArgs`.

    """
    args = LoginArgs.parse_obj({"context": context, **kwargs})
    docker_hook_data = DockerHookData.from_cfngin_context(context)
    docker_hook_data.client.login(**args.dict())
    LOGGER.info("logged into %s", args.registry)
    return docker_hook_data.update_context(context)

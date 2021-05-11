"""Docker login hook.

Replicates the functionality of the ``docker login`` CLI command.

This hook does not modify the Docker config file.
The credentials/authenticated session is stored in memory and is deleted after
processing a given CFNgin config file.

This hook can be executed as a pre or post hook.
The authenticated session carries over from pre to post and to each subsequent
built-in Docker hook.

.. rubric:: Hook Path

``runway.cfngin.hooks.docker.login``

.. rubric:: Args

dockercfg_path (Optional[str])
    Use a custom path for the Docker config file (``$HOME/.docker/config.json``
    if present, otherwise ``$HOME/.dockercfg``).
ecr (Optional[Union[bool, Dict[str, Optional[str]]]])
    Information describing an ECR registry. This is used to construct the registry URL.
    If providing a value for this field, do not provide a value for ``registry``.

    If using a private registry, the value can simply be ``true``.
    If using a public registry, more information is required.

    account_id (Optional[str])
        AWS account ID that owns the registry being logged into. If not provided,
        it will be acquired automatically if needed.
    alias (Optional[str])
        If it is a public repository, provide the alias.
    aws_region (Optional[str])
        AWS region where the registry is located. If not provided, it will be acquired
        automatically if needed.

email (Optional[str])
    The email for the registry account.
password (str)
    The plaintext password.
registry (Optional[str])
    URL to the registry (e.g. ``https://index.docker.io/v1/``).

    If providing a value for this field, do not provide a value for ``ecr``.
username (str)
    The registry username. Defaults to ``AWS`` if supplying ``ecr``.

.. rubric:: Example
.. code-block:: yaml

    pre_deploy:
      - path: runway.cfngin.hooks.docker.login
        args:
          ecr: true
          password: ${ecr login-password}

"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional, Union, cast

from .data_models import BaseModel, ElasticContainerRegistry
from .hook_data import DockerHookData

if TYPE_CHECKING:
    from ....context import CfnginContext

LOGGER = logging.getLogger(__name__.replace("._", "."))


class LoginArgs(BaseModel):
    """Args passed to the docker.login hook.

    Attributes:
        dockercfg_path: Path to a non-default Docker config file.
        email: The email for the registry account.
        password: The plaintext password for the registry account.
        registry: URI of the registry to login to.
        username: The registry username.

    """

    def __init__(
        self,
        *,
        context: Optional[CfnginContext] = None,
        dockercfg_path: Optional[str] = None,
        ecr: Optional[Union[bool, Dict[str, Optional[str]]]] = None,
        email: Optional[str] = None,
        password: str,
        registry: Optional[str] = None,
        username: Optional[str] = None,
        **_: Any,
    ) -> None:
        """Instantiate class.

        Args:
            context: CFNgin context object.
            dockercfg_path: Use a custom path for the Docker config file
                (``$HOME/.docker/config.json`` if present, otherwise ``$HOME/.dockercfg``).
            ecr: Information describing an ECR registry. This is used to construct
                the registry URL. If providing a value for this field, do not provide
                a value for ``registry``.
            email: The email for the registry account.
            password: The plaintext password for the registry account.
            registry: URL to the registry (e.g. ``https://index.docker.io/v1/``).
            username: The registry username.
                Defaults to ``AWS`` if supplying ``ecr``.

        """
        super().__init__(context=context)
        self.dockercfg_path = self._validate_str(dockercfg_path, optional=True)
        self.email = self._validate_str(email, optional=True)
        self.password = cast(str, self._validate_str(password, required=True))
        self.registry = self.determine_registry(
            context=context, ecr=ecr, registry=registry
        )
        if not username:
            self.username = cast(
                str, ("AWS" if ecr else self._validate_str(username, required=True))
            )
        else:
            self.username = cast(str, self._validate_str(username, required=True))

    @staticmethod
    def determine_registry(
        context: Optional[CfnginContext] = None,
        ecr: Optional[Union[bool, Dict[str, Optional[str]]]] = None,
        registry: Optional[str] = None,
    ) -> Optional[str]:
        """Determine repository URI."""
        if registry:
            return registry
        if ecr:
            return ElasticContainerRegistry.parse_obj(
                ecr if isinstance(ecr, dict) else {}, context=context  # type: ignore
            ).fqn
        return None


def login(*, context: CfnginContext, **kwargs: Any) -> DockerHookData:
    """Docker login hook.

    Replicates the functionality of ``docker login`` cli command.

    kwargs are parsed by :class:`~runway.cfngin.hooks.docker.LoginArgs`.

    """
    kwargs.pop("provider", None)
    args = LoginArgs.parse_obj(kwargs, context=context)
    docker_hook_data = DockerHookData.from_cfngin_context(context)
    docker_hook_data.client.login(**args.dict())
    LOGGER.info("logged into %s", args.registry)
    return docker_hook_data.update_context(context)

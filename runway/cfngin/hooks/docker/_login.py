"""Docker login action.

Replicates the functionality of ``docker login`` cli command.

CLI docs: https://docs.docker.com/engine/reference/commandline/login/

"""
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

from ._data_models import BaseModel, ElasticContainerRegistry
from ._hook_data import DockerHookData

if TYPE_CHECKING:
    from ....context import Context

LOGGER = logging.getLogger(__name__.replace("._", "."))


class LoginArgs(BaseModel):
    """Args passed to login."""

    _ctx: Optional["Context"]
    dockercfg_path: str
    email: str
    password: str
    registry: str
    username: str

    def __init__(
        self,
        password,  # type: str
        context=None,  # type: Optional["Context"]
        dockercfg_path=None,  # type: Optional[str]
        ecr=None,  # type: Optional[Union[bool, Dict[str, Optional[str]]]]
        email=None,  # type: Optional[str]
        registry=None,  # type: Optional[str]
        username=None,  # type: Optional[str]
    ):  # type: (...) -> None
        """Instantiate class."""
        self._ctx = context
        self.dockercfg_path = self._validate_str(dockercfg_path, optional=True)
        self.email = self._validate_str(email, optional=True)
        self.password = self._validate_str(password, required=True)
        self.registry = self.determine_registry(
            context=context, ecr=ecr, registry=registry
        )
        if not username:
            self.username = (
                "AWS" if ecr else self._validate_str(username, required=True)
            )

    @staticmethod
    def determine_registry(
        context=None,  # type: Optional["Context"]
        ecr=None,  # type: Optional[Union[bool, Dict[str, Optional[str]]]]
        registry=None,  # type: Optional[str]
    ):  # type: (...) -> Optional[str]
        """Determine repository URI."""
        if registry:
            return registry
        if ecr:
            return ElasticContainerRegistry.parse_obj(
                ecr if isinstance(ecr, dict) else {}, context=context
            ).fqn
        return None


def login(**kwargs):  # type: (Any) -> DockerHookData
    """Docker login hook.

    Replicates the functionality of ``docker login`` cli command.

    Keyword Args:
        dockercfg_path (Optional[str]): Use a custom path for the Docker config file
            (default ``$HOME/.docker/config.json`` if present,
            otherwise``$HOME/.dockercfg``).
        ecr (:class:`runway.cfngin.hooks.docker._data_models.ElasticContainerRegistry`):
            Information describing an ECR registry.
        email (Optional[str]): The email for the registry account.
        password (str): The plaintext password.
        registry (Optional[str]): URL to the registry (e.g. https://index.docker.io/v1/``)
        username (str): The registry username. Optional if supplying ``ecr``.

    """
    context = kwargs.pop("context")  # type: "Context"
    kwargs.pop("provider", None)  # not needed
    args = LoginArgs.parse_obj(kwargs, context=context)
    docker_hook_data = DockerHookData.from_cfngin_context(context)
    docker_hook_data.client.login(**args.dict())
    LOGGER.info("logged into %s", args.registry)
    return docker_hook_data.update_context(context)

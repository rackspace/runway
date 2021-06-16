"""K8s (kustomize) module."""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, cast

from typing_extensions import Literal

from .._logging import PrefixAdaptor
from ..compat import cached_property
from ..config.models.runway.options.k8s import RunwayK8sModuleOptionsDataModel
from ..core.components import DeployEnvironment
from ..env_mgr.kbenv import KBEnvManager
from ..exceptions import KubectlVersionNotSpecified
from ..utils import which
from .base import ModuleOptions, RunwayModule
from .utils import run_module_command

if TYPE_CHECKING:
    from .._logging import RunwayLogger
    from ..context import RunwayContext

LOGGER = cast("RunwayLogger", logging.getLogger(__name__))

KubectlCommandTypeDef = Literal[
    "annotation",
    "apply",
    "auth",
    "autoscale",
    "cp",
    "create",
    "delete",
    "describe",
    "diff",
    "edit",
    "exec",
    "expose",
    "get",
    "kustomize",
    "label",
    "logs",
    "patch",
    "port-forward",
    "proxy",
]


class K8s(RunwayModule):
    """Kubectl Runway Module."""

    options: K8sOptions

    def __init__(
        self,
        context: RunwayContext,
        *,
        explicitly_enabled: Optional[bool] = False,
        logger: RunwayLogger = LOGGER,
        module_root: Path,
        name: Optional[str] = None,
        options: Optional[Union[Dict[str, Any], ModuleOptions]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        **_: Any,
    ) -> None:
        """Instantiate class.

        Args:
            context: Runway context object for the current session.
            explicitly_enabled: Whether or not the module is explicitly enabled.
                This is can be set in the event that the current environment being
                deployed to matches the defined environments of the module/deployment.
            logger: Used to write logs.
            module_root: Root path of the module.
            name: Name of the module.
            options: Options passed to the module class from the config as ``options``
                or ``module_options`` if coming from the deployment level.
            parameters: Values to pass to the underlying infrastructure as code
                tool that will alter the resulting infrastructure being deployed.
                Used to templatize IaC.

        """
        super().__init__(
            context,
            explicitly_enabled=explicitly_enabled,
            logger=logger,
            module_root=module_root,
            name=name,
            options=K8sOptions.parse_obj(
                deploy_environment=context.env, obj=options or {}, path=module_root
            ),
            parameters=parameters,
        )
        # logger needs to be created here to use the correct logger
        self.logger = PrefixAdaptor(self.name, LOGGER)

    @cached_property
    def kbenv(self) -> KBEnvManager:
        """Kubectl environmet manager."""
        return KBEnvManager(self.path)

    @cached_property
    def kubectl_bin(self) -> str:
        """Path to kubectl binary."""
        try:
            return self.kbenv.install(self.options.kubectl_version)
        except KubectlVersionNotSpecified as exc:
            self.logger.verbose("kubectl version not specified; checking path")
            if not which("kubectl"):
                self.logger.error(
                    "kubectl not available and a version to install not specified"
                )
                self.logger.error(exc.message)
                sys.exit(1)
            return "kubectl"

    @cached_property
    def skip(self) -> bool:
        """Determine if the module should be skipped."""
        if self.options.kustomize_config.is_file():
            LOGGER.info(
                "processing kustomize overlay: %s", self.options.kustomize_config
            )
            return False
        LOGGER.info(
            "skipped; kustomize overlay for this environment/region not"
            " found -- looking for one of: %s",
            ", ".join(
                str(self.path / "overlays" / i / "kustomization.yaml")
                for i in self.options.gen_overlay_dirs(
                    self.ctx.env.name, self.ctx.env.aws_region
                )
            ),
        )
        return True

    def deploy(self) -> None:
        """Run kubectl apply."""
        if self.skip:
            return
        self.kubectl_kustomize()
        self.kubectl_apply()

    def destroy(self) -> None:
        """Run kubectl delete."""
        if self.skip:
            return
        self.kubectl_kustomize()
        self.kubectl_delete()

    def gen_cmd(
        self,
        command: KubectlCommandTypeDef,
        args_list: Optional[List[str]] = None,
    ) -> List[str]:
        """Generate and log a kubectl command.

        This does not execute the command, only prepares it for use.

        Args:
            command: The CDK command to be executed.
            args_list: Additional arguments to include in the generated command.

        Returns:
            The full command to be passed into a subprocess.

        """
        cmd_list = [self.kubectl_bin, command]
        cmd_list.extend(args_list or [])
        if command in ["apply", "delete"]:
            cmd_list.extend(["--kustomize", str(self.options.overlay_path)])
            if command == "delete":
                cmd_list.append("--ignore-not-found=true")
        elif command == "kustomize":
            cmd_list.append(str(self.options.overlay_path))
        LOGGER.debug("running command: %s", " ".join(cmd_list))
        return cmd_list

    def init(self) -> None:
        """Run init."""
        LOGGER.warning("init not currently supported for %s", self.__class__.__name__)

    def kubectl_apply(self) -> None:
        """Execute ``kubectl apply`` command.

        https://kubectl.docs.kubernetes.io/references/kubectl/apply/

        """
        self.logger.info("deploy (in progress)")
        run_module_command(
            cmd_list=self.gen_cmd("apply"),
            env_vars=self.ctx.env.vars,
            logger=self.logger,
        )
        self.logger.info("deploy (complete)")

    def kubectl_delete(self) -> None:
        """Execute ``kubectl delete`` command.

        https://kubectl.docs.kubernetes.io/references/kubectl/delete/

        """
        self.logger.info("destroy (in progress)")
        run_module_command(
            cmd_list=self.gen_cmd("delete"),
            env_vars=self.ctx.env.vars,
            logger=self.logger,
        )
        self.logger.info("destroy (complete)")

    def kubectl_kustomize(self) -> str:
        """Execute ``kubectl kustomize`` command.

        https://kubectl.docs.kubernetes.io/references/kubectl/kustomize/

        """
        kustomize_yml = subprocess.check_output(
            self.gen_cmd("kustomize"), env=self.ctx.env.vars
        ).decode()
        self.logger.debug("kustomized yaml generated by kubectl:\n\n%s", kustomize_yml)
        return kustomize_yml

    def plan(self) -> None:
        """Run kustomize build and display generated plan."""
        if self.skip:
            return
        self.logger.info(
            "kustomized yaml generated by kubectl:\n\n%s", self.kubectl_kustomize()
        )


class K8sOptions(ModuleOptions):
    """Module options for Kubernetes.

    Attributes:
        data: Options parsed into a data model.
        deploy_environment: Runway deploy environment object.
        kubectl_version: Version of kubectl to use.
        path: Module path.

    """

    data: RunwayK8sModuleOptionsDataModel
    deploy_environment: DeployEnvironment
    kubectl_version: Optional[str]
    path: Path

    def __init__(
        self,
        data: RunwayK8sModuleOptionsDataModel,
        deploy_environment: DeployEnvironment,
        path: Path,
    ) -> None:
        """Instantiate class.

        Args:
            data: Options parsed into a data model.
            deploy_environment: Current deploy environment.
            path: Module path.

        """
        self.data = data
        self.env = deploy_environment
        self.kubectl_version = data.kubectl_version
        self.path = path

    @cached_property
    def kustomize_config(self) -> Path:
        """Kustomize configuration file."""
        return self.overlay_path / "kustomization.yaml"

    @cached_property
    def overlay_path(self) -> Path:
        """Directory containing the kustomize overlay to use."""
        if self.data.overlay_path:
            return self.data.overlay_path
        return self.get_overlay_dir(
            path=self.path / "overlays",
            environment=self.env.name,
            region=self.env.aws_region,
        )

    @staticmethod
    def gen_overlay_dirs(environment: str, region: str) -> List[str]:
        """Generate possible overlay directories.

        Prefers more explicit direcory name but falls back to environmet name only.

        Args:
            environment: Current deploy environment.
            region : Current AWS region.

        """
        return [f"{environment}-{region}", environment]

    @classmethod
    def get_overlay_dir(cls, path: Path, environment: str, region: str) -> Path:
        """Determine the overlay directory to use."""
        overlay_dir = path
        for name in cls.gen_overlay_dirs(environment, region):
            overlay_dir = path / name
            if (overlay_dir / "kustomization.yaml").is_file():
                return overlay_dir
        return overlay_dir

    @classmethod
    def parse_obj(
        cls,
        deploy_environment: DeployEnvironment,
        obj: object,
        path: Optional[Path] = None,
    ) -> K8sOptions:
        """Parse options definition and return an options object.

        Args:
            deploy_environment: Current deploy environment.
            obj: Object to parse.
            path: Module path.

        """
        return cls(
            data=RunwayK8sModuleOptionsDataModel.parse_obj(obj),
            deploy_environment=deploy_environment,
            path=path or Path.cwd(),
        )

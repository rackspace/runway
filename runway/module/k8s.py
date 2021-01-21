"""K8s (kustomize) module."""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, cast

from .._logging import PrefixAdaptor
from ..env_mgr.kbenv import KB_VERSION_FILENAME, KBEnvManager
from ..util import DOC_SITE, which
from .base import RunwayModule
from .utils import run_module_command

if TYPE_CHECKING:
    from .._logging import RunwayLogger
    from ..context.runway import RunwayContext
    from .base import ModuleOptions

LOGGER = cast("RunwayLogger", logging.getLogger(__name__))


def gen_overlay_dirs(environment: str, region: str) -> List[str]:
    """Generate possible overlay directories."""
    return [
        # Give preference to explicit environment-region dirs
        "%s-%s" % (environment, region),
        # Fallback to environment name only
        environment,
    ]


def get_module_defined_k8s_ver(
    k8s_version_opts: Union[str, Dict[str, str]], env_name: str
) -> Optional[str]:
    """Return version of Terraform requested in module options."""
    if isinstance(k8s_version_opts, str):
        return k8s_version_opts
    if k8s_version_opts.get(env_name):
        return k8s_version_opts[env_name]
    if k8s_version_opts.get("*"):
        return k8s_version_opts["*"]
    return None


def get_overlay_dir(overlays_path: Path, environment: str, region: str) -> Path:
    """Determine overlay directory to use."""
    overlay_dir = overlays_path
    for name in gen_overlay_dirs(environment, region):
        overlay_dir = overlays_path / name
        if (overlay_dir / "kustomization.yaml").is_file():
            return overlay_dir
    return overlay_dir  # fallback to last dir


def generate_response(
    overlay_path: Path, module_path: Path, environment: str, region: str
) -> Dict[str, bool]:
    """Determine if environment is defined."""
    configfile = overlay_path / "kustomization.yaml"
    if configfile.is_file():
        LOGGER.info("processing kustomize overlay: %s", configfile)
        return {"skipped_configs": False}
    LOGGER.info(
        "skipped; kustomize overlay for this environment/region not"
        " found -- looking for one of: %s",
        ", ".join(
            str(module_path / "overlays" / i / "kustomization.yaml")
            for i in gen_overlay_dirs(environment, region)
        ),
    )
    return {"skipped_configs": True}


class K8s(RunwayModule):
    """Kubectl Runway Module."""

    options: Dict[str, Any]

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
            options=options,
            parameters=parameters,
        )
        # logger needs to be created here to use the correct logger
        self.logger = PrefixAdaptor(self.name, LOGGER)

    def run_kubectl(self, command: str = "plan") -> Dict[str, bool]:
        """Run kubectl."""
        if self.options.get("overlay_path"):
            # config path is overridden from runway
            kustomize_config_path = self.path / cast(
                str, self.options.get("overlay_path"),
            )
        else:
            kustomize_config_path = get_overlay_dir(
                self.path / "overlays",
                self.context.env.name,
                self.context.env.aws_region,
            )
        response = generate_response(
            kustomize_config_path,
            self.path,
            self.context.env.name,
            self.context.env.aws_region,
        )
        if response["skipped_configs"]:
            return response

        module_defined_k8s_ver = get_module_defined_k8s_ver(
            self.options.get("kubectl_version", {}), self.context.env.name,
        )
        if module_defined_k8s_ver:
            self.logger.debug("using kubectl version from the module definition")
            k8s_bin = KBEnvManager(self.path).install(module_defined_k8s_ver)
        elif os.path.isfile(os.path.join(kustomize_config_path, KB_VERSION_FILENAME)):
            self.logger.debug(
                "using kubectl version from the overlay directory: %s",
                kustomize_config_path,
            )
            k8s_bin = KBEnvManager(kustomize_config_path).install()
        elif os.path.isfile(os.path.join(self.path, KB_VERSION_FILENAME)):
            self.logger.debug(
                "using kubectl version from the module directory: %s", self.path
            )
            k8s_bin = KBEnvManager(self.path).install()
        elif (self.context.env.root_dir / KB_VERSION_FILENAME).is_file():
            file_path = self.context.env.root_dir / KB_VERSION_FILENAME
            self.logger.debug(
                "using kubectl version from the project's root directory: %s",
                file_path,
            )
            k8s_bin = KBEnvManager(self.context.env.root_dir).install()
        else:
            self.logger.debug("kubectl version not specified; checking path")
            if not which("kubectl"):
                self.logger.error(
                    "kubectl not available and a version to install not specified"
                )
                self.logger.error(
                    "learn how to use Runway to manage kubectl versions at %s"
                    "/page/kubernetes/advanced_features.html#version-management",
                    DOC_SITE,
                )
                sys.exit(1)
            k8s_bin = "kubectl"

        kustomize_cmd = [k8s_bin, "kustomize", kustomize_config_path]
        self.logger.debug("running kubectl command: %s", " ".join(kustomize_cmd))
        kustomize_yml = subprocess.check_output(
            kustomize_cmd, env=self.context.env.vars
        )
        if isinstance(kustomize_yml, bytes):  # python3 returns encoded bytes
            kustomize_yml = kustomize_yml.decode()
        if command == "plan":
            self.logger.info("yaml was generated by kubectl:\n\n%s", kustomize_yml)
        else:
            self.logger.debug("yaml generated by kubectl:\n\n%s", kustomize_yml)
        if command in ["apply", "delete"]:
            kubectl_command = [k8s_bin, command]
            if command == "delete":
                kubectl_command.append("--ignore-not-found=true")
            kubectl_command.extend(["-k", str(kustomize_config_path)])

            self.logger.info("%s (in progress)", command)
            self.logger.debug("running kubectl command: %s", " ".join(kubectl_command))
            run_module_command(
                kubectl_command, self.context.env.vars, logger=self.logger
            )
            self.logger.info("%s (complete)", command)
        return response

    def plan(self) -> None:
        """Run kustomize build and display generated plan."""
        self.run_kubectl(command="plan")

    def deploy(self) -> None:
        """Run kubectl apply."""
        self.run_kubectl(command="apply")

    def destroy(self) -> None:
        """Run kubectl delete."""
        self.run_kubectl(command="delete")

"""K8s (kustomize) module."""
import logging
import os
import subprocess
import sys

import six

from .._logging import PrefixAdaptor
from ..env_mgr.kbenv import KB_VERSION_FILENAME, KBEnvManager
from ..util import DOC_SITE, which
from . import RunwayModule, run_module_command

LOGGER = logging.getLogger(__name__)


def gen_overlay_dirs(environment, region):
    """Generate possible overlay directories."""
    return [
        # Give preference to explicit environment-region dirs
        "%s-%s" % (environment, region),
        # Fallback to environment name only
        environment,
    ]


def get_module_defined_k8s_ver(k8s_version_opts, env_name):
    """Return version of Terraform requested in module options."""
    if isinstance(k8s_version_opts, six.string_types):
        return k8s_version_opts
    if k8s_version_opts.get(env_name):
        return k8s_version_opts.get(env_name)
    if k8s_version_opts.get("*"):
        return k8s_version_opts.get("*")
    return None


def get_overlay_dir(overlays_path, environment, region):
    """Determine overlay directory to use."""
    for name in gen_overlay_dirs(environment, region):
        overlay_dir = os.path.join(overlays_path, name)
        if os.path.isfile(os.path.join(overlay_dir, "kustomization.yaml")):
            return overlay_dir
    return overlay_dir  # fallback to last dir


def generate_response(overlay_path, module_path, environment, region):
    """Determine if environment is defined."""
    configfile = os.path.join(overlay_path, "kustomization.yaml")
    if os.path.isdir(overlay_path) and os.path.isfile(configfile):
        LOGGER.info("processing kustomize overlay: %s", configfile)
        return {"skipped_configs": False}
    LOGGER.info(
        "skipped; kustomize overlay for this environment/region not"
        " found -- looking for one of: %s",
        ", ".join(
            [
                os.path.join(module_path, "overlays", i, "kustomization.yaml")
                for i in gen_overlay_dirs(environment, region)
            ]
        ),
    )
    return {"skipped_configs": True}


class K8s(RunwayModule):
    """Kubectl Runway Module."""

    def __init__(self, context, path, options=None):
        """Instantiate class.

        Args:
            context (Context): Runway context object.
            path (Union[str, Path]): Path to the module.
            options (Dict[str, Dict[str, Any]]): Everything in the module
                definition merged with applicable values from the deployment
                definition.

        """
        super(K8s, self).__init__(context, path, options)
        # logger needs to be created here to use the correct logger
        self.logger = PrefixAdaptor(self.name, LOGGER)

    def run_kubectl(self, command="plan"):
        """Run kubectl."""
        kustomize_config_path = os.path.join(
            self.path,
            "overlays",
            get_overlay_dir(
                os.path.join(self.path, "overlays"),
                self.context.env.name,
                self.context.env.aws_region,
            ),
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
            self.options.get("options", {}).get("kubectl_version", {}),
            self.context.env.name,
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
            kubectl_command.extend(["-k", kustomize_config_path])

            self.logger.info("%s (in progress)", command)
            self.logger.debug("running kubectl command: %s", " ".join(kubectl_command))
            run_module_command(
                kubectl_command, self.context.env.vars, logger=self.logger
            )
            self.logger.info("%s (complete)", command)
        return response

    def plan(self):
        """Run kustomize build and display generated plan."""
        self.run_kubectl(command="plan")

    def deploy(self):
        """Run kubectl apply."""
        self.run_kubectl(command="apply")

    def destroy(self):
        """Run kubectl delete."""
        self.run_kubectl(command="delete")

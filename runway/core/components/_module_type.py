"""Abstraction for the module 'type' value in a a Runway configuration."""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Dict, Optional, Type, cast

from typing_extensions import Literal

from ...utils import load_object_from_string

if TYPE_CHECKING:
    from ...config.models.runway import RunwayModuleTypeTypeDef
    from ...module.base import RunwayModule

LOGGER = logging.getLogger(__name__)


RunwayModuleTypeExtensionsTypeDef = Literal["cdk", "cfn", "k8s", "sls", "tf", "web"]


class RunwayModuleType:
    """Runway configuration ``type`` settings object.

    The ``type`` property of a Runway configuration can be
    used to explicitly specify what module type you are
    intending to deploy.

    Runway determines the type of module you are trying to
    deploy in 3 different ways. First, it will check for the
    ``type`` property as described here, next it will look
    for a suffix as described in :ref:`Module Definition<runway-module>`,
    and finally it will attempt to autodetect your module
    type by scanning the files of the project. If none of
    those settings produces a valid result an error will
    occur. The following are valid explicit types:

    +--------------------+-----------------------------------------------+
    | Type               | IaC Tool/Framework                            |
    +====================+===============================================+
    | ``cdk``            | AWS CDK                                       |
    +--------------------+-----------------------------------------------+
    | ``cloudformation`` | CloudFormation                                |
    +--------------------+-----------------------------------------------+
    | ``serverless``     | Serverless Framework                          |
    +--------------------+-----------------------------------------------+
    | ``terraform``      | Terraform                                     |
    +--------------------+-----------------------------------------------+
    | ``kubernetes``     | Kubernetes                                    |
    +--------------------+-----------------------------------------------+
    | ``static``         | :ref:`Static Site<mod-staticsite>`            |
    +--------------------+-----------------------------------------------+

    Even when specifying a module ``type`` the module structure
    needs to be conducive with that type of project. If the files contained
    within don't match the type then an error will occur.

    """

    EXTENSION_MAP: ClassVar[Dict[str, str]] = {
        "cdk": "runway.module.cdk.CloudDevelopmentKit",
        "cfn": "runway.module.cloudformation.CloudFormation",
        "k8s": "runway.module.k8s.K8s",
        "sls": "runway.module.serverless.Serverless",
        "tf": "runway.module.terraform.Terraform",
        "web": "runway.module.staticsite.handler.StaticSite",
    }

    TYPE_MAP: ClassVar[Dict[str, str]] = {
        "cdk": EXTENSION_MAP["cdk"],
        "cloudformation": EXTENSION_MAP["cfn"],
        "kubernetes": EXTENSION_MAP["k8s"],
        "serverless": EXTENSION_MAP["sls"],
        "static": EXTENSION_MAP["web"],
        "terraform": EXTENSION_MAP["tf"],
    }

    def __init__(
        self,
        path: Path,
        class_path: Optional[str] = None,
        type_str: Optional[RunwayModuleTypeTypeDef] = None,
    ) -> None:
        """Instantiate class.

        Keyword Args:
            path: The required path to the module
            class_path: A supplied class_path to override the autodetected one.
            type_str: An explicit type to assign to the RunwayModuleType

        """
        self.path = path
        self.class_path = class_path
        self.type_str = type_str
        self.module_class = self._determine_module_class()

    def _determine_module_class(self) -> Type[RunwayModule]:
        """Determine type of module and return deployment module class.

        Returns:
            object: The specified module class

        """
        if self.class_path:
            LOGGER.debug(
                'module class "%s" determined from explicit definition',
                self.class_path,
            )

        if not self.class_path and self.type_str:
            self.class_path = self.TYPE_MAP.get(self.type_str, None)
            if self.class_path:
                LOGGER.debug(
                    'module class "%s" determined from explicit type', self.class_path
                )

        if not self.class_path:
            self._set_class_path_based_on_extension()
            if self.class_path:
                LOGGER.debug(
                    'module class "%s" determined from path extension', self.class_path
                )

        if not self.class_path:
            self._set_class_path_based_on_autodetection()

        if not self.class_path:
            LOGGER.error(
                'module class could not be determined from path "%s"',
                os.path.basename(self.path),
            )
            sys.exit(1)

        return cast(Type["RunwayModule"], load_object_from_string(self.class_path))

    def _set_class_path_based_on_extension(self) -> None:
        """Based on the directory suffix set the class_path."""
        basename = os.path.basename(self.path)
        basename_split = basename.split(".")
        extension = basename_split[len(basename_split) - 1]
        self.class_path = self.EXTENSION_MAP.get(extension, None)
        if self.class_path:
            LOGGER.debug(
                'module class "%s" determined from path extension "%s"',
                self.class_path,
                extension,
            )

    def _set_class_path_based_on_autodetection(self) -> None:
        """Based on the files detected in the base path set the class_path."""
        if (
            any(
                (self.path / sls).is_file()
                for sls in ["serverless.js", "serverless.ts", "serverless.yml"]
            )
            and (self.path / "package.json").is_file()
        ):
            self.class_path = self.TYPE_MAP.get("serverless", None)
        elif next(self.path.glob("*.tf"), None):
            self.class_path = self.TYPE_MAP.get("terraform", None)
        elif (self.path / "cdk.json").is_file() and (
            self.path / "package.json"
        ).is_file():
            self.class_path = self.TYPE_MAP.get("cdk", None)
        elif (self.path / "overlays").is_dir() and self._find_kustomize_files():
            self.class_path = self.TYPE_MAP.get("kubernetes", None)
        elif (
            next(self.path.glob("*.env"), None)
            or next(self.path.glob("*.yaml"), None)
            or next(self.path.glob("*.yml"), None)
        ):
            self.class_path = self.TYPE_MAP.get("cloudformation", None)
        if self.class_path:
            LOGGER.debug(
                'module class "%s" determined from autodetection', self.class_path
            )

    def _find_kustomize_files(self) -> bool:
        """Return true if kustomize yaml file found.

        Returns:
            boolean: Whether the kustomize yaml exist

        """
        for _root, _dirnames, filenames in os.walk(self.path):
            for filename in filenames:
                if filename == "kustomization.yaml":
                    return True
        return False

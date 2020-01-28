"""Abstraction for the module 'type' value in a a Runway configuration."""
# pylint: disable=unused-import
from typing import Dict, List, Optional, Tuple, Union  # noqa: F401

import glob
import logging
import os
import sys

from .util import (load_object_from_string)

LOGGER = logging.getLogger('runway')


# noqa pylint: disable=too-few-public-methods
class RunwayModuleType(object):
    """Runway configuration ``type`` settings object.

    The ``type`` property of a Runway configuration can be
    used to explicitly specify what module type you are
    intending to deploy.

    Runway determines the type of module you are trying to
    deploy in 3 different ways. First, it will check for the
    ``type`` property as described here, next it will look
    for a suffix as described in :ref:`Module Definition<mod-definition>`,
    and finally it will attempt to autodetect your module
    type by scanning the files of the project. If none of
    those settings produces a valid result an error will
    occur. The following are valid explicit types:

    +--------------------+-----------------------------------------------+
    | Type               | IaC Tool/Framework                            |
    +====================+===============================================+
    | ``cdk``            | `AWS CDK`_                                    |
    +--------------------+-----------------------------------------------+
    | ``cloudformation`` | `CloudFormation`_                             |
    +--------------------+-----------------------------------------------+
    | ``serverless``     | `Serverless Framework`_                       |
    +--------------------+-----------------------------------------------+
    | ``terraform``      | `Terraform`_                                  |
    +--------------------+-----------------------------------------------+
    | ``kubernetes``     | `Kubernetes`_                                 |
    +--------------------+-----------------------------------------------+
    | ``static``         | :ref:`Static Site<mod-staticsite>`            |
    +--------------------+-----------------------------------------------+

    Even when specifying a module ``type`` the module structure
    needs to be conducive with that type of project. If the files contained
    within don't match the type then an error will occur.

    """

    EXTENSION_MAP = {
        'sls': 'runway.module.serverless.Serverless',
        'tf': 'runway.module.terraform.Terraform',
        'cdk': 'runway.module.cdk.CloudDevelopmentKit',
        'k8s': 'runway.module.k8s.K8s',
        'cfn': 'runway.module.cloudformation.CloudFormation',
        'web': 'runway.module.staticsite.StaticSite'
    }

    TYPE_MAP = {
        'serverless': EXTENSION_MAP.get('sls'),
        'terraform': EXTENSION_MAP.get('tf'),
        'cdk': EXTENSION_MAP.get('cdk'),
        'kubernetes': EXTENSION_MAP.get('k8s'),
        'cloudformation': EXTENSION_MAP.get('cfn'),
        'static': EXTENSION_MAP.get('web'),
    }

    def __init__(self, path, class_path=None, type_str=None):
        # type: (str, Optional[str], Optional[str]) -> RunwayModuleType
        """Initialization of the Module Type Configuration.  # noqa

        Keyword Args:
            path (str): The required path to the module
            class_path (Optional[str]): A supplied class_path to override
                the autodetected one.
            type_str (Optional[str]): An explicit type to assign to
                the RunwayModuleType
        """
        self.path = path
        self.class_path = class_path
        self.type_str = type_str
        self.module_class = self._determine_module_class()

    def _determine_module_class(self):
        """Determine type of module and return deployment module class.

        Returns:
            object: The specified module class

        """
        if not self.class_path:
            self._set_class_path_based_on_extension()

        if not self.class_path and self.type_str:
            self.class_path = self.TYPE_MAP.get(self.type_str, None)

        if not self.class_path:
            self._set_class_path_based_on_autodetection()

        if not self.class_path:
            LOGGER.error('No module class found for %s', os.path.basename(self.path))
            sys.exit(1)

        return load_object_from_string(self.class_path)

    def _set_class_path_based_on_extension(self):
        # type() -> void
        """Based on the directory suffix set the class_path."""
        basename = os.path.basename(self.path)
        basename_split = basename.split('.')
        extension = basename_split[len(basename_split) - 1]
        self.class_path = self.EXTENSION_MAP.get(extension, None)

    def _set_class_path_based_on_autodetection(self):
        # type() -> void
        """Based on the files detected in the base path set the class_path."""
        if (self._is_file('serverless.yml') or self._is_file('serverless.js')) \
                and self._is_file('package.json'):
            self.class_path = self.TYPE_MAP.get('serverless', None)
        elif self._has_glob('*.tf'):
            self.class_path = self.TYPE_MAP.get('terraform', None)
        elif self._is_file('cdk.json') and self._is_file('package.json'):
            self.class_path = self.TYPE_MAP.get('cdk', None)
        elif self._is_dir('overlays') and self._find_kustomize_files():
            self.class_path = self.TYPE_MAP.get('kubernetes', None)
        elif self._has_glob('*.env') \
            or self._has_glob('*.yaml') \
                or self._has_glob('*.yml'):
            self.class_path = self.TYPE_MAP.get('cloudformation', None)

    def _is_file(self, file_name):
        # type(str) -> boolean
        """Verify if specified filename is a file.

        Keyword Args:
            file_name (str): The filename relative to the initialized path

        Returns:
            boolean: Whether the file_name passed in is a file

        """
        return os.path.isfile(os.path.join(self.path, file_name))

    def _is_dir(self, dir_name):
        # type: (str) -> bool
        """Verify if specified dir_name is a directory.

        Keyword Args:
            dir_name (str): The directory relative to the initialized path

        Returns:
            boolean: Whether the passed in dir_name is a directory

        """
        return os.path.isdir(os.path.join(self.path, dir_name))

    def _has_glob(self, glb):
        # type: (str)-> bool
        """Verify if a glob of files exist.

        Keyword Args:
            glb (str): The glob pattern relative to the initialized path

        Returns:
            boolean: Whether the passed in glob of files exist

        """
        return glob.glob(os.path.join(self.path, glb))

    def _find_kustomize_files(self):
        # type: ()-> bool
        """Return true if kustomize yaml file found.

        Returns:
            boolean: Whether the kustomize yaml exist

        """
        for _root, _dirnames, filenames in os.walk(self.path):
            for filename in filenames:
                if filename == 'kustomization.yaml':
                    return True
        return False

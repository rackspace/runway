import glob
import logging
import os
import sys

from .util import (load_object_from_string)

LOGGER = logging.getLogger('runway')


class ModuleType(object):

    EXTENSION_MAP = {
        'sls': 'runway.module.serverless.Serverless',
        'tf': 'runway.module.terraform.Terraform',
        'cdk': 'runway.module.cdk.CloudDevelopmentKit',
        'k8s': 'runway.module.k8s.K8s',
        'cfn': 'runway.module.cloudformation.CloudFormation',
        'static': 'runway.module.staticsite.StaticSite'
    }

    TYPE_MAP = {
        'serverless': EXTENSION_MAP.get('sls'),
        'terraform': EXTENSION_MAP.get('tf'),
        'cdk': EXTENSION_MAP.get('cdk'),
        'kubernetes': EXTENSION_MAP.get('k8s'),
        'cloudformation': EXTENSION_MAP.get('cfn'),
        'static': EXTENSION_MAP.get('static'),
    }

    def __init__(self, path, class_path=None, type_str=None):
        self.path = path
        self.class_path = class_path
        self.type_str = type_str
        self.module_class = self._determine_module_class()

    def _determine_module_class(self):
        """Determine type of module and return deployment module class."""
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
        basename = os.path.basename(self.path)
        basename_split = basename.split('.')
        extension = basename_split[len(basename_split) - 1]
        self.class_path = self.EXTENSION_MAP.get(extension, None)

    def _set_class_path_based_on_autodetection(self):
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
        return os.path.isfile(os.path.join(self.path, file_name))

    def _is_dir(self, dir_name):
        return os.path.isdir(os.path.join(self.path, dir_name))

    def _has_glob(self, glb):
        return glob.glob(os.path.join(self.path, glb))

    def _find_kustomize_files(self):
        """Return true if kustomize yaml file found."""
        for _root, _dirnames, filenames in os.walk(self.path):
            for filename in filenames:
                if filename == 'kustomization.yaml':
                    return True
        return False

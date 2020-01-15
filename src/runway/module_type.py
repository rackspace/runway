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

    def __init__(self, path, class_path=None, type=None):
        self.path = path
        self.class_path = class_path
        self.type = type
        self.module_class = self.determine_module_class()

    def determine_module_class(self):  # pylint: disable=too-many-branches
        """Determine type of module and return deployment module class."""
        if not self.class_path:
            # First check directory name for type-indicating suffix
            basename = os.path.basename(self.path)
            basename_split = basename.split('.')
            extension = basename_split[len(basename_split) - 1]
            self.class_path = self.EXTENSION_MAP.get(extension, None)

        if not self.class_path and self.type:
            if self.type == 'static':
                self.class_path = self.EXTENSION_MAP.get('static', None)

        if not self.class_path:
            # Fallback to autodetection
            if (self.is_file('serverless.yml') or self.is_file('serverless.js')) \
                    and self.is_file('package.json'):
                self.class_path = 'runway.module.serverless.Serverless'
            elif self.has_glob('*.tf'):
                self.class_path = 'runway.module.terraform.Terraform'
            elif self.is_file('cdk.json') and self.is_file('package.json'):
                self.class_path = 'runway.module.cdk.CloudDevelopmentKit'
            elif self.is_dir('overlays') and self.find_kustomize_files():
                self.class_path = 'runway.module.k8s.K8s'
            elif self.has_glob('*.env') \
                or self.has_glob('*.yaml') \
                    or self.has_glob('*.yml'):
                self.class_path = 'runway.module.cloudformation.CloudFormation'

        if not self.class_path:
            LOGGER.error('No module class found for %s', os.path.basename(self.path))
            sys.exit(1)

        return load_object_from_string(self.class_path)

    def is_file(self, file_name):
        return os.path.isfile(os.path.join(self.path, file_name))

    def is_dir(self, dir_name):
        return os.path.isdir(os.path.join(self.path, dir_name))

    def has_glob(self, glb):
        return glob.glob(os.path.join(self.path, glb))

    def find_kustomize_files(self):
        """Return true if kustomize yaml file found."""
        for _root, _dirnames, filenames in os.walk(self.path):
            for filename in filenames:
                if filename == 'kustomization.yaml':
                    return True
        return False

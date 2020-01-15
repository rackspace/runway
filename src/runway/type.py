import glob
import logging
import os
import sys

from .util import (load_object_from_string)

LOGGER = logging.getLogger('runway')


class Type(object):

    def __init__(self, path, class_path=None, type_str=None):
        self.path = path
        self.class_path = class_path
        self.type_str = type_str

    def determine_module_class(self):  # pylint: disable=too-many-branches
        """Determine type of module and return deployment module class."""
        if not self.class_path:
            # First check directory name for type-indicating suffix
            basename = os.path.basename(self.path)
            if basename.endswith('.sls'):
                self.class_path = 'runway.module.serverless.Serverless'
            elif basename.endswith('.tf'):
                self.class_path = 'runway.module.terraform.Terraform'
            elif basename.endswith('.cdk'):
                self.class_path = 'runway.module.cdk.CloudDevelopmentKit'
            elif basename.endswith('.k8s'):
                self.class_path = 'runway.module.k8s.K8s'
            elif basename.endswith('.cfn'):
                self.class_path = 'runway.module.cloudformation.CloudFormation'
            elif basename.endswith('.static'):
                self.class_path = 'runway.module.staticsite.StaticSite'

        if not self.class_path:
            # Fallback to autodetection
            if (os.path.isfile(os.path.join(self.path, 'serverless.yml'))
                    or os.path.isfile(os.path.join(self.path, 'serverless.js'))) \
                    and os.path.isfile(os.path.join(self.path, 'package.json')):
                self.class_path = 'runway.module.serverless.Serverless'
            elif glob.glob(os.path.join(self.path, '*.tf')):
                self.class_path = 'runway.module.terraform.Terraform'
            elif os.path.isfile(os.path.join(self.path, 'cdk.json')) \
                    and os.path.isfile(os.path.join(self.path, 'package.json')):
                self.class_path = 'runway.module.cdk.CloudDevelopmentKit'
            elif os.path.isdir(os.path.join(self.path, 'overlays')) \
                    and self.find_kustomize_files(self.path):
                self.class_path = 'runway.module.k8s.K8s'
            elif glob.glob(os.path.join(self.path, '*.env')) or (
                    glob.glob(os.path.join(self.path, '*.yaml'))) or (
                        glob.glob(os.path.join(self.path, '*.yml'))):
                self.class_path = 'runway.module.cloudformation.CloudFormation'

        if not self.class_path:
            LOGGER.error('No module class found for %s', os.path.basename(self.path))
            sys.exit(1)

        LOGGER.info(self.path)
        return load_object_from_string(self.class_path)

    def find_kustomize_files(self, path):
        """Return true if kustomize yaml file found."""
        for _root, _dirnames, filenames in os.walk(path):
            for filename in filenames:
                if filename == 'kustomization.yaml':
                    return True
        return False

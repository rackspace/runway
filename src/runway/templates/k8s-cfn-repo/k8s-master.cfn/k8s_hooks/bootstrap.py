"""Execute the AWS CLI update-kubeconfig command."""
from __future__ import print_function
import os
import logging
import shutil

import six
import yaml

LOGGER = logging.getLogger(__name__)


def copy_template_to_env(path, env, region):
    """Copy k8s module template into new environment directory."""
    overlays_dir = os.path.join(path, 'overlays')
    template_dir = os.path.join(overlays_dir, 'template')
    env_dir = os.path.join(overlays_dir, env)
    if os.path.isdir(template_dir):
        if os.path.isdir(env_dir) or (
                os.path.isdir("%s-%s" % (env_dir, region))):
            LOGGER.info("Bootstrap of k8s module at \"%s\" skipped; module "
                        "already has a config for this environment", path)
        else:
            LOGGER.info("Copying overlay template at \"%s\" to new "
                        "environment directory \"%s\"", template_dir, env_dir)
            shutil.copytree(template_dir, env_dir, symlinks=True)
            # Update templated environment name in files
            for i in ['kustomization.yaml',
                      # namespace files can't be directly kustomized
                      'namespace.yaml']:
                templated_file_path = os.path.join(env_dir, i)
                if os.path.isfile(templated_file_path):
                    with open(templated_file_path, 'r') as stream:
                        filedata = stream.read()
                    if 'REPLACEMEENV' in filedata:
                        filedata = filedata.replace('REPLACEMEENV', env)
                        with open(templated_file_path, 'w') as stream:
                            stream.write(filedata)
    else:
        LOGGER.info("Skipping bootstrap of k8s module at \"%s\"; no template "
                    "directory present", path)


def create_runway_environments(provider, context, **kwargs):  # noqa pylint: disable=unused-argument
    """Copy k8s module templates into new environment directories.

    Args:
        provider (:class:`stacker.providers.base.BaseProvider`): provider
            instance
        context (:class:`stacker.context.Context`): context instance

    Returns: boolean for whether or not the hook succeeded.

    """
    LOGGER.info("Bootstrapping runway k8s modules, looking for unconfigured "
                "environments...")

    environment = kwargs['namespace']
    region = os.environ.get('AWS_DEFAULT_REGION')

    env_root = os.path.dirname(
        os.path.realpath(os.environ.get('RUNWAYCONFIG'))
    )
    with open(os.environ.get('RUNWAYCONFIG')) as data_file:
        runway_config = yaml.safe_load(data_file)

    for deployment in runway_config.get('deployments', []):
        for module in deployment.get('modules', []):
            if isinstance(module, six.string_types):
                path = module
            else:
                path = module.get('path')
            if path.endswith('.k8s'):
                copy_template_to_env(os.path.join(env_root, path),
                                     environment,
                                     region)
    return True

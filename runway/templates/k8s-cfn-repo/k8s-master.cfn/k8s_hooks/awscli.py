"""Execute the AWS CLI update-kubeconfig command."""
from __future__ import print_function
import os
import subprocess
import logging
import sys

from runway.cfngin.lookups.handlers.output import OutputLookup
from runway.util import which

LOGGER = logging.getLogger(__name__)


def aws_eks_update_kubeconfig(provider, context, **kwargs):  # noqa pylint: disable=unused-argument
    """Execute the aws cli eks update-kubeconfig command.

    Args:
        provider (:class:`stacker.providers.base.BaseProvider`): provider
            instance
        context (:class:`stacker.context.Context`): context instance

    Returns: boolean for whether or not the hook succeeded.

    """
    if kwargs.get('cluster-name'):
        eks_cluster_name = kwargs['cluster-name']
    else:
        eks_cluster_name = OutputLookup.handle(
            "%s::EksClusterName" % kwargs['stack'],
            provider=provider,
            context=context
        )
    LOGGER.info('writing kubeconfig...')
    subprocess.check_output(['runway', 'run-aws', '--', 'eks',
                             'update-kubeconfig', '--name', eks_cluster_name])
    LOGGER.info('kubeconfig written successfully...')

    # The newly-generated kubeconfig will have introduced a dependency on the
    # awscli. This is fine if a recent version is installed, or it's invoked
    # in a virtualenv with runway
    if not os.environ.get('PIPENV_ACTIVE') and (
            not os.environ.get('VIRTUAL_ENV') and not which('aws')):
        print('', file=sys.stderr)
        print('Warning: the generated kubeconfig uses the aws-cli for '
              'authentication, but it is not found in your environment. '
              'Either install it, or update the kubeconfig to use runway '
              'instead, e.g.:', file=sys.stderr)
        print('', file=sys.stderr)
        print('```', file=sys.stderr)
        print('      args:', file=sys.stderr)
        print('        - --region', file=sys.stderr)
        print('        - REGIONHERE', file=sys.stderr)
        print('        - eks', file=sys.stderr)
        print('        - get-token', file=sys.stderr)
        print('        - --cluster-name', file=sys.stderr)
        print('        - CLUSTERNAME', file=sys.stderr)
        print('        command: aws', file=sys.stderr)
        print('```', file=sys.stderr)
        print('', file=sys.stderr)
        print('becomes:', file=sys.stderr)
        print('', file=sys.stderr)
        print('```', file=sys.stderr)
        print('      args:', file=sys.stderr)
        print('        - run-aws', file=sys.stderr)
        print('        - --', file=sys.stderr)
        print('        - --region', file=sys.stderr)
        print('        - REGIONHERE', file=sys.stderr)
        print('        - eks', file=sys.stderr)
        print('        - get-token', file=sys.stderr)
        print('        - --cluster-name', file=sys.stderr)
        print('        - CLUSTERNAMEHERE', file=sys.stderr)
        print('        command: runway', file=sys.stderr)
        print('```', file=sys.stderr)
        print('', file=sys.stderr)
    return True

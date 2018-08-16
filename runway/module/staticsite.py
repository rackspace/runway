"""Static website module."""

import logging
import os
import sys
import tempfile

import yaml

from . import RunwayModule
from .cloudformation import CloudFormation

LOGGER = logging.getLogger('runway')


class StaticSite(RunwayModule):
    """Static website Runway Module."""

    def setup_website_module(self, command):
        """Create stacker configuration for website module."""
        name = self.options.get('name') if self.options.get('name') else self.options.get('path')  # noqa pylint: disable=line-too-long
        if not self.options.get('environments',
                                {}).get(self.context.env_name,
                                        {}).get('namespace'):
            LOGGER.fatal("staticsite: module %s's environment configuration "
                         "is missing a namespace definition!",
                         name)
            sys.exit(1)
        module_dir = tempfile.mkdtemp()
        LOGGER.info("staticsite: Generating CloudFormation configuration for "
                    "module %s in %s",
                    name,
                    module_dir)

        # Default parameter name matches build_staticsite hook
        hash_param = self.options.get('options', {}).get('source_hashing', {}).get('parameter') if self.options.get('options', {}).get('source_hashing', {}).get('parameter') else "${namespace}-%s-hash" % name # noqa pylint: disable=line-too-long
        build_staticsite_args = self.options.copy()
        if not build_staticsite_args.get('options'):
            build_staticsite_args['options'] = {}
        build_staticsite_args['artifact_bucket_rxref_lookup'] = "%s-dependencies::ArtifactsBucketName" % name  # noqa pylint: disable=line-too-long
        build_staticsite_args['options']['namespace'] = '${namespace}'
        build_staticsite_args['options']['name'] = name
        build_staticsite_args['options']['path'] = os.path.join(
            os.path.realpath(self.context.env_root),
            self.path
        )

        with open(os.path.join(module_dir, '01-dependencies.yaml'), 'w') as output_stream:  # noqa
            yaml.dump(
                {'namespace': '${namespace}',
                 'stacker_bucket': '',
                 'stacks': {
                     "%s-dependencies" % name: {
                         'class_path': 'runway.blueprints.staticsite.dependencies.Dependencies'}},  # noqa pylint: disable=line-too-long
                 'pre_destroy': [
                     {'path': 'runway.hooks.cleanup_s3.purge_bucket',
                      'required': True,
                      'args': {
                          'bucket_rxref_lookup': "%s-dependencies::%s" % (name, i)  # noqa
                      }} for i in ['AWSLogBucketName', 'ArtifactsBucketName']
                 ]},
                output_stream,
                default_flow_style=False
            )
        with open(os.path.join(module_dir, '02-staticsite.yaml'), 'w') as output_stream:  # noqa
            yaml.dump(
                {'namespace': '${namespace}',
                 'stacker_bucket': '',
                 'pre_build': [
                     {'path': 'runway.hooks.staticsite.build_staticsite.build',
                      'required': True,
                      'data_key': 'staticsite',
                      'args': build_staticsite_args}
                 ],
                 'stacks': {
                     name: {
                         'class_path': 'runway.blueprints.staticsite.staticsite.StaticSite',  # noqa
                         'variables': {
                             'LogBucketName': "${rxref %s-dependencies::AWSLogBucketName}" % name}}},  # noqa pylint: disable=line-too-long
                 'post_build': [
                     {'path': 'runway.hooks.staticsite.upload_staticsite.sync',
                      'required': True,
                      'args': {
                          'bucket_output_lookup': '%s::BucketName' % name,
                          'distribution_output_lookup': '%s::CFDistributionId' % name}}  # noqa
                 ],
                 'pre_destroy': [
                     {'path': 'runway.hooks.cleanup_s3.purge_bucket',
                      'required': True,
                      'args': {
                          'bucket_rxref_lookup': "%s::BucketName" % name
                      }}
                 ],
                 'post_destroy': [
                     {'path': 'runway.hooks.cleanup_ssm.delete_param',
                      'args': {
                          'parameter_name': hash_param
                      }}
                 ]},
                output_stream,
                default_flow_style=False
            )

        cfn = CloudFormation(
            self.context,
            module_dir,
            {i: self.options[i] for i in self.options if i != 'class_path'}
        )
        getattr(cfn, command)()

    def plan(self):
        """Create website CFN module and run stacker diff."""
        self.setup_website_module(command='plan')

    def deploy(self):
        """Create website CFN module and run stacker build."""
        self.setup_website_module(command='deploy')

    def destroy(self):
        """Create website CFN module and run stacker destroy."""
        self.setup_website_module(command='destroy')

"""Static website module."""

import copy
import logging
import os
import sys
import tempfile

import yaml

from . import RunwayModule
from .cloudformation import CloudFormation

LOGGER = logging.getLogger('runway')


def ensure_valid_environment_config(module_name, config):
    """Exit if config is invalid."""
    if not config or not config.get('namespace'):
        LOGGER.fatal("staticsite: module %s's environment configuration is "
                     "missing a namespace definition!",
                     module_name)
        sys.exit(1)


class StaticSite(RunwayModule):
    """Static website Runway Module."""

    def setup_website_module(self, command):
        """Create stacker configuration for website module."""
        ensure_valid_environment_config(self.name, self.environment_options)
        module_dir = tempfile.mkdtemp()
        LOGGER.info("staticsite: Generating CloudFormation configuration for "
                    "module %s in %s",
                    self.name,
                    module_dir)

        # Default parameter name matches build_staticsite hook
        source_hashing_options = self.module_options.get('source_hashing', {})
        hash_param = source_hashing_options.get('parameter', "${namespace}-%s-hash" % self.name)
        build_staticsite_args = {}
        build_staticsite_args['options'] = copy.deepcopy(self.module_options)
        build_staticsite_args['artifact_bucket_rxref_lookup'] = "%s-dependencies::ArtifactsBucketName" % self.name  # noqa pylint: disable=line-too-long
        build_staticsite_args['options']['namespace'] = '${namespace}'
        build_staticsite_args['options']['name'] = self.name
        build_staticsite_args['options']['path'] = os.path.join(
            os.path.realpath(self.context.env_root),
            self.path
        )

        with open(os.path.join(module_dir, '01-dependencies.yaml'), 'w') as output_stream:  # noqa
            yaml.dump(
                {'namespace': '${namespace}',
                 'stacker_bucket': '',
                 'stacks': {
                     "%s-dependencies" % self.name: {
                         'class_path': 'runway.blueprints.staticsite.dependencies.Dependencies'}},  # noqa pylint: disable=line-too-long
                 'pre_destroy': [
                     {'path': 'runway.hooks.cleanup_s3.purge_bucket',
                      'required': True,
                      'args': {
                          'bucket_rxref_lookup': "%s-dependencies::%s" % (self.name, i)
                      }} for i in ['AWSLogBucketName', 'ArtifactsBucketName']
                 ]},
                output_stream,
                default_flow_style=False
            )
        site_stack_variables = {
            'Aliases': '${default staticsite_aliases::undefined}',
            'RewriteDirectoryIndex': '${default staticsite_rewrite_directory_index::undefined}',  # noqa pylint: disable=line-too-long
            'WAFWebACL': '${default staticsite_web_acl::undefined}'
        }

        if self.environment_options.get('staticsite_enable_cf_logging', True):
            site_stack_variables['LogBucketName'] = "${rxref %s-dependencies::AWSLogBucketName}" % self.name  # noqa pylint: disable=line-too-long
        if self.environment_options.get('staticsite_acmcert_ssm_param'):
            site_stack_variables['AcmCertificateArn'] = '${ssmstore ${staticsite_acmcert_ssm_param}}'  # noqa pylint: disable=line-too-long
        else:
            site_stack_variables['AcmCertificateArn'] = '${default staticsite_acmcert_arn::undefined}'  # noqa pylint: disable=line-too-long

        # If staticsite_lambda_function_associations defined, add to stack config
        if self.environment_options.get('staticsite_lambda_function_associations'):
            site_stack_variables['lambda_function_associations'] = \
                self.environment_options.get('staticsite_lambda_function_associations')
            self.environment_options.pop('staticsite_lambda_function_associations')

        with open(os.path.join(module_dir, '02-staticsite.yaml'), 'w') as output_stream:
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
                     self.name: {
                         'class_path': 'runway.blueprints.staticsite.staticsite.StaticSite',
                         'variables': site_stack_variables}},
                 'post_build': [
                     {'path': 'runway.hooks.staticsite.upload_staticsite.sync',
                      'required': True,
                      'args': {
                          'bucket_output_lookup':
                              '%s::BucketName' % self.name,
                          'distributionid_output_lookup':
                              '%s::CFDistributionId' % self.name,
                          'distributiondomain_output_lookup':
                              '%s::CFDistributionDomainName' % self.name}}
                 ],
                 'pre_destroy': [
                     {'path': 'runway.hooks.cleanup_s3.purge_bucket',
                      'required': True,
                      'args': {
                          'bucket_rxref_lookup': "%s::BucketName" % self.name
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

        cfn_options = copy.deepcopy(self._runway_file_options)
        cfn_options.pop('class_path', None)
        cfn_module_instance = CloudFormation(self.context, module_dir, cfn_options)
        command_function = getattr(cfn_module_instance, command)
        command_function()

    def plan(self):
        """Create website CFN module and run stacker diff."""
        if self.environment_options:
            self.setup_website_module(command='plan')
        else:
            LOGGER.info("Skipping staticsite plan of %s; no environment "
                        "config found for this environment/region",
                        self.name)

    def deploy(self):
        """Create website CFN module and run stacker build."""
        if self.environment_options:
            self.setup_website_module(command='deploy')
        else:
            LOGGER.info("Skipping staticsite deploy of %s; no environment "
                        "config found for this environment/region",
                        self.name)

    def destroy(self):
        """Create website CFN module and run stacker destroy."""
        if self.environment_options:
            self.setup_website_module(command='destroy')
        else:
            LOGGER.info("Skipping staticsite destroy of %s; no environment "
                        "config found for this environment/region",
                        self.name)

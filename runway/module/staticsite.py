"""Static website module."""

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
    if not config.get('namespace'):
        LOGGER.fatal("staticsite: module %s's environment configuration is "
                     "missing a namespace definition!",
                     module_name)
        sys.exit(1)


class StaticSite(RunwayModule):
    """Static website Runway Module."""

    def setup_website_module(self, command):
        """Create stacker configuration for website module."""
        name = self.options.get('name', self.options.get('path'))
        # Make sure we remove any `.web` extension
        directory_suffix = '.web'
        if name.endswith(directory_suffix):
            name = name[:-len(directory_suffix)]

        ensure_valid_environment_config(
            name,
            self.options['parameters']
        )

        module_dir = tempfile.mkdtemp()
        LOGGER.info("staticsite: Generating CloudFormation configuration for "
                    "module %s in %s",
                    name,
                    module_dir)

        # Default parameter name matches build_staticsite hook
        hash_param = "${namespace}-%s-hash" % name
        if self.options.get('options', {}).get('source_hashing', {}).get('parameter'):
            hash_param = self.options.get('options', {}).get('source_hashing', {}).get(
                'parameter'
            )
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
        site_stack_variables = {
            'AcmCertificateArn': '${default staticsite_acmcert_arn::undefined}',
            'Aliases': '${default staticsite_aliases::undefined}',
            'DisableCloudFront': '${default staticsite_cf_disable::undefined}',
            'RewriteDirectoryIndex': '${default staticsite_rewrite_directory_index::undefined}',  # noqa pylint: disable=line-too-long
            'WAFWebACL': '${default staticsite_web_acl::undefined}'
        }

        parameters = self.options['parameters']

        if parameters.get('staticsite_acmcert_ssm_param'):
            site_stack_variables['AcmCertificateArn'] = '${ssmstore ${staticsite_acmcert_ssm_param}}'  # noqa pylint: disable=line-too-long

        if parameters.get('staticsite_enable_cf_logging', True):
            site_stack_variables['LogBucketName'] = "${rxref %s-dependencies::AWSLogBucketName}" % name  # noqa pylint: disable=line-too-long

        if parameters.get('staticsite_cf_disable', False):
            site_stack_variables['DisableCloudFront'] = "true"

        # If lambda_function_associations or custom_error_responses defined,
        # add to stack config
        for i in ['custom_error_responses', 'lambda_function_associations']:
            if parameters.get("staticsite_%s" % i):
                site_stack_variables[i] = parameters.pop("staticsite_%s" % i)

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
                         'variables': site_stack_variables}},
                 'post_build': [
                     {'path': 'runway.hooks.staticsite.upload_staticsite.sync',
                      'required': True,
                      'args': {
                          'bucket_output_lookup': '%s::BucketName' % name,
                          'website_url': '%s::BucketWebsiteURL' % name,
                          'cf_disabled': '%s' % site_stack_variables['DisableCloudFront'],
                          'distributionid_output_lookup': '%s::CFDistributionId' % name,  # noqa
                          'distributiondomain_output_lookup': '%s::CFDistributionDomainName' % name}}  # noqa pylint: disable=line-too-long
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
        if self.options['parameters']:
            self.setup_website_module(command='plan')
        else:
            LOGGER.info("Skipping staticsite plan of %s; no environment "
                        "config found for this environment/region",
                        self.options['path'])

    def deploy(self):
        """Create website CFN module and run stacker build."""
        parameters = self.options['parameters']
        if parameters:
            if parameters.get('staticsite_cf_disable', False) is False:
                msg = ("Please Note: Initial creation or updates to distribution settings "
                       "(e.g. url rewrites) will take quite a while (up to an hour). "
                       "Unless you receive an error your deployment is still running.")
                LOGGER.info(msg.upper())

            self.setup_website_module(command='deploy')
        else:
            LOGGER.info("Skipping staticsite deploy of %s; no environment "
                        "config found for this environment/region",
                        self.options['path'])

    def destroy(self):
        """Create website CFN module and run stacker destroy."""
        if self.options['parameters']:
            self.setup_website_module(command='destroy')
        else:
            LOGGER.info("Skipping staticsite destroy of %s; no environment "
                        "config found for this environment/region",
                        self.options['path'])

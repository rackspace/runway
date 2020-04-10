"""Static website module."""

import logging
import os
import sys
import tempfile
import warnings

from typing import Any, Dict, List, Union  # pylint: disable=unused-import

import yaml

from . import RunwayModule
from .cloudformation import CloudFormation

LOGGER = logging.getLogger('runway')


def add_url_scheme(url):
    """Add the scheme to an existing url.

    Args:
        url (str): The current url
    """
    if url.startswith('https://') or url.startswith('http://'):
        return url
    newurl = 'https://%s' % url
    return newurl


class StaticSite(RunwayModule):
    """Static website Runway Module."""

    def __init__(self, context, path, options=None):
        """Initialize."""
        super(StaticSite, self).__init__(context, path, options)
        self.name = self.options.get('name', self.options.get('path'))
        self.user_options = self.options.get('options', {})
        self.parameters = self.options.get('parameters')  # type: Dict[str, Any]
        self.region = self.context.env_region
        self._ensure_valid_environment_config()
        self._ensure_cloudfront_with_auth_at_edge()
        self._ensure_correct_region_with_auth_at_edge()

    def plan(self):
        """Create website CFN module and run stacker diff."""
        if self.parameters:
            self._setup_website_module(command='plan')
        else:
            LOGGER.info("Skipping staticsite plan of %s; no environment "
                        "config found for this environment/region",
                        self.options['path'])

    def deploy(self):
        """Create website CFN module and run stacker build."""
        if self.parameters:
            if self.parameters.get('staticsite_cf_disable', False) is False:
                msg = ("Please Note: Initial creation or updates to distribution settings "
                       "(e.g. url rewrites) will take quite a while (up to an hour). "
                       "Unless you receive an error your deployment is still running.")
                LOGGER.info(msg.upper())

                # Auth@Edge warning about subsequent deploys
                if self.parameters.get('staticsite_auth_at_edge', False) is True:
                    msg = ("PLEASE NOTE: A hook that is part of the dependencies stack of "
                           "the Auth@Edge static site deployment is designed to verify that "
                           "the correct Callback URLs are being used when a User Pool Client "
                           "already exists for the application. This ensures that there is no "
                           "interruption of service while the deployment reaches the stage "
                           "where the Callback URLs are updated to that of the Distribution. "
                           "Because of this you will receive a change set request on your first "
                           "subsequent deploy from the first, or any subsequent ones where the "
                           "alias domains have changed.")
                    LOGGER.info(msg)

            self._setup_website_module(command='deploy')
        else:
            LOGGER.info("Skipping staticsite deploy of %s; no environment "
                        "config found for this environment/region",
                        self.options['path'])

    def destroy(self):
        """Create website CFN module and run stacker destroy."""
        if self.parameters:
            self._setup_website_module(command='destroy')
        else:
            LOGGER.info("Skipping staticsite destroy of %s; no environment "
                        "config found for this environment/region",
                        self.options['path'])

    def _setup_website_module(self,  # type: StaticSite
                              command  # type: str
                             ):  # noqa: E124
        # type(...) -> return None
        """Create stacker configuration for website module."""
        module_dir = self._create_module_directory()
        self._create_dependencies_yaml(module_dir)
        self._create_staticsite_yaml(module_dir)
        # Don't destroy with the other stacks
        if command != 'destroy' and \
           (self.parameters.get('staticsite_auth_at_edge') or
            self.parameters.get('staticsite_rewrite_index_index')):  # noqa E129
            self._create_cleanup_yaml(module_dir)

        cfn = CloudFormation(
            self.context,
            module_dir,
            {i: self.options[i] for i in self.options if i != 'class_path'}
        )
        getattr(cfn, command)()

    def _create_module_directory(self):
        module_dir = tempfile.mkdtemp()
        LOGGER.info("staticsite: Generating CloudFormation configuration for "
                    "module %s in %s",
                    self.name,
                    module_dir)
        return module_dir

    def _create_dependencies_yaml(self, module_dir):
        pre_build = []

        pre_destroy = [
            {'path': 'runway.hooks.cleanup_s3.purge_bucket',
             'required': True,
             'args': {
                 'bucket_rxref_lookup': "%s-dependencies::%s" % (self.name, i)  # noqa
             }} for i in ['AWSLogBucketName', 'ArtifactsBucketName']
        ]

        if self.parameters.get('staticsite_auth_at_edge', False):
            # Retrieve the appropriate callback urls from the User Pool Client
            pre_build = [{
                'path': 'runway.hooks.staticsite.auth_at_edge.callback_url_retriever.get',
                'required': True,
                'data_key': 'aae_callback_url_retriever',
                'args': {
                    'user_pool_arn': self.parameters.get('staticsite_user_pool_arn', ''),
                    'stack_name': "${namespace}-%s-dependencies" % self.name
                }
            }]

            if self.parameters.get('staticsite_create_user_pool', False):
                # Retrieve the user pool id
                pre_destroy.append({
                    'path': 'runway.hooks.staticsite.auth_at_edge.user_pool_id_retriever.get',
                    'required': True,
                    'data_key': 'aae_user_pool_id_retriever',
                    'args': self._get_user_pool_id_retriever_variables(),
                })

                # Delete the domain prior to trying to delete the
                # User Pool Client that was created
                pre_destroy.append({
                    'path': 'runway.hooks.staticsite.auth_at_edge.domain_updater.delete',
                    'required': True,
                    'data_key': 'aae_domain_updater',
                    'args': self._get_domain_updater_variables(),
                })

        with open(os.path.join(module_dir, '01-dependencies.yaml'), 'w') as output_stream:  # noqa
            yaml.dump(
                {'namespace': '${namespace}',
                 'cfngin_bucket': '',
                 'stacks': {
                     "%s-dependencies" % self.name: {
                         'class_path': 'runway.blueprints.staticsite.dependencies.Dependencies',
                         'variables': self._get_dependencies_variables()}},
                 'pre_build': pre_build,
                 'pre_destroy': pre_destroy},
                output_stream,
                default_flow_style=False
            )

    def _create_staticsite_yaml(self, module_dir):
        # Default parameter name matches build_staticsite hook
        hash_param = self.user_options.get('source_hashing', {}).get(
            'parameter',
            "${namespace}-%s-hash" % self.name
        )

        build_staticsite_args = self.options.copy() or {}
        build_staticsite_args['artifact_bucket_rxref_lookup'] = "%s-dependencies::ArtifactsBucketName" % self.name  # noqa pylint: disable=line-too-long
        build_staticsite_args['options']['namespace'] = '${namespace}'
        build_staticsite_args['options']['name'] = self.name
        build_staticsite_args['options']['path'] = os.path.join(
            os.path.realpath(self.context.env_root),
            self.path
        )

        site_stack_variables = self._get_site_stack_variables()

        class_path = 'staticsite.StaticSite'

        pre_build = [{'path': 'runway.hooks.staticsite.build_staticsite.build',
                      'required': True,
                      'data_key': 'staticsite',
                      'args': build_staticsite_args}]

        post_build = [{'path': 'runway.hooks.staticsite.upload_staticsite.sync',
                       'required': True,
                       'args': {
                           'bucket_output_lookup': '%s::BucketName' % self.name,
                           'website_url': '%s::BucketWebsiteURL' % self.name,
                           'cf_disabled': site_stack_variables['DisableCloudFront'],
                           'distributionid_output_lookup': '%s::CFDistributionId' % (self.name),
                           'distributiondomain_output_lookup': '%s::CFDistributionDomainName' % self.name}}]  # noqa pylint: disable=line-too-long

        pre_destroy = [{'path': 'runway.hooks.cleanup_s3.purge_bucket',
                        'required': True,
                        'args': {'bucket_rxref_lookup': "%s::BucketName" % self.name}}]

        if self.parameters.get('staticsite_rewrite_directory_index') or \
           self.parameters.get('staticsite_auth_at_edge'):
            replicated_function_vars = self._get_replicated_function_variables()
            replicated_function_vars.update({
                'state_machine_arn':
                    '${rxref %s-cleanup::ReplicatedFunctionRemoverStateMachineArn}' % (
                        self.name
                    ),
            })
            pre_destroy.append({
                'path': 'runway.hooks.staticsite.cleanup.execute',
                'required': True,
                'data_key': 'cleanup',
                'args': replicated_function_vars
            })

        post_destroy = [{'path': 'runway.hooks.cleanup_ssm.delete_param',
                         'args': {'parameter_name': hash_param}}]

        if self.parameters.get('staticsite_auth_at_edge', False):
            class_path = 'auth_at_edge.AuthAtEdge'

            pre_build.append({
                'path': 'runway.hooks.staticsite.auth_at_edge.user_pool_id_retriever.get',
                'required': True,
                'data_key': 'aae_user_pool_id_retriever',
                'args': self._get_user_pool_id_retriever_variables()
            })
            pre_build.append({
                'path': 'runway.hooks.staticsite.auth_at_edge.domain_updater.update',
                'required': True,
                'data_key': 'aae_domain_updater',
                'args': self._get_domain_updater_variables()
            })
            pre_build.append({
                'path': 'runway.hooks.staticsite.auth_at_edge.lambda_config.write',
                'required': True,
                'data_key': 'aae_lambda_config',
                'args': self._get_lambda_config_variables(
                    site_stack_variables
                )
            })
            post_build.insert(0, {
                'path': 'runway.hooks.staticsite.auth_at_edge.client_updater.update',
                'required': True,
                'data_key': 'client_updater',
                'args': self._get_client_updater_variables(
                    self.name,
                    site_stack_variables
                )
            })

        if self.parameters.get('staticsite_role_boundary_arn', False):
            site_stack_variables['RoleBoundaryArn'] = \
                self.parameters.pop('staticsite_role_boundary_arn')

        # If lambda_function_associations or custom_error_responses defined,
        # add to stack config
        for i in ['custom_error_responses', 'lambda_function_associations']:
            if self.parameters.get("staticsite_%s" % i):
                site_stack_variables[i] = self.parameters.pop("staticsite_%s" % i)

        with open(os.path.join(module_dir, '02-staticsite.yaml'), 'w') as output_stream:  # noqa
            yaml.dump(
                {'namespace': '${namespace}',
                 'cfngin_bucket': '',
                 'pre_build': pre_build,
                 'stacks': {
                     self.name: {
                         'class_path': 'runway.blueprints.staticsite.%s' % class_path,  # noqa
                         'variables': site_stack_variables}},
                 'post_build': post_build,
                 'pre_destroy': pre_destroy,
                 'post_destroy': post_destroy},
                output_stream,
                default_flow_style=False
            )

    def _create_cleanup_yaml(self, module_dir):
        replicated_function_vars = self._get_replicated_function_variables()

        with open(os.path.join(module_dir, '03-cleanup.yaml'), 'w') as output_stream:  # noqa
            yaml.dump(
                {'namespace': '${namespace}',
                 'cfngin_bucket': '',
                 'stacks': {
                     '%s-cleanup' % self.name: {
                         'class_path': 'runway.blueprints.staticsite.cleanup.Cleanup',
                         'variables': replicated_function_vars
                     }
                 }},
                output_stream,
                default_flow_style=False
            )

    def _get_replicated_function_variables(self):
        replicated_function_vars = {
            'stack_name': '${namespace}-%s-cleanup' % self.name,
            'function_arns': [],
            'DisableCloudFront': self.parameters.get('staticsite_cf_disable', False),
        }  # type: Dict[str, Union[str, List[str]]]

        if self.parameters.get('staticsite_rewrite_directory_index'):
            replicated_function_vars['function_arns'].append(
                '${rxref %s::LambdaCFDirectoryIndexRewriteArn}' % self.name
            )

        if self.parameters.get('staticsite_auth_at_edge'):
            for lamb in ['CheckAuth',
                         'HttpHeaders',
                         'ParseAuth',
                         'RefreshAuth',
                         'SignOut']:
                replicated_function_vars['function_arns'].append(
                    '${rxref %s::Lambda%sArn}' % (self.name, lamb)
                )

        return replicated_function_vars

    def _get_site_stack_variables(self):
        site_stack_variables = {
            'Aliases': [],
            'DisableCloudFront': self.parameters.get('staticsite_cf_disable', False),
            'RewriteDirectoryIndex': self.parameters.get(
                'staticsite_rewrite_directory_index',
                ''
            ),
            'RedirectPathSignIn': '${default staticsite_redirect_path_sign_in::/parseauth}',
            'RedirectPathSignOut': '${default staticsite_redirect_path_sign_out::/}',
            'RedirectPathAuthRefresh':
                '${default staticsite_redirect_path_auth_refresh::/refreshauth}',
            'SignOutUrl': '${default staticsite_sign_out_url::/signout}',
            'WAFWebACL': self.parameters.get('staticsite_web_acl', ''),
        }

        if self.parameters.get('staticsite_aliases'):
            site_stack_variables['Aliases'] = self.parameters.get('staticsite_aliases').split(',')

        if self.parameters.get('staticsite_acmcert_arn'):
            site_stack_variables['AcmCertificateArn'] = \
                self.parameters['staticsite_acmcert_arn']

        if self.parameters.get('staticsite_acmcert_ssm_param'):
            dep_msg = ('Use of the "staticsite_acmcert_ssm_param" option has '
                       'been deprecated. The "staticsite_acmcert_arn" option '
                       'with an "ssm" lookup should be used instead.')
            warnings.warn(dep_msg, DeprecationWarning)
            LOGGER.warning(dep_msg)
            site_stack_variables['AcmCertificateArn'] = '${ssmstore ${staticsite_acmcert_ssm_param}}'  # noqa pylint: disable=line-too-long

        if self.parameters.get('staticsite_enable_cf_logging', True):
            site_stack_variables['LogBucketName'] = "${rxref %s-dependencies::AWSLogBucketName}" % self.name  # noqa pylint: disable=line-too-long

        if self.parameters.get('staticsite_auth_at_edge', False):
            self._ensure_auth_at_edge_requirements()
            site_stack_variables['UserPoolArn'] = self.parameters.get(
                'staticsite_user_pool_arn'
            )
            site_stack_variables['NonSPAMode'] = self.parameters.get(
                'staticsite_non_spa',
                False
            )
            site_stack_variables['HttpHeaders'] = self._get_http_headers()
            site_stack_variables['CookieSettings'] = self._get_cookie_settings()
            site_stack_variables['OAuthScopes'] = self._get_oauth_scopes()
            # pylint: disable=line-too-long
            site_stack_variables['SupportedIdentityProviders'] = self._get_supported_identity_providers()  # noqa
        else:
            # If lambda_function_associations or custom_error_responses defined,
            # add to stack config. Only if not using Auth@Edge
            for i in ['custom_error_responses', 'lambda_function_associations']:
                if self.parameters.get("staticsite_%s" % i):
                    site_stack_variables[i] = self.parameters.get("staticsite_%s" % i)
                    self.parameters.pop("staticsite_%s" % i)

        return site_stack_variables

    def _get_cookie_settings(self):
        """Retrieve the cookie settings from the variables or return the default."""
        if self.parameters.get('staticsite_cookie_settings'):
            return self.parameters.get('staticsite_cookie_settings')
        return {
            "idToken": "Path=/; Secure; SameSite=Lax",
            "accessToken": "Path=/; Secure; SameSite=Lax",
            "refreshToken": "Path=/; Secure; SameSite=Lax",
            "nonce": "Path=/; Secure; HttpOnly; Max-Age=1800; SameSite=Lax",
        }

    def _get_http_headers(self):
        """Retrieve the http headers from the variables or return the default."""
        if self.parameters.get('staticsite_http_headers'):
            return self.parameters.get('staticsite_http_headers')
        return {
            "Content-Security-Policy": "default-src https: 'unsafe-eval' 'unsafe-inline'; "
                                       # pylint: disable=line-too-long
                                       "font-src 'self' 'unsafe-inline' 'unsafe-eval' data: https:; "  # noqa
                                       "object-src 'none'; "
                                       # pylint: disable=line-too-long
                                       "connect-src 'self' https://*.amazonaws.com https://*.amazoncognito.com",  # noqa
            "Strict-Transport-Security": "max-age=31536000; "
                                         "includeSubdomains; "
                                         "preload",
            "Referrer-Policy": "same-origin",
            "X-XSS-Protection": "1; mode=block",
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
        }

    def _get_oauth_scopes(self):
        """Retrieve the oauth scopes from the variables or return the default."""
        if self.parameters.get('staticsite_oauth_scopes'):
            return self.parameters.get('staticsite_oauth_scopes')
        return [
            'phone',
            'email',
            'profile',
            'openid',
            'aws.cognito.signin.user.admin'
        ]

    def _get_supported_identity_providers(self):
        providers = self.parameters.get('staticsite_supported_identity_providers')
        if providers:
            return [provider.strip() for provider in providers.split(',')]
        return ['COGNITO']

    def _get_dependencies_variables(self):
        variables = {'OAuthScopes': self._get_oauth_scopes()}
        if self.parameters.get('staticsite_auth_at_edge', False):
            self._ensure_auth_at_edge_requirements()

            variables.update({
                'AuthAtEdge': self.parameters.get(
                    'staticsite_auth_at_edge',
                    False
                )
            })

            if self.parameters.get('staticsite_create_user_pool', False):
                variables.update({
                    'CreateUserPool': self.parameters.get('staticsite_create_user_pool', False)
                })

        return variables

    def _get_user_pool_id_retriever_variables(self):
        args = {
            'user_pool_arn': self.parameters.get('staticsite_user_pool_arn', ''),
        }

        if self.parameters.get('staticsite_create_user_pool', False):
            args['created_user_pool_id'] = \
                '${rxref %s-dependencies::AuthAtEdgeUserPoolId}' % (self.name)

        return args

    def _get_domain_updater_variables(self):
        return {
            'client_id_output_lookup': "%s-dependencies::AuthAtEdgeClient" % self.name,  # noqa pylint: disable=line-too-long
            'client_id': "${rxref %s-dependencies::AuthAtEdgeClient}" % self.name,
        }

    def _get_lambda_config_variables(self, site_stack_variables):
        return {
            'client_id': "${rxref %s-dependencies::AuthAtEdgeClient}" % self.name,  # noqa pylint: disable=line-too-long
            'bucket': "${rxref %s-dependencies::ArtifactsBucketName}" % self.name,
            'cookie_settings': site_stack_variables['CookieSettings'],
            'http_headers': site_stack_variables['HttpHeaders'],
            'oauth_scopes': site_stack_variables['OAuthScopes'],
            'redirect_path_refresh': site_stack_variables['RedirectPathAuthRefresh'],
            'redirect_path_sign_in': site_stack_variables['RedirectPathSignIn'],
            'redirect_path_sign_out': site_stack_variables['RedirectPathSignOut'],
        }

    def _get_client_updater_variables(self, name, site_stack_variables):
        aliases = [add_url_scheme(x) for x in site_stack_variables['Aliases']]
        return {
            'alternate_domains': aliases,
            'client_id': "${rxref %s-dependencies::AuthAtEdgeClient}" % self.name,
            'distribution_domain': '${rxref %s::CFDistributionDomainName}' % name,
            'oauth_scopes': site_stack_variables['OAuthScopes'],
            'redirect_path_sign_in': site_stack_variables['RedirectPathSignIn'],
            'redirect_path_sign_out': site_stack_variables['RedirectPathSignOut'],
            'supported_identity_providers': site_stack_variables['SupportedIdentityProviders'],
        }

    def _ensure_auth_at_edge_requirements(self):
        if not self.parameters.get('staticsite_user_pool_arn') and \
           not self.parameters.get('staticsite_create_user_pool'):
            LOGGER.fatal("A Cognito UserPool ARN is required with Auth@Edge. "
                         "You can supply your own or have one created.")
            sys.exit(1)

    def _ensure_correct_region_with_auth_at_edge(self):
        """Exit if not in the us-east-1 region and deploying to Auth@Edge.

        Lambda@Edge is only available within the us-east-1 region.
        """
        if self.parameters.get('staticsite_auth_at_edge', False) and self.region != 'us-east-1':
            LOGGER.fatal("Auth@Edge must be deployed in us-east-1.")
            sys.exit(1)

    def _ensure_cloudfront_with_auth_at_edge(self):
        """Exit if both the Auth@Edge and CloudFront disablement are true."""
        if self.parameters.get('staticsite_cf_disable', False) and \
           self.parameters.get('staticsite_auth_at_edge', False):
            LOGGER.fatal("CloudFront cannot be disabled when using Auth@Edge")
            sys.exit(1)

    def _ensure_valid_environment_config(self):
        """Exit if config is invalid."""
        if not self.parameters.get('namespace'):
            LOGGER.fatal("staticsite: module %s's environment configuration is "
                         "missing a namespace definition!",
                         self.name)
            sys.exit(1)

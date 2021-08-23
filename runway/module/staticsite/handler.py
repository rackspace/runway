"""Static website Module."""
from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, cast

import yaml

from ..._logging import PrefixAdaptor
from ...utils import YamlDumper
from ..base import RunwayModule
from ..cloudformation import CloudFormation
from .options import StaticSiteOptions
from .parameters import RunwayStaticSiteModuleParametersDataModel
from .utils import add_url_scheme

if TYPE_CHECKING:
    from ..._logging import RunwayLogger
    from ...context import RunwayContext
    from ..base import ModuleOptions

LOGGER = cast("RunwayLogger", logging.getLogger(__name__))


class StaticSite(RunwayModule):
    """Static website Runway Module."""

    options: StaticSiteOptions
    parameters: RunwayStaticSiteModuleParametersDataModel

    def __init__(
        self,
        context: RunwayContext,
        *,
        explicitly_enabled: Optional[bool] = False,
        logger: RunwayLogger = LOGGER,
        module_root: Path,
        name: Optional[str] = None,
        options: Optional[Union[Dict[str, Any], ModuleOptions]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        **_: Any,
    ) -> None:
        """Instantiate class.

        Args:
            context: Runway context object for the current session.
            explicitly_enabled: Whether or not the module is explicitly enabled.
                This is can be set in the event that the current environment being
                deployed to matches the defined environments of the module/deployment.
            logger: Used to write logs.
            module_root: Root path of the module.
            name: Name of the module.
            options: Options passed to the module class from the config as ``options``
                or ``module_options`` if coming from the deployment level.
            parameters: Values to pass to the underlying infrastructure as code
                tool that will alter the resulting infrastructure being deployed.
                Used to templatize IaC.

        """
        super().__init__(
            context,
            explicitly_enabled=explicitly_enabled,
            logger=logger,
            module_root=module_root,
            name=name,
            options=StaticSiteOptions.parse_obj(options or {}),
            parameters=parameters,
        )
        self.parameters = RunwayStaticSiteModuleParametersDataModel.parse_obj(
            self.parameters
        )
        # logger needs to be created here to use the correct logger
        self.logger = PrefixAdaptor(self.name, LOGGER)
        self._ensure_valid_environment_config()
        self._ensure_cloudfront_with_auth_at_edge()
        self._ensure_correct_region_with_auth_at_edge()

    def deploy(self) -> None:
        """Create website CFN module and run CFNgin.deploy."""
        if self.parameters:
            if not self.parameters.cf_disable:
                self.logger.warning(
                    "initial creation of & updates to distributions can take "
                    "up to an hour to complete"
                )

                # Auth@Edge warning about subsequent deploys
                if (
                    self.parameters.auth_at_edge
                    and not self.parameters.aliases
                    and self.ctx.is_interactive
                ):
                    self.logger.warning(
                        "A hook that is part of the dependencies stack of "
                        "the Auth@Edge static site deployment is designed "
                        "to verify that the correct Callback URLs are "
                        "being used when a User Pool Client already "
                        "exists for the application. This ensures that "
                        "there is no interruption of service while the "
                        "deployment reaches the stage where the Callback "
                        "URLs are updated to that of the Distribution. "
                        "Because of this you may receive a change set "
                        "prompt on subsequent deploys."
                    )
            self._setup_website_module(command="deploy")
        else:
            self.logger.info("skipped; environment required but not defined")

    def destroy(self) -> None:
        """Create website CFN module and run CFNgin.destroy."""
        if self.parameters:
            self._setup_website_module(command="destroy")
        else:
            self.logger.info("skipped; environment required but not defined")

    def init(self) -> None:
        """Run init."""
        LOGGER.warning("init not currently supported for %s", self.__class__.__name__)

    def plan(self) -> None:
        """Create website CFN module and run CFNgin.diff."""
        if self.parameters:
            self._setup_website_module(command="plan")
        else:
            self.logger.info("skipped; environment required but not defined")

    def _setup_website_module(self, command: str) -> None:
        """Create CFNgin configuration for website module."""
        self.logger.info("generating CFNgin config...")
        module_dir = self._create_module_directory()
        self._create_dependencies_yaml(module_dir)
        self._create_staticsite_yaml(module_dir)

        # Earlier Runway versions included a CFN stack with a state machine
        # that attempted to automatically clean up the orphaned Lambda@Edge
        # functions. This was found to be unreliable and has been removed.
        # For a period of time (e.g. until the next major release) leaving this
        # in to automatically delete the stack. Not a major priority to have
        # Runway delete the old `-cleanup` stack, as the resources in it don't
        # have any costs when unused.
        if command == "destroy" and (
            self.parameters.auth_at_edge
            or self.parameters.dict().get("staticsite_rewrite_index_index")
        ):
            self._create_cleanup_yaml(module_dir)

        cfn = CloudFormation(
            self.ctx,
            explicitly_enabled=self.explicitly_enabled,
            module_root=module_dir,
            name=self.name,
            options=self.options.data.dict(),
            parameters=self.parameters.dict(by_alias=True),
        )
        self.logger.info("%s (in progress)", command)
        getattr(cfn, command)()
        self.logger.info("%s (complete)", command)

    def _create_module_directory(self) -> Path:
        module_dir = Path(tempfile.mkdtemp())
        self.logger.debug("using temporary directory: %s", module_dir)
        return module_dir

    def _create_dependencies_yaml(self, module_dir: Path) -> None:
        pre_deploy: List[Any] = []

        pre_destroy = [
            {
                "path": "runway.cfngin.hooks.cleanup_s3.purge_bucket",
                "required": True,
                "args": {"bucket_name": f"${{rxref {self.name}-dependencies::{i}}}"},
            }
            for i in ["AWSLogBucketName", "ArtifactsBucketName"]
        ]

        if self.parameters.auth_at_edge:
            if not self.parameters.aliases:
                # Retrieve the appropriate callback urls from the User Pool Client
                pre_deploy.append(
                    {
                        "path": "runway.cfngin.hooks.staticsite.auth_at_edge."
                        "callback_url_retriever.get",
                        "required": True,
                        "data_key": "aae_callback_url_retriever",
                        "args": {
                            "user_pool_arn": self.parameters.user_pool_arn,
                            "aliases": self.parameters.aliases,
                            "stack_name": f"${{namespace}}-{self.name}-dependencies",
                        },
                    }
                )

            if self.parameters.create_user_pool:
                # Retrieve the user pool id
                pre_destroy.append(
                    {
                        "path": "runway.cfngin.hooks.staticsite.auth_at_edge."
                        "user_pool_id_retriever.get",
                        "required": True,
                        "data_key": "aae_user_pool_id_retriever",
                        "args": self._get_user_pool_id_retriever_variables(),
                    }
                )

                # Delete the domain prior to trying to delete the
                # User Pool Client that was created
                pre_destroy.append(
                    {
                        "path": "runway.cfngin.hooks.staticsite.auth_at_edge."
                        "domain_updater.delete",
                        "required": True,
                        "data_key": "aae_domain_updater",
                        "args": self._get_domain_updater_variables(),
                    }
                )
            else:
                # Retrieve the user pool id
                pre_deploy.append(
                    {
                        "path": "runway.cfngin.hooks.staticsite.auth_at_edge."
                        "user_pool_id_retriever.get",
                        "required": True,
                        "data_key": "aae_user_pool_id_retriever",
                        "args": self._get_user_pool_id_retriever_variables(),
                    }
                )

        content: Dict[str, Any] = {
            "namespace": "${namespace}",
            "cfngin_bucket": "",
            "stacks": {
                "%s-dependencies"
                % self.name: {
                    "class_path": "runway.blueprints.staticsite.dependencies.Dependencies",
                    "variables": self._get_dependencies_variables(),
                }
            },
            "pre_deploy": pre_deploy,
            "pre_destroy": pre_destroy,
        }

        with open(
            module_dir / "01-dependencies.yaml", "w", encoding="utf-8"
        ) as output_stream:
            yaml.dump(content, output_stream, default_flow_style=False)
        self.logger.debug(
            "created 01-dependencies.yaml:\n%s", yaml.dump(content, Dumper=YamlDumper)
        )

    def _create_staticsite_yaml(self, module_dir: Path) -> None:
        # Default parameter name matches build_staticsite hook
        if not self.options.source_hashing.parameter:
            self.options.source_hashing.parameter = f"${{namespace}}-{self.name}-hash"
        nonce_secret_param = f"${{namespace}}-{self.name}-nonce-secret"

        build_staticsite_args: Dict[str, Any] = {
            # ensures yaml.safe_load will work by using JSON to convert objects
            "options": json.loads(self.options.data.json(by_alias=True))
        }
        build_staticsite_args[
            "artifact_bucket_rxref_lookup"
        ] = f"{self.name}-dependencies::ArtifactsBucketName"
        build_staticsite_args["options"]["namespace"] = "${namespace}"  # type: ignore
        build_staticsite_args["options"]["name"] = self.name  # type: ignore
        build_staticsite_args["options"]["path"] = os.path.join(  # type: ignore
            os.path.realpath(self.ctx.env.root_dir), self.path
        )

        site_stack_variables = self._get_site_stack_variables()

        class_path = "staticsite.StaticSite"

        pre_deploy = [
            {
                "path": "runway.cfngin.hooks.staticsite.build_staticsite.build",
                "required": True,
                "data_key": "staticsite",
                "args": build_staticsite_args,
            }
        ]

        post_deploy = [
            {
                "path": "runway.cfngin.hooks.staticsite.upload_staticsite.sync",
                "required": True,
                "args": {
                    "bucket_name": f"${{cfn ${{namespace}}-{self.name}.BucketName}}",
                    "website_url": f"${{cfn ${{namespace}}-{self.name}.BucketWebsiteURL"
                    "::default=undefined}}",
                    "extra_files": [i.dict() for i in self.options.extra_files],
                    "cf_disabled": site_stack_variables["DisableCloudFront"],
                    "distribution_id": f"${{cfn ${{namespace}}-{self.name}.CFDistributionId"
                    "::default=undefined}",
                    "distribution_domain": f"${{cfn ${{namespace}}-{self.name}."
                    "CFDistributionDomainName::default=undefined}}",
                },
            }
        ]

        pre_destroy = [
            {
                "path": "runway.cfngin.hooks.cleanup_s3.purge_bucket",
                "required": True,
                "args": {"bucket_name": f"${{rxref {self.name}::BucketName}}"},
            }
        ]

        if self.parameters.rewrite_directory_index or self.parameters.auth_at_edge:
            pre_destroy.append(
                {
                    "path": "runway.cfngin.hooks.staticsite.cleanup.warn",
                    "required": False,
                    "args": {"stack_relative_name": self.name},
                }
            )

        post_destroy = [
            {
                "path": "runway.cfngin.hooks.cleanup_ssm.delete_param",
                "args": {"parameter_name": i},
            }
            for i in [
                self.options.source_hashing.parameter,
                nonce_secret_param,
                f"{self.options.source_hashing.parameter}extra",
            ]
        ]

        if self.parameters.auth_at_edge:
            class_path = "auth_at_edge.AuthAtEdge"

            pre_deploy.append(
                {
                    "path": "runway.cfngin.hooks.staticsite.auth_at_edge."
                    "user_pool_id_retriever.get",
                    "required": True,
                    "data_key": "aae_user_pool_id_retriever",
                    "args": self._get_user_pool_id_retriever_variables(),
                }
            )
            pre_deploy.append(
                {
                    "path": "runway.cfngin.hooks.staticsite.auth_at_edge.domain_updater.update",
                    "required": True,
                    "data_key": "aae_domain_updater",
                    "args": self._get_domain_updater_variables(),
                }
            )
            pre_deploy.append(
                {
                    "path": "runway.cfngin.hooks.staticsite.auth_at_edge.lambda_config.write",
                    "required": True,
                    "data_key": "aae_lambda_config",
                    "args": self._get_lambda_config_variables(
                        site_stack_variables,
                        nonce_secret_param,
                        self.parameters.required_group,
                    ),
                }
            )
            if not self.parameters.aliases:
                post_deploy.insert(
                    0,
                    {
                        "path": "runway.cfngin.hooks.staticsite.auth_at_edge."
                        "client_updater.update",
                        "required": True,
                        "data_key": "client_updater",
                        "args": self._get_client_updater_variables(
                            self.name, site_stack_variables
                        ),
                    },
                )

        if self.parameters.role_boundary_arn:
            site_stack_variables["RoleBoundaryArn"] = self.parameters.role_boundary_arn

        site_stack_variables["custom_error_responses"] = [
            i.dict(exclude_none=True) for i in self.parameters.custom_error_responses
        ]
        site_stack_variables["lambda_function_associations"] = [
            i.dict() for i in self.parameters.lambda_function_associations
        ]

        content = {
            "namespace": "${namespace}",
            "cfngin_bucket": "",
            "pre_deploy": pre_deploy,
            "stacks": {
                self.name: {
                    "class_path": f"runway.blueprints.staticsite.{class_path}",
                    "variables": site_stack_variables,
                }
            },
            "post_deploy": post_deploy,
            "pre_destroy": pre_destroy,
            "post_destroy": post_destroy,
        }

        with open(
            module_dir / "02-staticsite.yaml", "w", encoding="utf-8"
        ) as output_stream:
            yaml.dump(content, output_stream, default_flow_style=False)
        self.logger.debug(
            "created 02-staticsite.yaml:\n%s", yaml.dump(content, Dumper=YamlDumper)
        )

    def _create_cleanup_yaml(self, module_dir: Path) -> None:
        content = {
            "namespace": "${namespace}",
            "cfngin_bucket": "",
            "stacks": {
                "%s-cleanup"
                % self.name: {
                    "template_path": os.path.join(
                        tempfile.gettempdir(), "thisfileisnotused.yaml"
                    ),
                }
            },
        }

        with open(
            module_dir / "03-cleanup.yaml", "w", encoding="utf-8"
        ) as output_stream:
            yaml.dump(content, output_stream, default_flow_style=False)
        self.logger.debug(
            "created 03-cleanup.yaml:\n%s", yaml.dump(content, Dumper=YamlDumper)
        )

    def _get_site_stack_variables(self) -> Dict[str, Any]:
        site_stack_variables: Dict[str, Any] = {
            "Aliases": [],
            "Compresss": self.parameters.compress,
            "DisableCloudFront": self.parameters.cf_disable,
            "RewriteDirectoryIndex": self.parameters.rewrite_directory_index or "",
            "RedirectPathSignIn": "${default staticsite_redirect_path_sign_in::/parseauth}",
            "RedirectPathSignOut": "${default staticsite_redirect_path_sign_out::/}",
            "RedirectPathAuthRefresh": "${default staticsite_redirect_path_auth_refresh"
            "::/refreshauth}",
            "SignOutUrl": "${default staticsite_sign_out_url::/signout}",
            "WAFWebACL": self.parameters.web_acl or "",
        }

        if self.parameters.aliases:
            site_stack_variables["Aliases"] = self.parameters.aliases

        if self.parameters.acmcert_arn:
            site_stack_variables["AcmCertificateArn"] = self.parameters.acmcert_arn

        if self.parameters.enable_cf_logging:
            site_stack_variables[
                "LogBucketName"
            ] = f"${{rxref {self.name}-dependencies::AWSLogBucketName}}"

        if self.parameters.auth_at_edge:
            self._ensure_auth_at_edge_requirements()
            site_stack_variables["UserPoolArn"] = self.parameters.user_pool_arn
            site_stack_variables["NonSPAMode"] = self.parameters.non_spa
            site_stack_variables["HttpHeaders"] = self.parameters.http_headers
            site_stack_variables["CookieSettings"] = self.parameters.cookie_settings
            site_stack_variables["OAuthScopes"] = self.parameters.oauth_scopes
        else:
            site_stack_variables["custom_error_responses"] = [
                i.dict(exclude_none=True)
                for i in self.parameters.custom_error_responses
            ]
            site_stack_variables["lambda_function_associations"] = [
                i.dict() for i in self.parameters.lambda_function_associations
            ]

        return site_stack_variables

    def _get_dependencies_variables(self) -> Dict[str, Any]:
        variables: Dict[str, Any] = {"OAuthScopes": self.parameters.oauth_scopes}
        if self.parameters.auth_at_edge:
            self._ensure_auth_at_edge_requirements()

            variables.update(
                {
                    "AuthAtEdge": self.parameters.auth_at_edge,
                    "SupportedIdentityProviders": self.parameters.supported_identity_providers,
                    "RedirectPathSignIn": (
                        "${default staticsite_redirect_path_sign_in::/parseauth}"
                    ),
                    "RedirectPathSignOut": (
                        "${default staticsite_redirect_path_sign_out::/}"
                    ),
                },
            )

            if self.parameters.aliases:
                variables.update({"Aliases": self.parameters.aliases})
            if self.parameters.additional_redirect_domains:
                variables.update(
                    {
                        "AdditionalRedirectDomains": self.parameters.additional_redirect_domains
                    }
                )
            if self.parameters.create_user_pool:
                variables.update({"CreateUserPool": self.parameters.create_user_pool})

        return variables

    def _get_user_pool_id_retriever_variables(self) -> Dict[str, Any]:
        args: Dict[str, Any] = {
            "user_pool_arn": self.parameters.user_pool_arn,
        }

        if self.parameters.create_user_pool:
            args[
                "created_user_pool_id"
            ] = f"${{rxref {self.name}-dependencies::AuthAtEdgeUserPoolId}}"

        return args

    def _get_domain_updater_variables(self) -> Dict[str, str]:
        return {
            "client_id_output_lookup": f"{self.name}-dependencies::AuthAtEdgeClient",
            "client_id": f"${{rxref {self.name}-dependencies::AuthAtEdgeClient}}",
        }

    def _get_lambda_config_variables(
        self,
        site_stack_variables: Dict[str, Any],
        nonce_secret_param: str,
        required_group: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "client_id": f"${{rxref {self.name}-dependencies::AuthAtEdgeClient}}",
            "bucket": f"${{rxref {self.name}-dependencies::ArtifactsBucketName}}",
            "cookie_settings": site_stack_variables["CookieSettings"],
            "http_headers": site_stack_variables["HttpHeaders"],
            "nonce_signing_secret_param_name": nonce_secret_param,
            "oauth_scopes": site_stack_variables["OAuthScopes"],
            "redirect_path_refresh": site_stack_variables["RedirectPathAuthRefresh"],
            "redirect_path_sign_in": site_stack_variables["RedirectPathSignIn"],
            "redirect_path_sign_out": site_stack_variables["RedirectPathSignOut"],
            "required_group": required_group,
        }

    def _get_client_updater_variables(
        self, name: str, site_stack_variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        aliases = [add_url_scheme(x) for x in site_stack_variables["Aliases"]]
        return {
            "alternate_domains": aliases,
            "client_id": f"${{rxref {self.name}-dependencies::AuthAtEdgeClient}}",
            "distribution_domain": f"${{rxref {name}::CFDistributionDomainName}}",
            "oauth_scopes": site_stack_variables["OAuthScopes"],
            "redirect_path_sign_in": site_stack_variables["RedirectPathSignIn"],
            "redirect_path_sign_out": site_stack_variables["RedirectPathSignOut"],
            "supported_identity_providers": site_stack_variables[
                "SupportedIdentityProviders"
            ],
        }

    def _ensure_auth_at_edge_requirements(self) -> None:
        if not (self.parameters.user_pool_arn or self.parameters.create_user_pool):
            self.logger.error(
                "staticsite_user_pool_arn or staticsite_create_user_pool "
                "is required for Auth@Edge; "
            )
            sys.exit(1)

    def _ensure_correct_region_with_auth_at_edge(self) -> None:
        """Exit if not in the us-east-1 region and deploying to Auth@Edge.

        Lambda@Edge is only available within the us-east-1 region.

        """
        if self.parameters.auth_at_edge and self.region != "us-east-1":
            self.logger.error("Auth@Edge must be deployed in us-east-1.")
            sys.exit(1)

    def _ensure_cloudfront_with_auth_at_edge(self) -> None:
        """Exit if both the Auth@Edge and CloudFront disablement are true."""
        if self.parameters.cf_disable and self.parameters.auth_at_edge:
            self.logger.error(
                'staticsite_cf_disable must be "false" if '
                'staticsite_auth_at_edge is "true"'
            )
            sys.exit(1)

    def _ensure_valid_environment_config(self) -> None:
        """Exit if config is invalid."""
        if not self.parameters.namespace:
            self.logger.error("namespace parameter is required but not defined")
            sys.exit(1)

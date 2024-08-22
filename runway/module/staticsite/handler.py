"""Static website Module."""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import yaml

from ..._logging import PrefixAdaptor
from ...compat import cached_property
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


class StaticSite(RunwayModule[StaticSiteOptions]):
    """Static website Runway Module."""

    DEPRECATION_MSG = (
        "Static website Runway module support has been deprecated and "
        "may be removed in the next major release."
    )

    parameters: RunwayStaticSiteModuleParametersDataModel

    def __init__(
        self,
        context: RunwayContext,
        *,
        explicitly_enabled: bool | None = False,
        logger: RunwayLogger = LOGGER,
        module_root: Path,
        name: str | None = None,
        options: dict[str, Any] | ModuleOptions | None = None,
        parameters: dict[str, Any] | None = None,
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
        self.parameters = RunwayStaticSiteModuleParametersDataModel.model_validate(self.parameters)
        # logger needs to be created here to use the correct logger
        self.logger = PrefixAdaptor(self.name, LOGGER)
        LOGGER.warning("%s:%s", self.name, self.DEPRECATION_MSG)
        self._ensure_valid_environment_config()
        self._ensure_cloudfront_with_auth_at_edge()
        self._ensure_correct_region_with_auth_at_edge()

    @cached_property
    def sanitized_name(self) -> str:
        """Sanitized name safe to use in a CloudFormation Stack name.

        Errors are usually caused here by a ``.`` in the name.
        This unintelligently replaces ``.`` with ``-``.

        If issues are still encountered, we can check against the regex of
        ``(?=^.{1,128}$)^[a-zA-Z][-a-zA-Z0-9_]+$``.

        """
        return self.name.replace(".", "-").strip("-")

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
            or self.parameters.model_dump().get("staticsite_rewrite_index_index")
        ):
            self._create_cleanup_yaml(module_dir)

        cfn = CloudFormation(
            self.ctx,
            explicitly_enabled=self.explicitly_enabled,
            module_root=module_dir,
            name=self.name,
            options=self.options.data.model_dump(),
            parameters=self.parameters.model_dump(by_alias=True),
        )
        self.logger.info("%s (in progress)", command)
        getattr(cfn, command)()
        self.logger.info("%s (complete)", command)

    def _create_module_directory(self) -> Path:
        module_dir = Path(tempfile.mkdtemp())
        self.logger.debug("using temporary directory: %s", module_dir)
        return module_dir

    def _create_dependencies_yaml(self, module_dir: Path) -> Path:
        """Create CFNgin config file for Static Site dependency stack.

        Resulting config file is save to ``module_dir`` as ``01-dependencies.yaml``.

        Args:
            module_dir: Path to the Runway module.

        Returns:
            Path to the file that was created.

        """
        pre_deploy: list[Any] = []

        pre_destroy = [
            {
                "args": {"bucket_name": f"${{rxref {self.sanitized_name}-dependencies::{i}}}"},
                "path": "runway.cfngin.hooks.cleanup_s3.purge_bucket",
                "required": True,
            }
            for i in ["AWSLogBucketName", "ArtifactsBucketName"]
        ]

        if self.parameters.auth_at_edge:
            if not self.parameters.aliases:
                # Retrieve the appropriate callback urls from the User Pool Client
                pre_deploy.append(
                    {
                        "args": {
                            "user_pool_arn": self.parameters.user_pool_arn,
                            "aliases": self.parameters.aliases,
                            "stack_name": f"${{namespace}}-{self.sanitized_name}-dependencies",
                        },
                        "data_key": "aae_callback_url_retriever",
                        "path": "runway.cfngin.hooks.staticsite.auth_at_edge."
                        "callback_url_retriever.get",
                        "required": True,
                    }
                )

            if self.parameters.create_user_pool:
                # Retrieve the user pool id
                pre_destroy.append(
                    {
                        "args": self._get_user_pool_id_retriever_variables(),
                        "data_key": "aae_user_pool_id_retriever",
                        "path": "runway.cfngin.hooks.staticsite.auth_at_edge."
                        "user_pool_id_retriever.get",
                        "required": True,
                    }
                )

                # Delete the domain prior to trying to delete the
                # User Pool Client that was created
                pre_destroy.append(
                    {
                        "args": self._get_domain_updater_variables(),
                        "data_key": "aae_domain_updater",
                        "path": "runway.cfngin.hooks.staticsite.auth_at_edge."
                        "domain_updater.delete",
                        "required": True,
                    }
                )
            else:
                # Retrieve the user pool id
                pre_deploy.append(
                    {
                        "args": self._get_user_pool_id_retriever_variables(),
                        "data_key": "aae_user_pool_id_retriever",
                        "path": "runway.cfngin.hooks.staticsite.auth_at_edge."
                        "user_pool_id_retriever.get",
                        "required": True,
                    }
                )

        content: dict[str, Any] = {
            "cfngin_bucket": "",
            "namespace": "${namespace}",
            "pre_deploy": pre_deploy,
            "pre_destroy": pre_destroy,
            "service_role": self.parameters.service_role,
            "stacks": {
                f"{self.sanitized_name}-dependencies": {
                    "class_path": "runway.blueprints.staticsite.dependencies.Dependencies",
                    "variables": self._get_dependencies_variables(),
                }
            },
        }

        out_file = module_dir / "01-dependencies.yaml"
        out_file.write_text(
            yaml.dump(content, default_flow_style=False, sort_keys=True), encoding="utf-8"
        )
        self.logger.debug("created %s:\n%s", out_file.name, yaml.dump(content, Dumper=YamlDumper))
        return out_file

    def _create_staticsite_yaml(self, module_dir: Path) -> Path:
        """Create CFNgin config file for Static Site.

        Resulting config file is save to ``module_dir`` as ``02-staticsite.yaml``.

        Args:
            module_dir: Path to the Runway module.

        Returns:
            Path to the file that was created.

        """
        # Default parameter name matches build_staticsite hook
        if not self.options.source_hashing.parameter:
            self.options.source_hashing.parameter = f"${{namespace}}-{self.sanitized_name}-hash"
        nonce_secret_param = f"${{namespace}}-{self.sanitized_name}-nonce-secret"

        build_staticsite_args: dict[str, Any] = {
            # ensures yaml.safe_load will work by using JSON to convert objects
            "options": json.loads(self.options.data.model_dump_json(by_alias=True))
        }
        build_staticsite_args["artifact_bucket_rxref_lookup"] = (
            f"{self.sanitized_name}-dependencies::ArtifactsBucketName"
        )
        build_staticsite_args["options"]["namespace"] = "${namespace}"
        build_staticsite_args["options"]["name"] = self.sanitized_name
        build_staticsite_args["options"]["path"] = str(self.ctx.env.root_dir.resolve() / self.path)

        site_stack_variables = self._get_site_stack_variables()

        class_path = "staticsite.StaticSite"

        pre_deploy = [
            {
                "args": build_staticsite_args,
                "data_key": "staticsite",
                "path": "runway.cfngin.hooks.staticsite.build_staticsite.build",
                "required": True,
            }
        ]

        post_deploy = [
            {
                "args": {
                    "bucket_name": f"${{cfn ${{namespace}}-{self.sanitized_name}.BucketName}}",
                    "cf_disabled": site_stack_variables["DisableCloudFront"],
                    "distribution_domain": f"${{cfn ${{namespace}}-{self.sanitized_name}."
                    "CFDistributionDomainName::default=undefined}",
                    "distribution_id": f"${{cfn ${{namespace}}-{self.sanitized_name}"
                    ".CFDistributionId::default=undefined}",
                    "extra_files": [i.model_dump() for i in self.options.extra_files],
                    "website_url": f"${{cfn ${{namespace}}-{self.sanitized_name}"
                    ".BucketWebsiteURL::default=undefined}",
                },
                "path": "runway.cfngin.hooks.staticsite.upload_staticsite.sync",
                "required": True,
            }
        ]

        pre_destroy = [
            {
                "args": {"bucket_name": f"${{rxref {self.sanitized_name}::BucketName}}"},
                "path": "runway.cfngin.hooks.cleanup_s3.purge_bucket",
                "required": True,
            }
        ]

        if self.parameters.rewrite_directory_index or self.parameters.auth_at_edge:
            pre_destroy.append(
                {
                    "args": {"stack_relative_name": self.sanitized_name},
                    "path": "runway.cfngin.hooks.staticsite.cleanup.warn",
                    "required": False,
                }
            )

        post_destroy = [
            {
                "args": {"parameter_name": i},
                "path": "runway.cfngin.hooks.cleanup_ssm.delete_param",
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
                            self.sanitized_name, site_stack_variables
                        ),
                    },
                )

        if self.parameters.role_boundary_arn:
            site_stack_variables["RoleBoundaryArn"] = self.parameters.role_boundary_arn

        site_stack_variables["custom_error_responses"] = [
            i.model_dump(exclude_none=True) for i in self.parameters.custom_error_responses
        ]
        site_stack_variables["lambda_function_associations"] = [
            i.model_dump() for i in self.parameters.lambda_function_associations
        ]

        content: dict[str, Any] = {
            "cfngin_bucket": "",
            "namespace": "${namespace}",
            "post_deploy": post_deploy,
            "post_destroy": post_destroy,
            "pre_deploy": pre_deploy,
            "pre_destroy": pre_destroy,
            "service_role": self.parameters.service_role,
            "stacks": {
                self.sanitized_name: {
                    "class_path": f"runway.blueprints.staticsite.{class_path}",
                    "variables": site_stack_variables,
                }
            },
        }

        out_file = module_dir / "02-staticsite.yaml"
        out_file.write_text(
            yaml.dump(content, default_flow_style=False, sort_keys=True), encoding="utf-8"
        )
        self.logger.debug("created 02-staticsite.yaml:\n%s", yaml.dump(content, Dumper=YamlDumper))
        return out_file

    def _create_cleanup_yaml(self, module_dir: Path) -> Path:
        """Create CFNgin config file for Static Site cleanup stack.

        Resulting config file is save to ``module_dir`` as ``03-cleanup.yaml``.

        Args:
            module_dir: Path to the Runway module.

        Returns:
            Path to the file that was created.

        """
        content = {
            "namespace": "${namespace}",
            "cfngin_bucket": "",
            "service_role": self.parameters.service_role,
            "stacks": {
                f"{self.sanitized_name}-cleanup": {
                    "template_path": os.path.join(  # noqa: PTH118
                        tempfile.gettempdir(),
                        "thisfileisnotused.yaml",  # cspell: disable-line
                    ),
                }
            },
        }

        out_file = module_dir / "03-cleanup.yaml"
        out_file.write_text(
            yaml.dump(content, default_flow_style=False, sort_keys=True), encoding="utf-8"
        )
        self.logger.debug("created %s:\n%s", out_file.name, yaml.dump(content, Dumper=YamlDumper))
        return out_file

    def _get_site_stack_variables(self) -> dict[str, Any]:
        site_stack_variables: dict[str, Any] = {
            "Aliases": [],
            "Compress": self.parameters.compress,
            "DisableCloudFront": self.parameters.cf_disable,
            "RedirectPathAuthRefresh": "${default staticsite_redirect_path_auth_refresh::"
            "/refreshauth}",
            "RedirectPathSignIn": "${default staticsite_redirect_path_sign_in::/parseauth}",
            "RedirectPathSignOut": "${default staticsite_redirect_path_sign_out::/}",
            "RewriteDirectoryIndex": self.parameters.rewrite_directory_index or "",
            "SignOutUrl": "${default staticsite_sign_out_url::/signout}",
            "WAFWebACL": self.parameters.web_acl or "",
        }

        if self.parameters.aliases:
            site_stack_variables["Aliases"] = self.parameters.aliases

        if self.parameters.acmcert_arn:
            site_stack_variables["AcmCertificateArn"] = self.parameters.acmcert_arn

        if self.parameters.enable_cf_logging:
            site_stack_variables["LogBucketName"] = (
                f"${{rxref {self.sanitized_name}-dependencies::AWSLogBucketName}}"
            )

        if self.parameters.auth_at_edge:
            self._ensure_auth_at_edge_requirements()
            site_stack_variables["UserPoolArn"] = self.parameters.user_pool_arn
            site_stack_variables["NonSPAMode"] = self.parameters.non_spa
            site_stack_variables["HttpHeaders"] = self.parameters.http_headers
            site_stack_variables["CookieSettings"] = self.parameters.cookie_settings
            site_stack_variables["OAuthScopes"] = self.parameters.oauth_scopes
        else:
            site_stack_variables["custom_error_responses"] = [
                i.model_dump(exclude_none=True) for i in self.parameters.custom_error_responses
            ]
            site_stack_variables["lambda_function_associations"] = [
                i.model_dump() for i in self.parameters.lambda_function_associations
            ]

        return site_stack_variables

    def _get_dependencies_variables(self) -> dict[str, Any]:
        variables: dict[str, Any] = {"OAuthScopes": self.parameters.oauth_scopes}
        if self.parameters.auth_at_edge:
            self._ensure_auth_at_edge_requirements()

            variables.update(
                {
                    "AuthAtEdge": self.parameters.auth_at_edge,
                    "SupportedIdentityProviders": self.parameters.supported_identity_providers,
                    "RedirectPathSignIn": (
                        "${default staticsite_redirect_path_sign_in::/parseauth}"
                    ),
                    "RedirectPathSignOut": ("${default staticsite_redirect_path_sign_out::/}"),
                },
            )

            if self.parameters.aliases:
                variables.update({"Aliases": self.parameters.aliases})
            if self.parameters.additional_redirect_domains:
                variables.update(
                    {"AdditionalRedirectDomains": self.parameters.additional_redirect_domains}
                )
            if self.parameters.create_user_pool:
                variables.update({"CreateUserPool": self.parameters.create_user_pool})

        return variables

    def _get_user_pool_id_retriever_variables(self) -> dict[str, Any]:
        args: dict[str, Any] = {
            "user_pool_arn": self.parameters.user_pool_arn,
        }

        if self.parameters.create_user_pool:
            args["created_user_pool_id"] = (
                f"${{rxref {self.sanitized_name}-dependencies::AuthAtEdgeUserPoolId}}"
            )

        return args

    def _get_domain_updater_variables(self) -> dict[str, str]:
        return {
            "client_id_output_lookup": f"{self.sanitized_name}-dependencies::AuthAtEdgeClient",
            "client_id": f"${{rxref {self.sanitized_name}-dependencies::AuthAtEdgeClient}}",
        }

    def _get_lambda_config_variables(
        self,
        site_stack_variables: dict[str, Any],
        nonce_secret_param: str,
        required_group: str | None = None,
    ) -> dict[str, Any]:
        return {
            "client_id": f"${{rxref {self.sanitized_name}-dependencies::AuthAtEdgeClient}}",
            "bucket": f"${{rxref {self.sanitized_name}-dependencies::ArtifactsBucketName}}",
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
        self, name: str, site_stack_variables: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "alternate_domains": [add_url_scheme(x) for x in site_stack_variables["Aliases"]],
            "client_id": f"${{rxref {self.sanitized_name}-dependencies::AuthAtEdgeClient}}",
            "distribution_domain": f"${{rxref {name}::CFDistributionDomainName}}",
            "oauth_scopes": site_stack_variables["OAuthScopes"],
            "redirect_path_sign_in": site_stack_variables["RedirectPathSignIn"],
            "redirect_path_sign_out": site_stack_variables["RedirectPathSignOut"],
            "supported_identity_providers": self.parameters.supported_identity_providers,
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
                'staticsite_cf_disable must be "false" if staticsite_auth_at_edge is "true"'
            )
            sys.exit(1)

    def _ensure_valid_environment_config(self) -> None:
        """Exit if config is invalid."""
        if not self.parameters.namespace:
            self.logger.error("namespace parameter is required but not defined")
            sys.exit(1)

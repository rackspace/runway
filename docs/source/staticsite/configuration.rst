.. _staticsite:
.. _staticsite-configuration:

#############
Configuration
#############

Configuration options and parameters for :ref:`index:Static Site` :term:`Modules <module>`.
Example uses of the options and parameters can be found in the :ref:`Examples <staticsite-examples>` section.



*******
Options
*******

.. data:: build_output
  :type: str | None
  :value: None
  :noindex:

  Overrides default directory of top-level path setting.

  .. rubric:: Example
  .. code-block:: yaml

    options:
      build_output: dist

.. data:: build_steps
  :type: list[str]
  :value: []
  :noindex:

  The steps to run during the build portion of deployment.

  .. rubric:: Example
  .. code-block:: yaml

    options:
      build_steps:
        - npm ci
        - npm run build

.. data:: extra_files
  :type: list[dict[str, str | dict[str, Any]]]
  :value: []
  :noindex:

  Specifies extra files that should be uploaded to S3 after the build.

  Use ``extra_files`` if you want to have a single build artifact that can be used
  in many environments. These files should be excluded from source hashing and the build
  system. The end result is that you have a build artifact that can be deployed in any
  environment and behave exactly the same.

  See :ref:`Extra Files <static-extra-files>` for more details.

  .. rubric:: Example
  .. code-block:: yaml

    options:
      extra_files:
        - name: config.json # yaml or other text files are supported
          content: # this object will be json or yaml serialized
            endpoint: ${var api_endpoint.${env DEPLOY_ENVIRONMENT}}
        - name: config.any
          content_type: text/yaml # Explicit content type
          content:
            endpoint: ${var api_endpoint.${env DEPLOY_ENVIRONMENT}}
        - name: logo.png
          content_type: image/png
          file: logo-${env DEPLOY_ENVIRONMENT}.png # a reference to an existing file

  The example above produces a file named ``config.json`` with the contents below and a
  ``logo.png`` file.

  .. code-block:: json

    {
      "endpoint": "<api_endpoint value>"
    }

  .. versionadded:: 1.9.0

.. data:: pre_build_steps
  :type: list[dict[str, str]]
  :value: []
  :noindex:

  Commands to be run before generating the hash of files.

  .. rubric:: Example
  .. code-block:: yaml

    options:
      pre_build_steps:
        - command: npm ci
          cwd: ../myothermodule # directory relative to top-level path setting
        - command: npm run export
          cwd: ../myothermodule

.. data:: source_hashing
  :type: dict[str, str]
  :value: {}
  :noindex:

  Overrides for source hash collection and tracking

  .. rubric:: Example
  .. code-block:: yaml

    options:
      source_hashing:
        enabled: true # if false, build & upload will occur on every deploy
        parameter: /${namespace}/myparam # defaults to <namespace>-<name/path>-hash
        directories: # overrides default hash directory of top-level path setting
          - path: ./
          - path: ../common
            # Additional (gitignore-format) exclusions to
            # hashing (.gitignore files are loaded automatically)
            exclusions:
              - foo/*


**********
Parameters
**********

.. data:: cloudformation_service_role
  :type: str | None
  :value: None
  :noindex:

  IAM Role ARN that CloudFormation will use when creating, deleting and updating
  the CloudFormation stack resources.

  See the `AWS CloudFormation service role <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-iam-servicerole.html?icmpid=docs_cfn_console>`__ for more information.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      cloudformation_service_role: arn:aws:iam::123456789012:role/name

.. data:: namespace
  :type: str
  :noindex:

  The unique namespace for the deployment.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      namespace: my-awesome-website-${env DEPLOY_ENVIRONMENT}

.. _staticsite_acmcert_arn:

.. data:: staticsite_acmcert_arn
  :type: str | None
  :value: None
  :noindex:

  The certificate arn used for any alias domains supplied.
  This is a requirement when supplying any custom domain.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_acmcert_arn: arn:aws:acm:<region>:<account-id>:certificate/<cert>

.. data:: staticsite_aliases
  :type: str | None
  :value: None
  :noindex:

  Any custom domains that should be added to the CloudFront Distribution.
  This should be represented as a comma delimited list of domains.

  Requires staticsite_acmcert_arn_.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_aliases: example.com,foo.example.com

.. _staticsite_auth_at_edge:

.. data:: staticsite_auth_at_edge
  :type: bool
  :value: False
  :noindex:

  *Auth@Edge* make the static site *private* by placing it behind an authorization wall.
  See :ref:`Auth@Edge` for more details.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_auth_at_edge: true

  .. versionadded:: 1.5.0

.. _staticsite_cf_disable:

.. data:: staticsite_cf_disable
  :type: bool
  :value: False
  :noindex:

  Whether deployment of the CloudFront Distribution should be disabled.

  Useful for a development site as it makes it accessible via an S3 url with a much shorter launch time.
  This cannot be set to ``true`` when using :ref:`Auth@Edge`.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_cf_disable: false

  .. versionadded:: 1.5.0

.. data:: staticsite_compress
  :type: bool
  :value: True
  :noindex:

  Whether the CloudFront default cache behavior will automatically compress certain files.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_compress: false

.. data:: staticsite_cookie_settings
  :type: dict[str, str] | None
  :value: {"idToken": "Path=/; Secure; SameSite=Lax", "accessToken": "Path=/; Secure; SameSite=Lax", "refreshToken": "Path=/; Secure; SameSite=Lax", "nonce": "Path=/; Secure; HttpOnly; Max-Age=1800; SameSite=Lax"}
  :noindex:

  The default cookie settings for retrieved tokens and generated nonce's.

  Requires staticsite_auth_at_edge_.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_cookie_settings:
        idToken: "Path=/; Secure; SameSite=Lax"
        accessToken: "Path=/; Secure; SameSite=Lax"
        refreshToken: "Path=/; Secure; SameSite=Lax"
        nonce: "Path=/; Secure; HttpOnly; Max-Age=1800; SameSite=Lax"

  .. versionadded:: 1.5.0

.. _staticsite_create_user_pool:

.. data:: staticsite_create_user_pool
  :type: bool
  :value: False
  :noindex:

  Whether to create a User Pool for the :ref:`Auth@Edge` configuration.

  Requires staticsite_auth_at_edge_.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_create_user_pool: true

  .. versionadded:: 1.5.0

.. _staticsite_custom_error_responses:

.. data:: staticsite_custom_error_responses
  :type: list[dict[str, int | str]]
  :value: []
  :noindex:

  Define custom error responses.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_custom_error_responses:
        - ErrorCode: 404
          ResponseCode: 200
          ResponsePagePath: /index.html

.. data:: staticsite_enable_cf_logging
  :type: bool
  :value: True
  :noindex:

  Whether logging should be enabled for the CloudFront distribution.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_enable_cf_logging: true

.. data:: staticsite_http_headers
  :type: dict[str, str] | None
  :value: {"Content-Security-Policy": "default-src https: 'unsafe-eval' 'unsafe-inline'; font-src 'self' 'unsafe-inline' 'unsafe-eval' data: https:; object-src 'none'; connect-src 'self' https://*.amazonaws.com https://*.amazoncognito.com", "Strict-Transport-Security": "max-age=31536000;  includeSubdomains; preload", "Referrer-Policy": "same-origin", "X-XSS-Protection": "1; mode=block", "X-Frame-Options": "DENY", "X-Content-Type-Options": "nosniff"}
  :noindex:

  Headers that should be sent with each origin response.

  Requires staticsite_auth_at_edge_.

  .. note::
    Please note that the Content-Security-Policy is intentionally lax to allow for Single Page Application framework's to work as expected.
    Review your Content Security Policy for your project and update these as need be to match.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_http_headers:
        Content-Security-Policy: "default-src https: 'unsafe-eval' 'unsafe-inline'; font-src 'self' 'unsafe-inline' 'unsafe-eval' data: https:; object-src 'none'; connect-src 'self' https://*.amazonaws.com https://*.amazoncognito.com"
        Strict-Transport-Security: "max-age=31536000;  includeSubdomains; preload"
        Referrer-Policy: "same-origin"
        X-XSS-Protection: "1; mode=block"
        X-Frame-Options: "DENY"
        X-Content-Type-Options: "nosniff"

  .. versionadded:: 1.5.0

.. data:: staticsite_lambda_function_associations
  :type: list[dict[str, str]]
  :value: []
  :noindex:

  This section allows the user to deploy custom *Lambda@Edge* associations with their pre-build function versions.
  This takes precedence over staticsite_rewrite_directory_index_ and cannot currently be used with staticsite_auth_at_edge_.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_lambda_function_associations:
        - type: origin-request
          arn: arn:aws:lambda:<region>:<account-id>:function:<function>:<version>

.. data:: staticsite_non_spa
  :type: bool
  :value: False
  :noindex:

  Whether this site is a single page application (*SPA*).

  A custom error response directing ``ErrorCode: 404`` to the primary ``/index.html`` as a ``ResponseCode: 200`` is added, allowing the *SPA* to take over error handling.
  If you are not running an *SPA*, setting this to ``true`` will prevent this custom error from being added.
  If provided, staticsite_custom_error_responses_ takes precedence over this setting.

  Requires staticsite_auth_at_edge_.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_non_spa: true

  .. versionadded:: 1.5.0

.. data:: staticsite_oauth_scopes
  :type: list[str] | None
  :value: ["phone", "email", "profile", "openid", "aws.cognito.signin.user.admin"]
  :noindex:

  Scope is a mechanism in OAuth 2.0 to limit an application's access to a user's account.
  An application can request one or more scopes.
  This information is then presented to the user in the consent screen and the access token issued to the application will be limited to the scopes granted.

  Requires staticsite_auth_at_edge_.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_oauth_scopes:
        - phone
        - email
        - profile
        - openid
        - aws.cognito.signin.user.admin

  .. versionadded:: 1.5.0

.. data:: staticsite_redirect_path_auth_refresh
  :type: str | None
  :value: "/refreshauth"
  :noindex:

  The path that a user is redirected to when their authorization tokens have expired (1 hour).

  Requires staticsite_auth_at_edge_.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_redirect_path_auth_refresh: /refreshauth

  .. versionadded:: 1.5.0

.. data:: staticsite_redirect_path_sign_in
  :type: str | None
  :value: "/parseauth"
  :noindex:

  The path that a user is redirected to after sign-in.
  This corresponds with the ``parseauth`` *Lambda@Edge* function which will parse the authentication details and verify the reception.

  Requires staticsite_auth_at_edge_.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_redirect_path_sign_in: /parseauth

  .. versionadded:: 1.5.0

.. data:: staticsite_redirect_path_sign_out
  :type: str | None
  :value: "/"
  :noindex:

  The path that a user is redirected to after sign-out.
  This typically should be the root of the site as the user will be asked to re-login.

  Requires staticsite_auth_at_edge_.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_redirect_path_sign_out: /

  .. versionadded:: 1.5.0

.. _staticsite_rewrite_directory_index:

.. data:: staticsite_rewrite_directory_index
  :type: str | None
  :value: None
  :noindex:

  Deploy a *Lambda@Edge* function designed to rewrite directory indexes, e.g. supports accessing urls such as ``example.org/foo/``

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_rewrite_directory_index: index.html

.. data:: staticsite_role_boundary_arn
  :type: str | None
  :value: None
  :noindex:

  Defines an IAM Managed Policy that will be set as the permissions boundary for any IAM Roles created to support the site.
  (e.g. when using staticsite_auth_at_edge_ or staticsite_rewrite_directory_index_)

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_role_boundary_arn: arn:aws:iam::<account-id>:policy/<policy>

  .. versionadded:: 1.8.0

.. data:: staticsite_sign_out_url
  :type: str | None
  :value: "/signout"
  :noindex:

  The path a user should access to sign themselves out of the application.

  Requires staticsite_auth_at_edge_.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_sign_out_url: /signout

  .. versionadded:: 1.5.0

.. data:: staticsite_supported_identity_providers
  :type: str | None
  :value: "COGNITO"
  :noindex:

  A comma delimited list of the User Pool client identity providers.

  Requires staticsite_auth_at_edge_.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_supported_identity_providers: facebook,onelogin

  .. versionadded:: 1.5.0

.. data:: staticsite_user_pool_arn
  :type: str | None
  :value: None
  :noindex:

  The ARN of a pre-existing Cognito User Pool to use with :ref:`Auth@Edge`.

  Requires staticsite_auth_at_edge_.

  .. rubric:: Example
  .. code-block:: yaml

    parameters
      staticsite_user_pool_arn: arn:aws:cognito-idp:<region>:<account-id>:userpool/<pool>

  .. versionadded:: 1.5.0

.. data:: staticsite_additional_redirect_domains
  :type: str | None
  :value: None
  :noindex:

  Additional domains (beyond the `staticsite_aliases` domains or the CloudFront URL if no aliases are provided) that will be authorized by the :ref:`Auth@Edge` UserPool AppClient.
  This parameter typically won't be needed in production environments, but can be useful in development environments to allow bypassing Runway Auth@Edge.

  This should be represented as a comma delimited list of domains with protocols.
  Requires staticsite_auth_at_edge_.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_additional_redirect_domains: http://localhost:3000

  .. versionadded:: 1.14.0

.. data:: staticsite_web_acl
  :type: str | None
  :value: None
  :noindex:

  The ARN of a `web access control list (web ACL) <https://docs.aws.amazon.com/waf/latest/developerguide/web-acl.html>`__ to associate with the CloudFront Distribution.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_web_acl: arn:aws:waf::<account-id>:certificate/<cert>

.. data:: staticsite_required_group
  :type: str | None
  :value: None
  :noindex:

  Name of Cognito User Pool group of which users must be a member to be granted access to the site.
  Omit to allow all UserPool users to have access.

  Requires staticsite_auth_at_edge_.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_required_group: AuthorizedUsers

  .. versionadded:: 1.5.0

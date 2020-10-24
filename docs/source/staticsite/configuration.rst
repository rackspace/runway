.. _staticsite:

#############
Configuration
#############

Configuration options and parameters for :ref:`static site <mod-staticsite>` modules.
Example uses of the options and parameters can be found in the :ref:`Examples <staticsite-examples>` section.


*******
Options
*******

**build_output (Optional[str])**
  Overrides default directory of top-level path setting.

  .. rubric:: Example
  .. code-block:: yaml

    options:
      build_output: dist

**build_steps (Optional[List[str]])**
  The steps to run during the build portion of deployment.

  .. rubric:: Example
  .. code-block:: yaml

    options:
      build_steps:
        - npm ci
        - npm run build

**extra_files (Optional[List[Dict[str, Union[str, Dict[str, Any]]]]])**
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

**pre_build_steps (Optional[List[Dict[str, str]]])**
  Commands to be run before generating the hash of files.

  .. rubric:: Example
  .. code-block:: yaml

    options:
      pre_build_steps:
        - command: npm ci
          cwd: ../myothermodule # directory relative to top-level path setting
        - command: npm run export
          cwd: ../myothermodule

**source_hashing (Optional[Dict[str, str]])**
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
            # hashing (.giignore files are loaded automatically)
            exclusions:
              - foo/*

**********
Parameters
**********

**namespace (str)**
  The unique namespace for the deployment.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      namespace: my-awesome-website-${env DEPLOY_ENVIRONMENT}

.. _staticsite_acmcert_arn:

**staticsite_acmcert_arn (Optional[str])**
  The certificate arn used for any alias domains supplied.
  This is a requirement when supplying any custom domain.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_acmcert_arn: arn:aws:acm:<region>:<account-id>:certificate/<cert>

**staticsite_aliases (Optional[str])**
  Any custom domains that should be added to the CloudFront Distribution.
  This should be represented as a comma delimited list of domains.

  Requires staticsite_acmcert_arn_.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_aliases: example.com,foo.example.com

.. _staticsite_auth_at_edge:

**staticsite_auth_at_edge (Optional[bool])**
  *Auth@Edge* make the static site *private* by placing it behind an authorization wall. (*default:* ``false``)
  See :ref:`Auth@Edge` for more details.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_auth_at_edge: true

.. _staticsite_cf_disable:

**staticsite_cf_disable (Optional[bool])**
  Wether deployment of the CloudFront Distribution should be disabled. (*default:* ``false``)

  Useful for a development site as it makes it accessible via an S3 url with a much shorter launch time.
  This cannot be set to ``true`` when using :ref:`Auth@Edge`.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_cf_disable: false

**staticsite_cookie_settings (Optional[Dict[str, str]])**
  The default cookie settings for retrieved tokens and generated nonce's. *(default is shown in the example)*

  Requires staticsite_auth_at_edge_.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_cookie_settings:
        idToken: "Path=/; Secure; SameSite=Lax"
        accessToken: "Path=/; Secure; SameSite=Lax"
        refreshToken: "Path=/; Secure; SameSite=Lax"
        nonce: "Path=/; Secure; HttpOnly; Max-Age=1800; SameSite=Lax"

.. _staticsite_create_user_pool:

**staticsite_create_user_pool (Optional[bool])**
  Wether to create a User Pool for the :ref:`Auth@Edge` configuration.

  Requires staticsite_auth_at_edge_.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_create_user_pool: true

.. _staticsite_custom_error_responses:

**staticsite_custom_error_responses (Optional[List[Dict[str, Union[int, str]]]])**
  Define custom error responses.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_custom_error_responses:
        - ErrorCode: 404
          ResponseCode: 200
          ResponsePagePath: /index.html

**staticsite_enable_cf_logging (Optional[bool])**
  Wether logging should be enabled for the CloudFront distribution. (*default:* ``true``)

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_enable_cf_logging: true

**staticsite_http_headers (Optional[Dict[str, str]])**
  Headers that should be sent with each origin response. *(default is shown in the example)*

  Please note that the Content-Security-Policy is intentionally lax to allow for Single Page Application framework's to work as expected.
  Review your Content Security Policy for your project and update these as need be to match.

  Requires staticsite_auth_at_edge_.

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

**staticsite_lambda_function_associations (Optional[List[Dict[str, str]]])**
  This section allows the user to deploy custom *Lambda@Edge* associations with their pre-build function versions.
  This takes precedence over staticsite_rewrite_directory_index_ and cannot currently be used with staticsite_auth_at_edge_.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_lambda_function_associations:
        - type: origin-request
          arn: arn:aws:lambda:<region>:<account-id>:function:<function>:<version>

**staticsite_non_spa (Optional[bool])**
  Wether this site is a single page application (*SPA*). (*default:* ``true``)

  A custom error response directing ``ErrorCode: 404`` to the primary ``/index.html`` as a ``ResponseCode: 200`` is added, allowing the *SPA* to take over error handling.
  If you are not running an *SPA*, setting this to ``true`` will prevent this custom error from being added.
  If provided, staticsite_custom_error_responses_ takes precedence over this setting.

  Requires staticsite_auth_at_edge_.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_non_spa: true

**staticsite_oauth_scopes (Optional[List[str]])**
  Scope is a mechanism in OAuth 2.0 to limit an application's access to a user's account.
  An application can request one or more scopes.
  This information is then presented to the user in the consent screen and the access token issued to the application will be limited to the scopes granted. *(default is shown in the example)*

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

**staticsite_redirect_path_auth_refresh (Optional[str])**
  The path that a user is redirected to when their authorization tokens have expired (1 hour). (*default:* ``/refreshauth``)

  Requires staticsite_auth_at_edge_.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_redirect_path_auth_refresh: /refreshauth

**staticsite_redirect_path_sign_in (Optional[str])**
  The path that a user is redirected to after sign-in (*default:* ``/parseauth``).
  This corresponds with the ``parseauth`` *Lambda@Edge* function which will parse the authentication details and verify the reception.

  Requires staticsite_auth_at_edge_.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_redirect_path_sign_in: /parseauth

**staticsite_redirect_path_sign_out (Optional[str])**
  The path that a user is redirected to after sign-out (*default:* ``/``).
  This typically should be the root of the site as the user will be asked to re-login.

  Requires staticsite_auth_at_edge_.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_redirect_path_sign_out: /

.. _staticsite_rewrite_directory_index:

**staticsite_rewrite_directory_index (Optional[str])**
  Deploy a *Lambda@Edge* function designed to rewrite directory indexes, e.g. supports accessing urls such as ``example.org/foo/``

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_rewrite_directory_index: index.html

**staticsite_role_boundary_arn (Optional[str])**
  Defines an IAM Managed Policy that will be set as the permissions boundary for any IAM Roles created to support the site.
  (e.g. when using staticsite_auth_at_edge_ or staticsite_rewrite_directory_index_)

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_role_boundary_arn: arn:aws:iam::<account-id>:policy/<policy>

**staticsite_sign_out_url (Optional[str])**
  The path a user should access to sign themselves out of the application. (*default:* ``/signout``)

  Requires staticsite_auth_at_edge_.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_sign_out_url: /signout

**staticsite_supported_identity_providers (Optional[str])**
  A comma delimited list of the User Pool client identity providers. (*default:* `COGNITO`)

  Requires staticsite_auth_at_edge_.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_supported_identity_providers: facebook,onelogin

**staticsite_user_pool_arn (Optional[str])**
  The ARN of a pre-existing Cognito User Pool to use with :ref:`Auth@Edge`.

  Requires staticsite_auth_at_edge_.

  .. rubric:: Example
  .. code-block:: yaml

    parameters
      staticsite_user_pool_arn: arn:aws:cognito-idp:<region>:<account-id>:userpool/<pool>

**staticsite_additional_redirect_domains (Optional[str])**
  Additional domains (beyond the `staticsite_aliases` domains or the CloudFront URL if no
  aliases are provided) that will be authorized by the :ref:`Auth@Edge` UserPool AppClient.
  This parameter typically won't be needed in production environments, but can be useful in
  development environments to allow bypassing Runway Auth@Edge.

  This should be represented as a comma delimited list of domains with protocols. Requires
  staticsite_auth_at_edge_.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_additional_redirect_domains: http://localhost:3000

**staticsite_web_acl (Optional[str])**
  The ARN of a `web access control list (web ACL) <https://docs.aws.amazon.com/waf/latest/developerguide/web-acl.html>`__ to associate with the CloudFront Distribution.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_web_acl: arn:aws:waf::<account-id>:certificate/<cert>

**staticsite_required_group (Optional[str])**
  Name of Cognito User Pool group of which users must be a member to be granted access
  to the site. Omit to allow all UserPool users to have access.

  Requires staticsite_auth_at_edge_.

  .. rubric:: Example
  .. code-block:: yaml

    parameters:
      staticsite_required_group: AuthorizedUsers

#################
Advanced Features
#################

.. _`Auth@Edge`:

***********
*Auth@Edge*
***********

.. important: *Auth@Edge* static sites can only be deployed to us-east-1.
              This is due to the limitations of *Lambda@Edge*.

*Auth@Edge* provides the ability to make a static site private by using Cognito for authentication.
The solution is inspired by similar implementations such as `aws-samples/cloudfront-authorization-at-edge <https://github.com/aws-samples/cloudfront-authorization-at-edge>`__.

The following diagram depicts a high-level overview of this solution.

.. image:: ../images/staticsite/auth_at_edge/flow_diagram.png

Here is how the solution works:

1. The viewer’s web browser is redirected to Amazon Cognito custom UI page to sign up and authenticate.
2. After authentication, Cognito generates and cryptographically signs a JWT then responds with a redirect containing the JWT embedded in the URL.
3. The viewer’s web browser extracts JWT from the URL and makes a request to private content (private/* path), adding Authorization request header with JWT.
4. Amazon CloudFront routes the request to the nearest AWS edge location. The CloudFront distribution’s private behavior is configured to launch a *Lambda@Edge* function on ViewerRequest event.
5. *Lambda@Edge* decodes the JWT and checks if the user belongs to the correct Cognito User Pool. It also verifies the cryptographic signature using the public RSA key for Cognito User Pool. Crypto verification ensures that JWT was created by the trusted party.
6. After passing all of the verification steps, *Lambda@Edge* strips out the Authorization header and allows the request to pass through to designated origin for CloudFront. In this case, the origin is the private content Amazon S3 bucket.
7. After receiving response from the origin S3 bucket, CloudFront sends the response back to the browser. The browser displays the data from the returned response.

An example of an *Auth@Edge* static site configuration is as follows:

.. code-block:: yaml

  variables:
    dev:
      namespace: sample-app-dev
      staticsite_user_pool_arn: arn:aws:cognito-idp:us-east-1:123456789012:userpool/us-east-1_example

  deployments:
    - modules:
      - path: sampleapp
        type: static
        parameters:
          namespace: ${var ${env DEPLOY_ENVIRONMENT}.namespace}
          staticsite_auth_at_edge: true
          staticsite_user_pool_arn: ${var ${env DEPLOY_ENVIRONMENT}.staticsite_user_pool_arn}
      regions:
        - us-east-1

The *Auth@Edge* functionality uses an existing Cognito User Pool (optionally configured with federated identity providers) or can create one for you with the :ref:`staticsite_create_user_pool <staticsite_create_user_pool>` option.
A user pool app client will be automatically created within the pool for use with the application.

.. _static-extra-files:

***********
Extra Files
***********
The extra files option allows you to use a single build across many deployments. Some popular front end frameworks
guide you into including environment specfic parameters as part of the build. i.e. Angular and Redux-React. This forces
you to abandon `12 factor priciples <https://en.wikipedia.org/wiki/Twelve-Factor_App_methodology>`_ and slows down
deployments to other environments.

The static site ``extra_files`` option solves this problem by moving environment configuration out of your code and
into runway. A small change to the way the application references environment config will need to be made.

#. While bootstraping or early in the application lifecycle, make an HTTP call to load one of the ``extra_files``.

#. Make the content of the ``extra_file`` available to your app using an appropriate abstraction.

See :ref:`Static Site Examples <staticsite-examples>` to see how to do this in Angular and React.

.. rubric:: Configuration (``extra_files`` list item)

**name (str)**
    The destination name of the file to create.

**file (Optional[str])**
    A reference to an existing file. The content of this file will be uploaded to the static site S3 bucket using the
    name as the object key. This or ``content`` must be specified.

**content_type (Optional[str])**
    An explicit content type of the file. If not given, the content type will be auto detected based on the name. Only
    ``.json``, ``.yml``, and ``.yaml`` extentions are recognized automatically.

    * ``application/json`` to serialize ``content`` into JSON.
    * ``text/yaml`` to serialize ``content`` into YAML.

**content (Optional[Union[str, List[Any], Dict[str, Any]]])**
    Inline content that will be used as the file content. This or ``file`` must be specified.

.. note::

    If none of the files or content changed between builds and source hashing is enabled, the upload will be skipped.

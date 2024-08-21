###############
acm.Certificate
###############

:Hook Path: :class:`runway.cfngin.hooks.acm.Certificate`


Manage a DNS validated certificate in AWS Certificate Manager.

When used in the :attr:`~cfngin.config.pre_deploy` or :attr:`~cfngin.config.post_deploy` stage this hook will create a CloudFormation stack containing a DNS validated certificate.
It will automatically create a record in Route 53 to validate the certificate and wait for the stack to complete before returning the ``CertificateArn`` as hook data.
The CloudFormation stack also outputs the ARN of the certificate as ``CertificateArn`` so that it can be referenced from other stacks.

When used in the :attr:`~cfngin.config.pre_destroy` or :attr:`~cfngin.config.post_destroy` stage this hook will delete the validation record from Route 53 then destroy the stack created during a deploy stage.

If the hook fails during a deploy stage (e.g. stack rolls back or Route 53 can't be updated) all resources managed by this hook will be destroyed.
This is done to avoid orphaning resources/record sets which would cause errors during subsequent runs.
Resources effected include the CloudFormation stack it creates, ACM certificate, and Route 53 validation record.


.. versionadded:: 1.6.0



************
Requirements
************

- Route 53 hosted zone

  - authoritative for the domain the certificate is being created for
  - in the same AWS account as the certificate being created



****
Args
****

.. data:: alt_names
  :type: list[str]
  :value: []
  :noindex:

  Additional FQDNs to be included in the Subject Alternative Name extension of the ACM certificate.
  For example, you can add *www.example.net* to a certificate for which the ``domain`` field is
  *www.example.com* if users can reach your site by using either name.

.. data:: domain
  :type: str
  :noindex:

  The fully qualified domain name (FQDN), such as *www.example.com*, with which you want to secure an ACM certificate.
  Use an asterisk (``*``) to create a wildcard certificate that protects several sites in the same domain.
  For example, *\*.example.com* protects *www.example.com*, *site.example.com*, and *images.example.com*.

.. data:: hosted_zone_id
  :type: str
  :noindex:

  The ID of the Route 53 Hosted Zone that contains the resource record sets that you want to change.
  This must exist in the same account that the certificate will be created in.

.. data:: stack_name
  :type: str | None
  :value: None
  :noindex:

  Provide a name for the stack used to create the certificate.
  If not provided, the domain is used (replacing ``.`` with ``-``).
  If the is provided in a deploy stage, its needs to be provided in the matching destroy stage.

.. data:: ttl
  :type: int | None
  :value: None
  :noindex:

  The resource record cache time to live (TTL), in seconds. (*default:* ``300``)



*******
Example
*******

.. code-block:: yaml

    namespace: example
    cfngin_bucket: ''

    sys_path: ./

    pre_deploy:
      acm-cert:
        path: runway.cfngin.hooks.acm.Certificate
        required: true
        args:
          domain: www.example.com
          hosted_zone_id: ${rxref example-com::HostedZone}

    stack:
      sampleapp:
        class_path: blueprints.sampleapp.BlueprintClass
        variables:
          cert_arn: ${rxref www-example-com::CertificateArn}

    post_destroy:
      acm-cert:
        path: runway.cfngin.hooks.acm.Certificate
        required: true
        args:
          domain: www.example.com
          hosted_zone_id: ${rxref example-com::HostedZone}

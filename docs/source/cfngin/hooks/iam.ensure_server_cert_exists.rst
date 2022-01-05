#############################
iam.ensure_server_cert_exists
#############################

:Hook Path: ``runway.cfngin.hooks.iam.ensure_server_cert_exists``


Ensure server certificate exists.



****
Args
****

.. data:: cert_name
  :type: str
  :noindex:

  Name of the certificate that should exist.

.. data:: prompt
  :type: bool
  :value: True
  :noindex:

  Whether to prompt to upload a certificate if one does not exist.

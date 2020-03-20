"""CFNgin hooks for AWS Certificate Manager."""
# pylint: disable=unused-argument
import logging
from time import sleep

from troposphere.certificatemanager import Certificate as CertificateResource

from runway.util import MutableMap

from ..status import NO_CHANGE
from .base import Hook
from .utils import BlankBlueprint

LOGGER = logging.getLogger(__name__)


class Certificate(Hook):
    """Hook for managing a **AWS::CertificateManager::Certificate**.

    Keyword Args:
        alt_names (Optional[List[str]]): Additional FQDNs to be included in the
            Subject Alternative Name extension of the ACM certificate. For
            example, you can add www.example.net to a certificate for which the
            domain field is www.example.com if users can reach your site by
            using either name.
        domain (str): The fully qualified domain name (FQDN), such as
            www.example.com, with which you want to secure an ACM certificate.
            Use an asterisk (``*``) to create a wildcard certificate that
            protects several sites in the same domain. For example,
            *.example.com protects www.example.com, site.example.com, and
            images.example.com.
        hosted_zone_id (str): The ID of the Route 53 Hosted Zone that contains
            the resource record sets that you want to change. This must exist
            in the same account that the certificate will be created in.

    Example:
    .. code-block: yaml

        pre_build:
          example-wildcard-cert:
            path: runway.cfngin.hooks.acm.Certificate
            required: true
            args:
              domain: '*.example.com'
              hosted_zone_id: ${xref example-com::HostedZoneId}

    """

    def __init__(self, context, provider, **kwargs) -> None:
        """Instantiate class.

        Args:
            context (:class:`runway.cfngin.context.Context`): Context instance.
                (passed in by CFNgin)
            provider (:class:`runway.cfngin.providers.base.BaseProvider`):
                Provider instance. (passed in by CFNgin)

        """
        super(Certificate, self).__init__(context, provider, **kwargs)

        self.template_description = self.get_template_description()
        self.stack_name = kwargs['domain'].replace('.', '-')

        self.properties = MutableMap(**{
            'DomainName': self.args.domain,
            'SubjectAlternativeNames': self.args.get('alt_names', []),
            'Tags': self.tags,
            'ValidationMethod': 'DNS'
        })
        self.blueprint = self._create_blueprint()

        session = self.context.get_session()
        self.acm_client = session.client('acm')
        self.r53_client = session.client('route53')
        self.stack = self.generate_stack()

    def _create_blueprint(self):
        """Create CFNgin Blueprint."""
        blueprint = BlankBlueprint(self.stack_name, self.context)
        blueprint.template.set_version('2010-09-09')
        blueprint.template.set_description(self.template_description)

        cert = blueprint.template.add_resource(CertificateResource(
            'Certificate',
            **self.properties.data
        ))
        blueprint.add_output('%sArn' % cert.title, cert.ref())
        return blueprint

    def get_certificate(self, interval=5, stack_name=None):
        """Get the certificate being created by a CloudFormation.

        Args:
            interval (int): Number of seconds to wait between attempts.
            stack_name (str): Name of CloudFormation stack containing a pending
                certificate.

        Returns:
            str: Certificate ARN

        """
        stack_name = stack_name or self.stack.fqn
        response = self.provider.cloudformation.describe_stack_resources(
            StackName=stack_name,
            LogicalResourceId='Certificate'
        )['StackResources']
        if response:
            # can be returned without having a PhysicalResourceId
            if response[0].get('PhysicalResourceId'):
                return response[0]['PhysicalResourceId']
        LOGGER.debug('Waiting for certificate to be created...')
        sleep(interval)
        return self.get_certificate(stack_name)

    def get_validation_record(self, cert_arn=None, interval=5, stack_name=None):
        """Get validation record from the certificate being created.

        Args:
            cert_arn (str): ARN of the certificate to validate.
            interval (int): Number of seconds to wait between attempts.
            stack_name (str): Name of CloudFormation stack containing a pending
                certificate.

        Returns:
            Dict[str, str]: A record set to be added to Route 53.

        Raises:
            ValueError: No pending or too many pending certificates.

        """
        stack_name = stack_name or self.stack.fqn
        if not cert_arn:
            cert_arn = self.get_certificate(stack_name)
        cert = self.acm_client.describe_certificate(
            CertificateArn=cert_arn
        )['Certificate']

        try:
            domain_validation = [
                opt for opt in cert['DomainValidationOptions']
                if opt['ValidationStatus'] == 'PENDING_VALIDATION'
            ]
        except KeyError:
            LOGGER.debug('Waiting for DomainValidationOptions to become '
                         'available for the certificate...')
            sleep(interval)
            return self.get_validation_record(cert_arn=cert_arn,
                                              interval=interval)

        if not domain_validation:
            raise ValueError('No pending validations found for "{}"'.format(
                self.args.domain
            ))
        if len(domain_validation) > 1:
            raise ValueError(
                'Found {} pending validation options for "{}"; only one '
                'option is supported'.format(len(domain_validation),
                                             self.args.domain)
            )
        try:
            # the validation option can exists before the record set is ready
            return domain_validation[0]['ResourceRecord']
        except KeyError:
            LOGGER.debug('Waiting for DomainValidationOptions.ResourceRecord '
                         'to become available for the certificate...')
            sleep(interval)
            return self.get_validation_record(cert_arn=cert_arn,
                                              interval=interval)

    def put_record_set(self, record_set):
        """Create/update a record set on a Route 53 Hosted Zone.

        Args:
            record_set (Dict[str, str]): Record set to be added to Route 53.

        """
        LOGGER.info('Adding validation record to "%s"',
                    self.args.hosted_zone_id)
        LOGGER.debug('Validation Record: %s', record_set)
        return self.r53_client.change_resource_record_sets(
            HostedZoneId=self.args.hosted_zone_id,
            ChangeBatch={
                'Comment': self.get_template_description(),
                'Changes': [
                    {
                        # 'Action': 'CREATE',  # TODO revert after adding delete
                        'Action': 'UPSERT',  # create or update
                        'ResourceRecordSet': {
                            'Name': record_set['Name'],
                            'Type': record_set['Type'],
                            'ResourceRecords': [
                                {'Value': record_set['Value']}
                            ],
                            'TTL': 5
                        }
                    }
                ]
            }
        )

    def _deploy(self):
        """Deploy an ACM Certificate."""
        status = self.deploy_stack()
        cert_arn = self.get_certificate()
        result = {'CertificateArn': cert_arn}

        if status == NO_CHANGE:
            LOGGER.debug('Stack did not change; no action required')
            return result

        try:
            record = self.get_validation_record(cert_arn)
            self.put_record_set(record)
        except ValueError as err:
            if 'No pending validations' in str(err) and \
                    'updating existing stack' in status.reason:
                LOGGER.debug('Stack update did not cause recreation; '
                             'no action required')
            else:
                raise
        self.wait_for_stack()

        return result

    def post_deploy(self):
        """Run during the **post_deploy** stage."""
        return self._deploy()

    def post_destroy(self):
        """Run during the **post_destroy** stage."""
        LOGGER.warning('%s does not support "destory" at this time')

    def pre_deploy(self):
        """Run during the **pre_deploy** stage."""
        return self._deploy()

    def pre_destroy(self):
        """Run during the **pre_destroy** stage."""
        LOGGER.warning('%s does not support "destory" at this time')

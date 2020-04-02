"""CFNgin hooks for AWS Certificate Manager."""
import logging
import time

from botocore.exceptions import ClientError
from troposphere import Ref
from troposphere.certificatemanager import Certificate as CertificateResource

from runway.util import MutableMap

from ..blueprints.variables.types import CFNString
from ..exceptions import StackDoesNotExist, StackFailed, StackUpdateBadStatus
from ..status import NO_CHANGE, SUBMITTED
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
        stack_name (Optional[str]): Provide a name for the stack used to
            create the certificate. If not provided, the domain is used
            (replacing ``.`` with ``-``).
        ttl (Optional[int]): The resource record cache time to live (TTL),
            in seconds. (*default:* ``300``)

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

    def __init__(self, context, provider, **kwargs):
        """Instantiate class.

        Args:
            context (:class:`runway.cfngin.context.Context`): Context instance.
                (passed in by CFNgin)
            provider (:class:`runway.cfngin.providers.base.BaseProvider`):
                Provider instance. (passed in by CFNgin)

        """
        kwargs.setdefault('ttl', 300)
        super(Certificate, self).__init__(context, provider, **kwargs)

        self.template_description = self.get_template_description()
        self.stack_name = self.args.get('stack_name',
                                        kwargs['domain'].replace('.', '-'))

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
        self.stack = self.generate_stack(
            variables={'ValidateRecordTTL': self.args.ttl,
                       'DomainName': self.args.domain}
        )

    def _create_blueprint(self):
        """Create CFNgin Blueprint."""
        blueprint = BlankBlueprint(self.stack_name, self.context)
        blueprint.template.set_version('2010-09-09')
        blueprint.template.set_description(self.template_description)

        var_description = ('NO NOT CHANGE MANUALLY! Used to track the '
                           'state of a value set outside of CloudFormation'
                           ' using a Runway hook.')

        blueprint.VARIABLES = {
            'DomainName': {
                'type': CFNString,
                'description': var_description
            },
            'ValidateRecordTTL': {
                'type': CFNString,
                'description': var_description
            }
        }

        cert = blueprint.template.add_resource(CertificateResource(
            'Certificate',
            **self.properties.data
        ))
        blueprint.add_output('%sArn' % cert.title, cert.ref())
        blueprint.add_output('ValidateRecordTTL', Ref('ValidateRecordTTL'))
        blueprint.add_output('DomainName', Ref('DomainName'))
        return blueprint

    def domain_changed(self):
        """Check to ensure domain has not changed for existing stack."""
        try:
            stack_info = self.provider.get_stack(self.stack.fqn)
            if self.provider.is_stack_recreatable(stack_info):
                LOGGER.debug('Stack is in a recreatable state; '
                             'domain change does not matter')
                return False
            if self.provider.is_stack_in_progress(stack_info) or \
                    self.provider.is_stack_rolling_back(stack_info):
                LOGGER.debug('Stack is in progress; '
                             "can't check for domain change")
                return False
            if self.args.domain != \
                    self.provider.get_outputs(self.stack.fqn)['DomainName']:
                LOGGER.error('"domain" can\'t be changed for existing '
                             'certificate in stack "%s"', self.stack.fqn)
                return True
        except StackDoesNotExist:
            pass
        except KeyError:
            LOGGER.warning('Stack "%s" is missing output DomainName; '
                           'update may fail', self.stack.fqn)
        return False

    def get_certificate(self, interval=5):
        """Get the certificate being created by a CloudFormation.

        Args:
            interval (int): Number of seconds to wait between attempts.

        Returns:
            str: Certificate ARN

        """
        response = self.provider.cloudformation.describe_stack_resources(
            StackName=self.stack.fqn,
            LogicalResourceId='Certificate'
        )['StackResources']
        if response:
            # can be returned without having a PhysicalResourceId
            if response[0].get('PhysicalResourceId'):
                return response[0]['PhysicalResourceId']
        LOGGER.debug('Waiting for certificate to be created...')
        time.sleep(interval)
        return self.get_certificate(interval=interval)

    def get_validation_record(self, cert_arn=None, interval=5,
                              status='PENDING_VALIDATION'):
        """Get validation record from the certificate being created.

        Args:
            cert_arn (str): ARN of the certificate to validate.
            interval (int): Number of seconds to wait between attempts.
            status (str): Validation status to look for when finding a
                validation record. Typically only "PENDING_VALIDATION" or
                "SUCCESS" will be used.

        Returns:
            Dict[str, str]: A record set to be added to Route 53.

        Raises:
            ValueError: No pending or too many pending certificates.

        """
        if not cert_arn:
            cert_arn = self.get_certificate()
        cert = self.acm_client.describe_certificate(
            CertificateArn=cert_arn
        )['Certificate']

        try:
            domain_validation = [
                opt for opt in cert['DomainValidationOptions']
                if opt['ValidationStatus'] == status
            ]
        except KeyError:
            LOGGER.debug('Waiting for DomainValidationOptions to become '
                         'available for the certificate...')
            time.sleep(interval)
            return self.get_validation_record(cert_arn=cert_arn,
                                              interval=interval,
                                              status=status)

        if not domain_validation:
            raise ValueError(
                'No validations with status "{}" found for "{}"'.format(
                    status, self.args.domain
                )
            )
        if len(domain_validation) > 1:
            raise ValueError(
                'Found {} validation options of status "{}" for "{}"; only one '
                'option is supported'.format(len(domain_validation),
                                             status, self.args.domain)
            )
        try:
            # the validation option can exists before the record set is ready
            return domain_validation[0]['ResourceRecord']
        except KeyError:
            LOGGER.debug('Waiting for DomainValidationOptions.ResourceRecord '
                         'to become available for the certificate...')
            time.sleep(interval)
            return self.get_validation_record(cert_arn=cert_arn,
                                              interval=interval,
                                              status=status)

    def put_record_set(self, record_set):
        """Create/update a record set on a Route 53 Hosted Zone.

        Args:
            record_set (Dict[str, str]): Record set to be added to Route 53.

        """
        LOGGER.info('Adding validation record to "%s"',
                    self.args.hosted_zone_id)
        self.__change_record_set('CREATE', [record_set])

    def remove_validation_records(self, records=None):
        """Remove all record set entries used to validate an ACM Certificate.

        Args:
            records (Optional[List[Dict[str, str]]]): List of validation
                records to remove from Route 53. This can be provided in cases
                were the certificate has been deleted during a rollback.

        """
        if not records:
            cert_arn = self.get_certificate()
            cert = self.acm_client.describe_certificate(
                CertificateArn=cert_arn
            )['Certificate']

            records = [opt['ResourceRecord']
                       for opt in cert.get('DomainValidationOptions', [])
                       if opt['ValidationMethod'] == 'DNS']
        LOGGER.info('Removing %i validation record(s) from "%s"...',
                    len(records), self.args.hosted_zone_id)
        self.__change_record_set('DELETE', records)

    def update_record_set(self, record_set):
        """Update a validation record set when the cert has not changed.

        Args:
            record_set (Dict[str, str]): Record set to be updated in Route 53.

        """
        LOGGER.info('Updating record set...')
        self.__change_record_set('UPSERT', [record_set])

    def __change_record_set(self, action, record_sets):
        """Wrap boto3.client('acm').change_resource_record_sets.

        Args:
            action (str): Change action. [CREATE, DELETE, UPSERT]
            record_sets (List[Dict[str, str]]): Record sets to change.

        """
        if not record_sets:
            raise ValueError('Must provide one of more record sets')

        changes = [{
            'Action': action,
            'ResourceRecordSet': {
                'Name': record['Name'],
                'Type': record['Type'],
                'ResourceRecords': [
                    {'Value': record['Value']}
                ],
                'TTL': self.args.ttl
            }
        } for record in record_sets]

        LOGGER.debug('Making the following changes to hosted zone "%s":\n%s',
                     self.args.hosted_zone_id, changes)

        self.r53_client.change_resource_record_sets(
            HostedZoneId=self.args.hosted_zone_id,
            ChangeBatch={
                'Comment': self.get_template_description(),
                'Changes': changes
            }
        )

    def deploy(self, status=None):
        """Deploy an ACM Certificate."""
        record = None
        try:
            if self.domain_changed():
                return None

            if not status:
                status = self.deploy_stack()

            cert_arn = self.get_certificate()
            result = {'CertificateArn': cert_arn}

            if status == NO_CHANGE:
                LOGGER.debug('Stack did not change; no action required')
                return result

            if status == SUBMITTED:
                if status.reason == 'creating new stack':
                    record = self.get_validation_record(cert_arn)
                    self.put_record_set(record)
                    LOGGER.info('Waiting for certificate to validate; '
                                'this can take upwards of 30 minutes to '
                                'complete...')
                elif status.reason == 'updating existing stack':
                    # get the cert ARN again in case it changed during update
                    cert_arn = self.get_certificate()
                    record = self.get_validation_record(cert_arn, status='SUCCESS')
                    self.update_record_set(record)
                elif status.reason == 'destroying stack for re-creation':
                    # handle recreating a stack in a failed state
                    return self.deploy(status=self._wait_for_stack(
                        self._deploy_action,
                        last_status=status,
                        till_reason='creating new stack'
                    ))
                self._wait_for_stack(self._deploy_action, last_status=status)
                return result
        except (self.r53_client.exceptions.InvalidChangeBatch,
                self.r53_client.exceptions.NoSuchHostedZone,
                StackFailed) as err:
            LOGGER.error(err)
            self.destroy(records=[record], skip_r53=isinstance(
                err, (self.r53_client.exceptions.InvalidChangeBatch,
                      self.r53_client.exceptions.NoSuchHostedZone)
            ))
        except StackUpdateBadStatus as err:
            # don't try to destroy the stack when it can be in progress
            LOGGER.error(err)
        return None

    def destroy(self, records=None, skip_r53=False):
        """Destroy an ACM certificate.

        Args:
            records (Optional[List[Dict[str, str]]]): List of validation
                records to remove from Route 53. This can be provided in cases
                were the certificate has been deleted during a rollback.
            skip_r53 (bool): Skip the removal of validation records.

        """
        if not skip_r53:
            try:
                self.remove_validation_records(records)
            except (self.r53_client.exceptions.InvalidChangeBatch,
                    self.r53_client.exceptions.NoSuchHostedZone,
                    self.acm_client.exceptions.ResourceNotFoundException) as err:
                # these error are fine if they happen during destruction but
                # could require manual steps to finish cleanup.
                LOGGER.warning('Deletion of the validation records failed '
                               'with error:\n%s', err)
            except ClientError as err:
                if err.response['Error']['Message'] != ('Stack with id {} does'
                                                        ' not exist'.format(
                                                            self.stack.fqn)):
                    raise
                LOGGER.warning('Deletion of the validation records failed '
                               'with error:\n%s', err)
        else:
            LOGGER.info('Deletion of validation records was skipped')
        self.destroy_stack(wait=True)
        return True

    def post_deploy(self):
        """Run during the **post_deploy** stage."""
        return self.deploy()

    def post_destroy(self):
        """Run during the **post_destroy** stage."""
        return self.destroy()

    def pre_deploy(self):
        """Run during the **pre_deploy** stage."""
        return self.deploy()

    def pre_destroy(self):
        """Run during the **pre_destroy** stage."""
        return self.destroy()

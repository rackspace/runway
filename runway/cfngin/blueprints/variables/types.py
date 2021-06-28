"""CFNgin blueprint variable types."""
# pylint: disable=invalid-name,len-as-condition
from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    overload,
)

from troposphere import BaseAWSObject

if TYPE_CHECKING:
    from typing_extensions import Literal

_TroposphereType = TypeVar("_TroposphereType", bound=BaseAWSObject)


class TroposphereType(Generic[_TroposphereType]):
    """Represents a Troposphere type.

    :class:`Troposphere` will convert the value provided to the variable to
    the specified Troposphere type.

    Both resource and parameter classes (which are just used to configure
    other resources) are acceptable as configuration values.

    Complete resource definitions must be dictionaries, with the keys
    identifying the resource titles, and the values being used as the
    constructor parameters.

    Parameter classes can be defined as dictionary or a list of
    dictionaries. In either case, the keys and values will be used directly
    as constructor parameters.

    """

    def __init__(
        self,
        defined_type: Type[_TroposphereType],
        *,
        many: bool = False,
        optional: bool = False,
        validate: bool = True,
    ) -> None:
        """Instantiate class.

        Args:
            defined_type: Troposphere type.
            many: Whether or not multiple resources can be constructed.
                If the defined type is a resource, multiple resources can be
                passed as a dictionary of dictionaries.
                If it is a parameter class, multiple resources are passed as
                a list.
            optional: Whether an undefined/null configured value is acceptable.
                In that case a value of ``None`` will be passed to the template,
                even if ``many`` is enabled.
            validate: Whether to validate the generated object on creation.
                Should be left enabled unless the object will be augmented with
                mandatory parameters in the template code, such that it must be
                validated at a later point.

        """
        self._validate_type(defined_type)

        self._type = defined_type
        self._many = many
        self._optional = optional
        self._validate = validate

    @staticmethod
    def _validate_type(defined_type: Type[_TroposphereType]) -> None:
        if not hasattr(defined_type, "from_dict"):
            raise ValueError("Type must have `from_dict` attribute")

    @property
    def resource_name(self) -> str:
        """Name of the type or resource."""
        return str(getattr(self._type, "resource_name", None) or self._type.__name__)

    @overload
    def create(self, value: Dict[str, Any]) -> _TroposphereType:
        ...

    @overload
    def create(self, value: List[Dict[str, Any]]) -> List[_TroposphereType]:
        ...

    @overload
    def create(self, value: None) -> None:
        ...

    def create(
        self, value: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]
    ) -> Optional[Union[_TroposphereType, List[_TroposphereType]]]:
        """Create the troposphere type from the value.

        Args:
            value: A dictionary or list of dictionaries (see class documentation
                for details) to use as parameters to create the Troposphere type instance.
                Each dictionary will be passed to the ``from_dict`` method of
                the type.

        Returns:
            Returns the value converted to the troposphere type.

        """
        # Explicitly check with len such that non-sequence types throw.
        if self._optional and (value is None or len(value) == 0):
            return None

        if hasattr(self._type, "resource_type"):
            # Our type is a resource, so ensure we have a dict of title to
            # parameters
            if not isinstance(value, dict):
                raise ValueError(
                    "Resources must be specified as a dict of title to parameters"
                )
            if not self._many and len(value) > 1:
                raise ValueError(
                    "Only one resource can be provided for this "
                    "TroposphereType variable"
                )

            result = [self._type.from_dict(title, v) for title, v in value.items()]
        else:
            # Our type is for properties, not a resource, so don't use
            # titles
            if self._many and isinstance(value, list):
                result = [self._type.from_dict(None, v) for v in value]
            elif not isinstance(value, dict):
                raise ValueError(
                    "TroposphereType for a single non-resource"
                    "type must be specified as a dict of "
                    "parameters"
                )
            else:
                result = [self._type.from_dict(None, value)]

        if self._validate:
            for v in result:
                v._validate_props()

        return result[0] if not self._many else result


class CFNType:
    """Represents a CloudFormation Parameter Type.

    :class:`CFNType` can be used as the ``type`` for a Blueprint variable.
    Unlike other variables, a variable with ``type: CFNType``, will
    be submitted to CloudFormation as a Parameter.

    Attributes:
        parameter_type: Name of the CloudFormation Parameter type to specify when
            submitting as a CloudFormation Parameter.

    See Also:
        https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/parameters-section-structure.html

    """

    parameter_type: ClassVar[str]


# General CFN types
class CFNString(CFNType):
    """A literal string."""

    parameter_type: ClassVar[Literal["String"]] = "String"


class CFNNumber(CFNType):
    """An integer or float.

    AWS CloudFormation validates the parameter value as a number; however,
    whenyou use the parameter elsewhere in your template (for example, by using
    the Ref intrinsic function), the parameter value becomes a string.

    """

    parameter_type: ClassVar[Literal["Number"]] = "Number"


class CFNNumberList(CFNType):
    """An array of integers or floats that are separated by commas.

    AWS CloudFormation validates the parameter value as numbers; however,
    when you use the parameter elsewhere in your template (for example, by using
    the Ref intrinsic function), the parameter value becomes a list of strings.

    """

    parameter_type: ClassVar[Literal["List<Number>"]] = "List<Number>"


class CFNCommaDelimitedList(CFNType):
    """An array of literal strings that are separated by commas.

    The total number of strings should be one more than the total number of commas.
    Also, each member string is space trimmed.

    """

    parameter_type: ClassVar[Literal["CommaDelimitedList"]] = "CommaDelimitedList"


# AWS-Specific Parameter Types
# https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/parameters-section-structure.html#aws-specific-parameter-types
class EC2AvailabilityZoneName(CFNType):
    """An Availability Zone, such as us-west-2a."""

    parameter_type: ClassVar[
        Literal["AWS::EC2::AvailabilityZone::Name"]
    ] = "AWS::EC2::AvailabilityZone::Name"


class EC2ImageId(CFNType):
    """An Amazon EC2 image ID, such as ami-0ff8a91507f77f867.

    Note that the AWS CloudFormation console doesn't show a drop-down list of
    values for this parameter type.

    """

    parameter_type: ClassVar[Literal["AWS::EC2::Image::Id"]] = "AWS::EC2::Image::Id"


class EC2InstanceId(CFNType):
    """An Amazon EC2 instance ID, such as i-1e731a32."""

    parameter_type: ClassVar[
        Literal["AWS::EC2::Instance::Id"]
    ] = "AWS::EC2::Instance::Id"


class EC2KeyPairKeyName(CFNType):
    """An Amazon EC2 key pair name."""

    parameter_type: ClassVar[
        Literal["AWS::EC2::KeyPair::KeyName"]
    ] = "AWS::EC2::KeyPair::KeyName"


class EC2SecurityGroupGroupName(CFNType):
    """An EC2-Classic or default VPC security group name, such as my-sg-abc."""

    parameter_type: ClassVar[
        Literal["AWS::EC2::SecurityGroup::GroupName"]
    ] = "AWS::EC2::SecurityGroup::GroupName"


class EC2SecurityGroupId(CFNType):
    """A security group ID, such as sg-a123fd85."""

    parameter_type: ClassVar[
        Literal["AWS::EC2::SecurityGroup::Id"]
    ] = "AWS::EC2::SecurityGroup::Id"


class EC2SubnetId(CFNType):
    """A subnet ID, such as subnet-123a351e."""

    parameter_type: ClassVar[Literal["AWS::EC2::Subnet::Id"]] = "AWS::EC2::Subnet::Id"


class EC2VolumeId(CFNType):
    """An Amazon EBS volume ID, such as vol-3cdd3f56."""

    parameter_type: ClassVar[Literal["AWS::EC2::Volume::Id"]] = "AWS::EC2::Volume::Id"


class EC2VPCId(CFNType):
    """A VPC ID, such as vpc-a123baa3."""

    parameter_type: ClassVar[Literal["AWS::EC2::VPC::Id"]] = "AWS::EC2::VPC::Id"


class Route53HostedZoneId(CFNType):
    """An Amazon Route 53 hosted zone ID, such as Z23YXV4OVPL04A."""

    parameter_type: ClassVar[
        Literal["AWS::Route53::HostedZone::Id"]
    ] = "AWS::Route53::HostedZone::Id"


class EC2AvailabilityZoneNameList(CFNType):
    """An array of Availability Zones for a region, such as us-west-2a, us-west-2b."""

    parameter_type: ClassVar[
        Literal["List<AWS::EC2::AvailabilityZone::Name>"]
    ] = "List<AWS::EC2::AvailabilityZone::Name>"


class EC2ImageIdList(CFNType):
    """An array of Amazon EC2 image IDs, such as ami-0ff8a91507f77f867, ami-0a584ac55a7631c0c.

    Note that the AWS CloudFormation console doesn't show a drop-down list of
    values for this parameter type.

    """

    parameter_type: ClassVar[
        Literal["List<AWS::EC2::Image::Id>"]
    ] = "List<AWS::EC2::Image::Id>"


class EC2InstanceIdList(CFNType):
    """An array of Amazon EC2 instance IDs, such as i-1e731a32, i-1e731a34."""

    parameter_type: ClassVar[
        Literal["List<AWS::EC2::Instance::Id>"]
    ] = "List<AWS::EC2::Instance::Id>"


class EC2SecurityGroupGroupNameList(CFNType):
    """An array of EC2-Classic or default VPC security group names."""

    parameter_type: ClassVar[
        Literal["List<AWS::EC2::SecurityGroup::GroupName>"]
    ] = "List<AWS::EC2::SecurityGroup::GroupName>"


class EC2SecurityGroupIdList(CFNType):
    """An array of security group IDs, such as sg-a123fd85, sg-b456fd85."""

    parameter_type: ClassVar[
        Literal["List<AWS::EC2::SecurityGroup::Id>"]
    ] = "List<AWS::EC2::SecurityGroup::Id>"


class EC2SubnetIdList(CFNType):
    """An array of subnet IDs, such as subnet-123a351e, subnet-456b351e."""

    parameter_type: ClassVar[
        Literal["List<AWS::EC2::Subnet::Id>"]
    ] = "List<AWS::EC2::Subnet::Id>"


class EC2VolumeIdList(CFNType):
    """An array of Amazon EBS volume IDs, such as vol-3cdd3f56, vol-4cdd3f56."""

    parameter_type: ClassVar[
        Literal["List<AWS::EC2::Volume::Id>"]
    ] = "List<AWS::EC2::Volume::Id>"


class EC2VPCIdList(CFNType):
    """An array of VPC IDs, such as vpc-a123baa3, vpc-b456baa3."""

    parameter_type: ClassVar[
        Literal["List<AWS::EC2::VPC::Id>"]
    ] = "List<AWS::EC2::VPC::Id>"


class Route53HostedZoneIdList(CFNType):
    """An array of Amazon Route 53 hosted zone IDs, such as Z23YXV4OVPL04A, Z23YXV4OVPL04B."""

    parameter_type: ClassVar[
        Literal["List<AWS::Route53::HostedZone::Id>"]
    ] = "List<AWS::Route53::HostedZone::Id>"


# SSM Parameter Types
# https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/parameters-section-structure.html#aws-ssm-parameter-types
class SSMParameterName(CFNType):
    """The name of a Systems Manager parameter key.

    Use this parameter when you want to pass the parameter key.
    For example, you can use this type to validate that the parameter exists.

    """

    parameter_type: ClassVar[
        Literal["AWS::SSM::Parameter::Name"]
    ] = "AWS::SSM::Parameter::Name"


class SSMParameterValueString(CFNType):
    """A Systems Manager parameter whose value is a string.

    This corresponds to the String parameter type in Parameter Store.

    """

    parameter_type: ClassVar[
        Literal["AWS::SSM::Parameter::Value<String>"]
    ] = "AWS::SSM::Parameter::Value<String>"


class SSMParameterValueStringList(CFNType):
    """A Systems Manager parameter whose value is a list of strings.

    This corresponds to the StringList parameter type in Parameter Store.

    """

    parameter_type: ClassVar[
        Literal["AWS::SSM::Parameter::Value<List<String>>"]
    ] = "AWS::SSM::Parameter::Value<List<String>>"


class SSMParameterValueCommaDelimitedList(CFNType):
    """A Systems Manager parameter whose value is a list of strings.

    This corresponds to the StringList parameter type in Parameter Store.

    """

    parameter_type: ClassVar[
        Literal["AWS::SSM::Parameter::Value<CommaDelimitedList>"]
    ] = "AWS::SSM::Parameter::Value<CommaDelimitedList>"


class SSMParameterValueEC2AvailabilityZoneName(CFNType):
    """A Systems Manager parameter whose value is an AWS-specific parameter type."""

    parameter_type: ClassVar[
        Literal["AWS::SSM::Parameter::Value<AWS::EC2::AvailabilityZone::Name>"]
    ] = "AWS::SSM::Parameter::Value<AWS::EC2::AvailabilityZone::Name>"


class SSMParameterValueEC2ImageId(CFNType):
    """A Systems Manager parameter whose value is an AWS-specific parameter type."""

    parameter_type: ClassVar[
        Literal["AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>"]
    ] = "AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>"


class SSMParameterValueEC2InstanceId(CFNType):
    """A Systems Manager parameter whose value is an AWS-specific parameter type."""

    parameter_type: ClassVar[
        Literal["AWS::SSM::Parameter::Value<AWS::EC2::Instance::Id>"]
    ] = "AWS::SSM::Parameter::Value<AWS::EC2::Instance::Id>"


class SSMParameterValueEC2KeyPairKeyName(CFNType):
    """A Systems Manager parameter whose value is an AWS-specific parameter type."""

    parameter_type: ClassVar[
        Literal["AWS::SSM::Parameter::Value<AWS::EC2::KeyPair::KeyName>"]
    ] = "AWS::SSM::Parameter::Value<AWS::EC2::KeyPair::KeyName>"


class SSMParameterValueEC2SecurityGroupGroupName(CFNType):
    """A Systems Manager parameter whose value is an AWS-specific parameter type."""

    parameter_type: ClassVar[
        Literal["AWS::SSM::Parameter::Value<AWS::EC2::SecurityGroup::GroupName>"]
    ] = "AWS::SSM::Parameter::Value<AWS::EC2::SecurityGroup::GroupName>"


class SSMParameterValueEC2SecurityGroupId(CFNType):
    """A Systems Manager parameter whose value is an AWS-specific parameter type."""

    parameter_type: ClassVar[
        Literal["AWS::SSM::Parameter::Value<AWS::EC2::SecurityGroup::Id>"]
    ] = "AWS::SSM::Parameter::Value<AWS::EC2::SecurityGroup::Id>"


class SSMParameterValueEC2SubnetId(CFNType):
    """A Systems Manager parameter whose value is an AWS-specific parameter type."""

    parameter_type: ClassVar[
        Literal["AWS::SSM::Parameter::Value<AWS::EC2::Subnet::Id>"]
    ] = "AWS::SSM::Parameter::Value<AWS::EC2::Subnet::Id>"


class SSMParameterValueEC2VolumeId(CFNType):
    """A Systems Manager parameter whose value is an AWS-specific parameter type."""

    parameter_type: ClassVar[
        Literal["AWS::SSM::Parameter::Value<AWS::EC2::Volume::Id>"]
    ] = "AWS::SSM::Parameter::Value<AWS::EC2::Volume::Id>"


class SSMParameterValueEC2VPCId(CFNType):
    """A Systems Manager parameter whose value is an AWS-specific parameter type."""

    parameter_type: ClassVar[
        Literal["AWS::SSM::Parameter::Value<AWS::EC2::VPC::Id>"]
    ] = "AWS::SSM::Parameter::Value<AWS::EC2::VPC::Id>"


class SSMParameterValueRoute53HostedZoneId(CFNType):
    """A Systems Manager parameter whose value is an AWS-specific parameter type."""

    parameter_type: ClassVar[
        Literal["AWS::SSM::Parameter::Value<AWS::Route53::HostedZone::Id>"]
    ] = "AWS::SSM::Parameter::Value<AWS::Route53::HostedZone::Id>"


class SSMParameterValueEC2AvailabilityZoneNameList(CFNType):
    """A Systems Manager parameter whose value is an AWS-specific parameter type."""

    parameter_type: ClassVar[
        Literal["AWS::SSM::Parameter::Value<List<AWS::EC2::AvailabilityZone::Name>>"]
    ] = "AWS::SSM::Parameter::Value<List<AWS::EC2::AvailabilityZone::Name>>"


class SSMParameterValueEC2ImageIdList(CFNType):
    """A Systems Manager parameter whose value is an AWS-specific parameter type."""

    parameter_type: ClassVar[
        Literal["AWS::SSM::Parameter::Value<List<AWS::EC2::Image::Id>>"]
    ] = "AWS::SSM::Parameter::Value<List<AWS::EC2::Image::Id>>"


class SSMParameterValueEC2InstanceIdList(CFNType):
    """A Systems Manager parameter whose value is an AWS-specific parameter type."""

    parameter_type: ClassVar[
        Literal["AWS::SSM::Parameter::Value<List<AWS::EC2::Instance::Id>>"]
    ] = "AWS::SSM::Parameter::Value<List<AWS::EC2::Instance::Id>>"


class SSMParameterValueEC2SecurityGroupGroupNameList(CFNType):
    """A Systems Manager parameter whose value is an AWS-specific parameter type."""

    parameter_type: ClassVar[
        Literal["AWS::SSM::Parameter::Value<List<AWS::EC2::SecurityGroup::GroupName>>"]
    ] = "AWS::SSM::Parameter::Value<List<AWS::EC2::SecurityGroup::GroupName>>"


class SSMParameterValueEC2SecurityGroupIdList(CFNType):
    """A Systems Manager parameter whose value is an AWS-specific parameter type."""

    parameter_type: ClassVar[
        Literal["AWS::SSM::Parameter::Value<List<AWS::EC2::SecurityGroup::Id>>"]
    ] = "AWS::SSM::Parameter::Value<List<AWS::EC2::SecurityGroup::Id>>"


class SSMParameterValueEC2SubnetIdList(CFNType):
    """A Systems Manager parameter whose value is an AWS-specific parameter type."""

    parameter_type: ClassVar[
        Literal["AWS::SSM::Parameter::Value<List<AWS::EC2::Subnet::Id>>"]
    ] = "AWS::SSM::Parameter::Value<List<AWS::EC2::Subnet::Id>>"


class SSMParameterValueEC2VolumeIdList(CFNType):
    """A Systems Manager parameter whose value is an AWS-specific parameter type."""

    parameter_type: ClassVar[
        Literal["AWS::SSM::Parameter::Value<List<AWS::EC2::Volume::Id>>"]
    ] = "AWS::SSM::Parameter::Value<List<AWS::EC2::Volume::Id>>"


class SSMParameterValueEC2VPCIdList(CFNType):
    """A Systems Manager parameter whose value is an AWS-specific parameter type."""

    parameter_type: ClassVar[
        Literal["AWS::SSM::Parameter::Value<List<AWS::EC2::VPC::Id>>"]
    ] = "AWS::SSM::Parameter::Value<List<AWS::EC2::VPC::Id>>"


class SSMParameterValueRoute53HostedZoneIdList(CFNType):
    """A Systems Manager parameter whose value is an AWS-specific parameter type."""

    parameter_type: ClassVar[
        Literal["AWS::SSM::Parameter::Value<List<AWS::Route53::HostedZone::Id>>"]
    ] = "AWS::SSM::Parameter::Value<List<AWS::Route53::HostedZone::Id>>"

"""Support for AWS SSO.

IMPORTANT: This will be removed upon botocore/boto3 officially supporting
authentication with AWS SSO profiles.

The code in this directory is taken from
https://github.com/boto/botocore/tree/bf6d31f42f90a547707df4e83943702beacda45a
and modified to meet the requirements of this project.

"""
# Copyright 2012-2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

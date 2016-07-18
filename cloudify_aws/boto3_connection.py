#########
# Copyright (c) 2016 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#  * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  * See the License for the specific language governing permissions and
#  * limitations under the License.

from functools import wraps

import boto3
from botocore.exceptions import ClientError

from cloudify.exceptions import NonRecoverableError
from cloudify.decorators import operation


__all__ = ['connection', 'nonrecoverable_errors', 'b3operation']


def connection(aws_conf):
    return boto3.Session(
        aws_access_key_id=aws_conf['aws_access_key_id'],
        aws_secret_access_key=aws_conf['aws_secret_access_key'],
        region_name=aws_conf['ec2_region_name'],
        )


_non_recoverable_errors = [
    'IncompleteSignatureException',
    'UnrecognizedClientException',
    ]

_bad_codes = [
    400,  # bad request
    401,  # unauthorized
    402,  # payment required
    403,  # forbidden
    404,  # not found
    405,  # method not allowed
    406,  # not acceptable
    407,  # proxy auth required
    410,  # gone
    418,  # AWS does not support coffee
    ]


def nonrecoverable_errors(fun):
    """Decorator which raises NonRecoverableError if non recoverable errors
    from boto3 are caught"""
    def wrap(*args, **kwargs):
        try:
            fun(*args, **kwargs)
        except ClientError as e:
            if (e.response['ResponseMetadata']['HTTPStatusCode'] in _bad_codes
                    or e.response['Error']['Code'] in _non_recoverable_errors):
                raise NonRecoverableError(e)
            raise

    return wraps(fun)(wrap)


def b3operation(fun, *args, **kwargs):
    """Combine @operation and @nonrecoverable_errors"""
    @wraps(fun)
    @operation
    @nonrecoverable_errors
    def wrap(*args, **kwargs):
        fun(*args, **kwargs)

    return wrap

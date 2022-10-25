# Copyright (c) 2018 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
    Cognito.user_pool
    ~~~~~~~~
    AWS Cognito User Pool interface
"""

# Third party imports
from botocore.exceptions import (
    ClientError,
    ParamValidationError)

# Local imports
from cloudify_aws.cognito import CognitoBase
from cloudify_aws.common import decorators, utils

RESOURCE_NAME = 'PoolName'
DESCRIBE_INDEX = 'UserPool'
RESOURCE_TYPE = 'Cognito User Pool'


class CognitoUserPool(CognitoBase):
    """
        AWS Cognito User Pool interface
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        CognitoBase.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        if self.resource_id:
            try:
                resource = self.client.describe_user_pools(
                    UserPoolId=self.resource_id)
            except (ParamValidationError, ClientError):
                pass
            else:
                return resource.get(DESCRIBE_INDEX, {})
        return {}

    @property
    def status(self):
        """Gets the status of an external resource"""
        return self.properties.get('Status')

    def create(self, params):
        """Create a new AWS Cognito User Pool."""
        return self.make_client_call('create_user_pool', params)

    def delete(self, params=None):
        """Delete a new AWS Cognito User Pool."""
        return self.make_client_call('delete_user_pool', params)


@decorators.aws_resource(CognitoUserPool, RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS Cognito User Pool"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(CognitoUserPool, RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    """Creates an AWS Cognito User Pool"""
    create_response = utils.raise_on_substring(
        iface,
        'create',
        resource_config,
        'Role does not have a trust relationship')
    utils.update_resource_id(
        ctx.instance,
        create_response['UserPool']['Id'])
    utils.update_resource_arn(
        ctx.instance,
        create_response['UserPool']['Arn'])
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response).to_dict()


@decorators.aws_resource(CognitoUserPool,
                         RESOURCE_TYPE,
                         ignore_properties=True)
def delete(iface, resource_config, **_):
    """Deletes an AWS Cognito User Pool"""
    iface.delete(
        {
            'UserPoolId': utils.get_resource_id()
        }
    )

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
    Cognito.user_pool_client
    ~~~~~~~~
    AWS Cognito User Pool Client interface
"""

# Third party imports
from botocore.exceptions import ClientError, ParamValidationError

# Local imports
from cloudify_aws.common import decorators, utils
from cloudify_aws.cognito import CognitoBase

RESOURCE_NAME = 'ClientName'
DESCRIBE_INDEX = 'UserPoolClient'
RESOURCE_TYPE = 'Cognito User Pool Client'


class CognitoUserPoolClient(CognitoBase):
    """
        AWS Cognito Cognito User Pool Client interface
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        CognitoBase.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE
        self._user_pool_id = \
            self.ctx_node.properties['resource_config']['UserPoolId']

    @property
    def user_pool_id(self):
        return self._user_pool_id

    @user_pool_id.setter
    def user_pool_id(self, value):
        self._user_pool_id = value

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        if self.resource_id:
            try:
                resource = self.client.describe_user_pool_client(
                    UserPoolId=self.user_pool_id,
                    ClientId=self.resource_id
                )
            except (ParamValidationError, ClientError):
                pass
            else:
                return resource.get('UserPoolClient', {})
        return {}

    @property
    def status(self):
        """Gets the status of an external resource"""
        return self.properties

    def create(self, params):
        """Create a new AWS Cognito User Pool Client."""
        return self.make_client_call('create_user_pool_client', params)

    def delete(self, params=None):
        """Delete a new AWS Cognito User Pool Client."""
        return self.make_client_call('delete_user_pool_client', params)


@decorators.aws_resource(CognitoUserPoolClient, RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS Cognito User Pool Client"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(CognitoUserPoolClient, RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    """Creates an AWS Cognito User Pool Client"""
    create_response = iface.create(resource_config)
    utils.update_resource_id(
        ctx.instance, create_response['UserPoolClient']['ClientId'])
    utils.update_resource_id(
        ctx.instance,
        create_response['UserPoolClient']['ClientId'])
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response).to_dict()


@decorators.aws_resource(CognitoUserPoolClient,
                         RESOURCE_TYPE)
def delete(ctx, iface, resource_config, **_):
    """Deletes an AWS Cognito User Pool Client"""
    iface.user_pool_id = resource_config.get(
        'UserPoolId') or iface.user_pool_id
    iface.delete(
        {
            'UserPoolId': iface.user_pool_id,
            'ClientId': utils.get_resource_id(),
        }
    )

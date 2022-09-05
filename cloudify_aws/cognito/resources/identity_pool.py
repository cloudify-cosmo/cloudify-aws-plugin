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
    Cognito.identity_pool
    ~~~~~~~~
    AWS Cognito Identity Pool interface
"""

# Third party imports
from botocore.exceptions import ClientError, ParamValidationError

# Local imports
from ...iam.resources.role import IAMRole
from cloudify_aws.common import decorators, utils
from cloudify_aws.cognito import CognitoIdentityBase

RESOURCE_NAME = 'IdentityPoolName'
DESCRIBE_INDEX = 'IdentityPoolId'
RESOURCE_TYPE = 'Cognito Identity Pool'


class CognitoIdentityPool(CognitoIdentityBase):
    """
        AWS Cognito Identity Pool
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        CognitoIdentityBase.__init__(
            self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        if self.resource_id:
            try:
                resource = self.client.describe_identity_pool(
                    IdentityPoolId=self.resource_id)
            except (ParamValidationError, ClientError):
                pass
            else:
                return resource.get(DESCRIBE_INDEX, {})
        return {}

    @property
    def status(self):
        """Gets the status of an external resource"""
        return self.properties

    def create(self, params):
        """Create a new AWS Cognito Identity Pool."""
        return self.make_client_call('create_identity_pool', params)

    def delete(self, params=None):
        """Delete a new AWS Cognito Identity Pool."""
        return self.make_client_call('delete_identity_pool', params)

    def get_roles(self):
        return self.client.get_identity_pool_roles(
            IdentityPoolId=self.resource_id)

    def set_roles(self, params):
        return self.make_client_call('set_identity_pool_roles', params)


@decorators.aws_resource(CognitoIdentityPool, RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS Cognito Identity Pool"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(CognitoIdentityPool, RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    """Creates an AWS Cognito Identity Pool"""
    create_response = iface.create(resource_config)
    utils.update_resource_id(
        ctx.instance, create_response['IdentityPoolId'])


@decorators.aws_resource(CognitoIdentityPool,
                         RESOURCE_TYPE,
                         ignore_properties=True)
def delete(iface, resource_config, **_):
    """Deletes an AWS Cognito Identity Pool"""
    iface.delete(
        {
            'IdentityPoolId': utils.get_resource_id()
        }
    )


@decorators.aws_relationship(IAMRole, RESOURCE_TYPE)
def set(ctx, iface, **_):
    """Deletes an AWS Cognito Identity Pool"""
    identity_pool = CognitoIdentityPool(
        ctx.target.node,
        ctx.target.instance.runtime_properties['aws_resource_id'],
        logger=ctx.logger,
    )
    roles = identity_pool.get_roles()
    if ctx.source.node.id not in roles.get('Roles', {}):
        updated_roles = roles.get('Roles', {})
        updated_roles.update({
            ctx.source.node.id: utils.get_resource_arn(
                ctx.source.node,
                ctx.source.instance,
                raise_on_missing=True
            )
        })
        identity_pool.set_roles({
            'IdentityPoolId': identity_pool.resource_id,
            'Roles': updated_roles,
        })


@decorators.aws_relationship(IAMRole, RESOURCE_TYPE)
def unset(ctx, iface, **_):
    """Deletes an AWS Cognito Identity Pool"""
    identity_pool = CognitoIdentityPool(
        ctx.target.node,
        ctx.target.instance.runtime_properties['aws_resource_id'],
        logger=ctx.logger,
    )
    roles = identity_pool.get_roles()
    if ctx.source.node.id in roles.get('Roles', {}):
        updated_roles = roles.get('Roles', {})
        del updated_roles[ctx.source.node.id]
        identity_pool.set_roles({
            'IdentityPoolId': identity_pool.resource_id,
            'Roles': updated_roles,
        })

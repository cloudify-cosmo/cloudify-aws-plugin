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
'''
    IAM.Role
    ~~~~~~~~
    AWS IAM Role interface
'''
from json import dumps as json_dumps

# Boto
from botocore.exceptions import ClientError

# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.iam import IAMBase

RESOURCE_TYPE = 'IAM Role'
RESOURCE_NAME = 'RoleName'


class IAMRole(IAMBase):
    '''
        AWS IAM Role interface
    '''
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        IAMBase.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        '''Gets the properties of an external resource'''
        resource = None
        try:
            resource = self.client.get_role(RoleName=self.resource_id)
        except ClientError:
            pass
        if not resource or not resource.get('Role', dict()):
            return None
        return resource['Role']

    @property
    def status(self):
        '''Gets the status of an external resource'''
        if self.properties:
            return 'available'
        return None

    def create(self, params):
        '''
            Create a new AWS IAM Role.
        '''
        return self.make_client_call('create_role', params)

    def delete(self, params=None):
        '''
            Deletes an existing AWS IAM Role.
        '''
        params = params or dict()
        params.update(dict(RoleName=self.resource_id))
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        self.client.delete_role(**params)

    def attach_policy(self, params):
        '''
            Attaches an IAM Policy to an IAM Role
        '''
        self.logger.debug('Attaching IAM Policy "%s" to IAM Role "%s"'
                          % (params.get('PolicyArn'), self.resource_id))
        params = params or dict()
        params.update(dict(RoleName=self.resource_id))
        self.client.attach_role_policy(**params)

    def detach_policy(self, params):
        '''
            Detaches an IAM Policy from an IAM Role
        '''
        self.logger.debug('Detaching IAM Policy "%s" from IAM Role "%s"'
                          % (params.get('PolicyArn'), self.resource_id))
        params = params or dict()
        params.update(dict(RoleName=self.resource_id))
        self.client.detach_role_policy(**params)


@decorators.aws_resource(IAMRole, RESOURCE_TYPE)
@decorators.aws_params(RESOURCE_NAME)
def create(ctx, iface, resource_config, params, **_):
    '''Creates an AWS IAM Role'''

    if 'AssumeRolePolicyDocument' in params and \
            isinstance(params['AssumeRolePolicyDocument'], dict):
        params['AssumeRolePolicyDocument'] = \
            json_dumps(params['AssumeRolePolicyDocument'])

    # Actually create the resource
    create_response = iface.create(params)
    resource_id = create_response['Role']['RoleName']
    iface.update_resource_id(resource_id)
    utils.update_resource_id(ctx.instance, resource_id)
    utils.update_resource_arn(
        ctx.instance, create_response['Role']['Arn'])

    # attach policy role
    policies_arn = []
    policies = _.get('modify_role_attribute_args', []) + \
               ctx.node.properties.get('policy_arns', [])
    for policy in policies:
        payload = dict()
        payload['RoleName'] = resource_id
        payload['PolicyArn'] = policy['PolicyArn']
        policies_arn.append(payload['PolicyArn'])
        iface.attach_policy(payload)

    # If there are policies added attached to role, then we need to make
    # sure that when uninstall triggers, all the attached policies arn are
    # available to detach
    if policies_arn:
        ctx.instance.runtime_properties['policies'] = policies_arn


@decorators.aws_resource(IAMRole, RESOURCE_TYPE,
                         ignore_properties=True)
@decorators.wait_for_delete()
def delete(ctx, iface, resource_config, **_):
    '''Deletes an AWS IAM Role'''

    # If the current role associated
    if 'policies' in ctx.instance.runtime_properties:
        for policy in ctx.instance.runtime_properties['policies']:
            payload = dict()
            payload['PolicyArn'] = policy
            iface.detach_policy(payload)

    iface.delete(resource_config)


@decorators.aws_relationship(IAMRole, RESOURCE_TYPE)
def attach_to(ctx, iface, resource_config, **_):
    '''Attaches an IAM Role to something else'''
    if utils.is_node_type(ctx.target.node,
                          'cloudify.nodes.aws.iam.Policy'):
        resource_config['PolicyArn'] = utils.get_resource_arn(
            node=ctx.target.node,
            instance=ctx.target.instance,
            raise_on_missing=True)
        iface.attach_policy(resource_config)


@decorators.aws_relationship(IAMRole, RESOURCE_TYPE)
def detach_from(ctx, iface, resource_config, **_):
    '''Detaches an IAM Role from something else'''
    if utils.is_node_type(ctx.target.node,
                          'cloudify.nodes.aws.iam.Policy'):
        resource_config['PolicyArn'] = utils.get_resource_arn(
            node=ctx.target.node,
            instance=ctx.target.instance,
            raise_on_missing=True)
        iface.detach_policy(resource_config)

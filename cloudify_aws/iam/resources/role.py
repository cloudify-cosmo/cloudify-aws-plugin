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

from botocore.exceptions import ClientError
from cloudify.exceptions import NonRecoverableError

# Cloudify
from cloudify_aws.iam import IAMBase
from cloudify_aws.common import decorators, utils

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
        if not self.resource_id:
            return
        params = {'RoleName': self.resource_id}
        try:
            result = self.make_client_call('get_role', params)
        except NonRecoverableError as e:
            if 'An error occurred (NoSuchEntity)' in str(e):
                return None
            else:
                raise e
        if 'Role' in result:
            return result['Role']

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
        try:
            self.client.delete_role(**params)
        except ClientError as e:
            if 'DeleteConflict' in str(e):
                instance_profiles_list = self.client.list_instance_profiles()
                instance_profiles = instance_profiles_list.get(
                    'InstanceProfiles')
                for instance_profile in instance_profiles:
                    for role in instance_profile.get('Roles', []):
                        if self.resource_id in role.get('RoleName'):
                            pm = {
                                'InstanceProfileName': instance_profile.get(
                                       'InstanceProfileName'),
                                'RoleName': role.get('RoleName')
                            }
                            self.client.remove_role_from_instance_profile(**pm)
        self._properties = {}

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


def validate_polices(policies, policies_from_properties):
    for policy in policies_from_properties:
        if not isinstance(policy, dict) or 'PolicyArn' not in policy:
            raise NonRecoverableError(
                'The policy_arns property contains invalid value. It must be '
                'a list of dicts, and each dict must contain one key, '
                '"PolicyArn".')
        else:
            policies.append(policy)
    return policies


@decorators.aws_resource(IAMRole, RESOURCE_TYPE, waits_for_status=False)
@decorators.aws_params(RESOURCE_NAME)
def precreate(ctx, iface, **_):
    ctx.instance.runtime_properties['account_id'] = iface.account_id


@decorators.aws_resource(IAMRole, RESOURCE_TYPE, waits_for_status=False)
@decorators.aws_params(RESOURCE_NAME)
def create(ctx, iface, resource_config, params, **_):
    '''Creates an AWS IAM Role'''

    if 'AssumeRolePolicyDocument' in params and \
            isinstance(params['AssumeRolePolicyDocument'], dict):
        params['AssumeRolePolicyDocument'] = \
            json_dumps(params['AssumeRolePolicyDocument'])

    policies = validate_polices(_.get('modify_role_attribute_args', []),
                                ctx.node.properties.get('policy_arns', []))

    # Actually create the resource
    create_response = utils.handle_response(
        iface, 'create', params,
        raise_substrings='EntityAlreadyExists',
        raisable=NonRecoverableError)
    resource_id = create_response['Role']['RoleName']
    iface.update_resource_id(resource_id)
    utils.update_resource_id(ctx.instance, resource_id)
    utils.update_resource_arn(
        ctx.instance, create_response['Role']['Arn'])
    create_response.pop('ResponseMetadata', None)
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response).to_dict()

    # attach policy role
    policies_arn = []
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
                         ignore_properties=True,
                         waits_for_status=False)
def delete(ctx, iface, resource_config, **_):
    '''Deletes an AWS IAM Role'''

    # If the current role associated
    if 'policies' in ctx.instance.runtime_properties:
        for policy in ctx.instance.runtime_properties['policies']:
            payload = dict()
            payload['PolicyArn'] = policy
            iface.detach_policy(payload)
    utils.handle_response(iface, 'delete', resource_config, ['NoSuchEntity'])


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
        utils.handle_response(
            iface, 'detach_policy', resource_config, ['NoSuchEntity'])

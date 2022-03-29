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
    IAM.RolePolicy
    ~~~~~~~~~~
    AWS IAM Role Policy interface
'''
from json import dumps as json_dumps

# Cloudify
from cloudify_aws.common import decorators, utils, constants as CTS
from cloudify_aws.iam import IAMBase

RESOURCE_TYPE = 'IAM Role Policy'
ROLE_NAME = 'RoleName'
ROLE_TYPE = 'cloudify.nodes.aws.iam.Role'
RESOURCE_NAME = 'PolicyName'


class IAMRolePolicy(IAMBase):
    '''
        AWS IAM Role Policy interface
    '''
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        IAMBase.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        '''Gets the properties of an external resource'''
        return None

    @property
    def status(self):
        '''Gets the status of an external resource'''
        return None

    def create(self, params):
        '''
            Create a new AWS IAM Role Policy.
        '''
        return self.make_client_call('put_role_policy', params)

    def delete(self, params=None):
        '''
            Deletes an existing AWS IAM Role Policy.
        '''
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.delete_role_policy(**params)
        return res


@decorators.aws_resource(IAMRolePolicy, RESOURCE_TYPE, waits_for_status=False)
@decorators.aws_params(RESOURCE_NAME)
def create(ctx, iface, resource_config, params, **_):
    '''Creates an AWS IAM Role Policy'''

    # Add RoleName
    role_name = params.get(ROLE_NAME, '')
    if not role_name:
        params[ROLE_NAME] = \
            utils.find_resource_id_by_type(
                ctx.instance,
                ROLE_TYPE)
    if 'PolicyDocument' in params and \
            isinstance(params['PolicyDocument'], dict):
        params['PolicyDocument'] = json_dumps(params['PolicyDocument'])

    # Actually create the resource
    iface.create(params)


@decorators.aws_resource(IAMRolePolicy,
                         RESOURCE_TYPE,
                         ignore_properties=True,
                         waits_for_status=False)
def delete(ctx, iface, resource_config, **_):
    '''Deletes an AWS IAM Role Policy'''
    # Add RoleName
    role_name = resource_config.get(ROLE_NAME, '')
    if not role_name:
        resource_config[ROLE_NAME] = \
            utils.find_resource_id_by_type(
                ctx.instance,
                ROLE_TYPE)
    # Add Policy Name
    policy_name = resource_config.get(RESOURCE_NAME, '')
    if not policy_name:
        resource_config[RESOURCE_NAME] = \
            ctx.node.properties.get('resource_id') or \
            ctx.instance.runtime_properties[CTS.EXTERNAL_RESOURCE_ID] or \
            ctx.instance.id

    iface.delete(resource_config)

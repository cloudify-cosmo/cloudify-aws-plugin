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
    IAM.InstanceProfile
    ~~~~~~~~
    AWS IAM Profile interface
'''

# Boto
from botocore.exceptions import ClientError

# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.iam import IAMBase

RESOURCE_TYPE = 'IAM Instance Profile'
IAM_ROLE_TYPE = 'cloudify.nodes.aws.iam.Role'
RESOURCE_NAME = 'InstanceProfileName'


class IAMInstanceProfile(IAMBase):
    '''
        AWS IAM Profile interface
    '''
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        IAMBase.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        '''Gets the properties of an external resource'''
        if not self.resource_id:
            return
        try:
            resource = \
                self.client.get_instance_profile(
                    InstanceProfileName=self.resource_id)
        except ClientError:
            pass
        else:
            return None if not resource \
                else resource.get('InstanceProfile', dict())

    @property
    def status(self):
        '''Gets the status of an external resource'''
        return None

    def create(self, params):
        '''
            Create a new AWS IAM Profile.
        '''
        return self.make_client_call('create_instance_profile', params)

    def delete(self, params=None):
        '''
            Deletes an existing AWS IAM Profile.
        '''
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        self.client.delete_instance_profile(**params)

    def add_role_to_instance_profile(self, params=None):
        '''
            Adds a role to an AWS IAM Profile.
        '''
        self.logger.debug('Add role to %s with parameters: %s'
                          % (self.type_name, params))
        self.client.add_role_to_instance_profile(**params)

    def remove_role_from_instance_profile(self, params=None):
        '''
            Remove a role from an AWS IAM Profile.
        '''
        self.logger.debug('Remove role from %s with parameters: %s'
                          % (self.type_name, params))
        self.client.remove_role_from_instance_profile(**params)


@decorators.aws_resource(IAMInstanceProfile,
                         RESOURCE_TYPE,
                         waits_for_status=False)
def create(ctx, iface, resource_config, **_):
    '''Creates an AWS IAM Profile'''
    resource_id = \
        utils.get_resource_id(
            ctx.node,
            ctx.instance,
            resource_config.get(RESOURCE_NAME),
            use_instance_id=True
        ) or iface.resource_id
    resource_config[RESOURCE_NAME] = resource_id
    utils.update_resource_id(ctx.instance, resource_id)

    role_name = resource_config.pop('RoleName', None)

    create_response = iface.create(resource_config)
    resource_id = create_response['InstanceProfile'][RESOURCE_NAME]
    iface.update_resource_id(resource_id)
    utils.update_resource_id(ctx.instance, resource_id)
    utils.update_resource_arn(
        ctx.instance, create_response['InstanceProfile']['Arn'])

    role_name = role_name or \
        utils.find_resource_id_by_type(ctx.instance,
                                       IAM_ROLE_TYPE)
    if role_name:
        add_role_params = {
            RESOURCE_NAME: iface.resource_id,
            'RoleName': role_name
        }
        iface.add_role_to_instance_profile(add_role_params)
        ctx.instance.runtime_properties['RoleName'] = role_name


@decorators.aws_resource(IAMInstanceProfile,
                         RESOURCE_TYPE,
                         waits_for_status=False)
def delete(ctx, iface, resource_config, **_):
    '''Deletes an AWS IAM Profile'''
    instance_profile_name = resource_config.get(RESOURCE_NAME)
    if not instance_profile_name:
        instance_profile_name = iface.resource_id
    resource_config[RESOURCE_NAME] = instance_profile_name

    # Path parameter is not accepted by delete_instance_profile.
    try:
        del resource_config['Path']
    except KeyError:
        pass

    role_name = resource_config.pop('RoleName', None)
    if not role_name:
        role_name = \
            utils.find_resource_id_by_type(ctx.instance,
                                           IAM_ROLE_TYPE)
    if role_name:
        remove_role_params = {
            RESOURCE_NAME: instance_profile_name,
            'RoleName': role_name
        }
        utils.handle_response(
            iface,
            'remove_role_from_instance_profile',
            remove_role_params,
            ['NoSuchEntity'])

    utils.handle_response(iface, 'delete', resource_config, ['NoSuchEntity'])

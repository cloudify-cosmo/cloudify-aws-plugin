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
    IAM.User
    ~~~~~~~~
    AWS IAM User interface
'''
# Boto
from botocore.exceptions import ClientError, ParamValidationError

# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.iam import IAMBase
from cloudify_aws.iam.resources.group import IAMGroup

RESOURCE_TYPE = 'IAM User'
RESOURCE_NAME = 'UserName'


class IAMUser(IAMBase):
    '''
        AWS IAM User interface
    '''
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        IAMBase.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        '''Gets the properties of an external resource'''

        if not self.resource_id:
            return {}
        resource = None
        try:
            resource = self.client.get_user(UserName=self.resource_id)
        except (ParamValidationError, ClientError):
            pass
        if not resource or not resource.get('User', dict()):
            return None
        return resource['User']

    @property
    def status(self):
        '''Gets the status of an external resource'''
        if self.properties:
            return 'available'
        return None

    def create(self, params):
        '''
            Create a new AWS IAM User.
        '''
        return self.make_client_call('create_user', params)

    def delete(self, params=None):
        '''
            Deletes an existing AWS IAM User.
        '''
        params = params or dict()
        params.update(dict(UserName=self.resource_id))
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        self.client.delete_user(**params)

    def create_login_profile(self, params=None):
        '''
            Creates, or updates, a User Login Profile
        '''
        params = params or dict()
        params.update(dict(UserName=self.resource_id))
        # Check if the User already has a Login Profile
        try:
            # This will raise an exception if the User does not
            # have a Login Profile
            self.client.get_login_profile(**dict(UserName=self.resource_id))
            # Update an existing Login Profile
            self.logger.debug('Updating %s Login Profile with parameters: %s'
                              % (self.type_name, params))
            self.client.update_login_profile(**params)
        except ClientError:
            # Create a new Login Profile
            self.logger.debug('Creating %s Login Profile with parameters: %s'
                              % (self.type_name, params))
            self.client.create_login_profile(**params)

    def delete_login_profile(self, params=None):
        '''
            Deletes a User Login Profile
        '''
        params = params or dict()
        params.update(dict(UserName=self.resource_id))
        # Deletes an existing Login Profile
        self.logger.debug('Deleting %s Login Profile with parameters: %s'
                          % (self.type_name, params))
        self.client.delete_login_profile(**params)

    def create_access_key(self, params=None):
        '''
            Creates, or updates, a User Access Key
        '''
        params = params or dict()
        params.update(dict(UserName=self.resource_id))
        # Create a new Access Key
        self.logger.debug('Creating %s Access Key with parameters: %s'
                          % (self.type_name, params))
        res = self.client.create_access_key(**params)['AccessKey']
        self.logger.debug('Response: %s' % res)
        return res

    def delete_access_key(self, params=None):
        '''
            Deletes a User Access Key
        '''
        params = params or dict()
        params.update(dict(UserName=self.resource_id))
        # Deletes an existing Access Key
        self.logger.debug('Deleting %s Access Key with parameters: %s'
                          % (self.type_name, params))
        self.client.delete_access_key(**params)

    def attach_policy(self, params=None):
        '''
            Attaches a Policy to a User
        '''
        params = params or dict()
        params.update(dict(UserName=self.resource_id))
        # Attaches a Policy to a User
        self.logger.debug('Attaching IAM Policy to %s with parameters: %s'
                          % (self.type_name, params))
        self.client.attach_user_policy(**params)

    def detach_policy(self, params=None):
        '''
            Detaches a Policy from a User
        '''
        params = params or dict()
        params.update(dict(UserName=self.resource_id))
        # Detaches a Policy from a User
        self.logger.debug('Detaching IAM Policy from %s with parameters: %s'
                          % (self.type_name, params))
        self.client.detach_user_policy(**params)


@decorators.aws_resource(IAMUser, RESOURCE_TYPE, waits_for_status=False)
@decorators.aws_params(RESOURCE_NAME)
def create(ctx, iface, resource_config, params, **_):
    '''Creates an AWS IAM User'''

    # Actually create the resource
    create_response = iface.create(params)
    resource_id = create_response['User']['UserName']
    iface.update_resource_id(resource_id)
    utils.update_resource_id(ctx.instance, resource_id)
    utils.update_resource_arn(
        ctx.instance, create_response['User']['Arn'])


@decorators.aws_resource(IAMUser, RESOURCE_TYPE,
                         ignore_properties=True)
@decorators.wait_for_delete(status_pending=['available'])
def delete(iface, resource_config, **_):
    '''Deletes an AWS IAM User'''
    iface.update_resource_id(utils.get_resource_id())
    iface.delete(resource_config)


@decorators.aws_relationship(IAMUser, RESOURCE_TYPE)
def attach_to(ctx, iface, resource_config, **_):
    '''Attaches an IAM User to something else'''
    if utils.is_node_type(ctx.target.node,
                          'cloudify.nodes.aws.iam.Group'):
        resource_config['UserName'] = iface.resource_id
        IAMGroup(ctx.target.node, logger=ctx.logger,
                 resource_id=utils.get_resource_id(
                     node=ctx.target.node,
                     instance=ctx.target.instance,
                     raise_on_missing=True)).attach_user(resource_config)
    elif utils.is_node_type(ctx.target.node,
                            'cloudify.nodes.aws.iam.LoginProfile'):
        iface.create_login_profile(
            resource_config or
            ctx.target.instance.runtime_properties.get('resource_config'))
    elif utils.is_node_type(ctx.target.node,
                            'cloudify.nodes.aws.iam.AccessKey'):
        resp = iface.create_access_key(
            resource_config or
            ctx.target.instance.runtime_properties.get('resource_config'))
        utils.update_resource_id(ctx.target.instance, resp['AccessKeyId'])
        ctx.target.instance.runtime_properties['SecretAccessKey'] = \
            resp['SecretAccessKey']
    elif utils.is_node_type(ctx.target.node,
                            'cloudify.nodes.aws.iam.Policy'):
        resource_config['PolicyArn'] = utils.get_resource_arn(
            node=ctx.target.node,
            instance=ctx.target.instance,
            raise_on_missing=True)
        iface.attach_policy(resource_config)


@decorators.aws_relationship(IAMUser, RESOURCE_TYPE)
def detach_from(ctx, iface, resource_config, **_):
    '''Detaches an IAM User from something else'''
    if utils.is_node_type(ctx.target.node,
                          'cloudify.nodes.aws.iam.Group'):
        resource_config['UserName'] = iface.resource_id
        IAMGroup(ctx.target.node, logger=ctx.logger,
                 resource_id=utils.get_resource_id(
                     node=ctx.target.node,
                     instance=ctx.target.instance,
                     raise_on_missing=True)).detach_user(resource_config)
    elif utils.is_node_type(ctx.target.node,
                            'cloudify.nodes.aws.iam.LoginProfile'):
        iface.delete_login_profile(resource_config)
    elif utils.is_node_type(ctx.target.node,
                            'cloudify.nodes.aws.iam.AccessKey'):
        resource_config['AccessKeyId'] = utils.get_resource_id(
            node=ctx.target.node,
            instance=ctx.target.instance,
            raise_on_missing=True)
        iface.delete_access_key(resource_config)
    elif utils.is_node_type(ctx.target.node,
                            'cloudify.nodes.aws.iam.Policy'):
        resource_config['PolicyArn'] = utils.get_resource_arn(
            node=ctx.target.node,
            instance=ctx.target.instance,
            raise_on_missing=True)
        iface.detach_policy(resource_config)

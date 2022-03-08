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
    IAM.Group
    ~~~~~~~~~
    AWS IAM Group interface
'''
# Boto
from botocore.exceptions import ClientError, ParamValidationError

# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.iam import IAMBase

RESOURCE_TYPE = 'IAM Group'
RESOURCE_NAME = 'GroupName'


class IAMGroup(IAMBase):
    '''
        AWS IAM Group interface
    '''
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        IAMBase.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        '''Gets the properties of an external resource'''
        if not self.resource_id:
            return
        resource = None
        try:
            resource = self.client.get_group(GroupName=self.resource_id)
        except (ParamValidationError, ClientError):
            pass
        if not resource or not resource.get('Group', dict()):
            return None
        return resource['Group']

    @property
    def status(self):
        '''Gets the status of an external resource'''
        if self.properties:
            return 'available'
        return None

    def create(self, params):
        '''
            Create a new AWS IAM Group.
        '''
        self.logger.debug('Creating %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.create_group(**params)
        self.logger.debug('Response: %s' % res)
        self.update_resource_id(res['Group'][RESOURCE_NAME])
        return self.resource_id, res['Group']['Arn']

    def delete(self, params=None):
        '''
            Deletes an existing AWS IAM Group.
        '''
        params = params or dict()
        params.update(dict(GroupName=self.resource_id))
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        self.client.delete_group(**params)

    def attach_user(self, params=None):
        '''
            Attaches a User to a Group
        '''
        params = params or dict()
        params.update(dict(GroupName=self.resource_id))
        # Attaches a User to a Group
        self.logger.debug('Attaching IAM User to %s with parameters: %s'
                          % (self.type_name, params))
        self.client.add_user_to_group(**params)

    def detach_user(self, params=None):
        '''
            Detaches a User from a Group
        '''
        params = params or dict()
        params.update(dict(GroupName=self.resource_id))
        # Detaches a User from a Group
        self.logger.debug('Detaching IAM User from %s with parameters: %s'
                          % (self.type_name, params))
        self.client.remove_user_from_group(**params)

    def attach_policy(self, params=None):
        '''
            Attaches a Policy to a Group
        '''
        params = params or dict()
        params.update(dict(GroupName=self.resource_id))
        # Attaches a Policy to a Group
        self.logger.debug('Attaching IAM Policy to %s with parameters: %s'
                          % (self.type_name, params))
        self.client.attach_group_policy(**params)

    def detach_policy(self, params=None):
        '''
            Detaches a Policy from a Group
        '''
        params = params or dict()
        params.update(dict(GroupName=self.resource_id))
        # Detaches a Policy from a Group
        self.logger.debug('Detaching IAM Policy from %s with parameters: %s'
                          % (self.type_name, params))
        self.client.detach_group_policy(**params)


@decorators.aws_resource(IAMGroup,
                         RESOURCE_TYPE,
                         waits_for_status=False)
@decorators.aws_params(RESOURCE_NAME)
def create(ctx, iface, resource_config, params, **_):
    '''Creates an AWS IAM Group'''

    # Actually create the resource
    res_id, res_arn = iface.create(params)
    utils.update_resource_id(ctx.instance, res_id)
    utils.update_resource_arn(ctx.instance, res_arn)


@decorators.aws_resource(IAMGroup, RESOURCE_TYPE,
                         ignore_properties=True)
@decorators.wait_for_delete(status_pending=['available'])
def delete(iface, resource_config, **_):
    '''Deletes an AWS IAM Group'''
    iface.update_resource_id(utils.get_resource_id())
    iface.delete(resource_config)


@decorators.aws_relationship(IAMGroup, RESOURCE_TYPE)
def attach_to(ctx, iface, resource_config, **_):
    '''Attaches an IAM Group to something else'''
    if utils.is_node_type(ctx.target.node,
                          'cloudify.nodes.aws.iam.User'):
        resource_config['UserName'] = utils.get_resource_id(
            node=ctx.target.node,
            instance=ctx.target.instance,
            raise_on_missing=True)
        iface.attach_user(resource_config)
    elif utils.is_node_type(ctx.target.node,
                            'cloudify.nodes.aws.iam.Policy'):
        resource_config['PolicyArn'] = utils.get_resource_arn(
            node=ctx.target.node,
            instance=ctx.target.instance,
            raise_on_missing=True)
        iface.attach_policy(resource_config)


@decorators.aws_relationship(IAMGroup, RESOURCE_TYPE)
def detach_from(ctx, iface, resource_config, **_):
    '''Detaches an IAM Group from something else'''
    if utils.is_node_type(ctx.target.node,
                          'cloudify.nodes.aws.iam.User'):
        resource_config['UserName'] = utils.get_resource_id(
            node=ctx.target.node,
            instance=ctx.target.instance,
            raise_on_missing=True)
        iface.detach_user(resource_config)
    elif utils.is_node_type(ctx.target.node,
                            'cloudify.nodes.aws.iam.Policy'):
        resource_config['PolicyArn'] = utils.get_resource_arn(
            node=ctx.target.node,
            instance=ctx.target.instance,
            raise_on_missing=True)
        iface.detach_policy(resource_config)

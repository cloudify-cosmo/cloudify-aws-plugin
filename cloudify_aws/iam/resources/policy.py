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
    IAM.Policy
    ~~~~~~~~~~
    AWS IAM Policy interface
'''
from json import dumps as json_dumps

# Boto
from botocore.exceptions import ClientError, ParamValidationError

from cloudify.exceptions import NonRecoverableError

# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.iam import IAMBase

RESOURCE_TYPE = 'IAM Policy'
RESOURCE_NAME = 'PolicyName'


class IAMPolicy(IAMBase):
    '''
        AWS IAM Policy interface
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
            resource = self.client.get_policy(PolicyArn=self.resource_id)
        except (ParamValidationError, ClientError):
            pass
        if not resource or not resource.get('Policy', dict()):
            return None
        return resource['Policy']

    @property
    def status(self):
        '''Gets the status of an external resource'''
        if self.properties:
            return 'available'
        return None

    def create(self, params):
        '''
            Create a new AWS IAM Policy.
        '''
        return self.make_client_call('create_policy', params)

    def delete(self, params=None):
        '''
            Deletes an existing AWS IAM Policy.
        '''
        params = params or dict()
        params.update(dict(PolicyArn=self.resource_id))
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        self.client.delete_policy(**params)


@decorators.aws_resource(IAMPolicy,
                         RESOURCE_TYPE,
                         waits_for_status=False)
def create(ctx, iface, resource_config, **_):
    '''Creates an AWS IAM Policy'''
    resource_id = \
        utils.get_resource_id(
            ctx.node,
            ctx.instance,
            resource_config.get(RESOURCE_NAME),
            use_instance_id=True
        ) or iface.resource_id
    resource_config[RESOURCE_NAME] = resource_id
    utils.update_resource_id(ctx.instance, resource_id)

    if 'PolicyDocument' in resource_config and \
            isinstance(resource_config['PolicyDocument'], dict):
        resource_config['PolicyDocument'] = \
            json_dumps(resource_config['PolicyDocument'])
    # Actually create the resource
    create_response = utils.handle_response(
        iface, 'create', resource_config,
        raise_substrings='EntityAlreadyExists',
        raisable=NonRecoverableError)

    resource_id = create_response['Policy']['PolicyName']
    iface.update_resource_id(resource_id)
    utils.update_resource_id(ctx.instance, resource_id)
    utils.update_resource_arn(ctx.instance, create_response['Policy']['Arn'])


@decorators.aws_resource(IAMPolicy,
                         RESOURCE_TYPE,
                         ignore_properties=True)
@decorators.wait_for_delete()
def delete(iface, resource_config, **_):
    '''Deletes an AWS IAM Policy'''
    iface.update_resource_id(utils.get_resource_arn())
    utils.handle_response(iface, 'delete', resource_config, ['NoSuchEntity'])

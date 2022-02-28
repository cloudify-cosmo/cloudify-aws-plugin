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
    IAM.LoginProfile
    ~~~~~~~~~~~~~~~~
    AWS IAM User Login Profile
'''
# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.iam.resources.user import IAMUser

RESOURCE_TYPE = 'IAM User Login Profile'

class IAMUserProfile(IAMUser):
    '''
        AWS IAM User interface
    '''
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        IAMUser.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        '''Gets the properties of an external resource'''
        self.logger.info("yanivn new class properties")
        return True

    @property
    def status(self):
        '''Gets the status of an external resource'''
        self.logger.info("yanivn new class status")
        return 'available'

@decorators.aws_resource(IAMUserProfile,
                         RESOURCE_TYPE,
                         waits_for_status=False)
def configure(ctx, resource_config, **_):
    '''Configures an AWS IAM Login Profile'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = \
        utils.clean_params(resource_config)


@decorators.aws_relationship(IAMUser, RESOURCE_TYPE)
def attach_to(ctx, resource_config, **_):
    '''Attaches an IAM Login Profile to something else'''
    rtprops = ctx.source.instance.runtime_properties
    params = resource_config or rtprops.get('resource_config') or dict()
    if utils.is_node_type(ctx.target.node,
                          'cloudify.nodes.aws.iam.User'):
        IAMUser(
            ctx.target.node, logger=ctx.logger,
            resource_id=utils.get_resource_id(
                node=ctx.target.node,
                instance=ctx.target.instance,
                raise_on_missing=True)).create_login_profile(params)


@decorators.aws_relationship(IAMUser, RESOURCE_TYPE)
def detach_from(ctx, resource_config, **_):
    '''Detaches an IAM Login Profile from something else'''
    if utils.is_node_type(ctx.target.node,
                          'cloudify.nodes.aws.iam.User'):
        IAMUser(
            ctx.target.node, logger=ctx.logger,
            resource_id=utils.get_resource_id(
                node=ctx.target.node,
                instance=ctx.target.instance,
                raise_on_missing=True)).delete_login_profile(resource_config)

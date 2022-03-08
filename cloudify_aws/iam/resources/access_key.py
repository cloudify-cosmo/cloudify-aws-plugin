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
    IAM.AccessKey
    ~~~~~~~~~~~~~
    AWS IAM User Access Key
'''
# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.iam.resources.user import IAMUser

RESOURCE_TYPE = 'IAM User Access Key'


@decorators.aws_resource(IAMUser,
                         RESOURCE_TYPE,
                         waits_for_status=False)
def configure(ctx, resource_config, **_):
    '''Configures an AWS IAM Access Key'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = \
        utils.clean_params(resource_config)
    utils.update_resource_id(
        ctx.instance, utils.get_parent_resource_id(
            ctx.instance,
            'cloudify.relationships.aws.iam.access_key.connected_to'))


@decorators.aws_relationship(IAMUser, RESOURCE_TYPE)
def attach_to(ctx, resource_config, **_):
    '''Attaches an IAM Access Key to something else'''
    rtprops = ctx.source.instance.runtime_properties
    if utils.is_node_type(ctx.target.node,
                          'cloudify.nodes.aws.iam.User'):
        resp = IAMUser(
            ctx.target.node, logger=ctx.logger,
            resource_id=utils.get_resource_id(
                node=ctx.target.node,
                instance=ctx.target.instance,
                raise_on_missing=True)).create_access_key(
            resource_config or rtprops.get('resource_config'))
        utils.update_resource_id(ctx.source.instance, resp['AccessKeyId'])
        ctx.source.instance.runtime_properties['SecretAccessKey'] = \
            resp['SecretAccessKey']


@decorators.aws_relationship(IAMUser, RESOURCE_TYPE)
def detach_from(ctx, resource_config, **_):
    '''Detaches an IAM Access Key from something else'''
    if utils.is_node_type(ctx.target.node,
                          'cloudify.nodes.aws.iam.User'):
        resource_config['AccessKeyId'] = utils.get_resource_id(
            node=ctx.source.node,
            instance=ctx.source.instance,
            raise_on_missing=True)
        IAMUser(ctx.target.node,
                logger=ctx.logger,
                resource_id=utils.get_resource_id(
                    node=ctx.target.node,
                    instance=ctx.target.instance,
                    raise_on_missing=True)).delete_access_key(resource_config)

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
    RDS.Option
    ~~~~~~~~~~
    AWS RDS option interface
'''
# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.rds.resources.option_group import OptionGroup

RESOURCE_TYPE = 'RDS Option'
SECGROUP_TYPE = 'cloudify.nodes.aws.ec2.SecurityGroup'
SECGROUP_TYPE_DEPRECATED = 'cloudify.aws.nodes.SecurityGroup'


@decorators.aws_resource(resource_type=RESOURCE_TYPE)
def configure(ctx, resource_config, **_):
    '''Configures an AWS RDS Option'''
    # Save the parameters
    if resource_config.get('OptionName') and not utils.get_resource_id():
        utils.update_resource_id(ctx.instance, resource_config['OptionName'])
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_relationship(resource_type=RESOURCE_TYPE)
def attach_to(ctx, resource_config, **_):
    '''Attaches an RDS Option to something else'''
    rtprops = ctx.source.instance.runtime_properties
    params = resource_config or rtprops.get('resource_config') or dict()
    if utils.is_node_type(ctx.target.node,
                          'cloudify.nodes.aws.rds.OptionGroup'):
        params['OptionName'] = utils.get_resource_id(
            raise_on_missing=True,
            node=ctx.target.node,
            instance=ctx.target.instance
        )
        OptionGroup(
            ctx.target.node, logger=ctx.logger,
            resource_id=utils.get_resource_id(
                node=ctx.target.node,
                instance=ctx.target.instance,
                raise_on_missing=True)).include_option(params)
    elif utils.is_node_type(ctx.target.node, SECGROUP_TYPE) or \
            utils.is_node_type(ctx.target.node, SECGROUP_TYPE_DEPRECATED):
        security_groups = rtprops.get('resource_config').get(
            'VpcSecurityGroupMemberships', list())
        security_groups.append(
            utils.get_resource_id(
                node=ctx.target.node,
                instance=ctx.target.instance,
                raise_on_missing=True))
        ctx.source.instance.runtime_properties[
            'resource_config']['VpcSecurityGroupMemberships'] = security_groups


@decorators.aws_relationship(resource_type=RESOURCE_TYPE)
def detach_from(ctx, resource_config, **_):
    '''Detaches an RDS Option from something else'''
    rtprops = ctx.source.instance.runtime_properties
    params = resource_config or rtprops.get('resource_config') or dict()
    if utils.is_node_type(ctx.target.node,
                          'cloudify.nodes.aws.rds.OptionGroup'):
        params['OptionName'] = utils.get_resource_id(
            raise_on_missing=True,
            node=ctx.target.node,
            instance=ctx.target.instance
        )
        OptionGroup(
            ctx.target.node, logger=ctx.logger,
            resource_id=utils.get_resource_id(
                node=ctx.target.node,
                instance=ctx.target.instance,
                raise_on_missing=True)).remove_option(params)

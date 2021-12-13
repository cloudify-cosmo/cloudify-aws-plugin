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
    RDS.Parameter
    ~~~~~~~~~~~~~
    AWS RDS parameter interface
'''
# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.rds.resources.parameter_group import ParameterGroup

RESOURCE_TYPE = 'RDS Parameter'


@decorators.aws_resource(resource_type=RESOURCE_TYPE,
                         waits_for_status=False)
def configure(ctx, resource_config, **_):
    '''Configures an AWS RDS Parameter'''
    # Save the parameters
    if resource_config.get('ParameterName') and not utils.get_resource_id():
        utils.update_resource_id(
            ctx.instance,
            resource_config['ParameterName'])
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_relationship(resource_type=RESOURCE_TYPE)
def attach_to(ctx, resource_config, **_):
    '''Attaches an RDS Parameter to something else'''
    rtprops = ctx.source.instance.runtime_properties
    params = resource_config or rtprops.get('resource_config') or dict()
    if utils.is_node_type(ctx.target.node,
                          'cloudify.nodes.aws.rds.ParameterGroup'):
        params['ParameterName'] = utils.get_resource_id(
            node=ctx.target.node,
            instance=ctx.target.instance,
            raise_on_missing=True
        )
        ParameterGroup(
            ctx.target.node, logger=ctx.logger,
            resource_id=utils.get_resource_id(
                node=ctx.target.node,
                instance=ctx.target.instance,
                raise_on_missing=True)).update_parameter(params)


@decorators.aws_relationship(resource_type=RESOURCE_TYPE)
def detach_from(ctx, resource_config, **_):
    '''Detaches an RDS Parameter from something else'''
    pass

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
    EC2.Route
    ~~~~~~~~~~~~~~
    AWS EC2 Route interface
'''
from cloudify.exceptions import NonRecoverableError

# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.ec2 import EC2Base
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID

RESOURCE_TYPE = 'EC2 Route'
ROUTETABLE_ID = 'RouteTableId'
ROUTETABLE_TYPE = 'cloudify.nodes.aws.ec2.RouteTable'
ROUTETABLE_TYPE_DEPRECATED = 'cloudify.aws.nodes.RouteTable'
GATEWAY_ID = 'GatewayId'
NATGATEWAY_ID = 'NatGatewayId'
NATGATEWAY_TYPE = 'cloudify.nodes.aws.ec2.NATGateway'
INTERNETGATEWAY_TYPE = 'cloudify.nodes.aws.ec2.InternetGateway'
INTERNETGATEWAY_TYPE_DEPRECATED = 'cloudify.aws.nodes.InternetGateway'
VPNGATEWAY_TYPE = 'cloudify.nodes.aws.ec2.VPNGateway'
VPNGATEWAY_TYPE_DEPRECATED = 'cloudify.aws.nodes.VPNGateway'
DESTINATION_CIDR_BLOCK = 'DestinationCidrBlock'
DESTINATION_IPV6_CIDR_BLOCK = 'DestinationIpv6CidrBlock'


class EC2Route(EC2Base):
    '''
        EC2 Route interface
    '''
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    def properties(self):
        return {}

    def create(self, params):
        '''
            Create a new AWS EC2 Route.
        '''
        return self.make_client_call('create_route', params)

    def delete(self, params=None):
        '''
            Deletes an existing AWS EC2 Route.
        '''
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.delete_route(**params)
        self.logger.debug('Response: %s' % res)
        return res


@decorators.aws_resource(EC2Route,
                         resource_type=RESOURCE_TYPE,
                         waits_for_status=False)
def prepare(ctx, iface, resource_config, **_):
    '''Prepares an AWS EC2 Route'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2Route,
                         RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    '''Creates an AWS EC2 Route'''

    routetable_id = resource_config.get(ROUTETABLE_ID)
    gateway_id = resource_config.get(GATEWAY_ID)
    natgateway_id = resource_config.get(NATGATEWAY_ID)

    # If this value is missing,
    # it must be filled from a connected Route Table.
    if not routetable_id:
        targ = \
            utils.find_rel_by_node_type(ctx.instance, ROUTETABLE_TYPE) or \
            utils.find_rel_by_node_type(ctx.instance,
                                        ROUTETABLE_TYPE_DEPRECATED)

        # Attempt to use the Route Table ID from parameters.
        # Fallback to connected Route Table.
        resource_config[ROUTETABLE_ID] = \
            routetable_id or \
            targ.target.instance.runtime_properties.get(EXTERNAL_RESOURCE_ID)

    ctx.instance.runtime_properties['routetable_id'] = \
        resource_config[ROUTETABLE_ID]

    if DESTINATION_CIDR_BLOCK in resource_config:
        ctx.instance.runtime_properties[DESTINATION_CIDR_BLOCK] = \
            resource_config[DESTINATION_CIDR_BLOCK]
    elif DESTINATION_IPV6_CIDR_BLOCK in resource_config:
        ctx.instance.runtime_properties[DESTINATION_IPV6_CIDR_BLOCK] = \
            resource_config[DESTINATION_IPV6_CIDR_BLOCK]
    else:
        raise NonRecoverableError(
            'One of the following keyword arguments must be provided for '
            'route: {0} or {1}'.format(
                DESTINATION_CIDR_BLOCK,
                DESTINATION_IPV6_CIDR_BLOCK))

    # If this value is missing,
    # it must be filled from a connected Route Table.
    if not gateway_id:
        targ = \
            utils.find_rel_by_node_type(ctx.instance,
                                        INTERNETGATEWAY_TYPE) or \
            utils.find_rel_by_node_type(ctx.instance,
                                        INTERNETGATEWAY_TYPE_DEPRECATED) or \
            utils.find_rel_by_node_type(ctx.instance, VPNGATEWAY_TYPE) or \
            utils.find_rel_by_node_type(ctx.instance,
                                        VPNGATEWAY_TYPE_DEPRECATED)

        # Attempt to use the Route Table ID from parameters.
        # Fallback to connected Route Table.
        if gateway_id or targ:
            resource_config[GATEWAY_ID] = \
                gateway_id or targ.target.instance.runtime_properties\
                .get(EXTERNAL_RESOURCE_ID)

    if not natgateway_id:
        targ = utils.find_rel_by_node_type(ctx.instance, NATGATEWAY_TYPE)

        # Attempt to use the Route Table ID from parameters.
        # Fallback to connected Route Table.
        if natgateway_id or targ:
            resource_config[NATGATEWAY_ID] = \
                natgateway_id or targ.target.instance.runtime_properties\
                .get(EXTERNAL_RESOURCE_ID)

    # Actually create the resource
    create_response = iface.create(resource_config)
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response).to_dict()


@decorators.aws_resource(EC2Route,
                         RESOURCE_TYPE,
                         ignore_properties=True,
                         waits_for_status=False)
def delete(ctx, iface, resource_config, **_):
    '''Deletes an AWS EC2 Route'''
    routetable_id = resource_config.get(ROUTETABLE_ID)
    if DESTINATION_CIDR_BLOCK in ctx.instance.runtime_properties:
        resource_config[DESTINATION_CIDR_BLOCK] = \
            ctx.instance.runtime_properties[DESTINATION_CIDR_BLOCK]
    elif DESTINATION_IPV6_CIDR_BLOCK in ctx.instance.runtime_properties:
        resource_config[DESTINATION_IPV6_CIDR_BLOCK] = \
            ctx.instance.runtime_properties[DESTINATION_IPV6_CIDR_BLOCK]

    if not routetable_id:
        targ = \
            utils.find_rel_by_node_type(ctx.instance, ROUTETABLE_TYPE) or \
            utils.find_rel_by_node_type(ctx.instance,
                                        ROUTETABLE_TYPE_DEPRECATED)

        # Attempt to use the Route Table ID from parameters.
        # Fallback to connected Route Table.
        resource_config[ROUTETABLE_ID] = \
            routetable_id or \
            targ.target.instance.runtime_properties.get(EXTERNAL_RESOURCE_ID)

    iface.delete(resource_config)

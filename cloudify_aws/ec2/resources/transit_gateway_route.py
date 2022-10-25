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
    EC2.TransitGatewayRoute
    ~~~~~~~~~~~~~~
    AWS EC2 Transit Gateway Route interface
'''

from cloudify.exceptions import NonRecoverableError

# Cloudify
from cloudify_aws.ec2 import EC2Base
from cloudify_aws.common import decorators, utils
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID

from cloudify_aws.ec2.resources.transit_gateway_routetable import TG_TYPE
from cloudify_aws.ec2.resources.transit_gateway import (
    TG_ATTACHMENT,
    TG_ATTACHMENTS,
    TG_ATTACHMENT_ID)

ROUTE = 'Route'
CIDR = 'DestinationCidrBlock'
VPC_TYPE = 'cloudify.nodes.aws.ec2.Vpc'
RESOURCE_TYPE = 'EC2 Transit Gateway Route'
ROUTETABLE_TYPE = 'cloudify.nodes.aws.ec2.TransitGatewayRouteTable'
ROUTETABLES = 'TransitGatewayRouteTables'
ROUTETABLE_ID = 'TransitGatewayRouteTableId'
ROUTETABLE_IDS = 'TransitGatewayRouteTableIds'


class EC2TransitGatewayRoute(EC2Base):
    '''
        EC2 Transit Gateway Route interface
    '''
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE
        self._describe_call = 'describe_transit_gateways'
        self._type_key = ROUTETABLES
        self._id_key = ROUTETABLE_ID
        self._ids_key = ROUTETABLE_IDS

    def create(self, params):
        '''
            Create a new AWS EC2 Transit Gateway Route.
        '''
        return self.make_client_call('create_transit_gateway_route', params)

    def delete(self, params=None):
        '''
            Deletes an existing AWS EC2 Transit Gateway Route.
        '''
        return self.make_client_call('delete_transit_gateway_route', params)


@decorators.aws_resource(EC2TransitGatewayRoute, resource_type=RESOURCE_TYPE)
def prepare(ctx, iface, resource_config, **_):
    '''Prepares an AWS EC2 Transit Gateway Route'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2TransitGatewayRoute, RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    '''Creates an AWS EC2 Transit Gateway Route'''
    routetable_id = get_routetable_id(ctx.instance, resource_config)
    attachment_id = resource_config.get(TG_ATTACHMENT_ID) or get_attachment_id(
        ctx.instance)
    request = {
        CIDR: resource_config.get(CIDR),
        ROUTETABLE_ID: routetable_id,
        TG_ATTACHMENT_ID: attachment_id
    }
    create_response = utils.raise_on_substring(
        iface,
        'create',
        request,
        'IncorrectState'
    )
    if ROUTE in create_response:
        ctx.instance.runtime_properties['create_response'] = \
            utils.JsonCleanuper(create_response).to_dict()


@decorators.aws_resource(EC2TransitGatewayRoute,
                         RESOURCE_TYPE)
def delete(ctx, iface, resource_config, dry_run=False, **_):
    '''Deletes an AWS EC2 Transit Gateway Route'''
    routetable_id = get_routetable_id(ctx.instance, resource_config)
    request = {
        CIDR: resource_config.get(CIDR),
        ROUTETABLE_ID: routetable_id,
        'DryRun': dry_run
    }
    # Actually create the resource
    response = iface.delete(request)[ROUTE]
    ctx.instance.runtime_properties['delete_response'] = \
        utils.JsonCleanuper(response).to_dict()


def get_routetable_id(ctx_instance, params):
    routetable_id = params.get(ROUTETABLE_ID)
    if not routetable_id:
        targ = utils.find_rel_by_node_type(ctx_instance, ROUTETABLE_TYPE)
        if not targ:
            raise NonRecoverableError(
                'A route node type must provide a '
                'relationship to a node of type {t}.'.format(
                    t=ROUTETABLE_TYPE))
        routetable_id = targ.target.instance.runtime_properties.get(
            EXTERNAL_RESOURCE_ID)
    return routetable_id


def get_vpc_id(ctx_instance):
    targ = utils.find_rel_by_node_type(ctx_instance, VPC_TYPE)
    return targ.target.instance.runtime_properties.get(EXTERNAL_RESOURCE_ID)


def get_attachment_id(ctx_instance):
    vpc_id = get_vpc_id(ctx_instance)
    if not vpc_id:
        raise NonRecoverableError(
            'A route node type must provide a '
            'relationship to a node of type {t}.'.format(t=VPC_TYPE))
    table = utils.find_rel_by_node_type(ctx_instance, ROUTETABLE_TYPE)
    tg = utils.find_rel_by_node_type(table.target.instance, TG_TYPE)
    if not tg:
        raise NonRecoverableError(
            'A Transit Gateway Routetable must provide '
            'a relationship to a Transit Gateway.')
    attachments = tg.target.instance.runtime_properties.get(
        TG_ATTACHMENTS)
    if not attachments:
        raise NonRecoverableError(
            'A Transit Gateway must provide '
            'provide an attachment to a VPC.')
    attachment = attachments.get(vpc_id, {})
    if TG_ATTACHMENT not in attachment:
        raise NonRecoverableError(
            'No Attachments found in {a}'.format(a=attachments))
    return attachment[TG_ATTACHMENT].get(TG_ATTACHMENT_ID)

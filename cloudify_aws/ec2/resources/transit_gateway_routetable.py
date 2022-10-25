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
    EC2.TransitGatewayRouteTable
    ~~~~~~~~~~~~~~
    AWS EC2 Transit Gateway Route Table interface
'''

# Boto
from botocore.exceptions import ClientError
from cloudify.exceptions import NonRecoverableError, OperationRetry
# Cloudify
from cloudify_aws.ec2 import EC2Base
from cloudify_aws.common import decorators, utils
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID
from cloudify_aws.ec2.resources.transit_gateway import (
    TG_ID,
    TG_ATTACHMENT,
    TG_ATTACHMENTS,
    TG_ATTACHMENT_ID)

ASSOCIATION = 'Association'
ASSOCIATIONS = 'associations'
ROUTETABLE = 'TransitGatewayRouteTable'
VPC_TYPE = 'cloudify.nodes.aws.ec2.Vpc'
ROUTETABLES = 'TransitGatewayRouteTables'
ROUTETABLE_ID = 'TransitGatewayRouteTableId'
ROUTETABLE_IDS = 'TransitGatewayRouteTableIds'
TG_TYPE = 'cloudify.nodes.aws.ec2.TransitGateway'
RESOURCE_TYPE = 'EC2 Transit Gateway Route Table'


class EC2TransitGatewayRouteTable(EC2Base):
    '''
        EC2 Transit Gateway Route Table interface
    '''
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE
        self._describe_call = 'describe_transit_gateways'
        self._type_key = ROUTETABLES
        self._id_key = ROUTETABLE_ID
        self._ids_key = ROUTETABLE_IDS

    @property
    def properties(self):
        '''Gets the properties of an external resource'''
        if not self.resource_id:
            return {}
        params = {ROUTETABLE_IDS: [self.resource_id]}
        resources = self.describe(params)
        return None if not resources else resources.get(ROUTETABLES)[0]

    @property
    def status(self):
        '''Gets the status of an external resource'''
        props = self.properties
        if not props:
            return None
        return props['State']

    def describe(self, params):
        try:
            return self.make_client_call(
                'describe_transit_gateway_route_tables', params)
        except NonRecoverableError:
            return {}

    def create(self, params):
        '''
            Create a new AWS EC2 Transit Gateway Route Table.
        '''
        return self.make_client_call(
            'create_transit_gateway_route_table', params)

    def delete(self, params=None):
        '''
            Deletes an existing AWS EC2 Transit Gateway Route Table.
        '''
        return self.make_client_call(
            'delete_transit_gateway_route_table', params)

    def attach(self, params):
        '''
            Attach an AWS EC2 Transit Gateway Route Table to a Subnet.
        '''
        return self.make_client_call(
            'associate_transit_gateway_route_table', params)

    def detach(self, params):
        '''
            Detach an AWS EC2 Transit Gateway Route Table from a Subnet.
        '''
        return self.make_client_call(
            'disassociate_transit_gateway_route_table', params)


@decorators.aws_resource(
    EC2TransitGatewayRouteTable,
    resource_type=RESOURCE_TYPE,
    waits_for_status=False)
def prepare(ctx, iface, resource_config, **_):
    '''Prepares an AWS EC2 Route Table'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(
    EC2TransitGatewayRouteTable, RESOURCE_TYPE)
@decorators.tag_resources
@decorators.wait_for_status(status_good=['available'],
                            status_pending=['pending'])
def create(ctx, iface, resource_config, **_):
    '''Creates an AWS EC2 Transit Gateway Route Table'''
    transit_gateway_id = resource_config.get(TG_ID) or get_transit_gateway_id(
        ctx.instance)
    resource_config[TG_ID] = transit_gateway_id

    # Actually create the resource
    create_response = iface.create(resource_config)[ROUTETABLE]
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response).to_dict()
    transit_gateway_route_table_id = create_response.get(ROUTETABLE_ID)
    iface.update_resource_id(transit_gateway_route_table_id)
    utils.update_resource_id(ctx.instance,
                             transit_gateway_route_table_id)


@decorators.aws_resource(EC2TransitGatewayRouteTable, RESOURCE_TYPE,
                         ignore_properties=True)
@decorators.untag_resources
def delete(ctx, iface, resource_config, dry_run=False, **_):
    '''Deletes an AWS EC2 Transit Gateway Route Table'''
    resource_config['DryRun'] = dry_run
    resource_config[ROUTETABLE_ID] = iface.resource_id
    iface.delete(resource_config)


@decorators.aws_resource(EC2TransitGatewayRouteTable, RESOURCE_TYPE)
def attach(ctx, iface, resource_config, **_):
    '''Attaches an AWS EC2 Transit Gateway Route Table to a Transit Gateway'''
    route_table_id = resource_config.get(ROUTETABLE_ID, iface.resource_id)
    transit_gateway_attachment_id = get_attachment_id_from_runtime_props(ctx)
    gw = utils.find_rel_by_node_type(ctx.instance, TG_TYPE)
    if not gw:
        raise NonRecoverableError(
            'Transit Gateway Route Table must provide a '
            'relationship to a Transit Gateway.')
    transit_gateway_id = gw.target.instance.runtime_properties.get(
        EXTERNAL_RESOURCE_ID)
    result = iface.describe(
        {
            'Filters': [
                {
                    'Name': 'transit-gateway-id',
                    'Values': [transit_gateway_id]
                },
                {
                    'Name': 'transit-gateway-route-table-id',
                    'Values': [route_table_id]
                }
            ]
        }
    )
    if ROUTETABLES in result and len(result[ROUTETABLES]) == 1:
        if result[ROUTETABLES][0][ROUTETABLE_ID] == route_table_id:
            return
        detach_request = {
            ROUTETABLE_ID: result[ROUTETABLES][ROUTETABLE_ID],
            TG_ATTACHMENT_ID: transit_gateway_attachment_id
        }
        iface.detach(detach_request)
        raise OperationRetry(
            'Removing existing route table association: {r}'.format(
                r=result))
    request = {
        ROUTETABLE_ID: route_table_id,
        TG_ATTACHMENT_ID: transit_gateway_attachment_id
    }
    try:
        iface.attach(request)
    except (ClientError, NonRecoverableError) as e:
        raise OperationRetry(e)


@decorators.aws_resource(EC2TransitGatewayRouteTable, RESOURCE_TYPE,
                         ignore_properties=True)
def detach(ctx, iface, resource_config, **_):
    '''Detach an AWS EC2 Transit Gateway Route Table from a Transit Gateway'''
    route_table_id = resource_config.get(ROUTETABLE_ID, iface.resource_id)
    transit_gateway_attachment_id = get_attachment_id_from_runtime_props(ctx)
    request = {
        ROUTETABLE_ID: route_table_id,
        TG_ATTACHMENT_ID: transit_gateway_attachment_id
    }
    return utils.exit_on_substring(iface,
                                   'detach',
                                   request,
                                   'InvalidAssociation.NotFound')


def get_attachment_id_from_runtime_props(ctx):
    vpc = utils.find_rel_by_node_type(ctx.instance, VPC_TYPE)
    if not vpc:
        return
    vpc_id = vpc.target.instance.runtime_properties.get(EXTERNAL_RESOURCE_ID)
    gw = utils.find_rel_by_node_type(ctx.instance, TG_TYPE)
    if not gw:
        raise NonRecoverableError(
            'Transit Gateway Route Table must provide a '
            'relationship to a Transit Gateway.')
    if TG_ATTACHMENTS in gw.target.instance.runtime_properties:
        if vpc_id in gw.target.instance.runtime_properties[
                TG_ATTACHMENTS]:
            return gw.target.instance.runtime_properties[
                TG_ATTACHMENTS][vpc_id][TG_ATTACHMENT][TG_ATTACHMENT_ID]


def get_transit_gateway_id(ctx_instance):
    gw = utils.find_rel_by_node_type(ctx_instance, TG_TYPE)
    if not gw:
        raise NonRecoverableError(
            'Transit Gateway Route Table must provide a '
            'relationship to a Transit Gateway.')
    return gw.target.instance.runtime_properties.get(
        EXTERNAL_RESOURCE_ID)

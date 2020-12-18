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
    EC2.RouteTable
    ~~~~~~~~~~~~~~
    AWS EC2 Route Table interface
'''
# Boto
from botocore.exceptions import ClientError

# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.ec2 import EC2Base
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID

RESOURCE_TYPE = 'EC2 Route Table'
ROUTETABLE = 'RouteTable'
ROUTETABLES = 'RouteTables'
ROUTETABLE_ID = 'RouteTableId'
ROUTETABLE_IDS = 'RouteTableIds'
CIDR_BLOCK = 'CidrBlock'
VPC_ID = 'VpcId'
VPC_TYPE = 'cloudify.nodes.aws.ec2.Vpc'
VPC_TYPE_DEPRECATED = 'cloudify.aws.nodes.VPC'
SUBNET_ID = 'SubnetId'
SUBNET_TYPE = 'cloudify.nodes.aws.ec2.Subnet'
SUBNET_TYPE_DEPRECATED = 'cloudify.aws.nodes.Subnet'
ASSOCIATION_ID = 'AssociationId'


class EC2RouteTable(EC2Base):
    '''
        EC2 Route Table interface
    '''
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        '''Gets the properties of an external resource'''
        params = {ROUTETABLE_IDS: [self.resource_id]}
        try:
            resources = \
                self.client.describe_route_tables(**params)
        except ClientError:
            pass
        else:
            return None if not resources else resources.get(ROUTETABLES)[0]

    def create(self, params):
        '''
            Create a new AWS EC2 Route Table.
        '''
        return self.make_client_call('create_route_table', params)

    def delete(self, params=None):
        '''
            Deletes an existing AWS EC2 Route Table.
        '''
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.delete_route_table(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def attach(self, params):
        '''
            Attach an AWS EC2 Route Table to a Subnet.
        '''
        self.logger.debug('Attaching %s with: %s'
                          % (self.type_name, params.get(SUBNET_ID, None)))
        res = self.client.associate_route_table(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def detach(self, params):
        '''
            Detach an AWS EC2 Route Table from a Subnet.
        '''
        self.logger.debug('Detaching %s from: %s'
                          % (self.type_name, params.get(SUBNET_ID, None)))
        res = self.client.disassociate_route_table(**params)
        self.logger.debug('Response: %s' % res)
        return res


@decorators.aws_resource(EC2RouteTable, resource_type=RESOURCE_TYPE)
def prepare(ctx, iface, resource_config, **_):
    '''Prepares an AWS EC2 Route Table'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2RouteTable, RESOURCE_TYPE)
@decorators.tag_resources
def create(ctx, iface, resource_config, **_):
    '''Creates an AWS EC2 Route Table'''
    params = dict() if not resource_config else resource_config.copy()

    vpc_id = params.get(VPC_ID)

    # If either of these values is missing,
    # they must be filled from a connected VPC.
    if not vpc_id:
        targ = \
            utils.find_rel_by_node_type(ctx.instance, VPC_TYPE) or \
            utils.find_rel_by_node_type(ctx.instance, VPC_TYPE_DEPRECATED)

        # Attempt to use the VPC ID from parameters.
        # Fallback to connected VPC.
        params[VPC_ID] = vpc_id or targ.target\
            .instance.runtime_properties.get(EXTERNAL_RESOURCE_ID)

    # Actually create the resource
    create_response = iface.create(params)[ROUTETABLE]
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response).to_dict()
    route_table_id = create_response.get(ROUTETABLE_ID)
    iface.update_resource_id(route_table_id)
    utils.update_resource_id(ctx.instance,
                             route_table_id)


@decorators.aws_resource(EC2RouteTable, RESOURCE_TYPE,
                         ignore_properties=True)
@decorators.untag_resources
def delete(ctx, iface, resource_config, **_):
    '''Deletes an AWS EC2 Route Table'''
    params = \
        dict() if not resource_config else resource_config.copy()

    route_table_id = params.get(ROUTETABLE_ID)
    if not route_table_id:
        params[ROUTETABLE_ID] = \
            iface.resource_id or \
            ctx.instance.runtime_properties.get(EXTERNAL_RESOURCE_ID)

    iface.delete(params)


@decorators.aws_resource(EC2RouteTable, RESOURCE_TYPE)
def attach(ctx, iface, resource_config, **_):
    '''Attaches an AWS EC2 Route Table to a Subnet'''
    params = dict() if not resource_config else resource_config.copy()

    route_table_id = params.get(ROUTETABLE_ID)
    if not route_table_id:
        route_table_id = iface.resource_id

    params.update({ROUTETABLE_ID: route_table_id})

    targets = \
        utils.find_rels_by_node_type(ctx.instance, SUBNET_TYPE) or \
        utils.find_rels_by_node_type(ctx.instance, SUBNET_TYPE_DEPRECATED)
    association_id_list = []
    for target in targets:
        params[SUBNET_ID] = \
            target.target.instance.runtime_properties.get(EXTERNAL_RESOURCE_ID)
        association_id = iface.attach(params).get(ASSOCIATION_ID)
        association_id_list.append(association_id)
    ctx.instance.runtime_properties['association_ids'] = \
        association_id_list


@decorators.aws_resource(EC2RouteTable, RESOURCE_TYPE,
                         ignore_properties=True)
def detach(ctx, iface, resource_config, **_):
    '''Detach an AWS EC2 Route Table from a Subnet'''
    params = dict() if not resource_config else resource_config.copy()

    association_ids = ctx.instance.runtime_properties['association_ids']
    if association_ids and isinstance(association_ids, list):
        for association_id in association_ids:
            params.update({ASSOCIATION_ID: association_id})
            iface.detach(params)

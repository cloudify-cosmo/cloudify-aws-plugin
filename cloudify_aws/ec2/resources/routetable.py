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
from time import sleep

# Boto
from botocore.exceptions import ClientError
from cloudify.exceptions import OperationRetry

# Cloudify
from cloudify_aws.ec2 import EC2Base
from cloudify_aws.common import decorators, utils
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
        self._describe_call = 'describe_route_tables'
        self._type_key = ROUTETABLES
        self._ids_key = ROUTETABLE_IDS
        self._id_key = ROUTETABLE_ID

    @property
    def status(self):
        '''Gets the status of an external resource'''
        self.logger.error(
            'Improvements are needed to Route Table status property.')
        try:
            return \
                self.properties['Associations'][0]['AssociationState']['State']
        except (IndexError, KeyError, TypeError):
            return None

    @property
    def check_status(self):
        if self.status in ['associated']:
            return 'OK'
        return 'NOT OK'

    def create(self, params):
        '''
            Create a new AWS EC2 Route Table.
        '''
        return self.make_client_call('create_route_table', params)

    def delete(self, params=None, recurse=True):
        '''
            Deletes an existing AWS EC2 Route Table.
        '''
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        try:
            res = self.client.delete_route_table(**params)
        except ClientError:
            if not recurse:
                raise
            self.logger.error(
                'Failed to delete route table because of dependencies. '
                'Attempting cleanup.')
            for a in self.properties.get('Associations', []):
                if not a.get('Main'):
                    self.logger.info('Disassociating: {}'.format(a))
                    self.client.disassociate_route_table(
                        AssociationId=a.get('RouteTableAssociationId'))
            res = self.delete(params, False)
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

    vpc_id = resource_config.get(VPC_ID)

    # If either of these values is missing,
    # they must be filled from a connected VPC.
    if not vpc_id:
        targ = \
            utils.find_rel_by_node_type(ctx.instance, VPC_TYPE) or \
            utils.find_rel_by_node_type(ctx.instance, VPC_TYPE_DEPRECATED)

        # Attempt to use the VPC ID from parameters.
        # Fallback to connected VPC.
        resource_config[VPC_ID] = vpc_id or targ.target\
            .instance.runtime_properties.get(EXTERNAL_RESOURCE_ID)

    # Actually create the resource
    create_response = iface.create(resource_config)[ROUTETABLE]
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response).to_dict()
    route_table_id = create_response.get(ROUTETABLE_ID)
    iface.update_resource_id(route_table_id)
    utils.update_resource_id(ctx.instance,
                             route_table_id)
    max_wait = 5
    counter = 0
    while not iface.properties:
        ctx.logger.debug('Waiting for Route Table to be created.')
        sleep(5)
        if max_wait > counter:
            break
        counter += 1


@decorators.aws_resource(EC2RouteTable, RESOURCE_TYPE,
                         ignore_properties=True)
@decorators.untag_resources
def delete(ctx, iface, resource_config, dry_run=False, **_):
    '''Deletes an AWS EC2 Route Table'''
    resource_config['DryRun'] = dry_run
    route_table_id = resource_config.get(ROUTETABLE_ID)
    if not route_table_id:
        resource_config[ROUTETABLE_ID] = \
            iface.resource_id or \
            ctx.instance.runtime_properties.get(EXTERNAL_RESOURCE_ID)

    if iface.properties:
        iface.delete(resource_config)
        raise OperationRetry('Waiting for route table to delete.')


@decorators.aws_resource(EC2RouteTable, RESOURCE_TYPE)
def attach(ctx, iface, resource_config, **_):
    '''Attaches an AWS EC2 Route Table to a Subnet'''

    route_table_id = resource_config.get(ROUTETABLE_ID)
    if not route_table_id:
        route_table_id = iface.resource_id

    resource_config.update({ROUTETABLE_ID: route_table_id})

    targets = \
        utils.find_rels_by_node_type(ctx.instance, SUBNET_TYPE) or \
        utils.find_rels_by_node_type(ctx.instance, SUBNET_TYPE_DEPRECATED)
    association_id_list = []
    for target in targets:
        resource_config[SUBNET_ID] = \
            target.target.instance.runtime_properties.get(EXTERNAL_RESOURCE_ID)
        association_id = iface.attach(resource_config).get(ASSOCIATION_ID)
        association_id_list.append(association_id)
    ctx.instance.runtime_properties['association_ids'] = \
        association_id_list


@decorators.aws_resource(EC2RouteTable, RESOURCE_TYPE,
                         ignore_properties=True)
def detach(ctx, iface, resource_config, **_):
    '''Detach an AWS EC2 Route Table from a Subnet'''
    association_ids = ctx.instance.runtime_properties['association_ids']
    if association_ids and isinstance(association_ids, list):
        for association_id in association_ids:
            resource_config.update({ASSOCIATION_ID: association_id})
            return utils.exit_on_substring(iface=iface,
                                           method='detach',
                                           request=resource_config,
                                           substrings='InvalidAssociationID'
                                                      '.NotFound')


interface = EC2RouteTable

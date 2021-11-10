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
    EC2.VPC
    ~~~~~~~~~~~~~~
    AWS EC2 VPC interface
'''
# Third Party imports
from time import sleep

from botocore.exceptions import ClientError, ParamValidationError

# Local imports
from cloudify_aws.common import decorators, utils
from cloudify_aws.ec2 import EC2Base

RESOURCE_TYPE = 'EC2 Vpc'
VPC = 'Vpc'
VPCS = 'Vpcs'
VPC_ID = 'VpcId'
VPC_IDS = 'VpcIds'
CIDR_BLOCK = 'CidrBlock'


class EC2Vpc(EC2Base):
    '''
        EC2 Vpc interface
    '''
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        '''Gets the properties of an external resource'''
        params = {VPC_IDS: [self.resource_id]}
        try:
            resources = \
                self.client.describe_vpcs(**params)
        except (ClientError, ParamValidationError):
            pass
        else:
            return None if not resources else resources.get(VPCS, [None])[0]
        return None

    @property
    def status(self):
        '''Gets the status of an external resource'''
        props = self.properties
        if not props:
            return None
        return props['State']

    def create(self, params):
        '''
            Create a new AWS EC2 Vpc.
        '''
        return self.make_client_call('create_vpc', params)

    def delete(self, params=None):
        '''
            Deletes an existing AWS EC2 VPC.
        '''
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.delete_vpc(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def modify_vpc_attribute(self, params):
        '''
            Modify attribute of AWS EC2 VPC.
        '''
        self.logger.debug(
            'Modifying {0} attribute with parameters: {1}'.format(
                self.type_name, params))
        res = self.client.modify_vpc_attribute(**params)
        self.logger.debug('Response: {0}'.format(res))
        return res

    def populate_resource(self, ctx):
        route_tables = self.client.describe_route_tables(
            Filters=[{
                "Name": "vpc-id",
                "Values": [self.resource_id]
            }])['RouteTables']
        main_route_table_id = None
        for route_table in route_tables:
            for association in route_table.get('Associations', []):
                if association.get('Main'):
                    main_route_table_id = route_table['RouteTableId']
        ctx.instance.runtime_properties['main_route_table_id'] = \
            main_route_table_id


@decorators.aws_resource(EC2Vpc, resource_type=RESOURCE_TYPE)
def prepare(ctx, iface, resource_config, **_):
    '''Prepares an AWS EC2 Vpc'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2Vpc, RESOURCE_TYPE)
@decorators.wait_for_status(status_good=['available'],
                            status_pending=['pending'])
@decorators.tag_resources
def create(ctx, iface, resource_config, **_):
    '''Creates an AWS EC2 Vpc'''
    params = utils.clean_params(
        dict() if not resource_config else resource_config.copy())

    # Actually create the resource
    create_response = iface.create(params)[VPC]
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response).to_dict()

    vpc_id = create_response.get(VPC_ID, '')
    iface.update_resource_id(vpc_id)
    utils.update_resource_id(
        ctx.instance, vpc_id)

    modify_vpc_attribute_args = \
        _.get('modify_vpc_attribute_args')
    if modify_vpc_attribute_args:
        modify_vpc_attribute_args[VPC_ID] = \
            vpc_id
        iface.modify_vpc_attribute(
            modify_vpc_attribute_args)
    max_wait = 5
    counter = 0
    while not iface.properties:
        ctx.logger.debug('Waiting for VPC to be created.')
        sleep(5)
        if max_wait > counter:
            break
        counter += 1


@decorators.aws_resource(EC2Vpc, RESOURCE_TYPE,
                         ignore_properties=True)
@decorators.untag_resources
def delete(iface, resource_config, **_):
    '''Deletes an AWS EC2 Vpc'''

    params = dict() if not resource_config else resource_config.copy()

    if VPC_ID not in params:
        params.update({VPC_ID: iface.resource_id})

    iface.delete(params)


@decorators.aws_resource(EC2Vpc, RESOURCE_TYPE)
def modify_vpc_attribute(ctx, iface, resource_config, **_):
    params = \
        dict() if not resource_config else resource_config.copy()
    instance_id = \
        ctx.instance.runtime_properties.get(
            VPC_ID, iface.resource_id)
    params[VPC_ID] = instance_id
    iface.modify_vpc_attribute(params)

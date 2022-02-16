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
import sys
from time import sleep

from cloudify.exceptions import NonRecoverableError
from cloudify.utils import exception_to_error_cause

# Local imports
from cloudify_aws.ec2 import EC2Base
from cloudify_aws.common import decorators, utils

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
        self._describe_call = 'describe_vpcs'
        self._ids_key = VPC_IDS
        self._type_key = VPCS
        self._id_key = VPC_ID

    @property
    def check_status(self):
        if self.status in ['available']:
            return 'OK'
        return 'NOT OK'

    def create(self, params):
        '''
            Create a new AWS EC2 Vpc.
        '''
        result = self.make_client_call('create_vpc', params)
        self.create_response = result[VPC]
        return result

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


@decorators.aws_resource(EC2Vpc,
                         resource_type=RESOURCE_TYPE,
                         waits_for_status=False)
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
    try:
        create_response = iface.create(params)[VPC]
    except NonRecoverableError as ex:
        if 'VpcLimitExceeded' in str(ex):
            _, _, tb = sys.exc_info()
            raise NonRecoverableError(
                "Please add quota vpc or delete unused vpc and try again.",
                causes=[exception_to_error_cause(ex, tb)])
        else:
            raise ex
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


interface = EC2Vpc

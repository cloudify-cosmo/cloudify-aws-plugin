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

from botocore.exceptions import ClientError

from cloudify.utils import exception_to_error_cause
from cloudify.exceptions import NonRecoverableError, OperationRetry

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
        self.create_response = self.make_client_call('create_vpc', params)
        self.update_resource_id(self.create_response[VPC].get(VPC_ID, ''))

    def delete(self, params=None):
        '''
            Deletes an existing AWS EC2 VPC.
        '''
        try:
            return self.make_client_call('delete_vpc', params)
        except NonRecoverableError as e:
            if 'DependencyViolation' in str(e):
                self.cleanup_vpc()

    def cleanup_vpc_internet_gateways(self, vpc=None):
        vpc = vpc or self.resource_id
        igs = self.client.describe_internet_gateways(
            Filters=[{'Name': 'attachment.vpc-id', 'Values': [vpc]}])
        for ig in igs.get('InternetGateways', []):
            self.client.detach_internet_gateway(
                InternetGatewayId=ig.get('InternetGatewayId'), VpcId=vpc)

    def cleanup_vpc_route_tables(self, vpc=None):
        vpc = vpc or self.resource_id
        rts = self.client.describe_route_tables(
            Filters=[{'Name': 'vpc-id', 'Values': [vpc]}])
        for rt in rts.get('RouteTables', []):
            for rta in rt.get('Associations'):
                if not rta.get('Main'):
                    self.client.disassociate_route_table(
                        AssociationId=rta.get('RouteTableAssociationId'))

    def cleanup_vpc_subnets(self, vpc=None):
        vpc = vpc or self.resource_id
        subnets = self.client.describe_subnets(
            Filters=[{'Name': 'vpc-id', 'Values': [vpc]}])
        for subnet in subnets.get('Subnets', []):
            self.client.delete_subnet(SubnetId=subnet.get('SubnetId'))

    def cleanup_vpc_endpoints(self, vpc=None):
        vpc = vpc or self.resource_id
        eps = self.client.describe_vpc_endpoints(
            Filters=[{'Name': 'vpc-id', 'Values': [vpc]}])
        for ep in eps.get('VpcEndpoints', []):
            self.client.delete_vpc_endpoints(
                VpcEndpointIds=ep.get('VpcEndpointId'))

    def cleanup_vpc_security_groups(self, vpc=None):
        vpc = vpc or self.resource_id
        sgs = self.client.describe_security_groups(
            Filters=[{'Name': 'vpc-id', 'Values': [vpc]}])
        for g in sgs.get('SecurityGroups', []):
            if g.get('GroupName') == 'default':
                continue
            self.client.delete_security_group(GroupId=g.get('GroupId'))

    def clean_vpc_peering_connections(self, vpc=None):
        vpc = vpc or self.resource_id
        pcs = self.client.describe_vpc_peering_connections(
            Filters=[{'Name': 'requester-vpc-info.vpc-id', 'Values': [vpc]}])
        for pc in pcs.get('VpcPeeringConnections', []):
            self.client.delete_vpc_peering_connection(
                VpcPeeringConnectionId=pc.get('VpcPeeringConnectionId'))

    def cleanup_vpc_network_acls(self, vpc=None):
        vpc = vpc or self.resource_id
        alcs = self.client.describe_network_acls(
            Filters=[{'Name': 'vpc-id', 'Values': [vpc]}])
        for acl in alcs.get('NetworkAcls', []):
            if acl.get('IsDefault'):
                continue
            self.client.delete_network_acl(
                NetworkAclId=acl.get('NetworkAclId'))

    def cleanup_vpc(self):
        try:
            self.cleanup_vpc_internet_gateways()
            self.cleanup_vpc_route_tables()
            self.cleanup_vpc_endpoints()
            self.cleanup_vpc_security_groups()
            self.clean_vpc_peering_connections()
            self.cleanup_vpc_network_acls()
            self.cleanup_vpc_subnets()
        except (NonRecoverableError, ClientError) as e:
            raise OperationRetry(
                'Failed to delete VPC dependencies: {}.'.format(str(e)))
        raise OperationRetry('Retrying to delete vpc.')

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

    _create(iface, resource_config)
    utils.update_resource_id(ctx.instance, iface.resource_id)
    _modify_attribute(iface, _.get('modify_vpc_attribute_args'))


@decorators.aws_resource(class_decl=EC2Vpc,
                         resource_type=RESOURCE_TYPE,
                         waits_for_status=False)
def poststart(ctx, iface=None, **_):
    utils.update_expected_configuration(iface, ctx.instance.runtime_properties)


@decorators.aws_resource(class_decl=EC2Vpc,
                         resource_type=RESOURCE_TYPE,
                         waits_for_status=False)
def check_drift(ctx, iface=None, **_):
    return utils.check_drift(RESOURCE_TYPE, iface, ctx.logger)


@decorators.aws_resource(EC2Vpc, RESOURCE_TYPE,
                         ignore_properties=True)
@decorators.untag_resources
def delete(iface, resource_config, dry_run=False, **_):
    '''Deletes an AWS EC2 Vpc'''
    resource_config['DryRun'] = dry_run
    if VPC_ID not in resource_config:
        resource_config.update({VPC_ID: iface.resource_id})

    utils.handle_response(iface,
                          'delete',
                          resource_config,
                          raise_substrings='DependencyViolation')


@decorators.aws_resource(EC2Vpc, RESOURCE_TYPE)
def modify_vpc_attribute(ctx, iface, resource_config, **_):
    instance_id = \
        ctx.instance.runtime_properties.get(
            VPC_ID, iface.resource_id)
    resource_config[VPC_ID] = instance_id
    iface.modify_vpc_attribute(resource_config)


def _create(iface, params):
    # Actually create the resource
    try:
        iface.create(params)
    except NonRecoverableError as ex:
        if 'VpcLimitExceeded' in str(ex):
            _, _, tb = sys.exc_info()
            raise NonRecoverableError(
                "Please add quota vpc or delete unused vpc and try again.",
                causes=[exception_to_error_cause(ex, tb)])
        else:
            raise ex


def _modify_attribute(iface,  modify_vpc_attribute_args):
    if modify_vpc_attribute_args:
        modify_vpc_attribute_args[VPC_ID] = iface.resource_id
        iface.modify_vpc_attribute(modify_vpc_attribute_args)
    max_wait = 5
    counter = 0
    while not iface.properties:
        iface.logger.debug('Waiting for VPC to be created.')
        sleep(5)
        if max_wait > counter:
            break
        counter += 1


interface = EC2Vpc

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
    EC2.Subnet
    ~~~~~~~~~~~~~~
    AWS EC2 Subnet interface
'''

from deepdiff import DeepDiff

# Boto
from botocore.exceptions import (
    ClientError,
    CapacityNotAvailableError
)

# Cloudify
from cloudify.exceptions import NonRecoverableError, OperationRetry

from cloudify_aws.ec2 import EC2Base
from cloudify_aws.common import decorators, utils
from cloudify_common_sdk.utils import get_client_config
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID

RESOURCE_TYPE = 'EC2 Subnet'
SUBNET = 'Subnet'
SUBNETS = 'Subnets'
_SUBNETS = 'subnets'
SUBNET_ID = 'SubnetId'
SUBNET_IDS = 'SubnetIds'
CIDR_BLOCK = 'CidrBlock'
IPV6_CIDR_BLOCK = 'Ipv6CidrBlock'
VPC_ID = 'VpcId'
VPC_TYPE = 'cloudify.nodes.aws.ec2.Vpc'
VPC_TYPE_DEPRECATED = 'cloudify.aws.nodes.Vpc'
NO_ID_ERROR = 'Invalid type for parameter SubnetIds'


class EC2Subnet(EC2Base):
    '''
        EC2 Subnet interface
    '''
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE
        self._describe_call = 'describe_subnets'
        self._ids_key = SUBNET_IDS
        self._type_key = SUBNETS
        self._id_key = SUBNET_ID

    @property
    def check_status(self):
        if self.status in ['available']:
            return 'OK'
        return 'NOT OK'

    def compare_configuration(self):
        expected = self.expected_configuration
        remote = self.remote_configuration
        if 'AvailableIpAddressCount' in expected:
            del expected['AvailableIpAddressCount']
        if 'AvailableIpAddressCount' in remote:
            del remote['AvailableIpAddressCount']

        result = DeepDiff(expected, remote)
        delta = utils.JsonCleanuper(result)
        return delta.to_dict()

    def create(self, params):
        '''
            Create a new AWS EC2 Subnet.
        '''
        self.create_response = self.make_client_call('create_subnet', params)
        self.update_resource_id(
            self.create_response[SUBNET].get(SUBNET_ID, ''))

    def delete(self, params=None):
        '''
            Deletes an existing AWS EC2 Subnet.
        '''
        try:
            return self.make_client_call('delete_subnet', params)
        except (ClientError, NonRecoverableError) as e:
            if 'DependencyViolation' in str(e):
                self.cleanup_subnet_enis()
                raise OperationRetry('Retrying to delete subnet: {}'.format(
                    self.resource_id))
            raise

    def modify_subnet_attribute(self, params=None):
        '''
            Modifies an existing AWS EC2 Subnet Attribute.
        '''
        self.logger.debug(
            'Modifying {0} attribute with parameters: {1}'.format(
                self.type_name, params))
        res = self.client.modify_subnet_attribute(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def cleanup_subnet_enis(self, subnet=None):
        subnet = subnet or self.resource_id
        enis = self.client.describe_network_interfaces(
            Filters=[{'Name': 'subnet-id', 'Values': [subnet]}])
        for e in enis.get('NetworkInterfaces', []):
            self.client.delete_network_interface(
                NetworkInterfaceId=e.get('NetworkInterfaceId'))


@decorators.aws_resource(EC2Subnet,
                         resource_type=RESOURCE_TYPE,
                         waits_for_status=False)
def prepare(ctx, resource_config, **_):
    '''Prepares an AWS EC2 Subnet'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2Subnet, RESOURCE_TYPE)
@decorators.wait_for_status(status_good=['available'],
                            status_pending=['pending'])
@decorators.tag_resources
def create(ctx, iface, resource_config, **_):
    '''Creates an AWS EC2 Subnet'''
    resource_config = _create_subnet_params(resource_config, ctx.instance)
    _create(ctx.node, iface, resource_config, ctx.logger)
    utils.update_resource_id(ctx.instance, iface.resource_id)
    _modify_attribute(iface, _.get('modify_subnet_attribute_args'))


@decorators.aws_resource(EC2Subnet, RESOURCE_TYPE,
                         ignore_properties=True)
@decorators.untag_resources
def delete(ctx, iface, resource_config, dry_run=False, **_):
    '''Deletes an AWS EC2 Subnet'''

    if dry_run:
        resource_config['DryRun'] = dry_run
    subnet_id = resource_config.get(SUBNET_ID)

    if not subnet_id:
        resource_config[SUBNET_ID] = \
            iface.resource_id or \
            ctx.instance.runtime_properties.get(EXTERNAL_RESOURCE_ID)

    utils.handle_response(iface,
                          'delete',
                          resource_config,
                          exit_substrings='NotFound',
                          raise_substrings='DependencyViolation')

    ctx.logger.info("handle_response")


@decorators.aws_resource(EC2Subnet, RESOURCE_TYPE)
def modify_subnet_attribute(ctx, iface, resource_config, **_):
    instance_id = \
        ctx.instance.runtime_properties.get(
            SUBNET_ID, iface.resource_id)
    resource_config[SUBNET_ID] = instance_id
    iface.modify_subnet_attribute(resource_config)
    utils.update_expected_configuration(iface, ctx.instance.runtime_properties)


@decorators.aws_relationship(EC2Subnet, RESOURCE_TYPE)
def set_subnet(ctx, iface, resource_config, **_):
    subnet_id = \
        ctx.source.instance.runtime_properties.get(
            EXTERNAL_RESOURCE_ID, iface.resource_id)
    if _SUBNETS not in ctx.target.instance.runtime_properties:
        ctx.target.instance.runtime_properties[_SUBNETS] = []
    ctx.target.instance.runtime_properties[_SUBNETS].append(
        subnet_id)


@decorators.aws_relationship(EC2Subnet, RESOURCE_TYPE)
def unset_subnet(ctx, iface, resource_config, **_):
    subnet_id = \
        ctx.source.instance.runtime_properties.get(
            EXTERNAL_RESOURCE_ID, iface.resource_id)
    if _SUBNETS not in ctx.target.instance.runtime_properties:
        ctx.target.instance.runtime_properties[_SUBNETS] = []
    if subnet_id in ctx.target.instance.runtime_properties[_SUBNETS]:
        ctx.target.instance.runtime_properties[_SUBNETS].remove(subnet_id)


@decorators.aws_resource(class_decl=EC2Subnet,
                         resource_type=RESOURCE_TYPE,
                         waits_for_status=False)
def check_drift(ctx, iface=None, **_):
    return utils.check_drift(RESOURCE_TYPE, iface, ctx.logger)


@decorators.aws_resource(class_decl=EC2Subnet,
                         resource_type=RESOURCE_TYPE,
                         waits_for_status=False)
def poststart(ctx, iface=None, **_):
    utils.update_expected_configuration(iface, ctx.instance.runtime_properties)


def _create(ctx_node, iface, params, logger):
    # Actually create the resource
    try:
        iface.create(params)
    except (NonRecoverableError, CapacityNotAvailableError) as e:
        if isinstance(e, NonRecoverableError) and \
                'InvalidParameterValue' not in str(e):
            raise e
        config_from_utils = get_client_config(
            ctx_node=ctx_node, alternate_key='aws_config')
        region_name = config_from_utils.get('region_name')
        use_available_zones = ctx_node.properties.get(
            'use_available_zones', False)
        if use_available_zones:
            logger.error(
                "The Availability Zone chosen {0} "
                "is not available".format(params['AvailabilityZone']))
            valid_zone = \
                iface.get_available_zone({
                    'Filters': [
                        {'Name': 'region-name', 'Values': [region_name]}
                    ]
                })
            if valid_zone:
                logger.error(
                    "using {0} Availability Zone instead".format(valid_zone))
                params['AvailabilityZone'] = valid_zone
                iface.create(params)
            else:
                raise NonRecoverableError(
                    "no available Availability Zones "
                    "in region {0}".format(region_name))
        else:
            raise NonRecoverableError(
                "The Availability Zone chosen "
                "{0} is not available".format(params['AvailabilityZone']))


def _modify_attribute(iface,  modify_subnet_attribute_args):
    if modify_subnet_attribute_args:
        modify_subnet_attribute_args[SUBNET_ID] = \
            iface.resource_id
        iface.modify_subnet_attribute(
            modify_subnet_attribute_args)


def _create_subnet_params(params, ctx_instance):
    vpc_id = params.get(VPC_ID)
    cidr_block = params.get(CIDR_BLOCK)
    ipv6_cidr_block = params.get(IPV6_CIDR_BLOCK)
    # If either of these values is missing,
    # they must be filled from a connected VPC.
    if not vpc_id or not cidr_block or not ipv6_cidr_block:
        targ = \
            utils.find_rel_by_node_type(
                ctx_instance,
                VPC_TYPE) or utils.find_rel_by_node_type(
                ctx_instance,
                VPC_TYPE_DEPRECATED)

        # Attempt to use the VPC ID from parameters.
        # Fallback to connected VPC.
        params[VPC_ID] = \
            vpc_id or \
            targ.target.instance.runtime_properties.get(
                EXTERNAL_RESOURCE_ID)
        # Attempt to use the CIDR Block from parameters.
        # Fallback to connected VPC.
        params[CIDR_BLOCK] = \
            cidr_block or \
            targ.target.instance.runtime_properties.get(
                'resource_config', {}).get(CIDR_BLOCK)

    # If ipv6 cidr block is provided by user, then we need to make sure that
    # The subnet size must use a /64 prefix length
    if ipv6_cidr_block:
        ipv6_cidr_block = ipv6_cidr_block[:-2] + '64'
        params[IPV6_CIDR_BLOCK] = ipv6_cidr_block
        if 'Ipv6Native' in params and CIDR_BLOCK in params:
            del params[CIDR_BLOCK]
    return params


interface = EC2Subnet

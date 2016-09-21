# #######
# Copyright (c) 2016 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.
'''
    ec2.NetworkInterface
    ~~~~~~~~~~~~~~~~~~~~
    AWS EC2 Network Interface
'''


# Cloudify imports
from ec2 import connection
from cloudify import ctx
from cloudify.decorators import operation
from cloudify.exceptions import NonRecoverableError

import boto.exception


NODE_PROPERTIES_CREATE = [
    'subnet_id', 'private_ip_address',
    'description', 'groups'
]

SUBNET_RELATIONSHIP = \
    'cloudify.aws.relationships.eni_contained_in_subnet'
SUBNET_TYPE = 'cloudify.aws.nodes.Subnet'

SECURITY_GROUP_RELATIONSHIP = \
    'cloudify.aws.relationships.eni_connected_to_security_group'
SECURITY_GROUP_TYPE = 'cloudify.aws.nodes.SecurityGroup'


@operation
def create(**_):
    '''Creates an Elastic Network Interface'''
    ec2_client = connection.EC2ConnectionClient().client()
    # Only get relevant parameters
    params = {
        key: ctx.node.properties[key]
        for key in NODE_PROPERTIES_CREATE
        if key in ctx.node.properties
    }
    # If this is an external resource, set the ID and exit
    if params.get('use_external_resource'):
        _update_runtime_properties(
            _get_network_interface_object(
                ec2_client, params.get('resource_id')))
        return

    # Find a Subnet if an ID wasn't explicitly provided
    if 'subnet_id' not in params:
        subnet = _find_attached_subnet()
        if not subnet:
            raise NonRecoverableError(
                'Network Interface without a Subnet is not allowed')
        params['subnet_id'] = \
            subnet.instance.runtime_properties.get('aws_resource_id')
    # Find attached Security Groups
    params['groups'] = list(set(
        _find_attached_security_groups() + params.get('groups', list())))
    try:
        # Attempt to create the Network Interface
        if ctx.operation.retry_number == 0:
            ctx.logger.debug('create_network_interface({0})'.format(params))
            iface_obj = ec2_client.create_network_interface(**params)
            # Store the AWS resource ID for retry operations
            ctx.instance.runtime_properties['aws_resource_id'] = iface_obj.id
        else:
            # Read the state of the resource
            iface_obj = _get_network_interface_object(
                ec2_client,
                ctx.instance.runtime_properties['aws_resource_id'])
        ctx.logger.debug('response: {0}'.format(vars(iface_obj)))
        # Check if the resource is pending creation, retry if needed
        if iface_obj.status == 'pending':
            return ctx.operation.retry(
                message='Waiting to verify that Network Interface {0} '
                'has been added to your account.'.format(iface_obj.id))
        # Update Source/Dest check if needed
        if ctx.node.properties.get('source_dest_check') is not None:
            ec2_client.modify_network_interface_attribute(
                iface_obj.id,
                'sourceDestCheck',
                ctx.node.properties.get('source_dest_check'))
            # Update the object
            iface_obj = _get_network_interface_object(ec2_client, iface_obj.id)
        # Create tags if needed
        if isinstance(ctx.node.properties.get('tags'), dict):
            ec2_client.create_tags([iface_obj.id], ctx.node.properties['tags'])
            # Update the object
            iface_obj = _get_network_interface_object(ec2_client, iface_obj.id)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as ex:
        raise NonRecoverableError('{0}'.format(str(ex)))
    # Update the runtime properties
    ctx.logger.debug('Updating runtime properties')
    _update_runtime_properties(iface_obj)


@operation
def delete(**_):
    '''Deletes an Elastic Network Interface'''
    if not ctx.node.properties.get('use_external_resource') and \
       ctx.instance.runtime_properties.get('aws_resource_id'):
        ec2_client = connection.EC2ConnectionClient().client()
        try:
            # Delete the Network Interface
            ec2_client.delete_network_interface(
                ctx.instance.runtime_properties.get('aws_resource_id'))
        except (boto.exception.EC2ResponseError,
                boto.exception.BotoServerError) as ex:
            raise NonRecoverableError('{0}'.format(str(ex)))
    ctx.instance.runtime_properties = dict()


@operation
def attach_elastic_ip(**_):
    '''Attaches an Elastic IP to this Elastic Network Interface'''
    ec2_client = connection.EC2ConnectionClient().client()
    # Get the Elastic Netowrk Interface runtime properties
    eni_props = ctx.source.instance.runtime_properties
    # Attempt to associate the EIP with the ENI
    try:
        _get_address_object(
            ec2_client,
            ctx.target.instance.runtime_properties.get('aws_resource_id')
        ).associate(
            network_interface_id=eni_props.get('aws_resource_id'),
            private_ip_address=eni_props.get('aws_private_ip_address'))
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as ex:
        raise NonRecoverableError('{0}'.format(str(ex)))


@operation
def detach_elastic_ip(**_):
    '''Detaches an Elastic IP from this Elastic Network Interface'''
    ec2_client = connection.EC2ConnectionClient().client()
    # Attempt to disassociate the EIP from the ENI
    try:
        _get_address_object(
            ec2_client,
            ctx.target.instance.runtime_properties.get('aws_resource_id')
        ).disassociate()
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as ex:
        raise NonRecoverableError('{0}'.format(str(ex)))


def _find_attached_subnet():
    '''Finds a Subnet attached via relationship'''
    for rel in ctx.instance.relationships:
        if SUBNET_RELATIONSHIP in rel.type_hierarchy and \
           SUBNET_TYPE in rel.target.node.type_hierarchy:
            return rel.target
    return None


def _find_attached_security_groups():
    '''Finds all attached Security Groups via relationships'''
    return [
        x.instance.runtime_properties['aws_resource_id']
        for x in [
            rel.target for rel in ctx.instance.relationships
            if SECURITY_GROUP_RELATIONSHIP in rel.type_hierarchy and
            SECURITY_GROUP_TYPE in rel.target.node.type_hierarchy
        ]
        if 'aws_resource_id' in x.instance.runtime_properties
    ]


def _get_address_object(ec2_client, eip_ip):
    '''Gets an Address (Elastic IP) object from AWS'''
    eip_objs = ec2_client.get_all_addresses(addresses=[eip_ip])
    if not isinstance(eip_objs, list) or len(eip_objs) < 1:
        raise NonRecoverableError(
            'Could not get Address object')
    return eip_objs[0]


def _get_network_interface_object(ec2_client, eni_id):
    '''Gets a NetworkInterface object from AWS'''
    eni_objs = ec2_client.get_all_network_interfaces(
        network_interface_ids=[eni_id])
    if not isinstance(eni_objs, list) or len(eni_objs) < 1:
        raise NonRecoverableError(
            'Could not get NetworkInterface object of {0}'
            .format(eni_id))
    return eni_objs[0]


def _update_runtime_properties(obj):
    '''Updates instance runtime properties post-create'''
    # Convert to a dictionary
    iface = vars(obj)
    ctx.logger.debug('Updating runtime properties')
    ctx.instance.runtime_properties['aws_resource_id'] = \
        iface.get('id')
    ctx.instance.runtime_properties['aws_subnet_id'] = \
        iface.get('subnet_id')
    ctx.instance.runtime_properties['aws_vpc_id'] = \
        iface.get('vpc_id')
    ctx.instance.runtime_properties['aws_owner_id'] = \
        iface.get('owner_id')
    ctx.instance.runtime_properties['aws_mac_address'] = \
        iface.get('mac_address')
    ctx.instance.runtime_properties['aws_private_ip_address'] = \
        iface.get('private_ip_address')
    ctx.instance.runtime_properties['aws_source_dest_check'] = \
        iface.get('source_dest_check')
    ctx.instance.runtime_properties['aws_availability_zone'] = \
        iface.get('availability_zone')
    ctx.instance.runtime_properties['aws_tags'] = \
        iface.get('tags')
    ctx.instance.runtime_properties['aws_security_groups'] = \
        [x.id for x in iface.get('groups', list())]
    ctx.instance.runtime_properties['aws_region'] = \
        iface.get('region').name if iface.get('region') else None
    ctx.logger.debug('Updated runtime properties: {0}'.format(
        ctx.instance.runtime_properties))
    # Copy essential properties to runtime properties for Instance creation
    ctx.instance.runtime_properties['aws_device_index'] = \
        ctx.node.properties.get('device_index')
    ctx.instance.runtime_properties['aws_delete_on_termination'] = \
        ctx.node.properties.get('delete_on_termination')

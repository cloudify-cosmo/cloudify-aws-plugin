########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
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

# Boto Imports
from boto.exception import EC2ResponseError
from boto.exception import BotoServerError

# Cloudify imports
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from cloudify.decorators import operation
from ec2 import connection
from ec2 import utils


@operation
def create(**kwargs):
    """ Creates a Security Group on the account that is
        currently signed in."
    """
    ec2_client = connection.EC2ConnectionClient().client()

    group_name = ctx.node.properties['name']
    description = ctx.node.properties['description']

    ctx.logger.info('Creating Security Group: {0}'.format(group_name))

    try:
        group_object = ec2_client.create_security_group(group_name,
                                                        description)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('(Node: {0}): Error. Failed to create '
                                  'security group: API returned: {1}.'
                                  .format(ctx.instance.id, e))

    ctx.instance.runtime_properties['group_object'] = group_object

    ctx.logger.info('Created Security Group: {0}.'.format(group_name))


@operation
def delete(**kwargs):
    """ Deletes a security group from an account.
    """

    ec2_client = connection.EC2ConnectionClient().client()

    group_name = ctx.node.properties['group_name']

    ctx.logger.info('Deleting Security Group: {0}'.format(group_name))

    try:
        ec2_client.delete_security_group(group_name)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('(Node: {0}): Error. Failed to delete '
                                  'security group: API returned: {1}.'
                                  .format(ctx.instance.id, e))

    ctx.logger.info('Deleted Security Group: {0}.'.format(group_name))


@operation
def authorize_ip(**kwargs):
    """ Adds a rule to a security group using a provided protocol,
        address or address block, and port.
    """

    ec2_client = connection.EC2ConnectionClient().client()

    ip_protocol = ctx.node.properties['ip_protocol']
    from_port = ctx.node.properties['from_port']
    to_port = ctx.node.properties['to_port']
    cidr = ctx.node.properties['cidr']

    ctx.info.logger('Adding Rule to Security Group.')

    if 'group_object' in ctx.source.instance.runtime_properties:
        group = ctx.source.instance.runtime_properties['group_object']
        authorize_ip_by_id(group.id, ip_protocol, from_port, to_port, cidr)
    elif 'group_id' in ctx.node.properties:
        group = ctx.source.instance.runtime_properties['group_id']
        authorize_ip_by_id(ec2_client, group, ip_protocol,
                           from_port, to_port, cidr)
    elif 'group_name' in ctx.node.properties:
        group = ctx.source.instance.runtime_properties['group_name']
        authorize_ip_by_name(ec2_client, group, ip_protocol,
                             from_port, to_port, cidr)
    else:
        raise NonRecoverableError('(Node: {0}): Error. Failed to add rule '
                                  'to security group: No group provided.'
                                  .format(ctx.instance.id))

    ctx.logger.info('Added rule to Security Group: {0}'.format(group))
    ctx.logger.debut('Added rule to group: {0} '
                     'from {1} port: {2} to {1} port {3} '
                     'on cidr {4}.'.format(group, ip_protocol,
                                           from_port, to_port, cidr))


@operation
def deauthorize_ip(**kwargs):
    """ Removes a rule to a security group using a provided protocol,
        address or address block, and port.
    """

    ec2_client = connection.EC2ConnectionClient().client()

    ip_protocol = ctx.node.properties['ip_protocol']
    from_port = ctx.node.properties['from_port']
    to_port = ctx.node.properties['to_port']
    cidr = ctx.node.properties['cidr']

    ctx.info.logger('Adding Rule to Security Group.')

    if 'group_object' in ctx.source.instance.runtime_properties:
        group = ctx.source.instance.runtime_properties['group_object']
        deauthorize_ip_by_id(group.id, ip_protocol, from_port, to_port, cidr)
    elif 'group_id' in ctx.node.properties:
        group = ctx.source.instance.runtime_properties['group_id']
        deauthorize_ip_by_id(ec2_client, group, ip_protocol,
                             from_port, to_port, cidr)
    elif 'group_name' in ctx.node.properties:
        group = ctx.source.instance.runtime_properties['group_name']
        deauthorize_ip_by_name(ec2_client, group, ip_protocol,
                               from_port, to_port, cidr)
    else:
        raise NonRecoverableError('(Node: {0}): Error. Failed to remove rule '
                                  'to security group: No group provided.'
                                  .format(ctx.instance.id))

    ctx.logger.info('Removed rule to Security Group: {0}'.format(group))
    ctx.logger.debut('Removed rule to group: {0} '
                     'from {1} port: {2} to {1} port {3} '
                     'on cidr {4}.'.format(group, ip_protocol,
                                           from_port, to_port, cidr))


@operation
def authorize_group(**kwargs):
    """ Authorizes a security group using a provided ,
        src_security_group_name and src_security_group_owner_id.
    """

    ec2_client = connection.EC2ConnectionClient().client()

    group_name = ctx.node.properties['src_security_group_name']
    owner_id = ctx.node.properties['src_security_group_owner_id']

    ctx.info.logger('Authorizing Security Group.')

    try:
        ec2_client.authorize_security_group(
            src_security_group_name=group_name,
            src_security_group_owner_id=owner_id)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('(Node: {0}): Error. Failed to authorize '
                                  'security group: API returned: {1}.'
                                  .format(ctx.instance.id, e))

    ctx.logger.info('Authorized Security Group.')
    ctx.logger.debut('Authorized access from {0}.'.format(group_name))


@operation
def deauthorize_group(**kwargs):
    """ Deauthorizes a security group using a provided ,
        src_security_group_name and src_security_group_owner_id.
    """

    ec2_client = connection.EC2ConnectionClient().client()

    group_name = ctx.node.properties['src_security_group_name']
    owner_id = ctx.node.properties['src_security_group_owner_id']

    ctx.info.logger('Deauthorizing Security Group.')

    try:
        ec2_client.authorize_security_group(
            src_security_group_name=group_name,
            src_security_group_owner_id=owner_id)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('(Node: {0}): Error. Failed to deauthorize '
                                  'security group: API returned: {1}.'
                                  .format(ctx.instance.id, e))

    ctx.logger.info('Deauthorizes Security Group.')
    ctx.logger.debut('Deauthorizes access from {0}.'.format(group_name))


@operation
def creation_validation(**kwargs):
    """ Validate that the Security Group exists
    """

    if 'group_object' in ctx.source.instance.runtime_properties:
        group = ctx.source.instance.runtime_properties['group_object']
    elif 'group_id' in ctx.node.properties:
        group = ctx.source.instance.runtime_properties['group_id']
    elif 'group_name' in ctx.node.properties:
        group = ctx.source.instance.runtime_properties['group_name']

    if (utils.validate_group(group)):
        ctx.logger.info('Verified that group {0} was created.'.format(group))
    else:
        raise NonRecoverableError('Could not verify that the group {0} '
                                  'was created.'.format(group))


def authorize_ip_by_id(ec2_client, group, protocol, from_port, to_port, cidr):

    try:
        ec2_client.authorize_security_group(group_id=group,
                                            ip_protocol=protocol,
                                            from_port=from_port,
                                            to_port=to_port, cidr_ip=cidr)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('(Node: {0}): Error. Failed to add rule '
                                  'to security group: API returned: {1}.'
                                  .format(ctx.instance.id, e))


def deauthorize_ip_by_id(ec2_client, group, protocol,
                         from_port, to_port, cidr):

    try:
        ec2_client.revoke_security_group(group_id=group,
                                         ip_protocol=protocol,
                                         from_port=from_port,
                                         to_port=to_port, cidr_ip=cidr)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('(Node: {0}): Error. Failed to remoke rule '
                                  'to security group: API returned: {1}.'
                                  .format(ctx.instance.id, e))


def authorize_ip_by_name(ec2_client, group, protocol,
                         from_port, to_port, cidr):

    try:
        ec2_client.authorize_security_group(group_name=group,
                                            ip_protocol=protocol,
                                            from_port=from_port,
                                            to_port=to_port, cidr_ip=cidr)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('(Node: {0}): Error. Failed to add rule '
                                  'to security group: API returned: {1}.'
                                  .format(ctx.instance.id, e))


def deauthorize_ip_by_name(ec2_client, group, protocol,
                           from_port, to_port, cidr):

    try:
        ec2_client.revoke_security_group(group_name=group,
                                         ip_protocol=protocol,
                                         from_port=from_port,
                                         to_port=to_port, cidr_ip=cidr)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('(Node: {0}): Error. Failed to remove '
                                  'to security group: API returned: {1}.'
                                  .format(ctx.instance.id, e))

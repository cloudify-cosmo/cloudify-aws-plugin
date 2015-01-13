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

    name = ctx.node.properties['name']
    description = ctx.node.properties['description']

    ctx.logger.info('Creating Security Group: {0}'.format(name))

    try:
        group_object = ec2_client.create_security_group(name, description)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('(Node: {0}): Error. Failed to create '
                                  'security group: API returned: {1}.'
                                  .format(ctx.instance.id, e))

    ctx.instance.runtime_properties['group_object'] = group_object

    ctx.logger.info('Created Security Group: {0}.'.format(name))

    authorize(ctx=ctx)


@operation
def delete(**kwargs):
    """ Deletes a security group from an account.
    """

    ec2_client = connection.EC2ConnectionClient().client()

    group_name = ctx.instance.runtime_properties['group_name']

    ctx.logger.info('Deleting Security Group: {0}'.format(group_name))

    try:
        ec2_client.delete_security_group(group_name)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('(Node: {0}): Error. Failed to delete '
                                  'security group: API returned: {1}.'
                                  .format(ctx.instance.id, e))

    ctx.logger.info('Deleted Security Group: {0}.'.format(group_name))


@operation
def creation_validation(**kwargs):
    """ Validate that the Security Group exists
    """

    if 'group_object' in ctx.instance.runtime_properties:
        group = ctx.instance.runtime_properties['group_object']
    elif 'group_id' in ctx.instance.runtime_properties:
        group = ctx.instance.runtime_properties['group_id']
    elif 'group_name' in ctx.instance.runtime_properties:
        group = ctx.instance.runtime_properties['group_name']
    elif 'group_id' in ctx.node.properties:
        group = ctx.node.properties['group_id']
    elif 'group_name' in ctx.node.properties:
        group = ctx.node.properties['group_name']
    else:
        raise NonRecoverableError('No group name or group id provided.')

    if (utils.validate_group(group, ctx)):
        ctx.logger.info('Verified that group {0} was created.'.format(group))
    else:
        raise NonRecoverableError('Could not verify that the group {0} '
                                  'was created.'.format(group))


def authorize(ctx):
    """ Adds a rule to a security group using a provided protocol,
        address or address block, and port.
    """

    ec2_client = connection.EC2ConnectionClient().client()

    ctx.logger.info('Adding Rule to Security Group.')

    if 'group_object' in ctx.instance.runtime_properties:
        group = ctx.instance.runtime_properties['group_object']
        authorize_by_id(ec2_client, group.id, ctx)
    elif 'group_id' in ctx.instance.runtime_properties:
        group = ctx.instance.runtime_properties['group_id']
        authorize_by_id(ec2_client, group.id, ctx)
    elif 'group_name' in ctx.instance.runtime_properties:
        group = ctx.instance.runtime_properties['group_name']
        authorize_by_name(ec2_client, group.id, ctx)
    elif 'group_id' in ctx.node.properties:
        group = ctx.node.properties['group_id']
        authorize_by_id(ec2_client, group.id, ctx)
    elif 'group_name' in ctx.node.properties:
        group = ctx.node.properties['group_name']
        authorize_by_name(ec2_client, group.id, ctx)
    else:
        raise NonRecoverableError('No group name or group id provided.')

    ctx.logger.info('Added rules to Security Group: {0}'
                    'Rules: {1}'.format(group, ctx.node.properties['rules']))


def authorize_by_id(ec2_client, group, ctx):

    for r in ctx.node.properties['rules']:
        try:
            ec2_client.authorize_security_group(group_id=group,
                                                ip_protocol=r['ip_protocol'],
                                                from_port=r['from_port'],
                                                to_port=r['to_port'],
                                                cidr_ip=r['cidr_ip'])
        except (EC2ResponseError, BotoServerError) as e:
            raise NonRecoverableError('Unable to authorize that group: '
                                      '{0}'.format(e))


def authorize_by_name(ec2_client, group, ctx):

    for r in ctx.node.properties['rules']:
        try:
            ec2_client.authorize_security_group(group_name=group,
                                                ip_protocol=r['ip_protocol'],
                                                from_port=r['from_port'],
                                                to_port=r['to_port'],
                                                cidr_ip=r['cidr_ip'])
        except (EC2ResponseError, BotoServerError) as e:
            raise NonRecoverableError('Unable to authorize that group: '
                                      '{0}'.format(e))

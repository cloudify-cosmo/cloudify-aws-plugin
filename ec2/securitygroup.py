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
        raise NonRecoverableError('Error. Failed to create '
                                  'security group: API returned: {0}.'
                                  .format(e))

    ctx.instance.runtime_properties['group_object'] = {
        'id': group_object.id,
        'name': group_object.name
    }

    ctx.logger.info('Created Security Group: {0}.'.format(name))

    _authorize(ctx=ctx)


@operation
def delete(**kwargs):
    """ Deletes a security group from an account.
    """

    ec2_client = connection.EC2ConnectionClient().client()

    group_name = ctx.node.properties['name']

    ctx.logger.info('Deleting Security Group: {0}'.format(group_name))

    try:
        ec2_client.delete_security_group(group_name)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('Error. Failed to delete '
                                  'security group: API returned: {0}.'
                                  .format(e))

    ctx.logger.info('Deleted Security Group: {0}.'.format(group_name))


@operation
def creation_validation(**kwargs):
    """ Validate that the Security Group exists
    """

    if 'group_object' in ctx.instance.runtime_properties.keys():
        group_object = ctx.instance.runtime_properties['group_object']
        group = group_object['id']
    elif 'resource_id' in ctx.node.properties:
        group = ctx.node.properties['resource_id']
    elif 'name' in ctx.node.properties.keys():
        group = ctx.node.properties['name']
    else:
        raise NonRecoverableError('No group name or group id provided.')

    if (utils.validate_group(group, ctx)):
        ctx.logger.info('Verified that group {0} was created.'.format(group))
    else:
        raise NonRecoverableError('Could not verify that the group {0} '
                                  'was created.'.format(group))


@operation
def authorize(**kwargs):
    """ basically calls _authorize method, but exposes it as a
        lifecycle operation so that you can also add a rule in
        a blueprint.
    """
    _authorize(ctx=ctx)


def _authorize(ctx):
    """ Adds a rule to a security group using a provided protocol,
        address or address block, and port.
    """

    ec2_client = connection.EC2ConnectionClient().client()

    ctx.logger.info('Adding Rule to Security Group.')

    if 'group_object' in ctx.instance.runtime_properties.keys():
        group_object = ctx.instance.runtime_properties['group_object']
        group = group_object['id']
        authorize_by_id(ec2_client, group, ctx)
    elif 'resource_id' in ctx.node.properties.keys():
        group = ctx.node.properties['resource_id']
        authorize_by_id(ec2_client, group, ctx)
    elif 'name' in ctx.node.properties.keys():
        group = ctx.node.properties['name']
        authorize_by_name(ec2_client, group, ctx)
    else:
        raise NonRecoverableError('No group name or group id provided.')

    ctx.logger.info('Added rules to Security Group: {0}'
                    'Rules: {1}'.format(group, ctx.node.properties['rules']))


def authorize_by_id(ec2_client, group, ctx):
    """ For each rule listed in the blueprint,
        this will add the rule to the group with the given id.
    """

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
    """ For each rule listed in the blueprint,
        this will add the rule to the group with the given name.
    """

    for r in ctx.node.properties['rules']:
        try:
            ec2_client.authorize_security_group(group_name=group,
                                                ip_protocol=r['ip_protocol'],
                                                from_port=r['from_port'],
                                                to_port=r['to_port'],
                                                cidr_ip=r['cidr_ip']
                                                )
        except (EC2ResponseError, BotoServerError) as e:
            raise NonRecoverableError('Unable to authorize that group: '
                                      '{0}'.format(e))


@operation
def revoke(**kwargs):
    """ basically calls _revoke method, but exposes it as a
        lifecycle operation so that you can also remove a rule
        from a blueprint.
    """
    _revoke(ctx=ctx)


def _revoke(ctx):
    """ Removes a rule from a security group using a provided protocol,
        address or address block, and port.
    """

    ec2_client = connection.EC2ConnectionClient().client()

    ctx.logger.info('Revoking Rule from Security Group.')

    if 'group_object' in ctx.instance.runtime_properties.keys():
        group_object = ctx.instance.runtime_properties['group_object']
        group = group_object.id
        revoke_by_id(ec2_client, group, ctx)
    elif 'resource_id' in ctx.node.properties.keys():
        group = ctx.node.properties['resource_id']
        revoke_by_id(ec2_client, group, ctx)
    elif 'name' in ctx.node.properties.keys():
        group = ctx.node.properties['name']
        revoke_by_name(ec2_client, group, ctx)
    else:
        raise NonRecoverableError('No group name or group id provided.')

    ctx.logger.info('Revoked rules from Security Group: {0}'
                    'Rules: {1}'.format(group, ctx.node.properties['rules']))


def revoke_by_id(ec2_client, group, ctx):
    """ For each rule listed in the blueprint,
        this will remove the rule from the group with the given id.
    """

    for r in ctx.node.properties['rules']:
        try:
            ec2_client.revoke_security_group(group_id=group,
                                             ip_protocol=r['ip_protocol'],
                                             from_port=r['from_port'],
                                             to_port=r['to_port'],
                                             cidr_ip=r['cidr_ip'])
        except (EC2ResponseError, BotoServerError) as e:
            raise NonRecoverableError('Unable to revoke that rule: '
                                      '{0}'.format(e))


def revoke_by_name(ec2_client, group, ctx):
    """ For each rule listed in the blueprint,
        this will remove the rule from the group with the given name.
    """

    for r in ctx.node.properties['rules']:
        try:
            ec2_client.revoke_security_group(group_name=group,
                                             ip_protocol=r['ip_protocol'],
                                             from_port=r['from_port'],
                                             to_port=r['to_port'],
                                             cidr_ip=r['cidr_ip'])
        except (EC2ResponseError, BotoServerError) as e:
            raise NonRecoverableError('Unable to revoke that rule: '
                                      '{0}'.format(e))

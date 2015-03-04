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
import boto.exception

# Cloudify imports
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError, RecoverableError
from cloudify.decorators import operation
from ec2 import connection
from ec2 import utils


@operation
def create(**_):
    """ Creates a Security Group on this Amazon AWS account.
        ctx.node.properties:
            resource_id: When use_external_resource is false this
              is the name of the group.
            description: This is the group description
            rules: The rules which we want to create for the group.
        ctx.instance.runtime_properties:
            aws_resource_id: This is the security group ID assigned
              by Amazon when the group is created.
    """
    ec2_client = connection.EC2ConnectionClient().client()

    if ctx.node.properties['use_external_resource']:
        group_id = ctx.node.properties['resource_id']
        group = utils.get_security_group_from_id(group_id, ctx=ctx)
        if not group:
            raise NonRecoverableError(
                'External security group was indicated, but the given '
                'security group or Name does not exist.')
        ctx.instance.runtime_properties['aws_resource_id'] = group.id
        ctx.logger.info('Using external security group: {0}'.format(group.id))
        return

    if 'description' not in ctx.node.properties:
        raise NonRecoverableError(
            'Required description not in security group properties.')

    if 'rules' not in ctx.node.properties:
        raise NonRecoverableError(
            'Required rules not in security group properties.')

    name = ctx.node.properties['resource_id']
    description = ctx.node.properties['description']
    rules = ctx.node.properties['rules']

    ctx.logger.debug('Creating Security Group: {0}'.format(name))

    try:
        group_object = ec2_client.create_security_group(name, description)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}.'.format(str(e)))

    ctx.instance.runtime_properties['aws_resource_id'] = group_object.id
    ctx.logger.info('Created Security Group: {0}.'.format(name))
    authorize_by_id(ec2_client, group_object.id, rules)


@operation
def delete(retry_interval, **_):
    """ Deletes a security group from an account.
        runtime_properties:
            aws_resource_id: This is the security group ID assigned
              by Amazon when the group is created.
    """

    ec2_client = connection.EC2ConnectionClient().client()

    if 'aws_resource_id' not in ctx.instance.runtime_properties:
        raise NonRecoverableError(
            'Cannot delete security group because aws_resource_id'
            ' is not assigned.')

    group_id = ctx.instance.runtime_properties.get('aws_resource_id')
    ctx.logger.debug('Deleting Security Group: {0}'.format(group_id))

    try:
        ec2_client.delete_security_group(group_id=group_id)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    try:
        utils.get_security_group_from_id(group_id, ctx=ctx)
    except NonRecoverableError:
        ctx.logger.debug(
            'Generally NonRecoverableError indicates that an operation failed.'
            'In this case, everything worked correctly.')
        del(ctx.instance.runtime_properties['aws_resource_id'])
        ctx.logger.info('Deleted Security Group: {0}.'.format(group_id))
    else:
        raise RecoverableError(
            'Security group not deleted. Retrying...',
            retry_after=retry_interval)


@operation
def creation_validation(**_):
    """ This checks that all user supplied info is valid """
    required_properties = ['resource_id', 'use_external_resource',
                           'rules']

    for property_key in required_properties:
        utils.validate_node_property(property_key, ctx=ctx)

    if ctx.node.properties['use_external_resource']:
        if not utils.get_security_group_from_id(
                ctx.node.properties['resource_id'], ctx=ctx):
            raise NonRecoverableError('use_external_resource was specified, '
                                      'but the security group does not exist.')


@operation
def authorize(**_):
    """ Creates a Security Group on this Amazon AWS account.
        ctx.node.properties:
            resource_id: When use_external_resource is false this
              is the name of the group.
            description: This is the group description
            rules: The rules which we want to create for the group.
        ctx.instance.runtime_properties:
            aws_resource_id: This is the security group ID assigned
              by Amazon when the group is created.
    """

    if 'rules' not in ctx.node.properties:
        raise NonRecoverableError(
            'No rules provided. Unable to authorize security group.')

    if not ctx.node.properties['use_external_resource'] and \
            'aws_resource_id' not in ctx.instance.runtime_properties:
        raise NonRecoverableError(
            'Unable to authorize security group, '
            'neither aws_resource_id nor use_external_resource are true.')

    ctx.logger.debug('Attempting to authorize security group.')

    ec2_client = connection.EC2ConnectionClient().client()

    if ctx.node.properties['use_external_resource']:
        group_id = ctx.node.properties['resource_id']
        rules = ctx.node.properties['rules']
        authorize_by_id(ec2_client, group_id, rules)
    else:
        group_id = ctx.instance.runtime_properties.get('aws_resource_id')
        rules = ctx.node.properties['rules']
        authorize_by_id(ec2_client, group_id, rules)


def authorize_by_id(ec2_client, group, rules):
    """ For each rule listed in the blueprint,
        this will add the rule to the group with the given id.
    """

    for r in rules:
        try:
            ec2_client.authorize_security_group(
                group_id=group,
                ip_protocol=r['ip_protocol'],
                from_port=r['from_port'],
                to_port=r['to_port'],
                cidr_ip=r['cidr_ip'])
        except (boto.exception.EC2ResponseError,
                boto.exception.BotoServerError) as e:
            raise NonRecoverableError('{0}'.format(str(e)))

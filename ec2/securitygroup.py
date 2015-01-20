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
from cloudify.exceptions import NonRecoverableError
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

    name = ctx.node.properties['resource_id']
    description = ctx.node.properties['description']
    rules = ctx.node.properties['rules']

    ctx.logger.info('Creating Security Group: {0}'.format(name))

    try:
        group_object = ec2_client.create_security_group(name, description)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('Error. Failed to create '
                                  'security group: API returned: {0}.'
                                  .format(str(e)))

    ctx.instance.runtime_properties['aws_resource_id'] = group_object.id,

    ctx.logger.info('Created Security Group: {0}.'.format(name))

    authorize_by_id(ec2_client, group_object.id, rules)


@operation
def delete(**_):
    """ Deletes a security group from an account.
        runtime_properties:
            aws_resource_id: This is the security group ID assigned
              by Amazon when the group is created.
    """

    ec2_client = connection.EC2ConnectionClient().client()

    group_id = ctx.instance.runtime_properties['aws_resource_id']

    ctx.logger.info('Deleting Security Group: {0}'.format(group_id))

    try:
        ec2_client.delete_security_group(group_id=group_id)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('Error. Failed to delete '
                                  'security group: API returned: {0}.'
                                  .format(e))

    ctx.logger.info('Deleted Security Group: {0}.'.format(group_id))
    ctx.instance.runtime_properties.pop('aws_resource_id', None)


@operation
def creation_validation(**_):
    """ Validate that the Security Group exists.
        ctx.node.properties:
            resource_id: When use_external_resource is false this
              is the name of the group.
        ctx.instance.runtime_properties:
            aws_resource_id: This is the security group ID assigned
              by Amazon when the group is created.
    """

    if 'aws_resource_id' in ctx.instance.runtime_properties.keys():
        group = ctx.instance.runtime_properties['aws_resource_id']
    elif 'resource_id' in ctx.node.properties:
        group = ctx.node.properties['resource_id']
    else:
        raise NonRecoverableError('No group name or group id provided.')

    if (utils.validate_group(group, ctx=ctx)):
        ctx.logger.info('Verified that group {0} was created.'.format(group))
    else:
        raise NonRecoverableError('Could not verify that the group {0} '
                                  'was created.'.format(group))


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

    ec2_client = connection.EC2ConnectionClient().client()

    if ctx.node.properties('use_external_resource', False):
        group_id = ctx.node.properties['resource_id']
        rules = ctx.node.properties['rules']
        authorize_by_id(ec2_client, group_id, rules)
    else:
        group_id = ctx.instance.runtime_properties['aws_resource_id']
        rules = ctx.node.properties['rules']
        authorize_by_id(ec2_client, group_id, rules)


@operation
def revoke(**_):
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

    if ctx.node.properties.get('use_external_resource', False):
        group_id = ctx.node.properties['resource_id']
        rules = ctx.node.properties['rules']
        revoke_by_id(ec2_client, group_id, rules)
    else:
        group_id = ctx.instance.runtime_properties['aws_resource_id']
        rules = ctx.node.properties['rules']
        authorize_by_id(ec2_client, group_id, rules)


def authorize_by_id(ec2_client, group, rules):
    """ For each rule listed in the blueprint,
        this will add the rule to the group with the given id.
    """

    for r in rules:
        try:
            ec2_client.authorize_security_group(group_id=group,
                                                ip_protocol=r['ip_protocol'],
                                                from_port=r['from_port'],
                                                to_port=r['to_port'],
                                                cidr_ip=r['cidr_ip'])
        except boto.exception.EC2ResponseError as e:
            if 'InvalidPermission.Duplicate' in str(e):
                ctx.logger.debug('Rule already exists in that security group.')
            else:
                raise NonRecoverableError('Unable to authorize that group: '
                                          '{0}'.format(str(e)))
        except boto.exception.BotoServerError as e:
            raise NonRecoverableError('Unable to authorize that group: '
                                      '{0}'.format(str(e)))


def revoke_by_id(ec2_client, group, rules):
    """ For each rule listed in the blueprint,
        this will remove the rule from the group with the given id.
    """

    for r in rules:
        try:
            ec2_client.revoke_security_group(group_id=group,
                                             ip_protocol=r['ip_protocol'],
                                             from_port=r['from_port'],
                                             to_port=r['to_port'],
                                             cidr_ip=r['cidr_ip'])
        except (boto.exception.EC2ResponseError,
                boto.exception.BotoServerError) as e:
            raise NonRecoverableError('Unable to revoke that rule: '
                                      '{0}'.format(str(e)))

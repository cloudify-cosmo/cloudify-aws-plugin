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

# Built-in Imports
import re

# Third-party Imports
import boto.exception

# Cloudify imports
from ec2 import utils
from ec2 import constants
from ec2 import connection
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from cloudify.decorators import operation


@operation
def creation_validation(**_):
    """ This validates all Security Group Nodes before bootstrap.
    """

    for property_key in constants.SECURITY_GROUP_REQUIRED_PROPERTIES:
        utils.validate_node_property(property_key, ctx.node.properties)

    security_group = _get_security_group_from_id(
        ctx.node.properties['resource_id'])

    if ctx.node.properties['use_external_resource'] and not security_group:
        raise NonRecoverableError(
            'External resource, but the supplied '
            'security group does not exist in the account.')

    if not ctx.node.properties['use_external_resource'] and security_group:
        raise NonRecoverableError(
            'Not external resource, but the supplied '
            'security group exists in the account.')


@operation
def create(**_):
    """Creates an EC2 security group.
    """

    ec2_client = connection.EC2ConnectionClient().client()

    for property_name in constants.SECURITY_GROUP_REQUIRED_PROPERTIES:
        utils.validate_node_property(property_name, ctx.node.properties)

    if _create_external_securitygroup(ctx=ctx):
        return

    ctx.logger.debug(
        'Creating Security Group: {0}'
        .format(ctx.node.properties['resource_id']))

    try:
        group_object = ec2_client.create_security_group(
            ctx.node.properties['resource_id'],
            ctx.node.properties['description'])
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    _authorize_by_id(ec2_client, group_object.id, ctx.node.properties['rules'])
    utils.set_external_resource_id(
        group_object.id, ctx.instance, external=False)


@operation
def delete(**_):
    """ Deletes an EC2 security group.
    """

    ec2_client = connection.EC2ConnectionClient().client()

    group_id = utils.get_external_resource_id_or_raise(
        'delete security group', ctx.instance)

    if _delete_external_securitygroup(ctx):
        return

    ctx.logger.debug('Deleting Security Group: {0}'.format(group_id))

    _delete_security_group(group_id, ec2_client)

    utils.unassign_runtime_property_from_resource(
        constants.EXTERNAL_RESOURCE_ID, ctx.instance)

    ctx.logger.info(
        'Attempted to delete Security Group: {0}.'
        .format(group_id))


def _delete_security_group(group_id, ec2_client):
    """Tries to delete a Security group
    """

    try:
        ec2_client.delete_security_group(group_id=group_id)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))


def _authorize_by_id(ec2_client, group_id, rules):
    """ For each rule listed in the blueprint,
        this will add the rule to the group with the given id.

    :param ec2_client: The EC2 Client object.
    :param group: The group id that you want to add rules to.
    :param rules: A list of rules.
    :raises NonRecoverableError: if Boto or EC2 response is an error.
    """

    for r in rules:
        try:
            ec2_client.authorize_security_group(
                group_id=group_id,
                ip_protocol=r['ip_protocol'],
                from_port=r['from_port'],
                to_port=r['to_port'],
                cidr_ip=r['cidr_ip'])
        except (boto.exception.EC2ResponseError,
                boto.exception.BotoServerError) as e:
            raise NonRecoverableError('{0}'.format(str(e)))
        except Exception as e:
            _delete_security_group(group_id, ec2_client)
            raise


def _create_external_securitygroup(ctx):
    """If use_external_resource is True, this will set the runtime_properties,
    and then exit.

    :param ctx: The Cloudify context.
    :returns Boolean if use_external_resource is True or not.
    """

    if not utils.use_external_resource(ctx.node.properties):
        return False
    else:
        group_id = ctx.node.properties['resource_id']
        group = _get_security_group_from_id(group_id)
        if not group:
            raise NonRecoverableError(
                'External security group was indicated, but the given '
                'security group does not exist.')
        utils.set_external_resource_id(group.id, ctx.instance)
        return True


def _delete_external_securitygroup(ctx):
    """If use_external_resource is True, this will delete the runtime_properties,
    and then exit.

    :param ctx: The Cloudify context.
    :returns Boolean if use_external_resource is True or not.
    """

    if not utils.use_external_resource(ctx.node.properties):
        return False
    else:
        ctx.logger.info(
            'External resource. Not deleting security group from account.')
        utils.unassign_runtime_property_from_resource(
            constants.EXTERNAL_RESOURCE_ID, ctx.instance)
        return True


def _get_security_group_from_id(group_id):
    """Returns the security group object for a given security group id.

    :param group_id: The ID of a security group.
    :returns The boto security group object.
    """

    if not re.match('^sg\-[0-9a-z]{8}$', group_id):
        group = _get_security_group_from_name(group_id)
        return group

    group = _get_all_security_groups(list_of_group_ids=group_id)

    return group[0] if group else group


def _get_security_group_from_name(group_name):
    """Returns the security group object for a given group name.

    :param group_name: The name of a security group.
    :returns The boto security group object.
    """

    if re.match('^sg\-[0-9a-z]{8}$', group_name):
        group = _get_security_group_from_id(group_name)
        return group

    group = _get_all_security_groups(list_of_group_names=group_name)

    return group[0] if group else group


def _get_all_security_groups(list_of_group_names=None, list_of_group_ids=None):
    """Returns a list of security groups for a given list of group names and IDs.

    :param list_of_group_names: A list of security group names.
    :param list_of_group_ids: A list of security group IDs.
    :returns A list of security group objects.
    :raises NonRecoverableError: If Boto errors.
    """

    ec2_client = connection.EC2ConnectionClient().client()

    try:
        groups = ec2_client.get_all_security_groups(
            groupnames=list_of_group_names,
            group_ids=list_of_group_ids)
    except boto.exception.EC2ResponseError as e:
        if 'InvalidGroup.NotFound' in e:
            groups = ec2_client.get_all_security_groups()
            utils.log_available_resources(groups)
        return None
    except boto.exception.BotoServerError as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    return groups

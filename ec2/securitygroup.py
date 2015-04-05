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
        utils.get_resource_id())

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

    name = utils.get_resource_id()

    if _create_external_securitygroup(name):
        return

    ctx.logger.debug(
        'Creating Security Group: {0}'
        .format(name))

    try:
        group_object = ec2_client.create_security_group(
            name,
            ctx.node.properties['description'])
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    _create_group_rules(group_object)
    utils.set_external_resource_id(
        group_object.id, ctx.instance, external=False)


@operation
def delete(**_):
    """ Deletes an EC2 security group.
    """

    group_id = utils.get_external_resource_id_or_raise(
        'delete security group', ctx.instance)

    if _delete_external_securitygroup():
        return

    ctx.logger.debug('Deleting Security Group: {0}'.format(group_id))

    _delete_security_group(group_id)

    utils.unassign_runtime_property_from_resource(
        constants.EXTERNAL_RESOURCE_ID, ctx.instance)

    ctx.logger.info(
        'Attempted to delete Security Group: {0}.'
        .format(group_id))


def _delete_security_group(group_id):
    """Tries to delete a Security group
    """

    group_to_delete = _get_security_group_from_id(group_id)

    if not group_to_delete:
        raise NonRecoverableError(
            'Unable to delete security group {0}, because the group '
            'does not exist in the account'.format(group_id))

    try:
        group_to_delete.delete()
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))


def _create_group_rules(group_object):
    """For each rule listed in the blueprint,
    this will add the rule to the group with the given id.
    :param group: The group object that you want to add rules to.
    :raises NonRecoverableError: src_group_id OR ip_protocol,
    from_port, to_port, and cidr_ip are not provided.
    """

    for rule in ctx.node.properties['rules']:
        if 'src_group' in rule and 'cidr_ip' not in rule:
            _authorize_src_group(group_object, rule)
        elif 'cidr_ip' in rule:
            _authorize_cidr_ip(group_object, rule)
        else:
            raise NonRecoverableError(
                'You need to pass either src_group_id OR cidr_ip.')


def _authorize_cidr_ip(group_object, rule):

    try:
        group_object.authorize(
            ip_protocol=rule.get('ip_protocol'),
            from_port=rule.get('from_port'),
            to_port=rule.get('to_port'),
            cidr_ip=rule['cidr_ip']
        )
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError,
            KeyError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))
    except Exception as e:
        _delete_security_group(group_object.id)
        raise


def _authorize_src_group(group_object, rule):

    src_group_object = _get_security_group_from_id(rule['src_group_id'])

    try:
        group_object.authorize(
            ip_protocol=rule.get('ip_protocol'),
            from_port=rule.get('from_port'),
            to_port=rule.get('to_port'),
            src_group=src_group_object
        )
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError,
            KeyError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))
    except Exception as e:
        _delete_security_group(group_object.id)
        raise


def _create_external_securitygroup(name):
    """If use_external_resource is True, this will set the runtime_properties,
    and then exit.

    :param ctx: The Cloudify context.
    :return False: Cloudify resource. Continue operation.
    :return True: External resource. Set runtime_properties. Ignore operation.
    """

    if not utils.use_external_resource(ctx.node.properties):
        return False

    group = _get_security_group_from_id(name)
    if not group:
        raise NonRecoverableError(
            'External security group was indicated, but the given '
            'security group does not exist.')
    utils.set_external_resource_id(group.id, ctx.instance)
    return True


def _delete_external_securitygroup():
    """If use_external_resource is True, this will delete the runtime_properties,
    and then exit.

    :param ctx: The Cloudify context.
    :return False: Cloudify resource. Continue operation.
    :return True: External resource. Unset runtime_properties.
        Ignore operation.
    """

    if not utils.use_external_resource(ctx.node.properties):
        return False

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

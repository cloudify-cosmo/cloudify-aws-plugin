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
    """ This checks that all user supplied info is valid """

    address = _get_address_by_id(
        ctx.node.properties['resource_id'])

    if ctx.node.properties['use_external_resource'] and not address:
        raise NonRecoverableError(
            'External resource, but the supplied '
            'elasticip does not exist in the account.')

    if not ctx.node.properties['use_external_resource'] and address:
        raise NonRecoverableError(
            'Not external resource, but the supplied '
            'elasticip exists.')


@operation
def allocate(**_):
    """This allocates an Elastic IP in the connected account."""

    ec2_client = connection.EC2ConnectionClient().client()

    if _allocate_external_elasticip(ctx=ctx):
        return

    ctx.logger.debug('Attempting to allocate elasticip.')

    try:
        address_object = ec2_client.allocate_address(domain=None)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    utils.set_external_resource_id(
        address_object.public_ip, ctx.instance, ctx.logger, external=False)


@operation
def release(**_):
    """This releases an Elastic IP created by Cloudify
    in the connected account.
    """

    elasticip = \
        utils.get_external_resource_id_or_raise(
            'release elasticip', ctx.instance, ctx.logger)

    if _release_external_elasticip(ctx=ctx):
        return

    address_object = _get_address_object_by_id(elasticip)

    if not address_object:
        raise NonRecoverableError(
            'Unable to release elasticip. Elasticip not in account.')

    ctx.logger.debug('Attempting to release an Elastic IP.')

    try:
        deleted = address_object.delete()
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    if not deleted:
        raise NonRecoverableError(
            'Elastic IP {0} deletion failed for an unknown reason.'
            .format(address_object.public_ip))

    address = _get_address_object_by_id(address_object.public_ip)

    if not address:
        utils.unassign_runtime_property_from_resource(
            constants.EXTERNAL_RESOURCE_ID, ctx.instance, ctx.logger)
    else:
        return ctx.operation.retry(
            message='Elastic IP not released. Retrying...')


@operation
def associate(**_):
    """ Associates an Elastic IP created by Cloudify with an EC2 Instance
    that was also created by Cloudify.
    """

    ec2_client = connection.EC2ConnectionClient().client()

    instance_id = \
        utils.get_external_resource_id_or_raise(
            'associate elasticip', ctx.source.instance, ctx.logger)
    elasticip = \
        utils.get_external_resource_id_or_raise(
            'associate elasticip', ctx.target.instance, ctx.logger)

    if _associate_external_elasticip_or_instance(elasticip, ctx=ctx):
        return

    ctx.logger.debug(
        'Attempting to associate elasticip {0} and instance {1}.'
        .format(elasticip, instance_id))

    try:
        ec2_client.associate_address(
            instance_id=instance_id, public_ip=elasticip)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    ctx.logger.info(
        'Associated Elastic IP {0} with instance {1}.'
        .format(elasticip, instance_id))
    ctx.source.instance.runtime_properties['public_ip_address'] = elasticip


@operation
def disassociate(**_):
    """ Disassocates an Elastic IP created by Cloudify from an EC2 Instance
    that was also created by Cloudify.
    """
    ec2_client = connection.EC2ConnectionClient().client()

    instance_id = \
        utils.get_external_resource_id_or_raise(
            'disassociate elasticip', ctx.source.instance, ctx.logger)
    elasticip = \
        utils.get_external_resource_id_or_raise(
            'disassociate elasticip', ctx.target.instance, ctx.logger)

    if _disassociate_external_elasticip_or_instance(ctx=ctx):
        return

    ctx.logger.debug('Disassociating Elastic IP {0}'.format(elasticip))

    try:
        ec2_client.disassociate_address(public_ip=elasticip)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    utils.unassign_runtime_property_from_resource(
        'public_ip_address', ctx.source.instance, ctx.logger)

    ctx.logger.info(
        'Disassociated Elastic IP {0} from instance {1}.'
        .format(elasticip, instance_id))


def _allocate_external_elasticip(ctx):
    """Pretends to allocate an Elastic IP but if it was
    not created by Cloudify, it just sets runtime_properties
    and exits the operation.

    :return False: Cloudify resource. Continue operation.
    :return True: External resource. Set runtime_properties. Ignore operation.
    """

    if not utils.use_external_resource(ctx.node.properties, ctx.logger):
        return False

    address_ip = _get_address_by_id(
        ctx.node.properties['resource_id'])
    if not address_ip:
        raise NonRecoverableError(
            'External elasticip was indicated, but the given '
            'elasticip does not exist in the account.')
    utils.set_external_resource_id(address_ip, ctx.instance, ctx.logger)
    return True


def _release_external_elasticip(ctx):
    """Pretends to release an Elastic IP but if it was
    not created by Cloudify, it just deletes runtime_properties
    and exits the operation.

    :return False: Cloudify resource. Continue operation.
    :return True: External resource. Unset runtime_properties.
        Ignore operation.
    """

    if not utils.use_external_resource(ctx.node.properties, ctx.logger):
        return False

    utils.unassign_runtime_property_from_resource(
        constants.EXTERNAL_RESOURCE_ID, ctx.instance, ctx.logger)
    return True


def _associate_external_elasticip_or_instance(elasticip, ctx):
    """Pretends to associate an Elastic IP with an EC2 instance but if one
    was not created by Cloudify, it just sets runtime_properties
    and exits the operation.

    :return False: At least one is a Cloudify resource. Continue operation.
    :return True: Both are External resources. Set runtime_properties.
        Ignore operation.
    """

    if not utils.use_external_resource(ctx.source.node.properties, ctx.logger) \
            or not utils.use_external_resource(
                ctx.target.node.properties, ctx.logger):
        return False

    ctx.logger.info(
        'Either instance or elasticip is an external resource so not '
        'performing associate operation.')
    ctx.source.instance.runtime_properties['public_ip_address'] = \
        elasticip
    return True


def _disassociate_external_elasticip_or_instance(ctx):
    """Pretends to disassociate an Elastic IP with an EC2 instance but if one
    was not created by Cloudify, it just deletes runtime_properties
    and exits the operation.

    :return False: At least one is a Cloudify resource. Continue operation.
    :return True: Both are External resources. Set runtime_properties.
        Ignore operation.
    """

    if not utils.use_external_resource(ctx.source.node.properties, ctx.logger) \
            or not utils.use_external_resource(
                ctx.target.node.properties, ctx.logger):
        return False

    ctx.logger.info(
        'Either instance or elasticip is an external resource so not '
        'performing disassociate operation.')
    utils.unassign_runtime_property_from_resource(
        'public_ip_address', ctx.source.instance, ctx.logger)
    return True


def _get_address_by_id(address_id):
    """Returns the elastip ip for a given address elastip.

    :param address_id: The ID of a elastip.
    :returns The boto elastip ip.
    """

    address = _get_address_object_by_id(address_id)

    return address.public_ip if address else address


def _get_address_object_by_id(address_id):
    """Returns the elastip object for a given address elastip.

    :param address_id: The ID of a elastip.
    :returns The boto elastip object.
    """

    address = _get_all_addresses(address=address_id)

    return address[0] if address else address


def _get_all_addresses(address=None):
    """Returns a list of elastip objects for a given address elastip.

    :param address: The ID of a elastip.
    :returns A list of elasticip objects.
    :raises NonRecoverableError: If Boto errors.
    """

    ec2_client = connection.EC2ConnectionClient().client()

    try:
        addresses = ec2_client.get_all_addresses(address)
    except boto.exception.EC2ResponseError as e:
        if 'InvalidAddress.NotFound' in e:
            addresses = ec2_client.get_all_addresses()
            utils.log_available_resources(addresses, ctx.logger)
        return None
    except boto.exception.BotoServerError as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    return addresses

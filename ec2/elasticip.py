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
from ec2 import constants


@operation
def allocate(**_):
    ec2_client = connection.EC2ConnectionClient().client()

    if allocate_external_elasticip(ctx=ctx):
        return

    ctx.logger.debug('Attempting to allocate elasticip.')

    try:
        address_object = ec2_client.allocate_address(domain=None)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    utils.set_external_resource_id(
        address_object.public_ip, external=False, ctx=ctx)


@operation
def release(**_):
    """ Releases an Elastic IP from the connected region in the AWS account.
    """

    elasticip = \
        utils.get_external_resource_id_or_raise(
            'release elasticip', ctx.instance, ctx=ctx)

    if release_external_elasticip(ctx=ctx):
        return

    address_object = utils.get_address_object_by_id(elasticip, ctx=ctx)

    if not address_object:
        raise NonRecoverableError(
            'Unable to release elasticip. Elasticip not in account.')

    ctx.logger.debug('Attempting to release an Elastic IP.')

    try:
        address_object.delete()
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))
    except AttributeError as e:
        raise NonRecoverableError(
            'Attribute error raised on address_object.delete(). '
            'This indicates that a VPC elastic IP was used instead of EC2 '
            'classic: {0}'.format(str(e)))

    address = utils.get_address_object_by_id(address_object.public_ip, ctx=ctx)

    if not address:
        utils.unassign_runtime_property_from_resource(
            constants.EXTERNAL_RESOURCE_ID, ctx.instance, ctx=ctx)
    else:
        return ctx.operation.retry(
            message='Elastic IP not released. Retrying...')


@operation
def associate(**_):
    """ Associates an Elastic IP with an EC2 Instance.
    """

    ec2_client = connection.EC2ConnectionClient().client()

    instance_id = \
        utils.get_external_resource_id_or_raise(
            'associate elasticip', ctx.source.instance, ctx=ctx)
    elasticip = \
        utils.get_external_resource_id_or_raise(
            'associate elasticip', ctx.target.instance, ctx=ctx)
    if associate_external_elasticip_or_instance(elasticip, ctx=ctx):
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
    """ Disassociates an Elastic IP from an EC2 Instance.
    """
    ec2_client = connection.EC2ConnectionClient().client()

    instance_id = \
        utils.get_external_resource_id_or_raise(
            'disassociate elasticip', ctx.source.instance, ctx=ctx)
    elasticip = \
        utils.get_external_resource_id_or_raise(
            'disassociate elasticip', ctx.target.instance, ctx=ctx)
    if disassociate_external_elasticip_or_instance(ctx=ctx):
        return

    ctx.logger.debug('Disassociating Elastic IP {0}'.format(elasticip))

    try:
        ec2_client.disassociate_address(public_ip=elasticip)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    utils.unassign_runtime_property_from_resource(
        'public_ip_address', ctx.source.instance, ctx=ctx)

    ctx.logger.info(
        'Disassociated Elastic IP {0} from instance {1}.'
        .format(elasticip, instance_id))


def allocate_external_elasticip(ctx):

    if not ctx.node.properties['use_external_resource']:
        return False
    else:
        address_ip = utils.get_address_by_id(
            ctx.node.properties['resource_id'], ctx=ctx)
        if not address_ip:
            raise NonRecoverableError(
                'External elasticip was indicated, but the given '
                'elasticip does not exist in the account.')
        utils.set_external_resource_id(address_ip, ctx=ctx)
        return True


def release_external_elasticip(ctx):

    if not ctx.node.properties['use_external_resource']:
        return False
    else:
        utils.unassign_runtime_property_from_resource(
            constants.EXTERNAL_RESOURCE_ID, ctx.instance, ctx=ctx)
        return True


def associate_external_elasticip_or_instance(elasticip, ctx):

    if not ctx.source.node.properties['use_external_resource']:
        return False
    elif not ctx.target.node.properties['use_external_resource']:
        return False
    else:
        ctx.logger.info(
            'Either instance or elasticip is an external resource so not '
            'performing associate operation.')
        ctx.source.instance.runtime_properties['public_ip_address'] = \
            elasticip
        return True


def disassociate_external_elasticip_or_instance(ctx):

    if not ctx.source.node.properties['use_external_resource']:
        return False
    elif not ctx.target.node.properties['use_external_resource']:
        return False
    else:
        ctx.logger.info(
            'Either instance or elasticip is an external resource so not '
            'performing disassociate operation.')
        utils.unassign_runtime_property_from_resource(
            'public_ip_address', ctx.source.instance, ctx=ctx)
        return True


@operation
def creation_validation(**_):
    """ This checks that all user supplied info is valid """

    if ctx.node.properties['use_external_resource']:
        address = utils.get_address_by_id(
            ctx.node.properties['resource_id'], ctx=ctx)

    if not address:
        raise NonRecoverableError(
            'External elasticip was indicated, but the given '
            'elasticip does not exist.')

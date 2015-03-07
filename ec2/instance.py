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
from ec2 import utils
from ec2 import connection
from ec2 import constants


@operation
def run_instances(**_):
    ec2_client = connection.EC2ConnectionClient().client()

    if create_external_instance(ctx=ctx):
        return

    instance_parameters = utils.get_instance_parameters(ctx=ctx)

    ctx.logger.debug(
        'Attempting to create EC2 Instance. Sending these API parameters: {0}.'
        .format(instance_parameters))

    if ctx.operation.retry_number == 0:
        try:
            reservation = ec2_client.run_instances(**instance_parameters)
        except (boto.exception.EC2ResponseError,
                boto.exception.BotoServerError) as e:
            raise NonRecoverableError('{0}'.format(str(e)))

    instance_id = reservation.instances[0].id

    instance = utils.get_instance_from_id(instance_id, ctx=ctx)

    if instance is None:
        return ctx.operation.retry(
            message='Waiting to verify that instance {0} '
            'has been added to your account.'.format(instance_id))

    utils.set_external_resource_id(instance_id, external=False, ctx=ctx)


@operation
def start(**_):
    ec2_client = connection.EC2ConnectionClient().client()

    instance_id = \
        utils.get_external_resource_id_or_raise('start instance', ctx=ctx)

    if ctx.node.properties['use_external_resource']:
        assign_runtime_properties_to_instance(
            ctx=ctx, runtime_properties=constants.INSTANCE_INTERNAL_ATTRIBUTES)
        ctx.logger.info(
            'Setting Cloudify properties for external resource {0}, '
            'but not attempting to start server.'.format(instance_id))
        return

    if utils.get_instance_state(ctx=ctx) == constants.INSTANCE_STATE_STARTED:
        assign_runtime_properties_to_instance(
            ctx=ctx, runtime_properties=constants.INSTANCE_INTERNAL_ATTRIBUTES)
        ctx.logger.info('Instance {0} is running.'.format(instance_id))
        return

    ctx.logger.debug('Attempting to start instance: {0}.)'.format(instance_id))

    try:
        ec2_client.start_instances(instance_id)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    ctx.logger.debug('Attempted to start instance {0}.'.format(instance_id))

    if utils.get_instance_state(ctx=ctx) == constants.INSTANCE_STATE_STARTED:
        assign_runtime_properties_to_instance(
            ctx=ctx, runtime_properties=constants.INSTANCE_INTERNAL_ATTRIBUTES)
        ctx.logger.info('Instance {0} is running.'.format(instance_id))
    else:
        return ctx.operation.retry(
            message='Waiting server to be running. Retrying...')


@operation
def stop(**_):
    ec2_client = connection.EC2ConnectionClient().client()

    instance_id = \
        utils.get_external_resource_id_or_raise('stop instance', ctx=ctx)

    if ctx.node.properties['use_external_resource']:
        unassign_runtime_properties(
            ctx=ctx, runtime_properties=constants.INSTANCE_INTERNAL_ATTRIBUTES)
        ctx.logger.info(
            'External resource, not attempting to stop server: {0}.'
            .format(instance_id))
        return

    ctx.logger.debug(
        'Attempting to stop EC2 Instance. {0}.)'.format(instance_id))

    try:
        ec2_client.stop_instances(instance_id)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    ctx.logger.debug('Attempted to stop instance {0}.'.format(instance_id))

    if utils.get_instance_state(ctx=ctx) == constants.INSTANCE_STATE_STOPPED:
        unassign_runtime_properties(
            ctx=ctx, runtime_properties=constants.INSTANCE_INTERNAL_ATTRIBUTES)
        ctx.logger.info('Stopped instance {0}.'.format(instance_id))
    else:
        return ctx.operation.retry(
            message='Waiting server to stop. Retrying...')


@operation
def terminate(**_):
    ec2_client = connection.EC2ConnectionClient().client()

    instance_id = \
        utils.get_external_resource_id_or_raise(
            'terminate instance', ctx=ctx)

    if ctx.node.properties['use_external_resource']:
        unassign_runtime_properties(
            ctx=ctx, runtime_properties=[constants.EXTERNAL_RESOURCE_ID])
        ctx.logger.info(
            'Unsetting Cloudify properties for external resource {0}, '
            'but not attempting to terminate server.'.format(instance_id))
        return

    ctx.logger.debug(
        'Attempting to terminate EC2 Instance. {0}.)'.format(instance_id))

    try:
        ec2_client.terminate_instances(instance_id)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    ctx.logger.debug(
        'Attemped to terminate instance {0}'.format(instance_id))

    if utils.get_instance_state(ctx=ctx) == \
            constants.INSTANCE_STATE_TERMINATED:
        ctx.logger.info('Terminated instance: {0}.'.format(instance_id))
        unassign_runtime_properties(
            ctx=ctx, runtime_properties=[constants.EXTERNAL_RESOURCE_ID])


@operation
def creation_validation(**_):
    """ This checks that all user supplied info is valid """
    required_properties = ['resource_id', 'use_external_resource',
                           'image_id', 'instance_type']

    for property_key in required_properties:
        utils.validate_node_property(property_key, ctx=ctx)

    if ctx.node.properties['use_external_resource']:
        instance = utils.get_instance_from_id(
            ctx.node.properties['resource_id'], ctx=ctx)

    if not instance:
        raise NonRecoverableError(
            'Instance ID {0} does not exist in this account.'
            .format(ctx.node.properties['resource_id']))

    if 'image_id' not in ctx.node.properties['parameters']:
        raise NonRecoverableError(
            'Required parameter image_id not provided.')

    if 'instance_type' not in ctx.node.properties['parameters']:
        raise NonRecoverableError(
            'Required parameter instance_type not provided.')

    image_id = ctx.node.properties['parameters']['image_id']
    image_object = utils.get_image(image_id)

    if 'available' not in image_object.state:
        raise NonRecoverableError(
            'image_id {0} not available to this account.'.format(image_id))

    if 'ebs' not in image_object.root_device_type:
        raise NonRecoverableError(
            'image_id {0} not ebs-backed. Image must be of type \'ebs\'.'
            .format(image_id))


def assign_runtime_properties_to_instance(ctx, runtime_properties):

    for property_name in runtime_properties:
        if 'ip' is property_name:
            ctx.instance.runtime_properties[property_name] = \
                utils.get_instance_attribute('private_ip_address', ctx=ctx)
        elif 'public_ip_address' is property_name:
            ctx.instance.runtime_properties[property_name] = \
                utils.get_instance_attribute('ip_address', ctx=ctx)
        else:
            attribute = utils.get_instance_attribute(property_name, ctx=ctx)

        ctx.logger.debug('Set {0}: {1}.'.format(property_name, attribute))


def unassign_runtime_properties(ctx, runtime_properties):
    for property_name in runtime_properties:
        del(ctx.instance.runtime_properties[property_name])
        ctx.logger.debug('Deleted {0} runtime property.')


def create_external_instance(ctx):

    if not ctx.node.properties['use_external_resource']:
        return False
    else:
        instance_id = ctx.node.properties['resource_id']
        instance = utils.get_instance_from_id(instance_id, ctx=ctx)
        if instance is None:
            raise NonRecoverableError(
                'Cannot use_external_resource because instance_id {0} '
                'is not in this account.'.format(instance_id))
        utils.set_external_resource_id(instance.id, ctx=ctx)
        return True

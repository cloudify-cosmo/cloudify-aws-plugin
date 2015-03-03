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
from ec2 import utils
from ec2 import connection


@operation
def run_instances(**_):
    """ Creates an instance in EC2. If use_external_resource is true,
        this will assign accept the provided resource_id and validate
        retrieve the descriptive instance object from AWS. It then
        the instance's id from the instance object and assigns it to
        a runtime property.
        If use_external_resource is false or not given, the image_id
        and instance_type properties are taken from the node properties
        and inserted into the run_instances boto function arguments.
        Then the rest of the parameters are added to the arguments,
        overriding image_id and instance_type, if given.
        Except min_count and max_count, which are always set to 1.
        The run_instance function is sent to EC2. If no error is raised,
        the output of that function is returned and the instance id is
        assigned to the runtime properties.
    """

    ec2_client = connection.EC2ConnectionClient().client()

    if ctx.node.properties['use_external_resource']:
        instance_id = ctx.node.properties['resource_id']
        instance = utils.get_instance_from_id(instance_id, ctx=ctx)
        ctx.instance.runtime_properties['aws_resource_id'] = instance.id
        ctx.logger.info('Using existing instance: {0}.'.format(instance.id))
        return

    instance_parameters = utils.get_instance_parameters(ctx=ctx)

    ctx.logger.debug(
        'Attempting to create EC2 Instance. Sending these API parameters: {0}.'
        .format(instance_parameters))

    try:
        reservation = ec2_client.run_instances(**instance_parameters)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    instance_id = reservation.instances[0].id
    ctx.instance.runtime_properties['aws_resource_id'] = instance_id
    ctx.logger.info('Created instance: {0}.'.format(instance_id))


@operation
def start(retry_interval, **_):
    """ Starts an EC2 Classic Instance.
        If start command has already run, this does nothing.
        Requires:
            ctx.instance.runtime_properties['aws_resource_id']
        Sets:
            ctx.instance.runtime_properties['ip']
            ctx.instance.runtime_properties['private_dns_name']
            ctx.instance.runtime_properties['public_dns_name']
            ctx.instance.runtime_properties['public_ip_address']
    """
    ec2_client = connection.EC2ConnectionClient().client()

    if 'aws_resource_id' not in ctx.instance.runtime_properties:
        raise NonRecoverableError(
            'Cannot start instance because aws_resource_id is not assigned.')

    instance_id = ctx.instance.runtime_properties['aws_resource_id']

    if utils.get_instance_state(ctx=ctx) == 16:
        assign_runtime_properties_to_instance(ctx=ctx)
        ctx.logger.info('Instance {0} is running.'.format(instance_id))
        return

    ctx.logger.debug('Attempting to start instance: {0}.)'.format(instance_id))

    try:
        ec2_client.start_instances(instance_id)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        if 'does not exist' in e:
            raise RecoverableError(
                'Waiting for server to be running. Retrying...',
                retry_after=retry_interval)
        else:
            raise NonRecoverableError('{0}'.format(str(e)))

    if utils.get_instance_state(ctx=ctx) == 16:
        assign_runtime_properties_to_instance(ctx=ctx)
        ctx.logger.info('Instance {0} is running.'.format(instance_id))
    else:
        raise RecoverableError(
            'Waiting for server to be running. Retrying...',
            retry_after=retry_interval)


@operation
def stop(retry_interval, **_):
    """ Stops an existing EC2 instance.
        If already stopped, this does nothing.
        Requires:
            ctx.instance.runtime_properties['aws_resource_id']
    """
    ec2_client = connection.EC2ConnectionClient().client()

    if 'aws_resource_id' not in ctx.instance.runtime_properties:
        raise NonRecoverableError(
            'Cannot stop instance because aws_resource_id is not assigned.')

    instance_id = ctx.instance.runtime_properties['aws_resource_id']

    ctx.logger.debug(
        'Attempting to stop EC2 Instance. {0}.)'.format(instance_id))

    try:
        ec2_client.stop_instances(instance_id)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    if utils.get_instance_state(ctx=ctx) == 80:
        ctx.logger.info('Stopped instance {0}.'.format(instance_id))
        unassign_runtime_properties(ctx=ctx)
    else:
        raise RecoverableError(
            'Waiting for server to stop. Retrying...',
            retry_after=retry_interval)


@operation
def terminate(retry_interval, **_):
    """ Terminates an existing EC2 instance.
        If already terminated, this does nothing.
    """
    ec2_client = connection.EC2ConnectionClient().client()

    if 'aws_resource_id' not in ctx.instance.runtime_properties:
        raise NonRecoverableError(
            'Cannot terminate instance because aws_resource_id not assigned.')

    instance_id = ctx.instance.runtime_properties['aws_resource_id']

    ctx.logger.debug(
        'Attempting to terminate EC2 Instance. {0}.)'.format(instance_id))

    try:
        ec2_client.terminate_instances(instance_id)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    ctx.logger.debug(
        'Attemped to terminate instance {0}'.format(instance_id))

    if utils.get_instance_state(ctx=ctx) == 48:
        ctx.logger.info('Terminated instance: {0}.'.format(instance_id))
        del(ctx.instance.runtime_properties['aws_resource_id'])


@operation
def creation_validation(**_):
    """ This checks that all user supplied info is valid """
    required_properties = ['resource_id', 'use_external_resource',
                           'image_id', 'instance_type']

    for property_key in required_properties:
        utils.validate_node_property(property_key, ctx=ctx)

    if ctx.node.properties['use_external_resource']:
        utils.get_instance_from_id(
            ctx.node.properties['resource_id'], ctx=ctx)


def assign_runtime_properties_to_instance(
        ctx, runtime_properties=['private_dns_name', 'public_dns_name',
                                 'public_ip_address', 'ip']):

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


def unassign_runtime_properties(
        ctx, runtime_properties=['private_dns_name', 'public_dns_name',
                                 'public_ip_address', 'ip']):
    for property_name in runtime_properties:
        del(ctx.instance.runtime_properties[property_name])
        ctx.logger.debug('Deleted {0} runtime property.')

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
from ec2 import utils
from ec2 import connection

# EC2 Instance States
INSTANCE_RUNNING = 16
INSTANCE_TERMINATED = 48
INSTANCE_STOPPED = 80

# Timeouts
CREATION_TIMEOUT = 1
START_TIMEOUT = 1
STOP_TIMEOUT = 1
TERMINATION_TIMEOUT = 1
CHECK_INTERVAL = 1

# EC2 Method Arguments
RUN_INSTANCES_UNSUPPORTED = {
    'min_count': 1,
    'max_count': 1
}


@operation
def run_instances(**kwargs):
    """ Creates an EC2 Classic Instance.
    """
    ec2_client = connection.EC2ConnectionClient().client()

    arguments = dict()
    arguments['image_id'] = ctx.node.properties['image_id']
    arguments['instance_type'] = ctx.node.properties['instance_type']
    args_to_merge = build_arg_dict(ctx.node.properties['attributes'].copy(),
                                   RUN_INSTANCES_UNSUPPORTED)
    arguments.update(args_to_merge)

    ctx.logger.info('Creating EC2 Instance.')
    ctx.logger.debug('Attempting to create EC2 Instance.'
                     'Image id: {0}. Instance type: {1}.'
                     .format(arguments['image_id'],
                             arguments['instance_type']))
    ctx.logger.debug('Sending these API parameters: {0}.'
                     .format(arguments))

    try:
        reservation = ec2_client.run_instances(**arguments)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('Error. Failed to run EC2 Instance: '
                                  'API returned: {0}.'.format(e))

    instance_id = reservation.instances[0].id
    ctx.instance.runtime_properties['instance_id'] = instance_id

    if utils.validate_instance_id(reservation.instances[0].id, ctx=ctx):
        utils.validate_state(reservation.instances[0], INSTANCE_RUNNING,
                             CREATION_TIMEOUT, CHECK_INTERVAL, ctx=ctx)


@operation
def start(**kwargs):
    """ Starts an existing EC2 instance.
        If already started, this does nothing.
        You can run start on a started instance all you like.
        Nothing will happen.
    """
    ec2_client = connection.EC2ConnectionClient().client()

    instance_id = ctx.instance.runtime_properties['instance_id']

    ctx.logger.info('Starting EC2 Instance.')
    ctx.logger.debug('Attempting to start EC2 Classic Instance.'
                     '(Instance id: {0}.)'.format(instance_id))

    try:
        instances = ec2_client.start_instances(instance_id)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('Error. Failed to start EC2 Instance: '
                                  'API returned: {0}.'.format(e))

    if utils.validate_instance_id(instance_id, ctx=ctx):
        utils.validate_state(instances[0], INSTANCE_RUNNING,
                             START_TIMEOUT, CHECK_INTERVAL, ctx=ctx)


@operation
def stop(**kwargs):
    """ Stops an existing EC2 instance.
        If already stopped, this does nothing.
    """
    ec2_client = connection.EC2ConnectionClient().client()

    instance_id = ctx.instance.runtime_properties['instance_id']

    ctx.logger.info('Stopping EC2 Instance.')
    ctx.logger.debug('Attempting to stop EC2 Instance.'
                     '(Instance id: {0}.)'.format(instance_id))

    try:
        instances = ec2_client.stop_instances(instance_id)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('Error. Failed to stop EC2 Instance: '
                                  'API returned: {0}.'.format(e))

    if utils.validate_instance_id(instance_id, ctx=ctx):
        utils.validate_state(instances[0], INSTANCE_STOPPED,
                             STOP_TIMEOUT, CHECK_INTERVAL, ctx=ctx)


@operation
def terminate(**kwargs):
    """ Terminates an existing EC2 instance.
        If already terminated, this does nothing.
    """
    ec2_client = connection.EC2ConnectionClient().client()

    instance_id = ctx.instance.runtime_properties['instance_id']

    ctx.logger.info('Terminating EC2 Instance.')
    ctx.logger.debug('Attempting to terminate EC2 Instance.'
                     '(Instance id: {0}.)'.format(instance_id))

    try:
        instances = ec2_client.terminate_instances(instance_id)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('Error. Failed to terminate '
                                  'EC2 Instance: API returned: {0}.'
                                  .format(e))

    if utils.validate_instance_id(instance_id, ctx=ctx):
        utils.validate_state(instances[0], INSTANCE_TERMINATED,
                             TERMINATION_TIMEOUT, CHECK_INTERVAL, ctx=ctx)


@operation
def creation_validation(**kwargs):
    instance_id = ctx.instance.runtime_properties['instance_id']
    state = INSTANCE_RUNNING
    timeout_length = 1

    instance_object = utils.get_instance_from_id(instance_id, ctx=ctx)

    if utils.validate_state(instance_object, state,
                            timeout_length, CHECK_INTERVAL, ctx=ctx):
        ctx.logger.info('EC2 Instance is running.')
    else:
        raise NonRecoverableError('EC2 Instance not running.')


def build_arg_dict(user_supplied, unsupported):

    arguments = {}
    for pair in user_supplied.items():
        arguments['{0}'.format(pair[0])] = pair[1]
    for pair in unsupported.items():
        arguments['{0}'.format(pair[0])] = pair[1]
    return arguments

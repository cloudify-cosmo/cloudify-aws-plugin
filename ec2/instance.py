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
from boto.ec2 import EC2Connection as EC2
from boto.exception import EC2ResponseError
from boto.exception import BotoServerError

# Cloudify imports
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from cloudify.decorators import operation
from ec2 import utility

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
def create(**kwargs):
    """ Creates an EC2 instance from an (AMI) image_id and an instance_type.
    """

    arguments = dict()
    arguments['image_id'] = ctx.node.properties['image_id']
    arguments['instance_type'] = ctx.node.properties['instance_type']
    args_to_merge = build_arg_dict(ctx.node.properties['attributes'].copy(),
                                   RUN_INSTANCES_UNSUPPORTED)
    arguments.update(args_to_merge)

    ctx.logger.info('(Node: {0}): Creating instance.'.format(ctx.instance.id))
    ctx.logger.debug('(Node: {0}): Attempting to create instance.'
                     '(Image id: {1}. Instance type: {2}.)'
                     .format(ctx.instance.id, arguments['image_id'],
                             arguments['instance_type']))
    ctx.logger.debug('(Node: {0}): Run instance parameters: {1}.'
                     .format(ctx.instance.id, arguments))

    try:
        reservation = EC2().run_instances(**arguments)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('(Node: {0}): Error. Failed to run '
                                  'instance: API returned: {1}.'
                                  .format(ctx.instance.id, e))

    instance_id = reservation.instances[0].id
    ctx.instance.runtime_properties['instance_id'] = instance_id

    if utility.validate_instance_id(reservation.instances[0].id, ctx=ctx):
        utility.validate_state(reservation.instances[0], INSTANCE_RUNNING,
                               CREATION_TIMEOUT, CHECK_INTERVAL, ctx=ctx)


@operation
def start(**kwargs):
    """ Starts an existing EC2 instance. If already started, this does nothing.
    """

    instance_id = ctx.instance.runtime_properties['instance_id']

    ctx.logger.info('(Node: {0}): Starting instance.'.format(ctx.instance.id))
    ctx.logger.debug('(Node: {0}): Attempting to start instance.'
                     '(Instance id: {1}.)'.format(ctx.instance.id,
                                                  instance_id))

    try:
        instances = EC2().start_instances(instance_id)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('(Node: {0}): Error. Failed to start '
                                  'instance: API returned: {1}.'
                                  .format(ctx.instance.id, e))

    if utility.validate_instance_id(instance_id, ctx=ctx):
        utility.validate_state(instances[0], INSTANCE_RUNNING,
                               START_TIMEOUT, CHECK_INTERVAL, ctx=ctx)


@operation
def stop(**kwargs):
    """ Stops an existing EC2 instance. If already stopped, this does nothing.
    """

    instance_id = ctx.instance.runtime_properties['instance_id']

    ctx.logger.info('(Node: {0}): Stopping instance.'.format(ctx.instance.id))
    ctx.logger.debug('(Node: {0}): Attempting to stop instance.'
                     '(Instance id: {1}.)'.format(ctx.instance.id,
                                                  instance_id))

    try:
        instances = EC2().stop_instances(instance_id)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('(Node: {0}): Error. Failed to stop '
                                  'instance: API returned: {1}.'
                                  .format(ctx.instance.id, e))

    if utility.validate_instance_id(instance_id, ctx=ctx):
        utility.validate_state(instances[0], INSTANCE_STOPPED,
                               STOP_TIMEOUT, CHECK_INTERVAL, ctx=ctx)


@operation
def terminate(**kwargs):
    """ Terminates an existing EC2 instance.
    If already terminated, this does nothing.
    """

    instance_id = ctx.instance.runtime_properties['instance_id']

    ctx.logger.info('(Node: {0}): Terminating instance.'
                    .format(ctx.instance.id))
    ctx.logger.debug('(Node: {0}): Attempting to terminate instance.'
                     '(Instance id: {1}.)'.format(ctx.instance.id,
                                                  instance_id))

    try:
        instances = EC2().terminate_instances(instance_id)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('(Node: {0}): Error. Failed to terminate '
                                  'instance: API returned: {1}.'
                                  .format(ctx.instance.id, e))

    if utility.validate_instance_id(instance_id, ctx=ctx):
        utility.validate_state(instances[0], INSTANCE_TERMINATED,
                               TERMINATION_TIMEOUT, CHECK_INTERVAL, ctx=ctx)


@operation
def creation_validation(**kwargs):
    instance_id = ctx.instance.runtime_properties['instance_id']
    state = INSTANCE_RUNNING
    timeout_length = 1

    instance_object = utility.get_instance_from_id(instance_id, ctx=ctx)

    if utility.validate_state(instance_object, state,
                              timeout_length, CHECK_INTERVAL, ctx=ctx):
        ctx.logger.debug('Instance is running.')
    else:
        raise NonRecoverableError('Instance not running.')


def build_arg_dict(user_supplied, unsupported):

    arguments = {}
    for pair in user_supplied.items():
        arguments['{0}'.format(pair[0])] = pair[1]
    for pair in unsupported.items():
        arguments['{0}'.format(pair[0])] = pair[1]
    return arguments

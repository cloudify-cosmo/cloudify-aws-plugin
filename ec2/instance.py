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

# built-in package
import time

# other packages
from boto.ec2 import EC2Connection as EC2
from boto.exception import EC2ResponseError

# ctx packages
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError, RecoverableError
from cloudify.decorators import operation

# EC2 Instance States
INSTANCE_PENDING = 0
INSTANCE_RUNNING = 16
INSTANCE_SHUTTING_DOWN = 32
INSTANCE_TERMINATED = 48
INSTANCE_STOPPING = 64
INSTANCE_STOPPED = 80

# Timeouts
CREATION_TIMEOUT = 15 * 60
START_TIMEOUT = 15 * 30
STOP_TIMEOUT = 3 * 60
TERMINATION_TIMEOUT = 3 * 60
CHECK_INTERVAL = 20

# EC2 Method Arguments
RUN_INSTANCES_UNSUPPORTED = {
    'min_count': 1,
    'max_count': 1
}


@operation
def create(**kwargs):
    """ Creates an AWS Instance from an (AMI) image_id and an instance_type.
    """

    arguments = dict()
    arguments['image_id'] = ctx.node.properties['image_id']
    arguments['instance_type'] = ctx.node.properties['instance_type']
    arguments_to_merge = build_arg_dict(ctx.node.properties['attributes'].copy(),
                               RUN_INSTANCES_UNSUPPORTED)
    arguments.update(arguments_to_merge)

    ctx.logger.info('(Node: {0}): Creating instance.'.format(ctx.instance.id))
    ctx.logger.debug("""(Node: {0}): Attempting to create instance.
                        (Image id: {1}. Instance type: {2}.)"""
                     .format(ctx.instance.id, arguments['image_id'],
                             arguments['instance_type']))
    ctx.logger.debug('(Node: {0}): Run instance parameters: {1}.'
                     .format(ctx.instance.id, arguments))

    try:
        reservation = EC2().run_instances(**arguments)
    except EC2ResponseError:
        ctx.logger.error("""(Node: {0}): Error.
                         Failed to create instance: API returned: {1}."""
                         .format(ctx.instance.id, EC2ResponseError.body))
        raise NonRecoverableError("""(Node: {0}): Error.
                                     Failed to create instance:
                                     API returned: {1}."""
                                  .format(ctx.instance.id,
                                          EC2ResponseError.body))

    instance_id = reservation.instances[0].id
    ctx.instance.runtime_properties['instance_id'] = instance_id

    ctx.logger.debug("""(Node: {0}):
                        Attempting to verify the instance is running.
                        (Instance id: {1}.)"""
                     .format(ctx.instance.id, instance_id))
    ctx.logger.debug("""(Node: {0}): Checking State: Running, Timeout: {1}.
                        Check Interval: {2}.)"""
                     .format(ctx.instance.id,
                             CREATION_TIMEOUT, CHECK_INTERVAL))

    if _state_validation(instance_id, INSTANCE_RUNNING, CREATION_TIMEOUT,
                         CHECK_INTERVAL):
        ctx.instance.runtime_properties['instance_id'] = instance_id
        ctx.logger.info("""(Node: {0}): Instance started & is running.
                           (Instance id: {1})."""
                        .format(ctx.instance.id, instance_id))
    else:
        ctx.logger.error("""(Node: {0}):
                            Failed to verify that the instance is running.
                            (Instance id: {1})."""
                         .format(ctx.instance.id, instance_id))
        raise NonRecoverableError("""(Node: {0}): Instance did not create within
                                      specified timeout: {0}."""
                                  .format(ctx.instance.id, CREATION_TIMEOUT))


@operation
def start(**kwargs):

    instance_id = ctx.instance.runtime_properties['instance_id']

    ctx.logger.info('(Node: {0}): Starting instance.'.format(ctx.instance.id))
    ctx.logger.debug("""(Node: {0}): Attempting to start instance.
                        (Instance id: {1}.)"""
                     .format(ctx.instance.id, instance_id))

    try:
        EC2().start_instances(instance_id)
    except EC2ResponseError:
        ctx.logger.error("""(Node: {0}): Error.
                         Failed to start instance: API returned: {1}."""
                         .format(ctx.instance.id, EC2ResponseError.body))
        raise NonRecoverableError("""(Node: {0}):
                                     Error. Failed to start instance:
                                     API returned: {1}."""
                                  .format(ctx.instance.id,
                                          EC2ResponseError.body))

    ctx.logger.debug("""(Node: {0}): Attempting to verify the instance is started.
                     (Instance id: {1}.)"""
                     .format(ctx.instance.id, instance_id))
    ctx.logger.debug("""(Node: {0}): Checking State: Running, Timeout: {1}.
                        Check Interval: {2}.)"""
                     .format(ctx.instance.id,
                             CREATION_TIMEOUT, CHECK_INTERVAL))

    if _state_validation(instance_id, INSTANCE_RUNNING,
                         START_TIMEOUT, CHECK_INTERVAL):
        ctx.logger.info("""(Node: {0}): Instance started & is running.
                           (Instance id: {1})."""
                        .format(ctx.instance.id, instance_id))
    elif _state_validation(instance_id, INSTANCE_RUNNING,
                           START_TIMEOUT, CHECK_INTERVAL):
        ctx.logger.debug("""(Node: {0}): Instance still starting, but didn\'t
                            start within specified timeout {0}."""
                         .format(ctx.instance.id, START_TIMEOUT))
        raise RecoverableError("""(Node: {0}): Instance still starting,
                                  but didn\'t start within specified timeout:
                                  {0}."""
                               .format(ctx.instance.id, START_TIMEOUT))
    else:
        ctx.logger.error("""(Node: {0}):
                            Failed to verify that the instance is running.
                            (Instance id: {1})."""
                         .format(ctx.instance.id, instance_id))
        raise NonRecoverableError("""(Node: {0}):
                                     Instance did not create within specified
                                     timeout: {0}."""
                                  .format(ctx.instance.id, START_TIMEOUT))


@operation
def stop(**kwargs):

    instance_id = ctx.instance.runtime_properties['instance_id']

    ctx.logger.info('(Node: {0}): Stopping instance.'.format(ctx.instance.id))
    ctx.logger.debug('(Node: {0}): Attempting to stop instance.'
                     .format(ctx.instance.id))

    try:
        EC2().stop_instances(instance_id)
    except EC2ResponseError:
        ctx.logger.error("""(Node: {0}): Error.
                         Failed to stop instance: API returned: {1}."""
                         .format(ctx.instance.id, EC2ResponseError.body))
        raise NonRecoverableError("""(Node: {0}): Error.
                                     Failed to stop instance: API returned:
                                     {1}."""
                                  .format(ctx.instance.id,
                                          EC2ResponseError.body))

    ctx.logger.debug("""(Node: {0}):
                        Attempting to verify the instance is stopped.
                     (Instance id: {1}.)"""
                     .format(ctx.instance.id, instance_id))
    ctx.logger.debug("""(Node: {0}): Checking State: Stopped, Timeout: {1}
                        Check Interval: {2}.)"""
                     .format(ctx.instance.id,
                             CREATION_TIMEOUT, CHECK_INTERVAL))

    if _state_validation(instance_id, INSTANCE_STOPPED,
                         STOP_TIMEOUT, CHECK_INTERVAL):
        ctx.logger.info('(Node: {0}): Instance stopped. (Instance id: {1}).'
                        .format(ctx.instance.id, instance_id))
    elif _state_validation(instance_id, INSTANCE_STOPPED,
                           STOP_TIMEOUT, CHECK_INTERVAL):
        ctx.logger.debug("""(Node: {0}):
                            Instance didn\'t stop within specified timeout
                            {0}."""
                         .format(ctx.instance.id, STOP_TIMEOUT))
        raise RecoverableError("""(Node: {0}): Instance didn\'t stop within
                                  specified timeout: {0}."""
                               .format(ctx.instance.id, STOP_TIMEOUT))
    else:
        ctx.logger.error("""(Node: {0}): Failed to verify that the instance is
                            stopped. (Instance id: {1})."""
                         .format(ctx.instance.id, instance_id))
        raise NonRecoverableError("""(Node: {0}): Instance did not stop within
                                     specified timeout: {0}."""
                                  .format(ctx.instance.id, STOP_TIMEOUT))


@operation
def terminate(**kwargs):

    instance_id = ctx.instance.runtime_properties['instance_id']

    ctx.logger.info('(Node: {0}): Terminating instance.'
                    .format(ctx.instance.id))
    ctx.logger.debug('(Node: {0}): Attempting to terminate instance.'
                     .format(ctx.instance.id))

    try:
        EC2().terminate_instances(instance_id)
    except EC2ResponseError:
        ctx.logger.error("""(Node: {0}): Error.
                         Failed to terminate instance: API returned: {1}."""
                         .format(ctx.instance.id, EC2ResponseError.body))
        raise NonRecoverableError("""(Node: {0}): Error.
                                     Failed to terminate instance:
                                     API returned: {1}."""
                                  .format(ctx.instance.id,
                                          EC2ResponseError.body))

    ctx.logger.debug("""(Node: {0}):
                        Attempting to verify the instance is terminated.
                     (Instance id: {1}.)"""
                     .format(ctx.instance.id, instance_id))
    ctx.logger.debug("""(Node: {0}): Checking State: terminated, Timeout: {1}.
                        Check Interval: {2}.)"""
                     .format(ctx.instance.id, TERMINATION_TIMEOUT,
                             CHECK_INTERVAL))

    if _state_validation(instance_id, INSTANCE_TERMINATED,
                         TERMINATION_TIMEOUT, CHECK_INTERVAL):
        ctx.logger.info('(Node: {0}): Instance terminated. (Instance id: {1}).'
                        .format(ctx.instance.id, instance_id))
        del ctx.instance.runtime_properties['instance_id']
    else:
        ctx.logger.error("""(Node: {0}):
                            Failed to verify that the instance is terminated.
                            (Instance id: {1})."""
                         .format(ctx.instance.id, instance_id))
        raise NonRecoverableError("""(Node: {0}): Instance did not terminate
                                     within specified timeout: {0}."""
                                  .format(ctx.instance.id,
                                          TERMINATION_TIMEOUT))


def _state_validation(instance_id, state, timeout_length, check_interval):

    ctx.logger.debug("""Beginning state validation: instance id: {0},
                        states: {1}, timeout length: {2}""")

    timeout = time.time() + timeout_length

    while True:
        instance_state = EC2().get_all_instance_status(
            instance_ids=instance_id)[0]
        if state == int(instance_state.state_code):
            return True
        elif time.time() > timeout:
            return False
        else:
            time.sleep(check_interval)


@operation
def creation_validation(**kwargs):
    instance_id = ctx.instance.runtime_properties['instance_id']
    state = INSTANCE_RUNNING
    timeout_length = CREATION_TIMEOUT

    if _state_validation(instance_id, state, timeout_length, CHECK_INTERVAL):
        ctx.logger.debug('Instance is running.')
    else:
        raise NonRecoverableError('Instance not running.')


def build_arg_dict(user_supplied, unsupported):

    arguments = {}
    for pair in user_supplied.items():
        arguments[pair[0]] = pair[1]
    for pair in unsupported.items():
        arguments[pair[0]] = pair[1]
    return arguments

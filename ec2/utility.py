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

# built-in imports
import time

# other imports
from boto.ec2 import EC2Connection as EC2
from boto.exception import EC2ResponseError, BotoServerError

# Cloudify imports
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError


def validate_state(instance, state, timeout_length, check_interval):
    """ Check if an EC2 instance is in a particular state.

    :param instance: And EC2 instance.
    :param state: The state code (pending = 0, running = 16,
                  shutting down = 32, terminated = 48, stopping = 64,
                  stopped = 80
    :param timeout_length: How long to wait for a positive answer
           before we stop checking.
    :param check_interval: How long to wait between checks.
    :return: bool (True the desired state was reached, False, it was not.)
    """

    ctx.logger.debug('(Node: {0}): Attempting state validation: '
                     'instance id: {0}, state: {1}, timeout length: {2}, '
                     'check interval: {3}.'.format(instance.id, state,
                                                   timeout_length,
                                                   check_interval))

    timeout = time.time() + timeout_length

    while True:
        if state == get_instance_state(instance):
            ctx.logger.info('(Node: {0}): '
                            'Instance state validated: instance {0}.'
                            .format(instance.state))
            return True
        elif time.time() > timeout:
            ctx.logger.error('(Node: {0}): Timed out during instance '
                             'state validation: instance: {1}, '
                             'timeout length: {2}, '
                             'check interval: {3}.'
                             .format(ctx.instance.node, instance.id,
                                     timeout_length, check_interval))
            raise NonRecoverableError('(Node: {0}): Timed out during'
                                      'instance state validation: '
                                      'instance: {1}, '
                                      'timeout length: {2}, '
                                      'check interval: {3}.'
                                      .format(ctx.instance.id,
                                              timeout_length,
                                              check_interval))
        time.sleep(check_interval)


def get_instance_state(instance, ctx):
    """

    :param instance:
    :return:
    """

    state = instance.update()
    ctx.logger.debug('(Node: {0}): Instance state is {1}.'
                     .format(ctx.instance.id, state))
    return instance.state_code


def handle_ec2_error(ctx_instance_id, ec2_error, action, ctx):
    """

    :param ctx_instance_id: the Cloudify Context node ID
    :param ec2_error: EC2 Error Object
    :param action: A string that fits in nicely with the error code :)
    """

    ctx.logger.error('(Node: {0}): Error. Failed to {1} instance: '
                     'API returned: {2}.'
                     .format(ctx_instance_id, action, ec2_error))

    raise NonRecoverableError('(Node: {0}): Error. '
                              'Failed to {1} instance: '
                              'API returned: {2}.'
                              .format(ctx_instance_id, action, ec2_error))


def validate_instance_id(instance_id, ctx):
    """

    :param instance_id: An EC2 instance ID
    :return: True that the instance ID is valid or
             throws unrecoverable error
    """

    try:
        reservations = EC2().get_all_reservations(instance_id)
    except EC2ResponseError:
        handle_ec2_error(ctx.instance.id, EC2ResponseError,
                         'validate')
    except BotoServerError:
        handle_ec2_error(ctx.instance.id, BotoServerError, 'validate')

    instance = reservations[0].instances[0]

    if instance:
        return True
    else:
        ctx.logger.error('(Node: {0}): Unable to validate '
                         'instance ID: {1}.'
                         .format(ctx.instance.id, instance_id))
        raise NonRecoverableError('(Node: {0}): Unable to validate '
                                  'instance ID: {1}.'
                                  .format(ctx.instance.id, instance_id))

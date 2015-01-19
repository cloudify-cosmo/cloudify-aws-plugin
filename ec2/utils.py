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
from boto.exception import EC2ResponseError, BotoServerError

# Cloudify imports
from ec2 import connection
from cloudify.exceptions import NonRecoverableError


def validate_state(instance, state, timeout_length, check_interval, ctx):
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

    if check_interval < 1:
        check_interval = 1

    timeout = time.time() + timeout_length

    while True:
        if state == get_instance_state(instance, ctx=ctx):
            ctx.logger.info('(Node: {0}): '
                            'Instance state validated: instance {0}.'
                            .format(instance.state))
            return True
        elif time.time() > timeout:
            raise NonRecoverableError('(Node: {0}): Timed out during '
                                      'instance state validation: '
                                      'instance: {1}, '
                                      'timeout length: {2}, '
                                      'check interval: {3}.'
                                      .format(ctx.instance.id, instance.id,
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


def validate_instance_id(instance_id, ctx):
    """

    :param instance_id: An EC2 instance ID
    :return: True that the instance ID is valid or
             throws unrecoverable error
    """
    ec2_client = connection.EC2ConnectionClient().client()

    try:
        reservations = ec2_client.get_all_reservations(instance_id)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('(Node: {0}): Error. '
                                  'Failed to validate instance id: '
                                  'API returned: {1}.'
                                  .format(ctx.instance.id, e))

    instance = reservations[0].instances[0]

    if instance:
        return True
    else:
        raise NonRecoverableError('(Node: {0}): Unable to validate '
                                  'instance ID: {1}.'
                                  .format(ctx.instance.id, instance_id))


def get_instance_from_id(instance_id, ctx):
    ec2_client = connection.EC2ConnectionClient().client()

    try:
        reservations = ec2_client.get_all_reservations(instance_id)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('(Node: {0}): Error. '
                                  'Failed to get instance by id: '
                                  'API returned: {1}.'
                                  .format(ctx.instance.id, e))

    instance = reservations[0].instances[0]

    return instance


def validate_group(group, ctx):
    ctx.logger.debug('Testing if group with identifier '
                     ' {0} exists in this account.'.format(group))
    groups = get_security_group_from_id(group, ctx)

    if groups is not None:
        return True
    else:
        return False


def get_security_group_from_id(group, ctx):
    ec2_client = connection.EC2ConnectionClient().client()
    ctx.logger.debug('Getting Security Group by ID: {0}'.format(group))

    try:
        groups = ec2_client.get_all_security_groups(group_ids=group)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('(Node: {0}): Error. '
                                  'Failed to group by id: '
                                  'API returned: {1}.'
                                  .format(ctx.instance.id, e))
    return groups


def save_key_pair(key_pair_object, ctx):
    """ Saves the key pair to the file specified in the blueprint
    """

    ctx.logger.debug('Attempting to save the key_pair_object.')

    try:
        key_pair_object.save(ctx.node.properties['private_key_path'])
    except OSError:
        raise NonRecoverableError('Unable to save key pair to file: {0}.'
                                  'OS Returned: {1}'.format(
                                      ctx.node.properties['private_key_path'],
                                      OSError))

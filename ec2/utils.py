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

    ctx.logger.debug('Attempting state validation: '
                     'instance id: {0}, state: {1}, timeout length: {2}, '
                     'check interval: {3}.'.format(instance.id, state,
                                                   timeout_length,
                                                   check_interval))

    if check_interval < 1:
        check_interval = 1

    timeout = time.time() + timeout_length

    while True:
        if state == get_instance_state(instance, ctx=ctx):
            ctx.logger.info('Instance state validated: instance {0}.'
                            .format(instance.state))
            return True
        elif time.time() > timeout:
            raise NonRecoverableError('Timed out during '
                                      'instance state validation: '
                                      'instance: {0}, '
                                      'timeout length: {1}, '
                                      'check interval: {2}.'
                                      .format(instance.id,
                                              timeout_length,
                                              check_interval))
        time.sleep(check_interval)


def get_instance_state(instance, ctx):
    """ Gets the instance's current state
    """

    ctx.logger.debug('Checking the instance state for {0}.'
                     .format(instance.id))
    state = instance.update()
    ctx.logger.debug('Instance state is {0}.'
                     .format(state))
    return instance.state_code


def validate_instance_id(instance_id, ctx):
    """ Checks to see if instance_id resolves an instance from
        get_all_reservations
    """
    ec2_client = connection.EC2ConnectionClient().client()

    try:
        ec2_client.get_all_reservations(instance_id)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('Error. Failed to validate instance id: '
                                  'API returned: {0}.'
                                  .format(e))

    return True


def get_instance_from_id(instance_id, ctx):
    """ using the instance_id retrieves the instance object
        from the API and returns the object.
    """
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


def get_instance_attribute(instance, attribute, timeout_length):
    """ given the related instance object
        the given variable can be retrieved and returned
    """
    timeout = time.time() + timeout_length

    while instance.update() != 'running':
        time.sleep(5)
        if time.time() > timeout:
            raise NonRecoverableError('Timed out while attemting to get the '
                                      'instance {0}. Timeout length: {1}.'
                                      .format(attribute, timeout_length))
    attribute = getattr(instance, attribute)
    return attribute


def get_private_dns_name(instance, timeout_length):
    """ returns the private_dns_name variable for a given instance
    """
    return get_instance_attribute(instance,
                                  'private_dns_name', timeout_length)


def get_public_dns_name(instance, timeout_length):
    """ returns the public_dns_name variable for a given instance
    """
    return get_instance_attribute(instance,
                                  'public_dns_name', timeout_length)


def get_private_ip_address(instance, timeout_length):
    """ returns the private_ip_address variable for a given instance
    """
    return get_instance_attribute(instance,
                                  'private_ip_address', timeout_length)


def get_public_ip_address(instance, timeout_length):
    """ returns the public_ip_address variable for a given instance
    """
    return get_instance_attribute(instance,
                                  'public_ip_address', timeout_length)


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

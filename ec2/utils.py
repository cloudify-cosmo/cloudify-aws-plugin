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


def get_instance_variable(instance, variable):
    """ given the related instance object
        the given variable can be retrieved and returned
    """
    while instance.update() != 'running':
        time.sleep(5)
    variable = getattr(instance, variable)
    return variable


def get_private_dns_name(instance):
    """ returns the private_dns_name variable for a given instance
    """
    return get_instance_variable(instance, 'private_dns_name')


def get_public_dns_name(instance):
    """ returns the public_dns_name variable for a given instance
    """
    return get_instance_variable(instance, 'public_dns_name')


def get_private_ip_address(instance):
    """ returns the private_ip_address variable for a given instance
    """
    return get_instance_variable(instance, 'private_ip_address')


def get_public_ip_address(instance):
    """ returns the public_ip_address variable for a given instance
    """
    return get_instance_variable(instance, 'public_ip_address')

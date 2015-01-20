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

# Built-in Imports
import os

# Third-party Imports
import boto.exception

# Cloudify Imports
from ec2 import connection
from cloudify.exceptions import NonRecoverableError, RecoverableError


def get_instance_state(instance_id, ctx):
    instance = get_instance_from_id(instance_id, ctx=ctx)
    ctx.logger.debug('Checking the instance state for {0}.'
                     .format(instance.id))
    state = instance.update()
    ctx.logger.debug('Instance state is {0}.'
                     .format(state))
    return instance.state_code


def get_instance_from_id(instance_id, ctx):
    """ using the instance_id retrieves the instance object
        from the API and returns the object.
    """
    ec2_client = connection.EC2ConnectionClient().client()

    try:
        reservations = ec2_client.get_all_reservations(instance_id)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('Error. '
                                  'Failed to get instance by id: '
                                  'API returned: {1}.'
                                  .format(ctx.instance.id, str(e)))

    instance = reservations[0].instances[0]

    return instance


def get_instance_attribute(instance_id, attribute, check_interval, ctx):
    """ given the related instance object
        the given variable can be retrieved and returned
    """

    instance = get_instance_from_id(instance_id, ctx=ctx)
    if 'running' not in instance.update():
        raise RecoverableError('Waiting for server to be running. '
                               'Retrying...', retry_after=check_interval)

    attribute = getattr(instance, attribute)
    return attribute


def get_private_dns_name(instance, check_interval, ctx):
    """ returns the private_dns_name variable for a given instance
    """
    return get_instance_attribute(instance, 'private_dns_name',
                                  check_interval, ctx=ctx)


def get_public_dns_name(instance, check_interval, ctx):
    """ returns the public_dns_name variable for a given instance
    """
    return get_instance_attribute(instance, 'public_dns_name',
                                  check_interval, ctx=ctx)


def get_private_ip_address(instance, check_interval, ctx):
    """ returns the private_ip_address variable for a given instance
    """
    return get_instance_attribute(instance, 'private_ip_address',
                                  check_interval, ctx=ctx)


def get_public_ip_address(instance, check_interval, ctx):
    """ returns the public_ip_address variable for a given instance
    """
    return get_instance_attribute(instance, 'ip_address',
                                  check_interval, ctx=ctx)


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
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('(Node: {0}): Error. '
                                  'Failed to group by id: '
                                  'API returned: {1}.'
                                  .format(ctx.instance.id, str(e)))
    return groups


def save_key_pair(key_pair_object, ctx):
    """ Saves the key pair to the file specified in the blueprint. """

    ctx.logger.debug('Attempting to save the key_pair_object.')

    try:
        key_pair_object.save(ctx.node.properties['private_key_path'])
    except OSError:
        raise NonRecoverableError('Unable to save key pair to file: {0}.'
                                  'OS Returned: {1}'.format(
                                      ctx.node.properties['private_key_path'],
                                      OSError))


def delete_key_pair(key_pair_name, ctx):
    """ Deletes the key pair in the file specified in the blueprint. """

    ctx.logger.debug('Attempting to save the key_pair_object.')

    path = os.path.expanduser(ctx.node.properties['private_key_path'])
    file = os.path.join(path,
                        '{0}{1}'.format(
                            ctx.node.properties['resource_id'],
                            '.pem'))
    if os.path.exists(file):
        try:
            os.remove(file)
        except OSError:
            raise NonRecoverableError('Unable to save key pair to file: {0}.'
                                      'OS Returned: {1}'.format(path,
                                                                str(OSError)))

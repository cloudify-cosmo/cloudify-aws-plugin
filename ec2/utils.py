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
import time

# Third-party Imports
import boto.exception

# Cloudify Imports
from ec2 import connection
from cloudify.exceptions import NonRecoverableError, RecoverableError


def build_arg_dict(user_supplied, unsupported):

    arguments = {}
    for key in user_supplied.keys():
        if 'security_groups' in key and \
                type(user_supplied.get(key)) is not list:
            arguments['{0}'.format(key)] = user_supplied.get(key, None).split()
        arguments['{0}'.format(key)] = user_supplied.get(key, None)
    for key in unsupported.keys():
        arguments['{0}'.format(key)] = unsupported[key]
    return arguments


def validate_node_property(property_key, ctx):
    """ checks if the node property exists in the blueprint
        if not, raises unrecoverable Error
    """

    if property_key not in ctx.node.properties.keys() \
            or ctx.node.properties.get(property_key) is None:
        raise NonRecoverableError('{0} is a required input .'
                                  'Unable to create.'.format(property_key))


def save_key_pair(key_pair_object, ctx):
    """ Saves the key pair to the file specified in the blueprint. """

    ctx.logger.debug('Attempting to save the key_pair_object.')

    try:
        key_pair_object.save(ctx.node.properties['private_key_path'])
    except (boto.exception.BotoClientError, OSError) as e:
        raise NonRecoverableError('Unable to save key pair to file: {0}.'
                                  'OS Returned: {1}'.format(
                                      ctx.node.properties['private_key_path'],
                                      str(e)))
    path = os.path.expanduser(ctx.node.properties['private_key_path'])
    key_path = os.path.join(path,
                            '{0}{1}'.format(
                                ctx.node.properties['resource_id'],
                                '.pem'))
    os.chmod(key_path, 0400)


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


def search_for_key_file(ctx):
    """ Indicates whether the file exists locally. """

    path = os.path.expanduser(ctx.node.properties['private_key_path'])
    file = os.path.join(path,
                        '{0}{1}'.format(
                            ctx.node.properties['resource_id'],
                            '.pem'))
    if os.path.exists(file):
        return True
    else:
        return False


def get_instance_attribute(attribute, check_interval, ctx):
    """ given the related instance object
        the given variable can be retrieved and returned
    """

    instance_id = ctx.instance.runtime_properties['aws_resource_id']
    instance = get_instance_from_id(instance_id, ctx=ctx)
    if 'running' not in instance.update():
        raise RecoverableError('Waiting for server to be running. '
                               'Retrying...', retry_after=check_interval)

    attribute = getattr(instance, attribute)
    return attribute


def get_private_dns_name(check_interval, ctx):
    """ returns the private_dns_name variable for a given instance
    """
    return get_instance_attribute('private_dns_name', check_interval, ctx=ctx)


def get_public_dns_name(check_interval, ctx):
    """ returns the public_dns_name variable for a given instance
    """
    return get_instance_attribute('public_dns_name', check_interval, ctx=ctx)


def get_private_ip_address(check_interval, ctx):
    """ returns the private_ip_address variable for a given instance
    """
    return get_instance_attribute('private_ip_address',
                                  check_interval, ctx=ctx)


def get_public_ip_address(check_interval, ctx):
    """ returns the public_ip_address variable for a given instance
    """
    return get_instance_attribute('ip_address', check_interval, ctx=ctx)


def get_instance_state(ctx):
    instance_id = ctx.instance.runtime_properties['aws_resource_id']
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
    ctx.logger.debug('Getting Instance by ID: {0}'.format(instance_id))

    try:
        reservations = ec2_client.get_all_reservations(instance_id)
    except boto.exception.EC2ResponseError as e:
        report_all_instances(ctx=ctx)
        raise NonRecoverableError('Error. '
                                  'Failed to get instance by id: '
                                  'API returned: {0}.'
                                  .format(str(e)))
    except boto.exception.BotoServerError as e:
        raise NonRecoverableError('Error. '
                                  'Failed to get instance by id: '
                                  'API returned: {0}.'
                                  .format(str(e)))

    instance = reservations[0].instances[0]

    return instance


def get_security_group_from_id(group_id, ctx):
    ec2_client = connection.EC2ConnectionClient().client()
    ctx.logger.debug('Getting Security Group by ID: {0}'.format(group_id))

    try:
        group = ec2_client.get_all_security_groups(group_ids=group_id)
    except boto.exception.EC2ResponseError as e:
        group = get_security_group_from_name(group_id, ctx=ctx)
        raise NonRecoverableError('Error. '
                                  'Failed to group by id: '
                                  'API returned: {0}.'
                                  .format(str(e)))
    except boto.exception.BotoServerError as e:
        raise NonRecoverableError('Error. '
                                  'Failed to group by id: '
                                  'API returned: {0}.'
                                  .format(str(e)))

    if len(group) < 1:
        group = get_security_group_from_name(group_id, ctx=ctx)
    elif len(group) > 1:
        report_all_security_groups(ctx=ctx)
        raise NonRecoverableError('Error. '
                                  'Failed to group by id or name: '
                                  'Too many groups returned.')

    return group


def get_security_group_from_name(group_name, ctx):
    ec2_client = connection.EC2ConnectionClient().client()
    try:
        group = ec2_client.get_all_security_groups(groupnames=group_name)
    except boto.exception.EC2ResponseError as e:
        report_all_security_groups(ctx=ctx)
        raise NonRecoverableError('Error. '
                                  'Failed to group by id: '
                                  'API returned: {0}.'
                                  .format(str(e)))
    except boto.exception.BotoServerError as e:
        raise NonRecoverableError('Error. '
                                  'Failed to group by id: '
                                  'API returned: {0}.'
                                  .format(str(e)))
    if len(group) is not 1:
        report_all_security_groups(ctx=ctx)
        raise NonRecoverableError('Error. '
                                  'Failed to group by id or name: '
                                  'Too many groups returned.')

    return group


def get_key_pair_by_id(ctx):
    ec2_client = connection.EC2ConnectionClient().client()

    try:
        key = ec2_client.get_key_pair(ctx.node.properties['resource_id'])
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('Error. '
                                  'Failed to get key pair: '
                                  'API returned: {0}.'
                                  .format(str(e)))

    return key.name


def get_address_by_id(address_id, ctx):
    ec2_client = connection.EC2ConnectionClient().client()
    try:
        address = ec2_client.get_all_addresses(address_id)
    except boto.exception.EC2ResponseError as e:
        report_all_addresses(ctx=ctx)
        raise NonRecoverableError('Error. '
                                  'Failed to get address by id: '
                                  'API returned: {0}.'
                                  .format(str(e)))
    except (boto.exception.BotoServerError) as e:
        raise NonRecoverableError('Error. '
                                  'Failed to get address by id: '
                                  'API returned: {0}.'
                                  .format(str(e)))
    return address.public_ip


def get_address_object_by_id(address_id, ctx):
    ec2_client = connection.EC2ConnectionClient().client()
    try:
        address = ec2_client.get_all_addresses(address_id)
    except boto.exception.EC2ResponseError as e:
        report_all_addresses(ctx=ctx)
        raise NonRecoverableError('Error. '
                                  'Failed to get address by id: '
                                  'API returned: {0}.'
                                  .format(str(e)))
    except (boto.exception.BotoServerError) as e:
        raise NonRecoverableError('Error. '
                                  'Failed to get address by id: '
                                  'API returned: {0}.'
                                  .format(str(e)))
    return address


def report_all_instances(ctx):
    ec2_client = connection.EC2ConnectionClient().client()

    try:
        reservations = ec2_client.get_all_reservations()
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('Error. '
                                  'Failed to report all instances: '
                                  'API returned: {0}.'
                                  .format(str(e)))

    instances = [instance for res in reservations
                 for instance in res.instances]

    message = []
    for instance in instances:
        message.append('{}\n'.format(instance))

    ctx.logger.info('Available instances: {0}'.format(message))


def report_all_security_groups(ctx):
    ec2_client = connection.EC2ConnectionClient().client()

    try:
        groups = ec2_client.get_all_security_groups()
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('Error. '
                                  'Failed to report security groups: '
                                  'API returned: {0}.'
                                  .format(str(e)))
    message = []
    for group in groups:
        message.append('{}\n'.format(group))

    ctx.logger.info('Available groups: {0}'.format(message))


def report_all_addresses(ctx):
    ec2_client = connection.EC2ConnectionClient().client()
    try:
        addresses = ec2_client.get_all_addresses()
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('Error. '
                                  'Failed to report all addresses: '
                                  'API returned: {0}.'
                                  .format(str(e)))
    message = []
    for address in addresses:
        message.append('{}\n'.format(address))

    ctx.logger.info('Available addresses: {0}'.format(message))


def validate_state(instance_id, state, timeout_length, check_interval, ctx):
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
                     'check interval: {3}.'.format(instance_id, state,
                                                   timeout_length,
                                                   check_interval))

    instance = get_instance_from_id(instance_id, ctx=ctx)

    if check_interval < 1:
        check_interval = 1

    timeout = time.time() + timeout_length

    while True:
        instance.update()
        if state == int(instance.state_code):
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


def assign_runtime_properties_to_instance(retry_interval, ctx):

        ctx.instance.runtime_properties['private_dns_name'] = \
            get_private_dns_name(retry_interval, ctx=ctx)
        ctx.instance.runtime_properties['public_dns_name'] = \
            get_public_dns_name(retry_interval, ctx=ctx)
        ctx.instance.runtime_properties['public_ip_address'] = \
            get_public_ip_address(retry_interval, ctx=ctx)
        ctx.instance.runtime_properties['ip'] = \
            get_private_ip_address(retry_interval, ctx=ctx)
        ctx.logger.info('Public DNS: {}.'.format(
            ctx.instance.runtime_properties['public_dns_name']))
        ctx.logger.info('Public IP: {}.'.format(
            ctx.instance.runtime_properties['public_ip_address']))
        ctx.logger.info('Private DNS: {}.'.format(
            ctx.instance.runtime_properties['private_dns_name']))
        ctx.logger.info('Private IP (the ip): {}.'.format(
            ctx.instance.runtime_properties['ip']))

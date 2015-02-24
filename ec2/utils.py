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
import time

# Third-party Imports
import boto.exception

# Cloudify Imports
from ec2 import connection
from cloudify.exceptions import NonRecoverableError, RecoverableError


def get_parameters(ctx):
    """ These are the list of supported arguments to the run_instances
        function and their default values. Essentially, this checks to see
        if the user provided a value and takes the user's value. If the
        user did not provide a value, the key is deleted from the
        dictionary.
      :param ctx:  The Cloudify ctx context. This function uses the
                   node.properties attribute.
      :returns parameters dictionary
    """

    attached_group_ids = get_attached_security_group_ids(ctx=ctx)

    parameters = {
        'image_id': None, 'key_name': None, 'security_groups': None,
        'user_data': None, 'addressing_type': None,
        'instance_type': 'm1.small', 'placement': None, 'kernel_id': None,
        'ramdisk_id': None, 'monitoring_enabled': False, 'subnet_id': None,
        'block_device_map': None, 'disable_api_termination': False,
        'instance_initiated_shutdown_behavior': None,
        'private_ip_address': None, 'placement_group': None,
        'client_token': None, 'security_group_ids': None,
        'additional_info': None, 'instance_profile_name': None,
        'instance_profile_arn': None, 'tenancy': None, 'ebs_optimized': False,
        'network_interfaces': None, 'dry_run': False
    }

    node_parameter_keys = ctx.node.properties['parameters'].keys()

    for key in parameters.keys():
        if key is 'security_group_ids':
            if key in node_parameter_keys:
                parameters[key] = list(
                    set(attached_group_ids) | set(
                        ctx.node.properties['parameters'][key])
                )
            else:
                parameters[key] = attached_group_ids
        elif key is 'key_name':
            if key in node_parameter_keys:
                parameters[key] = ctx.node.properties['parameters'][key]
            else:
                parameters[key] = get_attached_keypair_id(ctx)
        elif key in node_parameter_keys:
            parameters[key] = ctx.node.properties['parameters'][key]
        elif key is 'image_id' or key is 'instance_type':
            parameters[key] = ctx.node.properties[key]
        else:
            del(parameters[key])

    return parameters


def validate_node_property(key, ctx):
    """ checks if the node property exists in the blueprint
        if not, raises unrecoverable Error
    """

    if key not in ctx.node.properties.keys() \
            or ctx.node.properties.get(key) is None:
        raise NonRecoverableError('{0} is a required input .'
                                  'Unable to create.'.format(key))


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
    ctx.logger.debug('Getting Instance by ID: {0}'.format(instance_id))

    instance = get_all_instances(ctx=ctx, list_of_instance_ids=instance_id)

    return instance


def get_attached_keypair_id(ctx):
    relationship_type = 'instance_connected_to_keypair'

    kplist = get_target_aws_resource_id(relationship_type, ctx=ctx)
    if kplist:
        return kplist[0]
    else:
        return kplist


def get_attached_security_group_ids(ctx):
    relationship_type = 'instance_connected_to_security_group'

    return get_target_aws_resource_id(relationship_type, ctx=ctx)


def get_target_aws_resource_id(relationship_type, ctx):
    """ This loops through the relationships of type and returns
        targets of those relationships.
    """

    ids = []

    if not hasattr(ctx.instance, 'relationships'):
        ctx.logger.info('Skipping attaching relationships, '
                        'because none are attached.')
        return ids

    for r in ctx.instance.relationships:
        if relationship_type in r.type:
            ids.append(
                r.target.instance.runtime_properties['aws_resource_id'])

    return ids


def get_key_pair_by_id(key_pair_id):
    ec2_client = connection.EC2ConnectionClient().client()

    try:
        key_pair = ec2_client.get_key_pair(key_pair_id)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('Failed to get key pair: {0}.'
                                  .format(str(e)))

    return key_pair


def get_security_group_from_id(group_id, ctx):

    group = get_all_security_groups(ctx=ctx, list_of_group_names=group_id)

    return group


def get_security_group_from_name(group_name, ctx):

    group = get_all_security_groups(ctx=ctx, list_of_group_names=group_name)

    return group


def get_address_by_id(address_id, ctx):

    address = get_address_object_by_id(address_id)

    return address.public_ip


def get_address_object_by_id(address_id, ctx):

    address = get_all_addresses(address_id, ctx=ctx)

    return address


def get_all_instances(ctx, list_of_instance_ids=None):
    ec2_client = connection.EC2ConnectionClient().client()

    try:
        reservations = ec2_client.get_all_reservations(list_of_instance_ids)
    except boto.exception.BotoServerError as e:
        raise NonRecoverableError('Failed to report all instances: '
                                  .format(str(e)))
    except boto.exception.EC2ResponseError as e:
        if 'InvalidInstanceID' in e:
            instances = [instance for res in ec2_client.get_all_reservations()
                         for instance in res.instances]
            log_available_resources(instances, ctx=ctx)
        raise NonRecoverableError('Failed to get requested instance: {0}'
                                  .format(str(e)))

    instances = [instance for res in reservations
                 for instance in res.instances]

    return instances


def get_all_security_groups(ctx,
                            list_of_group_names=None,
                            list_of_group_ids=None):

    ec2_client = connection.EC2ConnectionClient().client()

    try:
        groups = ec2_client.get_all_security_groups(
            groupnames=list_of_group_names,
            group_ids=list_of_group_ids)
    except boto.exception.BotoServerError as e:
        raise NonRecoverableError('Failed to report security groups: '
                                  .format(str(e)))
    except boto.exception.EC2ResponseError as e:
        if 'InvalidGroupId' in e:
            groups = ec2_client.get_all_security_groups()
            log_available_resources(groups, ctx=ctx)
        raise NonRecoverableError('Failed to get requested group: {0}.'
                                  .format(str(e)))

    return groups


def get_all_addresses(address, ctx):

    ec2_client = connection.EC2ConnectionClient().client()

    try:
        addresses = ec2_client.get_all_addresses(address)
    except (boto.exception.BotoServerError) as e:
        raise NonRecoverableError('Failed to get all addresses: {0}.'
                                  .format(str(e)))
    except (boto.exception.EC2ResponseError) as e:
        if 'InvalidAddress' in e:
            addresses = ec2_client.get_all_addresses()
            log_available_resources(addresses, ctx=ctx)
        raise NonRecoverableError('Failed to get requested addresse: {0}.'
                                  .format(str(e)))

    return addresses


def log_available_resources(list_of_resources, ctx):
    """This logs a list of resources.
    """

    message = []

    for resource in list_of_resources:
        message.append('{0}\n'.format(resource))

    ctx.logger.info('Available resources: {0}'.format(list_of_resources))


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

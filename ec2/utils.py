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
import re

# Third-party Imports
import boto.exception

# Cloudify Imports
from ec2 import connection
from ec2 import constants
from cloudify.exceptions import NonRecoverableError


def get_instance_parameters(ctx):
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


def get_image(image_id, ctx):

    ec2_client = connection.EC2ConnectionClient().client()

    if not image_id:
        raise NonRecoverableError(
            'No image_id was provided.')

    try:
        image = ec2_client.get_image(image_id)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}.'.format(str(e)))

    return image


def get_instance_attribute(attribute, ctx):
    """ given the related instance object
        the given variable can be retrieved and returned
    """

    if 'aws_resource_id' not in ctx.instance.runtime_properties:
        raise NonRecoverableError(
            'Unable to get instance attibute {0}, because aws_resource_id '
            'has not been set.'.format(attribute))

    instance_id = ctx.instance.runtime_properties['aws_resource_id']
    instance = get_instance_from_id(instance_id, ctx=ctx)

    if instance is None:
        raise NonRecoverableError(
            'Unable to get instance attibute {0}, because no instance with id '
            '{1} exists in this account.'.format(attribute, instance_id))

    attribute = getattr(instance, attribute)
    return attribute


def get_instance_state(ctx):
    state = get_instance_attribute('state_code', ctx=ctx)
    return state


def get_instance_from_id(instance_id, ctx):
    """ using the instance_id retrieves the instance object
        from the API and returns the object.
    """
    ctx.logger.debug('Getting Instance by ID: {0}'.format(instance_id))

    instance = get_all_instances(ctx=ctx, list_of_instance_ids=instance_id)

    return instance[0] if instance else instance


def get_attached_keypair_id(ctx):
    """ returns a list of provided keypairs
    """

    relationship_type = 'instance_connected_to_keypair'

    kplist = get_target_aws_resource_ids(relationship_type, ctx=ctx)

    return kplist[0] if kplist else kplist


def get_attached_security_group_ids(ctx):
    """ returns a list of attached security groups
    """

    relationship_type = 'instance_connected_to_security_group'

    return get_target_aws_resource_ids(relationship_type, ctx=ctx)


def get_target_aws_resource_ids(relationship_type, ctx):
    """ This loops through the relationships of type and returns
        targets of those relationships.
    """

    ids = []

    if not getattr(ctx.instance, 'relationships', []):
        ctx.logger.info('Skipping attaching relationships, '
                        'because none are attached to this node.')
        return ids

    for r in ctx.instance.relationships:
        if relationship_type in r.type:
            ids.append(
                r.target.instance.runtime_properties['aws_resource_id'])

    return ids


def get_key_pair_by_id(key_pair_id):
    """Returns the key pair object for a given key pair id
    """

    ec2_client = connection.EC2ConnectionClient().client()

    try:
        key_pair = ec2_client.get_key_pair(key_pair_id)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}.'.format(str(e)))

    return key_pair


def get_security_group_from_id(group_id, ctx):
    """ returns the group object for a given group id.
    """

    if not re.match('^sg\-[0-9a-z]{8}$', group_id):
        group = get_security_group_from_name(group_id, ctx)
        return group

    group = get_all_security_groups(ctx=ctx, list_of_group_ids=group_id)

    return group[0] if group else group


def get_security_group_from_name(group_name, ctx):
    """Returns the group object for a given group name.
    """

    if re.match('^sg\-[0-9a-z]{8}$', group_name):
        group = get_security_group_from_id(group_name, ctx)
        return group

    group = get_all_security_groups(ctx=ctx, list_of_group_names=group_name)

    return group[0] if group else group


def get_address_by_id(address_id, ctx):
    """returns the address for a given address_id
    """

    address = get_address_object_by_id(address_id, ctx=ctx)

    return address.public_ip if address else address


def get_address_object_by_id(address_id, ctx):
    """returns the address object for a given address_id
    """

    address = get_all_addresses(ctx, address=address_id)

    return address[0] if address else address


def get_all_instances(ctx, list_of_instance_ids=None):
    """returns a list of instances. If an InvalidInstanceID is raised
    then all of the instances are logged.
    """

    ec2_client = connection.EC2ConnectionClient().client()

    try:
        reservations = ec2_client.get_all_reservations(list_of_instance_ids)
    except boto.exception.EC2ResponseError as e:
        if 'InvalidInstanceID.NotFound' in e:
            instances = [instance for res in ec2_client.get_all_reservations()
                         for instance in res.instances]
            log_available_resources(instances, ctx=ctx)
        return None
    except boto.exception.BotoServerError as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    instances = [instance for res in reservations
                 for instance in res.instances]

    return instances


def get_all_security_groups(ctx,
                            list_of_group_names=None,
                            list_of_group_ids=None):
    """Returns a list of security groups. If an InvalidGroupId error is raised
    then it all of the security groups are logged.
    """

    ec2_client = connection.EC2ConnectionClient().client()

    try:
        groups = ec2_client.get_all_security_groups(
            groupnames=list_of_group_names,
            group_ids=list_of_group_ids)
    except boto.exception.EC2ResponseError as e:
        if 'InvalidGroup.NotFound' in e:
            groups = ec2_client.get_all_security_groups()
            log_available_resources(groups, ctx=ctx)
        return None
    except boto.exception.BotoServerError as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    return groups


def get_all_addresses(ctx, address=None):
    """Returns a list of addresses. If InvalidAddress is raised all
    addresses get logged.
    """

    ec2_client = connection.EC2ConnectionClient().client()

    try:
        addresses = ec2_client.get_all_addresses(address)
    except boto.exception.EC2ResponseError as e:
        if 'InvalidAddress.NotFound' in e:
            addresses = ec2_client.get_all_addresses()
            log_available_resources(addresses, ctx=ctx)
        return None
    except boto.exception.BotoServerError as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    return addresses


def log_available_resources(list_of_resources, ctx):
    """This logs a list of available resources.
    """

    message = 'Available resources: \n'

    for resource in list_of_resources:
        message = '{0}{1}\n'.format(message, resource)

    ctx.logger.debug(message)


def get_external_resource_id_or_raise(operation, ctx):

    ctx.logger.debug(
        'Checking if {0} in instance runtime_properties, for {0} operation.'
        .format(constants.EXTERNAL_RESOURCE_ID, operation))

    if constants.EXTERNAL_RESOURCE_ID not in ctx.instance.runtime_properties:
        raise NonRecoverableError(
            'Cannot {0} because {1} is not assigned.'
            .format(operation, constants.EXTERNAL_RESOURCE_ID))

    return ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID]


def set_external_resource_id(value, ctx, external=True):

    if not external:
        resource_type = 'Cloudify'
    else:
        resource_type = 'external'

    ctx.logger.info(
        'Using {0} resource: {1}'.format(
            resource_type, value))
    ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID] = value

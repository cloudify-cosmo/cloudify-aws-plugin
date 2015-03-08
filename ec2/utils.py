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
from ec2 import constants
from ec2 import connection
from cloudify.exceptions import NonRecoverableError


def get_instance_parameters(ctx):
    """The parameters to the run_instance boto call.

    :param ctx:  The Cloudify ctx context.
    :returns parameters dictionary
    """

    parameters = constants.RUN_INSTANCE_PARAMETERS

    attached_group_ids = get_attached_security_group_ids(ctx=ctx)

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
    """Checks if the node property exists in the blueprint.

    :raises NonRecoverableError: if key not in the node's properties
    """

    if key not in ctx.node.properties:
        raise NonRecoverableError(
            '{0} is a required input. Unable to create.'.format(key))


def get_image(image_id, ctx):
    """Gets the boto object that represents the AMI image for image id.

    :param image_id: The ID of the AMI image.
    :param ctx:  The Cloudify ctx context.
    :returns an object that represents an AMI image.
    """

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
    """Gets an attribute from a boto object that represents an EC2 Instance.

    :param attribute: The named python attribute of a boto object.
    :param ctx:  The Cloudify ctx context.
    :returns python attribute of a boto object representing an EC2 instance.
    :raises NonRecoverableError if constants.EXTERNAL_RESOURCE_ID not set
    :raises NonRecoverableError if no instance is found.
    """

    if constants.EXTERNAL_RESOURCE_ID not in ctx.instance.runtime_properties:
        raise NonRecoverableError(
            'Unable to get instance attibute {0}, because {1} is not set.'
            .format(attribute, constants.EXTERNAL_RESOURCE_ID))

    instance_id = \
        ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID]
    instance = get_instance_from_id(instance_id, ctx=ctx)

    if instance is None:
        raise NonRecoverableError(
            'Unable to get instance attibute {0}, because no instance with id '
            '{1} exists in this account.'.format(attribute, instance_id))

    attribute = getattr(instance, attribute)
    return attribute


def get_instance_state(ctx):
    """Gets the instance state code of a EC2 Instance

    :param ctx:  The Cloudify ctx context.
    :returns a state code from a boto object representing an EC2 Image.
    """
    state = get_instance_attribute('state_code', ctx=ctx)
    return state


def get_instance_from_id(instance_id, ctx):
    """Gets the instance ID of a EC2 Instance

    :param instance_id: The ID of an EC2 Instance
    :param ctx:  The Cloudify ctx context.
    :returns an ID of a an EC2 Instance or None.
    """
    ctx.logger.debug('Getting Instance by ID: {0}'.format(instance_id))

    instance = get_all_instances(ctx=ctx, list_of_instance_ids=instance_id)

    return instance[0] if instance else instance


def get_attached_keypair_id(ctx):
    """Gets the ID of a keypair connected via a relationship to a node.

    :param ctx:  The Cloudify ctx context.
    :returns the ID of a keypair or None.
    """

    relationship_type = 'instance_connected_to_keypair'

    kplist = get_target_aws_resource_ids(relationship_type, ctx=ctx)

    return kplist[0] if kplist else kplist


def get_attached_security_group_ids(ctx):
    """Gets a list of security group ids connected via a relationship to a node.

    :param ctx:  The Cloudify ctx context.
    :returns a list of security group ids.
    """

    relationship_type = 'instance_connected_to_security_group'

    return get_target_aws_resource_ids(relationship_type, ctx=ctx)


def get_target_aws_resource_ids(relationship_type, ctx):
    """Gets a list of target node ids connected via a relationship to a node.

    :param relationship_type: A string representing the type of relationship.
    :param ctx:  The Cloudify ctx context.
    :returns a list of security group ids.
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
    """Returns the key pair object for a given key pair id.

    :param key_pair_id: The ID of a keypair.
    :returns The boto keypair object.
    :raises NonRecoverableError: If EC2 finds no matching key pairs.
    """

    ec2_client = connection.EC2ConnectionClient().client()

    try:
        key_pair = ec2_client.get_key_pair(key_pair_id)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}.'.format(str(e)))

    return key_pair


def get_security_group_from_id(group_id, ctx):
    """Returns the security group object for a given security group id.

    :param ctx:  The Cloudify ctx context.
    :param group_id: The ID of a security group.
    :returns The boto security group object.
    :raises NonRecoverableError: If EC2 finds no matching groups.
    """

    if not re.match('^sg\-[0-9a-z]{8}$', group_id):
        group = get_security_group_from_name(group_id, ctx)
        return group

    group = get_all_security_groups(ctx=ctx, list_of_group_ids=group_id)

    return group[0] if group else group


def get_security_group_from_name(group_name, ctx):
    """Returns the security group object for a given group name.

    :param ctx:  The Cloudify ctx context.
    :param group_name: The name of a security group.
    :returns The boto security group object.
    """

    if re.match('^sg\-[0-9a-z]{8}$', group_name):
        group = get_security_group_from_id(group_name, ctx)
        return group

    group = get_all_security_groups(ctx=ctx, list_of_group_names=group_name)

    return group[0] if group else group


def get_address_by_id(address_id, ctx):
    """Returns the elastip ip for a given address elastip.

    :param ctx:  The Cloudify ctx context.
    :param address_id: The ID of a elastip.
    :returns The boto elastip ip.
    :raises NonRecoverableError: If EC2 finds no matching elastips.
    """

    address = get_address_object_by_id(address_id, ctx=ctx)

    return address.public_ip if address else address


def get_address_object_by_id(address_id, ctx):
    """Returns the elastip object for a given address elastip.

    :param ctx:  The Cloudify ctx context.
    :param address_id: The ID of a elastip.
    :returns The boto elastip object.
    :raises NonRecoverableError: If EC2 finds no matching elastips.
    """

    address = get_all_addresses(ctx, address=address_id)

    return address[0] if address else address


def get_all_instances(ctx, list_of_instance_ids=None):
    """Returns a list of instance objects for a list of instance IDs.

    :param ctx:  The Cloudify ctx context.
    :param address_id: The ID of an EC2 Instance.
    :returns a list of instance objects.
    :raises NonRecoverableError: If Boto errors.
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
    """Returns a list of security groups for a given list of group names and IDs.

    :param ctx:  The Cloudify ctx context.
    :param list_of_group_names: A list of security group names.
    :param list_of_group_ids: A list of security group IDs.
    :returns A list of security group objects.
    :raises NonRecoverableError: If Boto errors.
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
    """Returns a list of elastip objects for a given address elastip.

    :param ctx:  The Cloudify ctx context.
    :param address: The ID of a elastip.
    :returns A list of elasticip objects.
    :raises NonRecoverableError: If Boto errors.
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


def get_external_resource_id_or_raise(operation, ctx_instance, ctx):
    """Checks if the EXTERNAL_RESOURCE_ID runtime_property is set and returns it.

    :param operation: A string representing what is happening.
    :param ctx_instance: The CTX Node-Instance Context.
    :param ctx:  The Cloudify ctx context.
    :returns The EXTERNAL_RESOURCE_ID runtime_property for a CTX Instance.
    :raises NonRecoverableError: If EXTERNAL_RESOURCE_ID has not been set.
    """

    ctx.logger.debug(
        'Checking if {0} in instance runtime_properties, for {0} operation.'
        .format(constants.EXTERNAL_RESOURCE_ID, operation))

    if constants.EXTERNAL_RESOURCE_ID not in ctx_instance.runtime_properties:
        raise NonRecoverableError(
            'Cannot {0} because {1} is not assigned.'
            .format(operation, constants.EXTERNAL_RESOURCE_ID))

    return ctx_instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID]


def set_external_resource_id(value, ctx, external=True):
    """Sets the EXTERNAL_RESOURCE_ID runtime_property for a Node-Instance.

    :param value: the desired EXTERNAL_RESOURCE_ID runtime_property
    :param ctx:  The Cloudify ctx context.
    :param external:  Boolean representing if it is external resource or not.
    """

    if not external:
        resource_type = 'Cloudify'
    else:
        resource_type = 'external'

    ctx.logger.info('Using {0} resource: {1}'.format(resource_type, value))
    ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID] = value


def unassign_runtime_property_from_resource(property_name, ctx_instance, ctx):
    """Pops a runtime_property and reports to debug.

    :param property_name: The runtime_property to remove.
    :param ctx_instance: The CTX Node-Instance Context.
    :param ctx:  The Cloudify ctx context.
    """

    value = ctx_instance.runtime_properties.pop(property_name)
    ctx.logger.debug(
        'Unassigned {0} runtime property: {1}'.format(property_name, value))


def use_external_resource(node_properties, ctx):
    """Checks if use_external_resource node property is true,
    logs the ID and answer to the debug log,
    and returns boolean False (if not external) or True.

    :param node_properties: The ctx node properties for a node.
    :param ctx:  The Cloudify ctx context.
    :returns boolean: False if not external.
    """

    if not node_properties['use_external_resource']:
        ctx.logger.debug(
            'Using Cloudify resource_id: {0}.'
            .format(node_properties['resource_id']))
        return False
    else:
        ctx.logger.debug(
            'Using external resource_id: {0}.'
            .format(node_properties['resource_id']))
        return True

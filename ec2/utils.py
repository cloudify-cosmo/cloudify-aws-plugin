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

# Cloudify Imports
from ec2 import constants
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError


def validate_node_property(key, node_properties):
    """Checks if the node property exists in the blueprint.

    :raises NonRecoverableError: if key not in the node's properties
    """

    if key not in node_properties:
        raise NonRecoverableError(
            '{0} is a required input. Unable to create.'.format(key))


def log_available_resources(list_of_resources, ctx_logger):
    """This logs a list of available resources.
    """

    message = 'Available resources: \n'

    for resource in list_of_resources:
        message = '{0}{1}\n'.format(message, resource)

    ctx_logger.debug(message)


def get_external_resource_id_or_raise(operation, ctx_instance):
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


def set_external_resource_id(value, ctx_instance, external=True):
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
    ctx_instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID] = value


def unassign_runtime_property_from_resource(
        property_name, ctx_instance, ctx_logger):
    """Pops a runtime_property and reports to debug.

    :param property_name: The runtime_property to remove.
    :param ctx_instance: The CTX Node-Instance Context.
    :param ctx:  The Cloudify ctx context.
    """

    value = ctx_instance.runtime_properties.pop(property_name)
    ctx_logger.debug(
        'Unassigned {0} runtime property: {1}'.format(property_name, value))


def use_external_resource(node_properties, ctx_logger):
    """Checks if use_external_resource node property is true,
    logs the ID and answer to the debug log,
    and returns boolean False (if not external) or True.

    :param node_properties: The ctx node properties for a node.
    :param ctx:  The Cloudify ctx context.
    :returns boolean: False if not external.
    """

    if not node_properties['use_external_resource']:
        ctx_logger.debug(
            'Using Cloudify resource_id: {0}.'
            .format(node_properties['resource_id']))
        return False
    else:
        ctx_logger.debug(
            'Using external resource_id: {0}.'
            .format(node_properties['resource_id']))
        return True


def get_target_external_resource_ids(relationship_type):
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
                r.target.instance.runtime_properties[
                    constants.EXTERNAL_RESOURCE_ID])

    return ids


def get_resource_id(ctx):
    """Returns the resource id, if the user doesn't provide one,
    this will create one for them.

    :param node_properties: The node properties dictionary.
    :return resource_id: A string.
    """

    if ctx.node.properties['resource_id']:
        return ctx.node.properties['resource_id']

    return '{0}-{1}'.format(ctx.deployment.id, ctx.instance.id)

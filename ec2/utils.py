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
import json

# Cloudify Imports
from ec2 import constants
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError


def validate_node_property(key, ctx_node_properties):
    """Checks if the node property exists in the blueprint.

    :raises NonRecoverableError: if key not in the node's properties
    """

    if key not in ctx_node_properties:
        raise NonRecoverableError(
            '{0} is a required input. Unable to create.'.format(key))


def log_available_resources(list_of_resources):
    """This logs a list of available resources.
    """

    message = 'Available resources: \n'

    for resource in list_of_resources:
        message = '{0}{1}\n'.format(message, resource)

    ctx.logger.debug(message)


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


def unassign_runtime_property_from_resource(property_name, ctx_instance):
    """Pops a runtime_property and reports to debug.

    :param property_name: The runtime_property to remove.
    :param ctx_instance: The CTX Node-Instance Context.
    :param ctx:  The Cloudify ctx context.
    """

    value = ctx_instance.runtime_properties.pop(property_name)
    ctx.logger.debug(
        'Unassigned {0} runtime property: {1}'.format(property_name, value))


def use_external_resource(ctx_node_properties):
    """Checks if use_external_resource node property is true,
    logs the ID and answer to the debug log,
    and returns boolean False (if not external) or True.

    :param node_properties: The ctx node properties for a node.
    :param ctx:  The Cloudify ctx context.
    :returns boolean: False if not external.
    """

    if not ctx_node_properties['use_external_resource']:
        ctx.logger.debug(
            'Using Cloudify resource_id: {0}.'
            .format(ctx_node_properties['resource_id']))
        return False
    else:
        ctx.logger.debug(
            'Using external resource_id: {0}.'
            .format(ctx_node_properties['resource_id']))
        return True


def get_target_external_resource_ids(relationship_type, ctx_instance):
    """Gets a list of target node ids connected via a relationship to a node.

    :param relationship_type: A string representing the type of relationship.
    :param ctx:  The Cloudify ctx context.
    :returns a list of security group ids.
    """

    ids = []

    if not getattr(ctx_instance, 'relationships', []):
        ctx.logger.info('Skipping attaching relationships, '
                        'because none are attached to this node.')
        return ids

    for r in ctx_instance.relationships:
        if relationship_type in r.type:
            ids.append(
                r.target.instance.runtime_properties[
                    constants.EXTERNAL_RESOURCE_ID])

    return ids


def get_resource_id():
    """Returns the resource id, if the user doesn't provide one,
    this will create one for them.

    :param node_properties: The node properties dictionary.
    :return resource_id: A string.
    """

    if ctx.node.properties['resource_id']:
        return ctx.node.properties['resource_id']
    elif 'private_key_path' in ctx.node.properties:
        directory_path, filename = \
            os.path.split(ctx.node.properties['private_key_path'])
        resource_id, filetype = filename.split('.')
        return resource_id

    return '{0}-{1}'.format(ctx.deployment.id, ctx.instance.id)


def get_provider_variables():

    provider_context = {
        "agents_keypair": _get_variable('agents_keypair'),
        "agents_security_group":
            _get_variable('agents_security_group'),
        "manager_keypair": _get_variable('manager_keypair'),
        "manager_security_group":
            _get_variable('manager_security_group'),
        "manager_resource_id": _get_variable('manager_resource_id'),
        "manager_ip_address": _get_variable('manager_ip_address')
    }

    ctx.logger.info(provider_context)

    return provider_context


def _get_variable(variable_name):

    if variable_name in os.environ:
        return os.environ[variable_name]

    variable_from_file = _get_provider_variable_from_file(variable_name)

    if not variable_from_file:
        return None

    return variable_from_file


def _get_provider_variable_from_file(variable_name):

    aws_configuration = _get_provider_context_file_path()
    provider_context = _get_provider_context(aws_configuration)

    if variable_name in provider_context:
        return provider_context[variable_name]

    return None


def _get_provider_context_file_path():

    if 'home_dir' in ctx.node.properties['cloudify_agent']:
        return os.path.join(
            ctx.node.properties['cloudify_agent']['home_dir'],
            os.path.split(constants.AWS_CONFIG_PATH)[-1])

    return os.path.expanduser(constants.AWS_CONFIG_PATH)


def _get_provider_context(aws_configuration):

    if os.path.exists(aws_configuration):
        try:
            with open(aws_configuration) as provider_context_file:
                return json.load(provider_context_file)
        except ValueError:
            ctx.logger.debug(
                'AWS provider configuration {0} does not contain a JSON '
                'object. This may or may not be intentional.'
                .format(aws_configuration))

    return {}

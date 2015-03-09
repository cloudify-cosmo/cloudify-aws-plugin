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

# Third-party Imports
import boto.exception

# Cloudify imports
from ec2 import utils
from ec2 import constants
from ec2 import connection
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from cloudify.decorators import operation


@operation
def creation_validation(**_):
    """ This checks that all user supplied info is valid """

    for property_key in constants.INSTANCE_REQUIRED_PROPERTIES:
        utils.validate_node_property(property_key, ctx.node.properties)

    instance = _get_instance_from_id(ctx.node.properties['resource_id'])

    if ctx.node.properties['use_external_resource']:
        if not instance:
            raise NonRecoverableError(
                'External resource, but the supplied '
                'instance id is not in the account.')

    if not ctx.node.properties['resource_id']:
        if instance:
            raise NonRecoverableError(
                'Not external resource, but the supplied '
                'but the instance already exists.')

    image_id = ctx.node.properties['image_id']
    image_object = _get_image(image_id)

    if 'available' not in image_object.state:
        raise NonRecoverableError(
            'image_id {0} not available to this account.'.format(image_id))

    if 'ebs' not in image_object.root_device_type:
        raise NonRecoverableError(
            'image_id {0} not ebs-backed. Image must be of type \'ebs\'.'
            .format(image_id))


@operation
def run_instances(**_):
    ec2_client = connection.EC2ConnectionClient().client()

    for property_name in constants.INSTANCE_REQUIRED_PROPERTIES:
        utils.validate_node_property(property_name, ctx.node.properties)

    if _create_external_instance(ctx=ctx):
        return

    instance_parameters = _get_instance_parameters(ctx.node.properties)

    ctx.logger.debug(
        'Attempting to create EC2 Instance with these API parameters: {0}.'
        .format(instance_parameters))

    if ctx.operation.retry_number == 0:
        try:
            reservation = ec2_client.run_instances(**instance_parameters)
        except (boto.exception.EC2ResponseError,
                boto.exception.BotoServerError) as e:
            raise NonRecoverableError('{0}'.format(str(e)))

    instance_id = reservation.instances[0].id

    instance = _get_instance_from_id(instance_id)

    if instance is None:
        return ctx.operation.retry(
            message='Waiting to verify that instance {0} '
            'has been added to your account.'.format(instance_id))

    utils.set_external_resource_id(instance_id, ctx.instance, external=False)


@operation
def start(**_):
    ec2_client = connection.EC2ConnectionClient().client()

    instance_id = \
        utils.get_external_resource_id_or_raise(
            'start instance', ctx.instance)

    if _start_external_instance(instance_id, ctx=ctx):
        return

    if _get_instance_state(ctx.instance) == constants.INSTANCE_STATE_STARTED:
        _instance_started_assign_runtime_properties(instance_id, ctx=ctx)
        return

    ctx.logger.debug('Attempting to start instance: {0}.)'.format(instance_id))

    try:
        ec2_client.start_instances(instance_id)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    ctx.logger.debug('Attempted to start instance {0}.'.format(instance_id))

    if _get_instance_state(ctx.instance) == constants.INSTANCE_STATE_STARTED:
        _instance_started_assign_runtime_properties(instance_id, ctx=ctx)
    else:
        return ctx.operation.retry(
            message='Waiting server to be running. Retrying...')


@operation
def stop(**_):
    ec2_client = connection.EC2ConnectionClient().client()

    instance_id = \
        utils.get_external_resource_id_or_raise(
            'stop instance', ctx.instance)

    if _stop_external_instance(instance_id, ctx=ctx):
        return

    ctx.logger.debug(
        'Attempting to stop EC2 Instance. {0}.)'.format(instance_id))

    try:
        ec2_client.stop_instances(instance_id)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    ctx.logger.debug('Attempted to stop instance {0}.'.format(instance_id))

    if _get_instance_state(ctx.instance) == constants.INSTANCE_STATE_STOPPED:
        _unassign_runtime_properties(
            runtime_properties=constants.INSTANCE_INTERNAL_ATTRIBUTES,
            ctx_instance=ctx.instance)
        ctx.logger.info('Stopped instance {0}.'.format(instance_id))
    else:
        return ctx.operation.retry(
            message='Waiting server to stop. Retrying...')


@operation
def terminate(**_):
    ec2_client = connection.EC2ConnectionClient().client()

    instance_id = \
        utils.get_external_resource_id_or_raise(
            'terminate instance', ctx.instance)

    if _terminate_external_instance(instance_id, ctx=ctx):
        return

    ctx.logger.debug(
        'Attempting to terminate EC2 Instance. {0}.)'.format(instance_id))

    try:
        ec2_client.terminate_instances(instance_id)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    ctx.logger.debug(
        'Attemped to terminate instance {0}'.format(instance_id))

    if _get_instance_state(ctx.instance) == \
            constants.INSTANCE_STATE_TERMINATED:
        ctx.logger.info('Terminated instance: {0}.'.format(instance_id))
        utils.unassign_runtime_property_from_resource(
            constants.EXTERNAL_RESOURCE_ID, ctx.instance)
    else:
        return ctx.operation.retry(
            message='Waiting server to terminate. Retrying...')


def _assign_runtime_properties_to_instance(runtime_properties, ctx):

    for property_name in runtime_properties:
        if 'ip' is property_name:
            ctx.instance.runtime_properties[property_name] = \
                _get_instance_attribute('private_ip_address', ctx.instance)
        elif 'public_ip_address' is property_name:
            ctx.instance.runtime_properties[property_name] = \
                _get_instance_attribute('ip_address', ctx.instance)
        else:
            attribute = _get_instance_attribute(property_name, ctx.instance)

        ctx.logger.debug('Set {0}: {1}.'.format(property_name, attribute))


def _instance_started_assign_runtime_properties(instance_id, ctx):
        _assign_runtime_properties_to_instance(
            runtime_properties=constants.INSTANCE_INTERNAL_ATTRIBUTES, ctx=ctx)
        ctx.logger.info('Instance {0} is running.'.format(instance_id))


def _unassign_runtime_properties(runtime_properties, ctx_instance):
    for property_name in runtime_properties:
        utils.unassign_runtime_property_from_resource(
            property_name, ctx_instance)


def _create_external_instance(ctx):

    if not utils.use_external_resource(ctx.node.properties):
        return False
    else:
        instance_id = ctx.node.properties['resource_id']
        instance = _get_instance_from_id(instance_id)
        if instance is None:
            raise NonRecoverableError(
                'Cannot use_external_resource because instance_id {0} '
                'is not in this account.'.format(instance_id))
        utils.set_external_resource_id(instance.id, ctx.instance)
        return True


def _start_external_instance(instance_id, ctx):

    if not utils.use_external_resource(ctx.node.properties):
        return False
    else:
        ctx.logger.info(
            'Not starting instance {0}, because it is an external resource.'
            .format(instance_id))
        _instance_started_assign_runtime_properties(instance_id)
        return True


def _stop_external_instance(instance_id, ctx):

    if not utils.use_external_resource(ctx.node.properties):
        return False
    else:
        ctx.logger.info(
            'External resource. Not stopping instance {0}.'
            .format(instance_id))
        _unassign_runtime_properties(
            runtime_properties=constants.INSTANCE_INTERNAL_ATTRIBUTES,
            ctx_instance=ctx.instance)
        return True


def _terminate_external_instance(instance_id, ctx):

    if not utils.use_external_resource(ctx.node.properties):
        return False
    else:
        ctx.logger.info(
            'External resource. Not terminating instance {0}.'
            .format(instance_id))
        utils.unassign_runtime_property_from_resource(
            constants.EXTERNAL_RESOURCE_ID, ctx.instance)
        return True


def _get_all_instances(list_of_instance_ids=None):
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
            utils.log_available_resources(instances)
        return None
    except boto.exception.BotoServerError as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    instances = [instance for res in reservations
                 for instance in res.instances]

    return instances


def _get_instance_from_id(instance_id):
    """Gets the instance ID of a EC2 Instance

    :param instance_id: The ID of an EC2 Instance
    :param ctx:  The Cloudify ctx context.
    :returns an ID of a an EC2 Instance or None.
    """

    instance = _get_all_instances(list_of_instance_ids=instance_id)

    return instance[0] if instance else instance


def _get_image(image_id):
    """Gets the boto object that represents the AMI image for image id.

    :param image_id: The ID of the AMI image.
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


def _get_instance_attribute(attribute, ctx_instance):
    """Gets an attribute from a boto object that represents an EC2 Instance.

    :param attribute: The named python attribute of a boto object.
    :param ctx:  The Cloudify ctx context.
    :returns python attribute of a boto object representing an EC2 instance.
    :raises NonRecoverableError if constants.EXTERNAL_RESOURCE_ID not set
    :raises NonRecoverableError if no instance is found.
    """

    if constants.EXTERNAL_RESOURCE_ID not in ctx_instance.runtime_properties:
        raise NonRecoverableError(
            'Unable to get instance attibute {0}, because {1} is not set.'
            .format(attribute, constants.EXTERNAL_RESOURCE_ID))

    instance_id = \
        ctx_instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID]
    instance = _get_instance_from_id(instance_id)

    if instance is None:
        raise NonRecoverableError(
            'Unable to get instance attibute {0}, because no instance with id '
            '{1} exists in this account.'.format(attribute, instance_id))

    attribute = getattr(instance, attribute)
    return attribute


def _get_instance_state(ctx_instance):
    """Gets the instance state code of a EC2 Instance

    :param ctx:  The Cloudify ctx context.
    :returns a state code from a boto object representing an EC2 Image.
    """
    state = _get_instance_attribute('state_code', ctx_instance)
    return state


def _get_instance_parameters(node_properties):
    """The parameters to the run_instance boto call.

    :param ctx:  The Cloudify ctx context.
    :returns parameters dictionary
    """

    parameters = constants.RUN_INSTANCE_PARAMETERS

    attached_group_ids = \
        utils.get_target_external_resource_ids(
            constants.INSTANCE_SECURITY_GROUP_RELATIONSHIP)

    node_parameter_keys = node_properties['parameters'].keys()

    for key in parameters.keys():
        if key is 'security_group_ids':
            if key in node_parameter_keys:
                parameters[key] = list(
                    set(attached_group_ids) | set(
                        node_properties['parameters'][key])
                )
            else:
                parameters[key] = attached_group_ids
        elif key is 'key_name':
            if key in node_parameter_keys:
                parameters[key] = node_properties['parameters'][key]
            else:
                parameters[key] = \
                    utils.get_target_external_resource_ids(
                        constants.INSTANCE_KEYPAIR_RELATIONSHIP)
        elif key in node_parameter_keys:
            parameters[key] = node_properties['parameters'][key]
        elif key is 'image_id' or key is 'instance_type':
            parameters[key] = node_properties[key]
        else:
            del(parameters[key])

    return parameters

########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
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

import os

# Third-party Imports
import boto.exception

# Cloudify imports
from ec2 import utils
from ec2 import constants
from ec2 import connection
from cloudify import ctx
from cloudify import compute
from cloudify.exceptions import NonRecoverableError
from cloudify.decorators import operation
from ec2 import passwd
from ec2.keypair import KEYPAIR_AWS_TYPE


@operation
def creation_validation(**_):
    """ This checks that all user supplied info is valid """

    for property_key in constants.INSTANCE_REQUIRED_PROPERTIES:
        utils.validate_node_property(property_key, ctx.node.properties)

    instance = _get_instance_from_id(utils.get_resource_id())

    if ctx.node.properties['use_external_resource'] and not instance:
        raise NonRecoverableError(
            'External resource, but the supplied '
            'instance id is not in the account.')

    if not ctx.node.properties['use_external_resource'] and instance:
        raise NonRecoverableError(
            'Not external resource, but the supplied '
            'but the instance already exists.')

    image_id = ctx.node.properties['image_id']
    image_object = _get_image(image_id)

    if 'available' not in image_object.state:
        raise NonRecoverableError(
            'image_id {0} not available to this account.'.format(image_id))


@operation
def run_instances(**_):
    ec2_client = connection.EC2ConnectionClient().client()

    for property_name in constants.INSTANCE_REQUIRED_PROPERTIES:
        utils.validate_node_property(property_name, ctx.node.properties)

    if _create_external_instance():
        return

    instance_parameters = _get_instance_parameters()

    ctx.logger.info(
        'Attempting to create EC2 Instance with these API parameters: {0}.'
        .format(instance_parameters))

    instance_id = _run_instances_if_needed(ec2_client, instance_parameters)

    instance = _get_instance_from_id(instance_id)

    if instance is None:
        return ctx.operation.retry(
            message='Waiting to verify that instance {0} '
            'has been added to your account.'.format(instance_id))

    utils.set_external_resource_id(
        instance_id, ctx.instance, external=False)
    _instance_created_assign_runtime_properties()


@operation
def modify_instance_attributes(new_attributes, **_):
    _modify_instance_attributes(new_attributes)


def _modify_instance_attributes(new_attributes):

    instance_id = \
        ctx.instance.runtime_properties.get(constants.EXTERNAL_RESOURCE_ID)

    if not instance_id:
        ctx.operation.retry('instance_id not yet set.')

    instance = _get_instance_from_id(instance_id)

    for attribute, value in new_attributes.items():
        try:
            instance.modify_attribute(attribute, value)
        except (boto.exception.EC2ResponseError,
                boto.exception.BotoServerError,
                AttributeError) as e:
            raise NonRecoverableError('{0}'.format(str(e)))


@operation
def start(start_retry_interval=30, private_key_path=None, **_):
    ec2_client = connection.EC2ConnectionClient().client()

    instance_id = \
        utils.get_external_resource_id_or_raise(
            'start instance', ctx.instance)

    if _start_external_instance(instance_id):
        return

    if _get_instance_state() == constants.INSTANCE_STATE_STARTED:
        if ctx.node.properties['use_password']:
            password_success = _retrieve_windows_pass(
                ec2_client=ec2_client,
                instance_id=instance_id,
                private_key_path=private_key_path)
            if not password_success:
                return ctx.operation.retry(
                    message='Waiting for server to post generated password',
                    retry_after=start_retry_interval)

        _instance_started_assign_runtime_properties_and_tag(instance_id)
        return

    ctx.logger.debug('Attempting to start instance: {0}.)'.format(instance_id))

    try:
        ec2_client.start_instances(instance_id)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    ctx.logger.debug('Attempted to start instance {0}.'.format(instance_id))

    if _get_instance_state() == constants.INSTANCE_STATE_STARTED:
        if ctx.node.properties['use_password']:
            password_success = _retrieve_windows_pass(
                ec2_client=ec2_client,
                instance_id=instance_id,
                private_key_path=private_key_path)
            if not password_success:
                return ctx.operation.retry(
                    message='Waiting for server to post generated password',
                    retry_after=start_retry_interval)
        _instance_started_assign_runtime_properties_and_tag(instance_id)
    else:
        return ctx.operation.retry(
            message='Waiting server to be running. Retrying...',
            retry_after=start_retry_interval)


@operation
def stop(**_):
    ec2_client = connection.EC2ConnectionClient().client()

    instance_id = \
        utils.get_external_resource_id_or_raise(
            'stop instance', ctx.instance)

    if _stop_external_instance(instance_id):
        return

    ctx.logger.debug(
        'Attempting to stop EC2 Instance. {0}.)'.format(instance_id))

    try:
        ec2_client.stop_instances(instance_id)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    ctx.logger.debug('Attempted to stop instance {0}.'.format(instance_id))

    if _get_instance_state() == constants.INSTANCE_STATE_STOPPED:
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

    if _terminate_external_instance(instance_id):
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

    if _get_instance_state() == \
            constants.INSTANCE_STATE_TERMINATED:
        ctx.logger.info('Terminated instance: {0}.'.format(instance_id))
        utils.unassign_runtime_property_from_resource(
            constants.EXTERNAL_RESOURCE_ID, ctx.instance)
    else:
        return ctx.operation.retry(
            message='Waiting server to terminate. Retrying...')


def _assign_runtime_properties_to_instance(runtime_properties):

    for property_name in runtime_properties:
        if 'ip' is property_name:
            ctx.instance.runtime_properties[property_name] = \
                _get_instance_attribute('private_ip_address')
        elif 'public_ip_address' is property_name:
            ctx.instance.runtime_properties[property_name] = \
                _get_instance_attribute('ip_address')
        else:
            ctx.instance.runtime_properties[property_name] = \
                _get_instance_attribute(property_name)


def _instance_created_assign_runtime_properties():
    _assign_runtime_properties_to_instance(
        runtime_properties=constants.INSTANCE_INTERNAL_ATTRIBUTES_POST_CREATE)


def _instance_started_assign_runtime_properties_and_tag(instance_id):

    instance = _get_instance_from_id(instance_id)
    utils.add_tag(instance)

    _assign_runtime_properties_to_instance(
        runtime_properties=constants.INSTANCE_INTERNAL_ATTRIBUTES)
    ctx.logger.info('Instance {0} is running.'.format(instance_id))


def _retrieve_windows_pass(ec2_client,
                           instance_id,
                           private_key_path):
    private_key = _get_private_key(private_key_path)
    ctx.logger.debug('retrieving password for server')
    password = _get_windows_password(ec2_client=ec2_client,
                                     instance_id=instance_id,
                                     private_key_path=private_key)

    if password:
        ctx.instance.runtime_properties[
            constants.ADMIN_PASSWORD_PROPERTY] = password
        ctx.logger.info('Server has been set with a password')
        return True
    return False


def _get_private_key(private_key_path):
    pk_node_by_rel = \
        utils.get_single_connected_node_by_type(
            ctx, KEYPAIR_AWS_TYPE, True)

    if private_key_path:
        if pk_node_by_rel:
            raise NonRecoverableError("server can't both have a "
                                      '"private_key_path" input and be '
                                      'connected to a keypair via a '
                                      'relationship at the same time')
        key_path = private_key_path
    else:
        if pk_node_by_rel and pk_node_by_rel.properties['private_key_path']:
            key_path = pk_node_by_rel.properties['private_key_path']
        else:
            key_path = ctx.bootstrap_context.cloudify_agent.agent_key_path

    if key_path:
        key_path = os.path.expanduser(key_path)
        if os.path.isfile(key_path):
            return key_path

    err_message = 'Cannot find private key file'
    if key_path:
        err_message += '; expected file path was {0}'.format(key_path)
    raise NonRecoverableError(err_message)


def _get_windows_password(ec2_client,
                          instance_id,
                          private_key_path):
    password_data = ec2_client.get_password_data(instance_id=instance_id)
    if not password_data:
        return None

    return passwd.get_windows_passwd(private_key_path, password_data)


def _unassign_runtime_properties(runtime_properties, ctx_instance):
    for property_name in runtime_properties:
        utils.unassign_runtime_property_from_resource(
            property_name, ctx_instance)


def _run_instances_if_needed(ec2_client, instance_parameters):

    if ctx.operation.retry_number == 0:

        try:
            reservation = ec2_client.run_instances(**instance_parameters)
        except (boto.exception.EC2ResponseError,
                boto.exception.BotoServerError) as e:
            raise NonRecoverableError('{0}'.format(str(e)))
        ctx.instance.runtime_properties['reservation_id'] = reservation.id
        return reservation.instances[0].id

    elif constants.EXTERNAL_RESOURCE_ID not in ctx.instance.runtime_properties:

        instances = _get_instances_from_reservation_id(ec2_client)

        if not instances:
            raise NonRecoverableError(
                'Instance failed for an unknown reason. Node ID: {0}. '
                .format(ctx.instance.id))
        elif len(instances) != 1:
            raise NonRecoverableError(
                'More than one instance was created by the install workflow. '
                'Unable to handle request.')

        return instances[0].id

    return ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID]


def _handle_userdata(parameters):

    existing_userdata = parameters.get('user_data')
    install_agent_userdata = ctx.agent.init_script()

    if not (existing_userdata or install_agent_userdata):
        return parameters

    if not existing_userdata:
        final_userdata = install_agent_userdata
    elif not install_agent_userdata:
        final_userdata = existing_userdata
    else:
        final_userdata = compute.create_multi_mimetype_userdata(
            [existing_userdata, install_agent_userdata])

    parameters['user_data'] = final_userdata

    return parameters


def _get_instances_from_reservation_id(ec2_client):

    try:
        reservations = ec2_client.get_all_instances(
            filters={
                'reservation-id':
                    ctx.instance.runtime_properties['reservation_id']
            })
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    if len(reservations) < 1:
        return None

    return reservations[0].instances


def _create_external_instance():

    if not utils.use_external_resource(ctx.node.properties):
        return False

    instance_id = ctx.node.properties['resource_id']
    instance = _get_instance_from_id(instance_id)
    if instance is None:
        raise NonRecoverableError(
            'Cannot use_external_resource because instance_id {0} '
            'is not in this account.'.format(instance_id))
    utils.set_external_resource_id(instance.id, ctx.instance)
    return True


def _start_external_instance(instance_id):

    if not utils.use_external_resource(ctx.node.properties):
        return False

    ctx.logger.info(
        'Not starting instance {0}, because it is an external resource.'
        .format(instance_id))
    _instance_started_assign_runtime_properties_and_tag(instance_id)
    return True


def _stop_external_instance(instance_id):

    if not utils.use_external_resource(ctx.node.properties):
        return False

    ctx.logger.info(
        'External resource. Not stopping instance {0}.'
        .format(instance_id))
    _unassign_runtime_properties(
        runtime_properties=constants.INSTANCE_INTERNAL_ATTRIBUTES,
        ctx_instance=ctx.instance)
    return True


def _terminate_external_instance(instance_id):

    if not utils.use_external_resource(ctx.node.properties):
        return False

    ctx.logger.info(
        'External resource. Not terminating instance {0}.'
        .format(instance_id))
    utils.unassign_runtime_property_from_resource(
        constants.EXTERNAL_RESOURCE_ID, ctx.instance)
    return True


def _get_all_instances(list_of_instance_ids=None):
    """Returns a list of instance objects for a list of instance IDs.

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

    instances = []

    for reservation in reservations:
        for instance in reservation.instances:
            instances.append(instance)

    return instances


def _get_instance_from_id(instance_id):
    """Gets the instance ID of a EC2 Instance

    :param instance_id: The ID of an EC2 Instance
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
        image_object = ec2_client.get_image(image_id)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}.'.format(str(e)))

    return image_object


def _get_instance_attribute(attribute):
    """Gets an attribute from a boto object that represents an EC2 Instance.

    :param attribute: The named python attribute of a boto object.
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
    instance_object = _get_instance_from_id(instance_id)

    if not instance_object:
        if not ctx.node.properties['use_external_resource']:
            ec2_client = connection.EC2ConnectionClient().client()
            instances = _get_instances_from_reservation_id(ec2_client)
            if not instances:
                raise NonRecoverableError(
                    'Unable to get instance attibute {0}, because '
                    'no instance with id {1} exists in this account.'
                    .format(attribute, instance_id))
            elif len(instances) != 1:
                raise NonRecoverableError(
                    'Unable to get instance attibute {0}, because more '
                    'than one instance with id {1} exists in this account.'
                    .format(attribute, instance_id))
            instance_object = instances[0]
        else:
            raise NonRecoverableError(
                'External resource, but the supplied '
                'instance id {0} is not in the account.'.format(instance_id))

    attribute = getattr(instance_object, attribute)
    return attribute


def _get_instance_state():
    """Gets the instance state code of a EC2 Instance

    :returns a state code from a boto object representing an EC2 Image.
    """
    state = _get_instance_attribute('state_code')
    return state


def _get_instance_parameters():
    """The parameters to the run_instance boto call.

    :returns parameters dictionary
    """

    provider_variables = utils.get_provider_variables()

    attached_group_ids = \
        utils.get_target_external_resource_ids(
            constants.INSTANCE_SECURITY_GROUP_RELATIONSHIP,
            ctx.instance)

    if provider_variables.get(constants.AGENTS_SECURITY_GROUP):
        attached_group_ids.append(
            provider_variables[constants.AGENTS_SECURITY_GROUP])

    parameters = \
        provider_variables.get(constants.AGENTS_AWS_INSTANCE_PARAMETERS)
    parameters.update({
        'image_id': ctx.node.properties['image_id'],
        'instance_type': ctx.node.properties['instance_type'],
        'security_group_ids': attached_group_ids,
        'key_name': _get_instance_keypair(provider_variables),
        'subnet_id': _get_instance_subnet(provider_variables)
    })

    parameters.update(ctx.node.properties['parameters'])
    parameters = _handle_userdata(parameters)

    return parameters


def _get_instance_keypair(provider_variables):
    """Gets the instance key pair. If more or less than one is provided,
    this will raise an error.

    """
    list_of_keypairs = \
        utils.get_target_external_resource_ids(
            constants.INSTANCE_KEYPAIR_RELATIONSHIP, ctx.instance)

    if not list_of_keypairs and \
            provider_variables.get(constants.AGENTS_KEYPAIR):
        list_of_keypairs.append(provider_variables[constants.AGENTS_KEYPAIR])
    elif len(list_of_keypairs) > 1:
        raise NonRecoverableError(
            'Only one keypair may be attached to an instance.')

    return list_of_keypairs[0] if list_of_keypairs else None


def _get_instance_subnet(provider_variables):

    list_of_subnets = \
        utils.get_target_external_resource_ids(
            constants.INSTANCE_SUBNET_RELATIONSHIP, ctx.instance
        )

    if not list_of_subnets and provider_variables.get(constants.SUBNET):
        list_of_subnets.append(provider_variables[constants.SUBNET])
    elif len(list_of_subnets) > 1:
        raise NonRecoverableError(
            'instance may only be attached to one subnet')

    return list_of_subnets[0] if list_of_subnets else None

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

# Built in Imports
import datetime

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
    """ This validates all EBS volume Nodes before bootstrap.
    """

    for property_key in constants.VOLUME_REQUIRED_PROPERTIES:
        utils.validate_node_property(property_key, ctx.node.properties)

    volume_object = _get_volumes_from_id(utils.get_resource_id())

    if ctx.node.properties['use_external_resource'] and not volume_object:
        raise NonRecoverableError(
            'External resource, but the supplied '
            'EBS volume does not exist in the account.')

    if not ctx.node.properties['use_external_resource'] and volume_object:
        raise NonRecoverableError(
            'Not external resource, but the supplied '
            'EBS volume exists in the account.')


@operation
def create(args, **_):
    """Creates an EBS volume.
    """

    ec2_client = connection.EC2ConnectionClient().client()

    for property_name in constants.VOLUME_REQUIRED_PROPERTIES:
        utils.validate_node_property(property_name, ctx.node.properties)

    if _create_external_volume():
        return

    ctx.logger.debug('Creating EBS volume')

    create_volume_args = dict(
        size=ctx.node.properties['size'],
        zone=ctx.node.properties[constants.ZONE]
    )

    create_volume_args.update(args)

    try:
        new_volume = ec2_client.create_volume(**create_volume_args)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    ctx.instance.runtime_properties[constants.ZONE] = new_volume.zone

    utils.set_external_resource_id(
        new_volume.id, ctx.instance, external=False)


@operation
def delete(**_):
    """ Deletes an EBS Volume.
    """

    volume_id = utils.get_external_resource_id_or_raise(
        'delete EBS volume', ctx.instance)

    if _delete_external_volume():
        return

    ctx.logger.debug('Deleting EBS volume: {0}'.format(volume_id))

    if not _delete_volume(volume_id):
        return ctx.operation.retry(
            message='Failed to delete volume {0}.'
                    .format(volume_id))

    utils.unassign_runtime_property_from_resource(
            constants.ZONE, ctx.instance)

    utils.unassign_runtime_property_from_resource(
        constants.EXTERNAL_RESOURCE_ID, ctx.instance)

    ctx.logger.info(
        'Deleted EBS volume: {0}.'
        .format(volume_id))


@operation
def attach(**_):
    """ Attaches an EBS volume created by Cloudify with an EC2 Instance
    that was also created by Cloudify.
    """

    volume_id = \
        utils.get_external_resource_id_or_raise(
            'attach volume', ctx.source.instance)
    instance_id = \
        utils.get_external_resource_id_or_raise(
            'attach volume', ctx.target.instance)

    if ctx.source.node.properties[constants.ZONE] not in \
            ctx.target.instance.runtime_properties.get('placement'):
        ctx.logger.info(
            'Volume Zone {0} and Instance Zone {1} do not match. '
            'This may lead to an error.'.format(
                ctx.source.node.properties[constants.ZONE],
                ctx.target.instance.runtime_properties.get('placement')
            )
        )

    if _attach_external_volume_or_instance(instance_id):
        return

    volume_object = _get_volumes_from_id(volume_id)

    if not volume_object:
        raise NonRecoverableError(
            'EBS volume {0} not found in account.'.format(volume_id))

    if constants.VOLUME_CREATING in volume_object.update():
        return ctx.operation.retry(
            message='Waiting for volume to be ready. '
                    'Volume in state {0}'
                    .format(volume_object.status))
    elif constants.VOLUME_AVAILABLE not in volume_object.update():
        raise NonRecoverableError(
            'Cannot attach Volume {0} because it is in state {1}.'
            .format(volume_object.id, volume_object.status))

    ctx.logger.debug(
        'Attempting to attach volume {0} to instance {1}.'
        .format(volume_id, instance_id))

    try:
        volume_object.attach(
            instance_id,
            ctx.source.node.properties['device'])
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    ctx.source.instance.runtime_properties['instance_id'] = \
        instance_id
    ctx.logger.info(
        'Attached EBS volume {0} with instance {1}.'
        .format(volume_id, instance_id))


@operation
def detach(args, **_):
    """ Detaches an EBS Volume created by Cloudify from an EC2 Instance
    that was also created by Cloudify.
    """

    volume_id = \
        utils.get_external_resource_id_or_raise(
            'detach volume', ctx.source.instance)
    instance_id = \
        utils.get_external_resource_id_or_raise(
            'detach volume', ctx.target.instance)

    if _detach_external_volume_or_instance():
        return

    ctx.logger.debug('Detaching EBS volume {0}'.format(volume_id))

    volume_object = _get_volumes_from_id(volume_id)

    if not volume_object:
        raise NonRecoverableError(
            'EBS volume {0} not found in account.'.format(volume_id))

    try:
        detached = volume_object.detach(**args)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    if not detached:
        raise NonRecoverableError(
            'Failed to detach volume {0} from instance {1}'
            .format(volume_id, instance_id))

    utils.unassign_runtime_property_from_resource(
        'instance_id', ctx.source.instance)
    ctx.logger.info(
        'Detached volume {0} from instance {1}.'
        .format(volume_id, instance_id))


@operation
def create_snapshot(args, **_):
    """ Create a snapshot of an EBS Volume
    """

    volume_id = \
        utils.get_external_resource_id_or_raise(
            'create snapshot', ctx.instance)

    ctx.logger.info(
        'Trying to create a snapshot of EBS volume {0}.'
        .format(volume_id))

    volume_object = _get_volumes_from_id(volume_id)

    if not args:
        snapshot_desc = \
            unicode(datetime.datetime.now()) + \
            ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID]
        args = dict(description=snapshot_desc)

    try:
        new_snapshot = volume_object.create_snapshot(**args)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    ctx.logger.info(
        'Created snapshot of EBS volume {0}.'.format(volume_id))

    if constants.VOLUME_SNAPSHOT_ATTRIBUTE not in \
            ctx.instance.runtime_properties:
        ctx.instance.runtime_properties[
            constants.VOLUME_SNAPSHOT_ATTRIBUTE] = list()

    ctx.instance.runtime_properties[
        constants.VOLUME_SNAPSHOT_ATTRIBUTE].append(new_snapshot.id)


def _delete_volume(volume_id):
    """

    :param volume_id:
    :return: True if the item is deleted,
    False if the item cannot be deleted yet.
    """

    volume_to_delete = _get_volumes_from_id(volume_id)

    if not volume_to_delete:
        ctx.logger.info(
            'Volume id {0} does\'t exist.'
            .format(volume_id))
        return True

    if volume_to_delete.status not in \
            constants.VOLUME_AVAILABLE or \
            volume_to_delete.status in \
            constants.VOLUME_IN_USE:
        return False

    try:
        output = volume_to_delete.delete()
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    return output


def _create_external_volume():
    """If use_external_resource is True, this will set the runtime_properties,
    and then exit.

    :return False: Cloudify resource. Continue operation.
    :return True: External resource. Set runtime_properties. Ignore operation.
    """

    if not utils.use_external_resource(ctx.node.properties):
        return False

    volume_id = ctx.node.properties['resource_id']

    volume = _get_volumes_from_id(volume_id)
    if not volume:
        raise NonRecoverableError(
            'External EBS volume was indicated, but the '
            'volume id does not exist.')
    utils.set_external_resource_id(volume.id, ctx.instance)
    return True


def _delete_external_volume():
    """If use_external_resource is True, this will delete the runtime_properties,
    and then exit.

    :return False: Cloudify resource. Continue operation.
    :return True: External resource. Unset runtime_properties.
        Ignore operation.
    """

    if not utils.use_external_resource(ctx.node.properties):
        return False

    ctx.logger.info(
        'External resource. Not deleting EBS volume from account.')
    utils.unassign_runtime_property_from_resource(
        constants.EXTERNAL_RESOURCE_ID, ctx.instance)
    return True


def _attach_external_volume_or_instance(instance_id):
    """Pretends to attach an external EBC volume with an EC2 instance
    but if one was not created by Cloudify, it just sets runtime_properties
    and exits the operation.

    :return False: At least one is a Cloudify resource. Continue operation.
    :return True: Both are External resources. Set runtime_properties.
        Ignore operation.
    """

    if not utils.use_external_resource(ctx.source.node.properties) \
            or not utils.use_external_resource(
                ctx.target.node.properties):
        return False

    ctx.source.instance.runtime_properties['instance_id'] = \
        instance_id
    ctx.logger.info(
        'Either instance or volume is an external resource so not '
        'performing attach operation.')
    return True


def _detach_external_volume_or_instance():
    """Pretends to detach an external EBC volume with an EC2 instance
    but if one was not created by Cloudify, it just sets runtime_properties
    and exits the operation.

    :return False: At least one is a Cloudify resource. Continue operation.
    :return True: Both are External resources. Set runtime_properties.
        Ignore operation.
    """

    if not utils.use_external_resource(ctx.source.node.properties) \
            or not utils.use_external_resource(
                ctx.target.node.properties):
        return False

    utils.unassign_runtime_property_from_resource(
        'instance_id', ctx.source.instance)
    ctx.logger.info(
        'Either instance or EBS volume is an external resource so not '
        'performing detach operation.')
    return True


def _get_volumes_from_id(volume_id):
    """Returns the EBS Volume object for a given EBS Volume id.

    :param volume_id: The ID of an EBS Volume.
    :returns The boto EBS volume object.
    """

    volumes = _get_volumes(list_of_volume_ids=volume_id)

    return volumes[0] if volumes else volumes


def _get_volumes(list_of_volume_ids):
    """Returns a list of EBS Volumes for a given list of volume IDs.

    :param list_of_volume_ids: A list of EBS volume IDs.
    :returns A list of EBS objects.
    :raises NonRecoverableError: If Boto errors.
    """

    ec2_client = connection.EC2ConnectionClient().client()

    try:
        volumes = ec2_client.get_all_volumes(
            volume_ids=list_of_volume_ids)
    except boto.exception.EC2ResponseError as e:
        if 'InvalidVolume.NotFound' in e:
            all_volumes = ec2_client.get_all_volumes()
            utils.log_available_resources(all_volumes)
        return None
    except boto.exception.BotoServerError as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    return volumes

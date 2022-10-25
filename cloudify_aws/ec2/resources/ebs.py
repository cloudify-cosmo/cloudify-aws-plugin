# Copyright (c) 2018 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
    EC2.Volume
    ~~~~~~~~~~~~~~
    AWS EC2 EBS Volume
"""
# Boto
from botocore.exceptions import CapacityNotAvailableError

# Cloudify
from cloudify.exceptions import NonRecoverableError
from cloudify_aws.common import decorators
from cloudify_aws.common import constants
from cloudify_aws.common import utils
from cloudify_aws.ec2 import EC2Base


RESOURCE_TYPE_VOLUME = 'EC2 EBS Volume'
RESOURCE_TYPE_VOLUME_ATTACHMENT = 'EC2 EBS Volume Attachment'

VOLUME_IDS = 'VolumeIds'
VOLUME_STATE = 'State'
VOLUME_ID = 'VolumeId'
VOLUMES = 'Volumes'


ATTACHING = 'attaching'
ATTACHED = 'attached'

DETACHING = 'detaching'
DETACHED = 'detached'

CREATING = 'creating'
AVAILABLE = 'available'
INUSE = 'in-use'

DELETING = 'deleting'
DELETED = 'deleted'

EC2_INSTANCE_TYPE = 'cloudify.nodes.aws.ec2.Instances'


class EC2VolumeMixin(object):
    """
        EC2 EBS Volume
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE_VOLUME
        self._describe_call = 'describe_volumes'
        self._type_key = VOLUMES
        self._id_key = VOLUME_ID
        self._ids_key = VOLUME_IDS

    @property
    def status(self):
        """
        Gets the status of an external resource
        :return:
        """
        return self.properties[VOLUME_STATE]\
            if self.properties and self.properties.get(VOLUME_STATE) else None

    def attach(self, params):

        return self.make_client_call('attach_volume', params)

    def detach(self, params={}):
        """
        Detaches An AWS EC2 EBS Volume From Instance
        :param params:
        :return:
        """
        self.logger.debug('Detaching {0} with: {1}'
                          .format(self.type_name, params.get(VOLUME_ID, None)))
        res = self.client.detach_volume(**params)
        self.logger.debug('Response: {0}'.format(res))
        return res


class EC2Volume(EC2VolumeMixin, EC2Base):
    """
        EC2 EBS Volume
    """

    def create(self, params):
        """
        Creates An existing AWS EC2 EBS Volume
        :param params:
        :return: dict of created volume
        """
        return self.make_client_call('create_volume', params)

    def delete(self, params=None):
        """
        Deletes An existing AWS EC2 EBS Volume
        :param params:
        :return: None
        """
        self.logger.debug('Deleting {0} with parameters: {1}'
                          .format(self.type_name, params))
        res = self.client.delete_volume(**params)
        self.logger.debug('Response: {0}'.format(res))
        return res


class EC2VolumeAttachment(EC2VolumeMixin, EC2Base):
    """
        EC2 EBS Volume Attachment
    """

    def create(self, params):
        """
        Attaches An AWS EC2 EBS Volume From Instance
        :param params:
        :return:
        """
        return self.attach(params)

    def delete(self, params=None):
        """
        Detaches An AWS EC2 EBS Volume From Instance
        :param params:
        :return:
        """
        return self.detach(params)


def _attach_ebs(params, iface, _ctx):
    """
    :param params:
    :param iface:
    :param _ctx:
    """
    # Attach ebs volume to ec2 instance resource
    create_response = iface.create(params)

    # Check if the resource attaching done
    if create_response:
        _ctx.instance.runtime_properties['ebs_attach'] =\
            utils.JsonCleanuper(create_response).to_dict()
        return create_response

    else:
        raise NonRecoverableError(
            '{0} ID# "{1}" reported an empty response'
            .format(RESOURCE_TYPE_VOLUME_ATTACHMENT, iface.resource_id))


def _detach_ebs(iface, volume_id, **kwargs):
    """
    :param iface:
    :param volume_id:
    """
    deleted_params = {'VolumeId': volume_id}
    if 'Device' in kwargs:
        deleted_params['Device'] = kwargs['Device']
    if 'Force' in kwargs:
        deleted_params['Force'] = kwargs['Force']
    if 'InstanceId' in kwargs:
        deleted_params['InstanceId'] = kwargs['InstanceId']
    if 'DryRun' in kwargs:
        deleted_params['DryRun'] = kwargs['DryRun']
    if iface.status not in [DETACHED, AVAILABLE]:
        iface.delete(deleted_params)


def _create_attachment(ctx, iface, resource_config):
    """
    :param ctx:
    :param iface:
    :param resource_config:
    """
    response = _attach_ebs(resource_config, iface, ctx)
    # Update the ebs_id (volume_id)
    ebs_id = response.get(VOLUME_ID, '')
    utils.update_resource_id(ctx.instance, ebs_id)
    iface.update_resource_id(ebs_id)


def _delete_attachment(ctx, iface, **kwargs):
    """
    :param ctx:
    :param iface:
    """
    resource_id = \
        ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID]
    _detach_ebs(iface, resource_id, **kwargs)


@decorators.aws_resource(EC2Volume, resource_type=RESOURCE_TYPE_VOLUME)
def prepare(ctx, resource_config, **_):
    """
    Prepares an AWS EC2 EBS Volume
    :param ctx:
    :param resource_config:
    :param _:
    :return:
    """
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2Volume, RESOURCE_TYPE_VOLUME)
@decorators.wait_for_status(status_good=[AVAILABLE], status_pending=[CREATING])
@decorators.tag_resources
def create(ctx, iface, resource_config, **_):
    """
    Creates an AWS EC2 EBS Volume
    :param ctx:
    :param iface:
    :param resource_config:
    :param _:
    :return:
    """
    # Actually create ebs resource
    region_name = ctx.node.properties['client_config']['region_name']
    use_available_zones = ctx.node.properties.get('use_available_zones', False)
    try:
        create_response = iface.create(resource_config)
    except CapacityNotAvailableError:
        if use_available_zones:
            ctx.logger.warn(
                "The Availability Zone chosen {0} "
                "is not available".format(resource_config['AvailabilityZone']))
            valid_zone = \
                iface.get_available_zone({
                    'Filters': [
                        {'Name': 'region-name', 'Values': [region_name]}
                    ]
                })
            if valid_zone:
                ctx.logger.info(
                    "using {0} Availability Zone instead".format(valid_zone))
                resource_config['AvailabilityZone'] = valid_zone
                create_response = iface.create(resource_config)
            else:
                raise NonRecoverableError(
                    "no available Availability Zones "
                    "in region {0}".format(region_name))
        else:
            raise NonRecoverableError(
                "The Availability Zone chosen "
                "{0} is not available".format(
                    resource_config['AvailabilityZone']))
    # Check if the resource created
    if not create_response:
        raise NonRecoverableError(
            '{0} ID# "{1}" reported an empty response'.format(
                RESOURCE_TYPE_VOLUME, iface.resource_id))

    ctx.instance.runtime_properties['ebs_create'] = \
        utils.JsonCleanuper(create_response).to_dict()

    # Update the ebs_id (volume_id)
    ebs_id = create_response.get(VOLUME_ID, '')
    utils.update_resource_id(ctx.instance, ebs_id)
    iface.update_resource_id(ebs_id)


@decorators.aws_resource(EC2Volume, RESOURCE_TYPE_VOLUME,
                         ignore_properties=True)
@decorators.untag_resources
def delete(ctx, iface, resource_config, dry_run=False, **_):
    """
    Deletes an AWS EC2 EBS Volume
    :param ctx:
    :param iface:
    :param resource_config:
    :param _:
    :return:
    """
    deleted_params = dict()
    resource_id = \
        ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID]
    deleted_params[VOLUME_ID] = resource_id

    volume_config = ctx.instance.runtime_properties['resource_config']
    if isinstance(volume_config, dict):
        deleted_params['DryRun'] = volume_config.get('DryRun') or dry_run
    iface.delete(deleted_params)


@decorators.aws_relationship(EC2Volume, RESOURCE_TYPE_VOLUME)
@decorators.wait_on_relationship_status(status_good=[ATTACHED, INUSE],
                                        status_pending=[ATTACHING])
def attach_using_relationship(ctx, iface, **_):
    """
    Attaches an AWS EC2 EBS Volume TO Instance
    :param ctx:
    :param iface:
    :param _:
    """
    device_name = ctx.source.node.properties.get('device_name')
    # Check if device name is provide or not
    if not device_name:
        raise NonRecoverableError('Cannot attach volume {0} to EC2 instance '
                                  'without specifying device name')
    instance_id = utils.find_ids_of_rels_by_node_type(
        ctx.source.instance, EC2_INSTANCE_TYPE)
    volume_id = iface.resource_id
    if not instance_id:
        raise NonRecoverableError(
            'EC2 instance id {0} is missing.Attaching volume'
            ' {1} is not possible'.format(instance_id, volume_id)
        )
    # Prepare params in order to attach volume
    params = {
        'Device': device_name,
        'InstanceId': instance_id[0],
        'VolumeId': volume_id
    }
    iface = EC2VolumeAttachment(ctx.source.node, logger=ctx.logger,
                                resource_id=utils.get_resource_id(
                                    node=ctx.source.node,
                                    instance=ctx.source.instance,
                                    raise_on_missing=True))

    _attach_ebs(params, iface, ctx.source)


@decorators.aws_relationship(EC2Volume, RESOURCE_TYPE_VOLUME)
@decorators.wait_on_relationship_unlink(status_deleted=[DETACHED, AVAILABLE],
                                        status_pending=[DETACHING, INUSE])
def detach_using_relationship(ctx, **_):
    """
    De-attaches an AWS EC2 EBS Volume TO Instance
    :param ctx:
    :param _:
    """
    iface = EC2VolumeAttachment(ctx.source.node, logger=ctx.logger,
                                resource_id=utils.get_resource_id(
                                    node=ctx.source.node,
                                    instance=ctx.source.instance,
                                    raise_on_missing=True))
    resource_id = \
        ctx.source.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID]
    _detach_ebs(iface, resource_id)


@decorators.aws_resource(EC2VolumeAttachment, RESOURCE_TYPE_VOLUME_ATTACHMENT)
@decorators.wait_for_status(status_good=[ATTACHED, INUSE],
                            status_pending=[ATTACHING])
def attach(ctx, iface, resource_config, **_):
    """
    Attaches an AWS EC2 EBS Volume TO Instance
    :param ctx:
    :param iface:
    :param resource_config:
    :param _:
    """
    _create_attachment(ctx, iface, resource_config)


@decorators.aws_resource(EC2VolumeAttachment, RESOURCE_TYPE_VOLUME_ATTACHMENT,
                         ignore_properties=True)
@decorators.wait_for_delete(status_deleted=[DETACHED, AVAILABLE],
                            status_pending=[DETACHING, INUSE])
def detach(ctx, iface, resource_config, **kwargs):
    """
    De-attaches an AWS EC2 EBS Volume TO Instance
    :param ctx:
    :param iface:
    :param resource_config
    :param _:
    """
    _delete_attachment(ctx, iface, **kwargs)


@decorators.aws_resource(EC2VolumeAttachment, RESOURCE_TYPE_VOLUME_ATTACHMENT)
def poststart(ctx, iface, resource_config, **_):
    """
    Attaches an AWS EC2 EBS Volume TO Instance
    :param ctx:
    :param iface:
    :param resource_config:
    :param _:
    """

    ctx.instance.runtime_properties['ebs_attach'] = utils.JsonCleanuper(
        iface.properties).to_dict()

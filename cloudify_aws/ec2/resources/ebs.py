# #######
# Copyright (c) 2018 GigaSpaces Technologies Ltd. All rights reserved
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
"""
    EC2.Volume
    ~~~~~~~~~~~~~~
    AWS EC2 EBS Volume
"""
# Boto
from botocore.exceptions import ClientError

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


class EC2VolumeMixin(object):
    """
        EC2 EBS Volume
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE_VOLUME

    @property
    def properties(self):
        """
        Gets the properties of an external resource
        :return: dict of selected volume
        """
        params = {VOLUME_IDS: [self.resource_id]}
        try:
            resources = \
                self.client.describe_volumes(**params)
        except ClientError:
            pass
        else:
            return resources.get(VOLUMES)[0] if resources else None

    @property
    def status(self):
        """
        Gets the status of an external resource
        :return:
        """
        return self.properties[VOLUME_STATE]\
            if self.properties and self.properties.get(VOLUME_STATE) else None


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
        EC2 EBS Volume
    """

    def create(self, params):
        """
        Attaches An AWS EC2 EBS Volume From Instance
        :param params:
        :return:
        """
        return self.make_client_call('attach_volume', params)

    def delete(self, params=None):
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


@decorators.aws_resource(resource_type=RESOURCE_TYPE_VOLUME)
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
    params = \
        dict() if not resource_config else resource_config.copy()

    # Create ebs resource
    create_response = iface.create(params)
    # Check if the resource created
    if create_response:
        ctx.instance.runtime_properties['eps_create'] =\
            utils.JsonCleanuper(create_response).to_dict()

        # Update the esp_id (volume_id)
        esp_id = create_response.get(VOLUME_ID, '')
        utils.update_resource_id(ctx.instance, esp_id)
        iface.update_resource_id(esp_id)

    else:
        raise NonRecoverableError(
            '{0} ID# "{1}" reported an empty response'
            .format(RESOURCE_TYPE_VOLUME, iface.resource_id))


@decorators.aws_resource(EC2Volume, RESOURCE_TYPE_VOLUME,
                         ignore_properties=True)
@decorators.untag_resources
def delete(ctx, iface, resource_config, **_):
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
    deleted_params['DryRun'] = volume_config.get('DryRun') or False
    iface.delete(deleted_params)


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
    :return:
    """
    params = \
        dict() if not resource_config else resource_config.copy()

    # Attach ebs volume to ec2 instance resource
    create_response = iface.create(params)

    # Check if the resource attaching done
    if create_response:
        ctx.instance.runtime_properties['eps_attach'] =\
            utils.JsonCleanuper(create_response).to_dict()

        # Update the esp_id (volume_id)
        esp_id = create_response.get(VOLUME_ID, '')
        utils.update_resource_id(ctx.instance, esp_id)
        iface.update_resource_id(esp_id)

    else:
        raise NonRecoverableError(
            '{0} ID# "{1}" reported an empty response'
            .format(RESOURCE_TYPE_VOLUME_ATTACHMENT, iface.resource_id))


@decorators.aws_resource(EC2VolumeAttachment, RESOURCE_TYPE_VOLUME_ATTACHMENT,
                         ignore_properties=True)
@decorators.wait_for_status(status_good=[DETACHED, AVAILABLE],
                            status_pending=[DETACHING, INUSE])
def detach(ctx, iface, resource_config, **_):
    """
    De-attaches an AWS EC2 EBS Volume TO Instance
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
    deleted_params['DryRun'] = volume_config.get('DryRun') or False
    iface.delete(deleted_params)

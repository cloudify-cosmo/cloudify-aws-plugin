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
    EC2.Image
    ~~~~~~~~~~~~~~
    AWS EC2 Image interface
"""
# Cloudify
from cloudify_aws.ec2 import EC2Base
from cloudify_aws.common import decorators, utils
from cloudify.exceptions import NonRecoverableError

# Boto
from botocore.exceptions import ClientError, ParamValidationError

RESOURCE_TYPE = 'EC2 Image'
IMAGES = 'Images'
DRY_RUN = 'DryRun'
IMAGE_ID = 'ImageId'
IMAGE_IDS = 'ImageIds'
OWNERS = 'Owners'
EXECUTABLE_USERS = 'ExecutableUsers'
FILTERS = 'Filters'


class EC2Image(EC2Base):
    """
        EC2 Image interface
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE
        image_filters = ctx_node.properties["resource_config"].get(
            "kwargs", {}).get("Filters")
        self._describe_image_filters = None
        self._describe_call = "describe_images"
        self._ids_key = IMAGE_IDS
        self._type_key = IMAGES
        self._id_key = IMAGE_ID
        if resource_id:
            self.prepare_describe_image_filter({IMAGE_IDS: [resource_id]})
        elif image_filters:
            self.prepare_describe_image_filter({FILTERS: image_filters})

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        params = self.describe_image_filters
        if not params:
            return
        try:
            resources = self.client.describe_images(**params)
        except (ClientError, ParamValidationError):
            pass
        else:
            images = [] if not resources else resources.get(IMAGES)
            if len(images):
                return images[0]
            raise NonRecoverableError(
                "Found no AMIs matching provided filters.")

    @property
    def status(self):
        """Gets the status of an external resource"""
        try:
            props = self.properties
        except NonRecoverableError as e:
            if 'Found no AMIs matching provided filters' in str(e):
                props = None
            else:
                raise e
        if not props:
            return None
        return props.get('State')

    def create(self, params):
        """
            Create a new AWS EC2 Image.
        """
        self.logger.debug('Creating %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.create_image(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def delete(self, params=None):
        self.logger.debug('Deleting %s' % self.type_name)
        self.logger.debug('Deregistering ImageId %s' % params.get('ImageId'))
        self.client.deregister_image(**params)

    @property
    def describe_image_filters(self):
        return self._describe_image_filters

    def prepare_describe_image_filter(self, params):
        dry_run = params.get(DRY_RUN, False)
        image_ids = params.get(IMAGE_IDS, [])
        owners = params.get(OWNERS, [])
        executable_users = params.get(EXECUTABLE_USERS, [])
        filters = params.get(FILTERS, [])
        if any([dry_run, image_ids, owners, executable_users, filters]):
            self._describe_image_filters = {
                DRY_RUN: dry_run,
                IMAGE_IDS: image_ids,
                OWNERS: owners,
                EXECUTABLE_USERS: executable_users,
                FILTERS: filters}
            self.logger.debug('Updated image filter: {}'.format(
                self.describe_image_filters))


@decorators.aws_resource(EC2Image,
                         resource_type=RESOURCE_TYPE,
                         waits_for_status=False)
def prepare(ctx, iface, resource_config, **_):
    """Prepares an AWS EC2 Image"""
    # Save the parameters
    if ctx.node.properties.get('use_external_resource'):
        ctx.instance.runtime_properties['resource_config'] = resource_config
        iface.prepare_describe_image_filter(resource_config)
        try:
            iface.properties.get(IMAGE_ID)
        except AttributeError:
            raise NonRecoverableError(
                'Failed to find AMI with parameters: {}'.format(
                    resource_config))
        utils.update_resource_id(ctx.instance, iface.properties.get(IMAGE_ID))


@decorators.aws_resource(EC2Image, resource_type=RESOURCE_TYPE)
@decorators.wait_for_status(status_good=['available'], fail_on_missing=False)
def create(ctx, iface, resource_config, **_):
    """Create an AWS EC2 Image"""
    if ctx.node.properties.get('use_external_resource'):
        # if use_external_resource there we are using an existing image
        return

    if 'InstanceId' not in resource_config:
        resource_config['InstanceId'] = utils.find_resource_id_by_type(
            ctx.instance, 'cloudify.nodes.aws.ec2.Instances')
    params = utils.clean_empty_vals(resource_config)

    # Actually create the resource
    create_response = iface.create(params)
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response).to_dict()
    iface.update_resource_id(create_response['ImageId'])
    utils.update_resource_id(ctx.instance, create_response['ImageId'])


@decorators.aws_resource(EC2Image,
                         resource_type=RESOURCE_TYPE,
                         waits_for_status=False)
@decorators.wait_for_delete(status_deleted=['deregistered'])
def delete(ctx, iface, resource_config, **_):
    """delete/deregister an AWS EC2 Image"""
    if not ctx.node.properties.get('use_external_resource'):
        dry_run = resource_config.get(DRY_RUN, False)
        params = {'ImageId': iface.resource_id, 'DryRun': dry_run}
        try:
            iface.delete(params)
        except ClientError as e:
            if 'is no longer available' in str(e):
                return
            raise e

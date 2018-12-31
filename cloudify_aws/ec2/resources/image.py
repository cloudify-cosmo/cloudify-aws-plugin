# #######
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
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.
"""
    EC2.Image
    ~~~~~~~~~~~~~~
    AWS EC2 Image interface
"""
# Cloudify
from cloudify.exceptions import NonRecoverableError
from cloudify_aws.common import decorators, utils
from cloudify_aws.ec2 import EC2Base
# Boto
from botocore.exceptions import ClientError

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
        self.describe_image_filters = {}

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        params = self.describe_image_filters
        try:
            resources = \
                self.client.describe_images(**params)
        except ClientError:
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
        props = self.properties
        if not props:
            return None
        return props['State']

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
        return


def prepare_describe_image_filter(params, iface):
    iface.describe_image_filters = {
        DRY_RUN: params.get(DRY_RUN, False),
        IMAGE_IDS: params.get(IMAGE_IDS, []),
        OWNERS: params.get(OWNERS, []),
        EXECUTABLE_USERS: params.get(EXECUTABLE_USERS, []),
        FILTERS: params.get(FILTERS, [])
    }
    return iface


@decorators.aws_resource(EC2Image, resource_type=RESOURCE_TYPE)
def prepare(ctx, iface, resource_config, **_):
    """Prepares an AWS EC2 Image"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config
    iface = \
        prepare_describe_image_filter(
            resource_config.copy(),
            iface)
    ami = iface.properties
    utils.update_resource_id(ctx.instance, ami.get(IMAGE_ID))

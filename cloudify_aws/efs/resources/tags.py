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
    EFS.FileSystemTags
    ~~~~~~~~
    AWS EFS File System Tags interface
"""
# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.efs import EFSBase
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID
# Boto
from botocore.exceptions import ClientError, ParamValidationError

RESOURCE_TYPE = 'EFS File System Tags'
FILESYSTEM_ID = 'FileSystemId'
TAGS = 'Tags'
FILESYSTEM_TYPE = 'cloudify.nodes.aws.efs.FileSystem'


class EFSFileSystemTags(EFSBase):
    """
        AWS EFS File System Tags interface
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EFSBase.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        try:
            resource = \
                self.client.describe_tags(
                    {FILESYSTEM_ID: self.resource_id})
        except (ParamValidationError, ClientError):
            pass
        else:
            return [] if not resource else resource.get(TAGS, [])
        return None

    @property
    def status(self):
        """Gets the status of an external resource"""
        return None

    def create(self, params):
        """
            Create a new AWS EFS File System Tags.
        """
        return self.make_client_call('create_tags', params)

    def delete(self, params=None):
        """
            Deletes an existing AWS EFS File System Tags.
        """
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        self.client.delete_tags(**params)


@decorators.aws_resource(EFSFileSystemTags, RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS EFS File System Tags"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EFSFileSystemTags, RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    """Creates an AWS EFS File System Tags"""

    # Create a copy of the resource config for clean manipulation.
    params = \
        dict() if not resource_config else resource_config.copy()

    # Get the FILESYSTEM_ID from either params or a relationship.
    file_system_id = params.get(FILESYSTEM_ID)
    if not file_system_id:
        targ = utils.find_rel_by_node_type(
            ctx.instance,
            FILESYSTEM_TYPE
        )
        file_system_id = \
            targ.target.instance.runtime_properties.get(
                EXTERNAL_RESOURCE_ID
            )
        params[FILESYSTEM_ID] = file_system_id
    ctx.instance.runtime_properties[FILESYSTEM_ID] = file_system_id
    utils.update_resource_id(ctx.instance, file_system_id)

    # Actually create the resource
    iface.create(params)


@decorators.aws_resource(EFSFileSystemTags, RESOURCE_TYPE)
def delete(ctx, iface, resource_config, **_):
    """Deletes an AWS EFS File System Tags"""

    # Create a copy of the resource config for clean manipulation.
    params = \
        dict() if not resource_config else resource_config.copy()

    # Add the required FILESYSTEM_ID parameter.
    file_system_id = params.get(FILESYSTEM_ID)
    if not file_system_id:
        params[FILESYSTEM_ID] = \
            ctx.instance.runtime_properties.get(
                FILESYSTEM_ID, iface.resource_id)

    tags = params.pop(TAGS, {})
    params['TagKeys'] = [tag.get('Key') for tag in tags]

    # Actually delete the resource
    iface.delete(params)

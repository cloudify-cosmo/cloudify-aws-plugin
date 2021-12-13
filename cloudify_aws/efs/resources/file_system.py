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
    EFS.FileSystem
    ~~~~~~~~
    AWS EFS File System interface
"""
# Third Party imports
from botocore.exceptions import ClientError, ParamValidationError

# Local imports
from cloudify_aws.efs import EFSBase
from cloudify_aws.common._compat import text_type
from cloudify_aws.common import decorators, utils

RESOURCE_TYPE = 'EFS File System'
FILESYSTEM_ID = 'FileSystemId'
FILESYSTEMS = 'FileSystems'
CREATION_TOKEN = 'CreationToken'


class EFSFileSystem(EFSBase):
    """
        AWS EFS File System interface
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EFSBase.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        params = {FILESYSTEM_ID: self.resource_id}
        try:
            resources = \
                self.client.describe_file_systems(**params)
        except (ParamValidationError, ClientError):
            pass
        else:
            return resources.get(FILESYSTEMS, [None])[0]
        return None

    @property
    def status(self):
        """Gets the status of an external resource"""
        return None

    def create(self, params):
        """
            Create a new AWS EFS File System.
        """
        return self.make_client_call('create_file_system', params)

    def delete(self, params=None):
        """
            Deletes an existing AWS EFS File System.
        """
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        self.client.delete_file_system(**params)


@decorators.aws_resource(EFSFileSystem, RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS EFS File System"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EFSFileSystem, RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    """Creates an AWS EFS File System"""

    # Create a copy of the resource config for clean manipulation.
    params = \
        dict() if not resource_config else resource_config.copy()

    # The creation token is used by AWS to ensure idempotent fs creation.
    creation_token = \
        params.get(
            CREATION_TOKEN,
            ctx.instance.runtime_properties.get(CREATION_TOKEN))
    if not creation_token:
        creation_token = utils.get_uuid()
        ctx.instance.runtime_properties[CREATION_TOKEN] = \
            creation_token
        params[CREATION_TOKEN] = creation_token

    output = iface.create(params)
    utils.update_resource_id(ctx.instance, output.get(FILESYSTEM_ID))


@decorators.aws_resource(EFSFileSystem, RESOURCE_TYPE,
                         ignore_properties=True)
def delete(ctx, iface, resource_config, **_):
    """Deletes an AWS EFS File System"""

    # Create a copy of the resource config for clean manipulation.
    params = \
        dict() if not resource_config else resource_config.copy()
    file_system_id = params.get(FILESYSTEM_ID)
    if not file_system_id:
        params[FILESYSTEM_ID] = iface.resource_id

    # Actually delete the resource
    try:
        iface.delete(params)
    except ClientError as e:
        return ctx.operation.retry(text_type(e))

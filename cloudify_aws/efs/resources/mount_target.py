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
    EFS.MountTarget
    ~~~~~~~~
    AWS EFS Mount Target interface
"""
# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID
from cloudify_aws.efs import EFSBase
# Boto
from botocore.exceptions import ClientError

RESOURCE_TYPE = 'EFS Mount Target'
MOUNTTARGET_ID = 'MountTargetId'
FILESYSTEM_ID = 'FileSystemId'
FILESYSTEM_TYPE = 'cloudify.nodes.aws.efs.FileSystem'
SUBNET_ID = 'SubnetId'
SUBNET_TYPE = 'cloudify.nodes.aws.ec2.Subnet'
SUBNET_TYPE_DEPRECATED = 'cloudify.aws.nodes.Subnet'
SECGROUP_TYPE = 'cloudify.nodes.aws.ec2.SecurityGroup'
SECGROUP_TYPE_DEPRECATED = 'cloudify.aws.nodes.SecurityGroup'
SECGROUPS = 'SecurityGroups'
IP_ADDRESS = 'IpAddress'
NAT_ID = 'NetworkInterfaceId'


class EFSMountTarget(EFSBase):
    """
        AWS EFS Mount Target interface
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
                self.client.describe_mount_targets(**params)
        except ClientError:
            pass
        else:
            return resources.get(MOUNTTARGET_ID, [None])[0]
        return None

    @property
    def status(self):
        """Gets the status of an external resource"""
        return None

    def create(self, params):
        """
            Create a new AWS EFS Mount Target.
        """
        return self.make_client_call('create_mount_target', params)

    def delete(self, params=None):
        """
            Deletes an existing AWS EFS Mount Target.
        """
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        self.client.delete_mount_target(**params)


@decorators.aws_resource(EFSMountTarget, RESOURCE_TYPE, waits_for_status=False)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS EFS Mount Target"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EFSMountTarget, RESOURCE_TYPE, waits_for_status=False)
def create(ctx, iface, resource_config, **_):
    """Creates an AWS EFS Mount Target"""
    # Add File System ID
    file_system_id = resource_config.get(FILESYSTEM_ID)
    if not file_system_id:
        file_system = \
            utils.find_rel_by_node_type(
                ctx.instance,
                FILESYSTEM_TYPE)
        file_system_id = file_system.target.instance.runtime_properties[
            EXTERNAL_RESOURCE_ID]
        resource_config[FILESYSTEM_ID] = file_system_id

    # Add Subnet
    subnet_id = resource_config.get(SUBNET_ID)
    if not subnet_id:
        subnet = \
            utils.find_rel_by_node_type(
                ctx.instance,
                SUBNET_TYPE) or utils.find_rel_by_node_type(
                ctx.instance,
                SUBNET_TYPE_DEPRECATED)

        subnet_id = \
            subnet.target.instance.runtime_properties[EXTERNAL_RESOURCE_ID]
        resource_config[SUBNET_ID] = subnet_id

    # Add Security Groups
    secgroups_list = resource_config.get(SECGROUPS, [])
    resource_config[SECGROUPS] = \
        utils.add_resources_from_rels(
            ctx.instance,
            SECGROUP_TYPE,
            secgroups_list) or \
        utils.add_resources_from_rels(
            ctx.instance,
            SECGROUP_TYPE_DEPRECATED,
            secgroups_list)

    output = iface.create(resource_config)
    utils.update_resource_id(ctx.instance, output.get(MOUNTTARGET_ID))
    ctx.instance.runtime_properties[FILESYSTEM_ID] = output.get(FILESYSTEM_ID)
    ctx.instance.runtime_properties[SUBNET_ID] = output.get(SUBNET_ID)
    ctx.instance.runtime_properties[IP_ADDRESS] = output.get(IP_ADDRESS)
    ctx.instance.runtime_properties[NAT_ID] = output.get(NAT_ID)


@decorators.aws_resource(EFSMountTarget,
                         RESOURCE_TYPE,
                         ignore_properties=True,
                         waits_for_status=False)
def delete(iface, resource_config, **_):
    """Deletes an AWS EFS Mount Target"""
    mount_target_id = resource_config.get(MOUNTTARGET_ID)
    if not mount_target_id:
        resource_config[MOUNTTARGET_ID] = iface.resource_id

    # Actually delete the resource
    iface.delete(resource_config)

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

# Standard imports
import unittest

# Third party imports
from mock import patch, MagicMock

from cloudify.state import current_ctx

# Local imports
from cloudify_aws.efs.resources import mount_target
from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG
from cloudify_aws.common.tests.test_base import DELETE_RESPONSE


# Constants
MOUNT_TARGET_TH = ['cloudify.nodes.Root',
                   'cloudify.nodes.aws.efs.MountTarget']

NODE_PROPERTIES = {
    'use_external_resource': False,
    'resource_config': {
        'kwargs': {
            'AutoScalingGroupName': 'test-autoscaling1',
            'MinSize': '1',
            'MaxSize': '1',
            'DefaultCooldown': '300',
            'AvailabilityZones': ['aws_region']
        }
    },
    'client_config': CLIENT_CONFIG
}

RUNTIME_PROPERTIES_AFTER_CREATE = {
    'IpAddress': 'ip_id',
    'NetworkInterfaceId': 'nat_id',
    'resource_config': {},
    'FileSystemId': 'filesystem_id',
    'SubnetId': 'subnet_id',
    'aws_resource_id': 'mount_id'
}


class TestEFSMountTarget(TestBase):

    def setUp(self):
        super(TestEFSMountTarget, self).setUp()

        self.fake_boto, self.fake_client = self.fake_boto_client('efs')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None

        super(TestEFSMountTarget, self).tearDown()

    def test_prepare(self):
        self._prepare_check(
            type_hierarchy=MOUNT_TARGET_TH,
            type_name='efs',
            type_class=mount_target
        )

    def _prepare_context(self, runtime_prop=None):
        mock_subnet = MagicMock()
        mock_subnet.type_hierarchy = 'cloudify.relationships.depends_on'
        mock_subnet.target.instance.runtime_properties = {
            'aws_resource_id': 'aws_net_id'
        }
        mock_subnet.target.node.type_hierarchy = [
            'cloudify.nodes.Root',
            'cloudify.nodes.aws.ec2.Subnet'
        ]

        mock_group = MagicMock()
        mock_group.type_hierarchy = 'cloudify.relationships.depends_on'
        mock_group.target.instance.runtime_properties = {
            'aws_resource_id': 'aws_group_id'
        }
        mock_group.target.node.type_hierarchy = [
            'cloudify.nodes.Root',
            'cloudify.nodes.aws.ec2.SecurityGroup'
        ]

        mock_file_system = MagicMock()
        mock_file_system.type_hierarchy = 'cloudify.relationships.depends_on'
        mock_file_system.target.instance.runtime_properties = {
            'aws_resource_id': 'aws_file_id'
        }
        mock_file_system.target.node.type_hierarchy = [
            'cloudify.nodes.Root',
            'cloudify.nodes.aws.efs.FileSystem'
        ]

        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=runtime_prop if runtime_prop else {
                'resource_config': {}
            },
            type_hierarchy=MOUNT_TARGET_TH,
            test_relationships=[mock_subnet, mock_group, mock_file_system]
        )

        current_ctx.set(_ctx)
        return _ctx

    def test_create(self):
        _ctx = self._prepare_context()

        self.fake_client.create_mount_target = MagicMock(
            return_value={
                'MountTargetId': 'mount_id',
                'FileSystemId': 'filesystem_id',
                'SubnetId': 'subnet_id',
                'IpAddress': 'ip_id',
                'NetworkInterfaceId': 'nat_id'
            }
        )

        mount_target.create(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_called_with('efs', **CLIENT_CONFIG)

        self.fake_client.create_mount_target.assert_called_with(
            AutoScalingGroupName='test-autoscaling1',
            AvailabilityZones=['aws_region'],
            DefaultCooldown='300',
            FileSystemId='aws_file_id',
            MaxSize='1',
            MinSize='1',
            SecurityGroups=['aws_group_id'],
            SubnetId='aws_net_id'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_delete(self):
        _ctx = self._prepare_context(RUNTIME_PROPERTIES_AFTER_CREATE)

        self.fake_client.delete_mount_target = self.mock_return(
            DELETE_RESPONSE)

        mount_target.delete(ctx=_ctx, resource_config={}, iface=None)

        self.fake_boto.assert_called_with('efs', **CLIENT_CONFIG)

        self.fake_client.delete_mount_target.assert_called_with(
            MountTargetId='mount_id'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_EFSMountTarget_properties(self):
        test_instance = mount_target.EFSMountTarget(
            "ctx_node", resource_id='target_id', client=self.fake_client,
            logger=None
        )

        self.assertEqual(test_instance.properties, None)

    def test_EFSMountTarget_properties_NotEmpty(self):
        test_instance = mount_target.EFSMountTarget(
            "ctx_node", resource_id='target_id', client=self.fake_client,
            logger=None
        )

        self.fake_client.describe_mount_targets = MagicMock(
            return_value={
                'MountTargetId': ['Some_Target']
            }
        )

        self.assertEqual(test_instance.properties, 'Some_Target')

        self.fake_client.describe_mount_targets.assert_called_with(
            FileSystemId='target_id'
        )

    def test_EFSMountTarget_status(self):
        test_instance = mount_target.EFSMountTarget(
            "ctx_node", resource_id='target_id', client=self.fake_client,
            logger=None
        )

        self.assertEqual(test_instance.status, None)


if __name__ == '__main__':
    unittest.main()

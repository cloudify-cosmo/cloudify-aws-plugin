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
from mock import MagicMock, patch

from cloudify.state import current_ctx
from cloudify.exceptions import OperationRetry

# Local imports
from cloudify_aws.efs.resources import file_system
from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG
from cloudify_aws.common.tests.test_base import DELETE_RESPONSE


# Constants
FILE_SYSTEM_TH = ['cloudify.nodes.Root',
                  'cloudify.nodes.aws.efs.FileSystem']

NODE_PROPERTIES = {
    'use_external_resource': False,
    'resource_config': {},
    'client_config': CLIENT_CONFIG
}

RUNTIME_PROPERTIES_AFTER_CREATE = {
    'CreationToken': 'xxx-ccc',
    'aws_resource_id': 'fs_id',
    'resource_config': {}
}


class TestEFSFileSystem(TestBase):

    def setUp(self):
        super(TestEFSFileSystem, self).setUp()

        self.fake_boto, self.fake_client = self.fake_boto_client('efs')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None

        super(TestEFSFileSystem, self).tearDown()

    def test_prepare(self):
        self._prepare_check(
            type_hierarchy=FILE_SYSTEM_TH,
            type_name='efs',
            type_class=file_system
        )

    def test_create_raises_UnknownServiceError(self):
        self._prepare_create_raises_UnknownServiceError(
            type_hierarchy=FILE_SYSTEM_TH,
            type_name='efs',
            type_class=file_system
        )

    def _prepare_context(self, runtime_prop=None):
        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=runtime_prop if runtime_prop else {
                'resource_config': {}
            },
            type_hierarchy=FILE_SYSTEM_TH
        )

        current_ctx.set(_ctx)
        return _ctx

    def test_create(self):
        _ctx = self._prepare_context()

        self.fake_client.create_file_system = MagicMock(
            return_value={
                'FileSystemId': 'fs_id'
            }
        )

        with patch(
            'cloudify_aws.common.utils.get_uuid',
            MagicMock(return_value="xxx-ccc")
        ):
            file_system.create(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_called_with('efs', **CLIENT_CONFIG)

        self.fake_client.create_file_system.assert_called_with(
            CreationToken='xxx-ccc'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_delete(self):
        _ctx = self._prepare_context(RUNTIME_PROPERTIES_AFTER_CREATE)

        self.fake_client.delete_file_system = self.mock_return(DELETE_RESPONSE)

        file_system.delete(ctx=_ctx, resource_config={}, iface=None)

        self.fake_boto.assert_called_with('efs', **CLIENT_CONFIG)

        self.fake_client.delete_file_system.assert_called_with(
            FileSystemId='fs_id'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_delete_client_error(self):
        _ctx = self._prepare_context(RUNTIME_PROPERTIES_AFTER_CREATE)

        self.fake_client.delete_file_system = self._gen_client_error(
            "delete_file_system"
        )

        _ctx.operation.retry = MagicMock(return_value="Retry")

        self.assertRaises(
            OperationRetry,
            file_system.delete,
            ctx=_ctx,
            resource_config={},
            iface=None)

        self.fake_boto.assert_called_with('efs', **CLIENT_CONFIG)

        self.fake_client.delete_file_system.assert_called_with(
            FileSystemId='fs_id'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_EFSFileSystem_properties(self):
        test_instance = file_system.EFSFileSystem(
            "ctx_node", resource_id='fs_id', client=self.fake_client,
            logger=None
        )

        self.assertEqual(test_instance.properties, None)

    def test_EFSFileSystem_properties_NotEmpty(self):
        test_instance = file_system.EFSFileSystem(
            "ctx_node", resource_id='fs_id', client=self.fake_client,
            logger=None
        )

        self.fake_client.describe_file_systems = MagicMock(
            return_value={
                'FileSystems': ['Some_FileSystem']
            }
        )

        self.assertEqual(test_instance.properties, 'Some_FileSystem')

        self.fake_client.describe_file_systems.assert_called_with(
            FileSystemId='fs_id'
        )

    def test_EFSFileSystem_status(self):
        test_instance = file_system.EFSFileSystem(
            "ctx_node", resource_id='fs_id', client=self.fake_client,
            logger=None
        )

        self.assertEqual(test_instance.status, None)


if __name__ == '__main__':
    unittest.main()

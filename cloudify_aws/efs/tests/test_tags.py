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

# Local imports
from cloudify_aws.efs.resources import tags
from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG
from cloudify_aws.common.tests.test_base import DELETE_RESPONSE


# Constants
TAGS_TH = ['cloudify.nodes.Root',
           'cloudify.nodes.aws.efs.FileSystemTags']

NODE_PROPERTIES = {
    'use_external_resource': False,
    'resource_config': {
        'Tags': [{
            'Key': 'Name',
            'Value': 'file_system_tags'
        }]
    },
    'client_config': CLIENT_CONFIG
}

RUNTIME_PROPERTIES_AFTER_CREATE = {
    'resource_config': {},
    'FileSystemId': 'aws_net_id',
    'aws_resource_id': 'aws_net_id'
}


class TestEFSFileSystemTagsTags(TestBase):

    def setUp(self):
        super(TestEFSFileSystemTagsTags, self).setUp()

        self.fake_boto, self.fake_client = self.fake_boto_client('efs')
        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None

        super(TestEFSFileSystemTagsTags, self).tearDown()

    def test_prepare(self):
        self._prepare_check(
            type_hierarchy=TAGS_TH,
            type_name='efs',
            type_class=tags
        )

    def _prepare_context(self, runtime_prop=None):
        mock_fs = MagicMock()
        mock_fs.type_hierarchy = 'cloudify.relationships.depends_on'
        mock_fs.target.instance.runtime_properties = {
            'aws_resource_id': 'aws_net_id'
        }
        mock_fs.target.node.type_hierarchy = [
            'cloudify.nodes.Root',
            'cloudify.nodes.aws.efs.FileSystem'
        ]

        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=runtime_prop if runtime_prop else {
                'resource_config': {}
            },
            type_hierarchy=TAGS_TH,
            test_relationships=[mock_fs]
        )

        current_ctx.set(_ctx)
        return _ctx

    def test_create(self):
        _ctx = self._prepare_context()

        self.fake_client.create_tags = MagicMock(
            return_value={}
        )

        tags.create(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_called_with('efs', **CLIENT_CONFIG)

        self.fake_client.create_tags.assert_called_with(
            FileSystemId='aws_net_id',
            Tags=[{'Key': 'Name', 'Value': 'file_system_tags'}]
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_delete(self):
        _ctx = self._prepare_context(RUNTIME_PROPERTIES_AFTER_CREATE)

        self.fake_client.delete_tags = self.mock_return(DELETE_RESPONSE)

        tags.delete(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_called_with('efs', **CLIENT_CONFIG)

        self.fake_client.delete_tags.assert_called_with(
            FileSystemId='aws_net_id', TagKeys=['Name']
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_EFSFileSystemTags_properties(self):
        test_instance = tags.EFSFileSystemTags(
            "ctx_node", resource_id='fs_tags_id', client=self.fake_client,
            logger=None
        )

        self.assertEqual(test_instance.properties, None)

    def test_EFSFileSystemTags_properties_NotEmpty(self):
        test_instance = tags.EFSFileSystemTags(
            "ctx_node", resource_id='fs_tags_id', client=self.fake_client,
            logger=None
        )

        self.fake_client.describe_tags = MagicMock(
            return_value={
                'Tags': ['Some_Tags']
            }
        )

        self.assertEqual(test_instance.properties, ['Some_Tags'])

        self.fake_client.describe_tags.assert_called_with(
            {'FileSystemId': 'fs_tags_id'}
        )

    def test_EFSFileSystemTags_status(self):
        test_instance = tags.EFSFileSystemTags(
            "ctx_node", resource_id='fs_tags_id', client=self.fake_client,
            logger=None
        )

        self.assertEqual(test_instance.status, None)


if __name__ == '__main__':
    unittest.main()

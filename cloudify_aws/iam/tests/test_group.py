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
from cloudify_aws.iam.resources import group
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID
from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG
from cloudify_aws.common.tests.test_base import DELETE_RESPONSE
from cloudify_aws.common.tests.test_base import DEFAULT_RUNTIME_PROPERTIES


# Constants
GROUP_TH = ['cloudify.nodes.Root',
            'cloudify.nodes.aws.iam.Group']

NODE_PROPERTIES = {
    'resource_id': "group_name_id",
    'use_external_resource': False,
    'resource_config': {
        'kwargs': {
            'Path': 'some_path'
        }
    },
    'client_config': CLIENT_CONFIG
}

RUNTIME_PROPERTIES_AFTER_CREATE = {
    'aws_resource_arn': 'arn_id',
    'aws_resource_id': 'group_name_id',
    'resource_config': {}
}
ctx_node = MagicMock(
    properties=NODE_PROPERTIES,
    plugin=MagicMock(properties={})
)


@patch('cloudify_common_sdk.utils.ctx_from_import')
@patch('cloudify_aws.common.connection.Boto3Connection.get_account_id')
class TestIAMGroup(TestBase):

    def setUp(self):
        super(TestIAMGroup, self).setUp()

        self.fake_boto, self.fake_client = self.fake_boto_client('iam')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None

        super(TestIAMGroup, self).tearDown()

    def test_create_raises_UnknownServiceError(self, *_):
        fake_boto = self._prepare_create_raises_UnknownServiceError(
            type_hierarchy=GROUP_TH,
            type_name='iam',
            type_class=group
        )
        fake_boto.assert_called_with(
            'iam',
            aws_access_key_id='xxx',
            aws_secret_access_key='yyy',
            region_name='aq-testzone-1')

    def test_create(self, *_):
        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=DEFAULT_RUNTIME_PROPERTIES,
            type_hierarchy=GROUP_TH
        )

        current_ctx.set(_ctx)
        del _ctx.instance.runtime_properties[EXTERNAL_RESOURCE_ID]

        self.fake_client.create_group = MagicMock(return_value={
            'Group': {
                'GroupName': "group_name_id",
                'Arn': 'arn_id'
            }
        })

        group.create(ctx=_ctx, resource_config=None, iface=None, params=None)

        self.fake_boto.assert_called_with(
            'iam',
            aws_access_key_id='xxx',
            aws_secret_access_key='yyy',
            region_name='aq-testzone-1')

        self.fake_client.create_group.assert_called_with(
            GroupName='group_name_id', Path='some_path'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_delete(self, _, mock_import_ctx, *__):
        _ctx = self.get_mock_ctx(
            'test_delete',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES_AFTER_CREATE,
            type_hierarchy=GROUP_TH,
            ctx_operation_name='cloudify.interfaces.lifecycle.delete'
        )

        current_ctx.set(_ctx)
        current_ctx.set(_ctx)
        mock_import_ctx.node = _ctx.node
        mock_import_ctx.instance = _ctx.instance
        mock_import_ctx.operation = _ctx.operation

        self.fake_client.delete_group = self.mock_return(DELETE_RESPONSE)

        group.delete(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_called_with(
            'iam',
            aws_access_key_id='xxx',
            aws_secret_access_key='yyy',
            region_name='aq-testzone-1')

        self.fake_client.delete_group.assert_called_with(
            GroupName='group_name_id'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            {
                '__deleted': True,
            }
        )

    def test_attach_to_User(self, *_):
        _source_ctx, _target_ctx, _ctx = self._create_common_relationships(
            'test_attach_to',
            GROUP_TH,
            ['cloudify.nodes.Root', 'cloudify.nodes.aws.iam.User']
        )
        current_ctx.set(_ctx)

        self.fake_client.add_user_to_group = MagicMock(return_value={})

        group.attach_to(
            ctx=_ctx, resource_config=None, iface=None
        )

        self.fake_client.add_user_to_group.assert_called_with(
            GroupName='aws_resource_mock_id',
            UserName='aws_target_mock_id'
        )

        self.assertEqual(
            _source_ctx.instance.runtime_properties, {
                '_set_changed': True,
                'aws_resource_id': 'aws_resource_mock_id',
                'resource_config': {},
                'resource_id': 'prepare_attach_source'
            }
        )

    def test_detach_from_User(self, *_):
        _source_ctx, _target_ctx, _ctx = self._create_common_relationships(
            'test_detach_from',
            GROUP_TH,
            ['cloudify.nodes.Root', 'cloudify.nodes.aws.iam.User']
        )
        current_ctx.set(_ctx)

        self.fake_client.remove_user_from_group = MagicMock(
            return_value={}
        )

        group.detach_from(
            ctx=_ctx, resource_config=None, iface=None
        )

        self.fake_client.remove_user_from_group.assert_called_with(
            GroupName='aws_resource_mock_id',
            UserName='aws_target_mock_id'
        )

        self.assertEqual(
            _source_ctx.instance.runtime_properties, {
                '_set_changed': True,
                'aws_resource_id': 'aws_resource_mock_id',
                'resource_config': {},
                'resource_id': 'prepare_attach_source'
            }
        )

    def test_detach_from_Policy(self, *_):
        _source_ctx, _target_ctx, _ctx = self._create_common_relationships(
            'test_detach_from',
            GROUP_TH,
            ['cloudify.nodes.Root', 'cloudify.nodes.aws.iam.Policy']
        )
        current_ctx.set(_ctx)

        self.fake_client.detach_group_policy = MagicMock(return_value={})

        group.detach_from(
            ctx=_ctx, resource_config=None, iface=None
        )

        self.fake_client.detach_group_policy.assert_called_with(
            GroupName='aws_resource_mock_id',
            PolicyArn='aws_resource_mock_arn'
        )

        self.assertEqual(
            _source_ctx.instance.runtime_properties, {
                '_set_changed': True,
                'aws_resource_id': 'aws_resource_mock_id',
                'resource_config': {},
                'resource_id': 'prepare_attach_source'
            }
        )

    def test_attach_to_Policy(self, *_):
        _source_ctx, _target_ctx, _ctx = self._create_common_relationships(
            'test_attach_to',
            GROUP_TH,
            ['cloudify.nodes.Root', 'cloudify.nodes.aws.iam.Policy']
        )
        current_ctx.set(_ctx)

        self.fake_client.attach_group_policy = MagicMock(return_value={})

        group.attach_to(
            ctx=_ctx, resource_config=None, iface=None
        )

        self.fake_client.attach_group_policy.assert_called_with(
            GroupName='aws_resource_mock_id',
            PolicyArn='aws_resource_mock_arn'
        )

        self.assertEqual(
            _source_ctx.instance.runtime_properties, {
                '_set_changed': True,
                'aws_resource_id': 'aws_resource_mock_id',
                'resource_config': {},
                'resource_id': 'prepare_attach_source'
            }
        )

    def test_IAMGroupClass_properties(self, *_):
        self.fake_client.get_group = MagicMock(return_value={
            'Group': {
                'GroupName': "group_name_id",
                'Arn': 'arn_id'
            }
        })

        test_instance = group.IAMGroup(ctx_node, resource_id='group_id',
                                       client=self.fake_client,
                                       logger=None)

        self.assertEqual(test_instance.properties, {
            'GroupName': "group_name_id",
            'Arn': 'arn_id'
        })

        self.fake_client.get_group.assert_called_with(
            GroupName='group_id'
        )

    def test_IAMGroupClass_status(self, *_):
        self.fake_client.get_group = MagicMock(return_value={
            'Group': {
                'GroupName': "group_name_id",
                'Arn': 'arn_id'
            }
        })

        test_instance = group.IAMGroup(ctx_node, resource_id='group_id',
                                       client=self.fake_client,
                                       logger=None)

        self.assertEqual(test_instance.status, 'available')

        self.fake_client.get_group.assert_called_with(
            GroupName='group_id'
        )


if __name__ == '__main__':
    unittest.main()

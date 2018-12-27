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

from mock import patch, MagicMock
import unittest

from cloudify.state import current_ctx

from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG

from cloudify_aws.iam.resources import instance_profile

INSTANCE_PROFILE_TH = ['cloudify.nodes.Root',
                       'cloudify.nodes.aws.iam.InstanceProfile']

NODE_PROPERTIES = {
    'use_external_resource': False,
    'resource_config': {
        'RoleName': "role"
    },
    'client_config': CLIENT_CONFIG
}


class TestIAMInstanceProfile(TestBase):

    def setUp(self):
        super(TestIAMInstanceProfile, self).setUp()

        self.fake_boto, self.fake_client = self.fake_boto_client('iam')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()
        self.instance_profile = \
            instance_profile.IAMInstanceProfile(
                "ctx_node",
                resource_id=True,
                client=MagicMock(),
                logger=None)

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None

        super(TestIAMInstanceProfile, self).tearDown()

    def test_class_properties(self):

        effect = \
            self.get_client_error_exception(name='IAM Instance Profile')
        self.instance_profile.client = self.make_client_function(
            'get_instance_profile',
            side_effect=effect)
        res = self.instance_profile.properties
        self.assertIsNone(res)

    def test_create(self):
        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties={},
            type_hierarchy=INSTANCE_PROFILE_TH
        )

        current_ctx.set(_ctx)

        self.fake_client.create_instance_profile = \
            MagicMock(
                return_value={
                    'InstanceProfile': {
                        'InstanceProfileName': "name",
                        'Arn': "arn"
                    }})

        instance_profile.create(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_called_with('iam', **CLIENT_CONFIG)

        self.assertEqual(
            _ctx.instance.runtime_properties,
            {'aws_resource_id': 'name',
             'aws_resource_arn': "arn",
             'RoleName': "role"}
        )

    def test_create_no_role(self):
        _ctx = self.get_mock_ctx(
            'test_create_no_role',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties={},
            type_hierarchy=INSTANCE_PROFILE_TH
        )

        current_ctx.set(_ctx)
        del _ctx.node.properties['resource_config']['RoleName']

        self.fake_client.create_instance_profile = \
            MagicMock(
                return_value={
                    'InstanceProfile': {
                        'InstanceProfileName': "name",
                        'Arn': "arn"
                    }})

        instance_profile.create(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_called_with('iam', **CLIENT_CONFIG)

        self.assertEqual(
            _ctx.instance.runtime_properties,
            {'aws_resource_id': 'name',
             'aws_resource_arn': "arn"}
        )

    def test_delete(self):
        _ctx = self.get_mock_ctx(
            'test_delete',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties={},
            type_hierarchy=INSTANCE_PROFILE_TH
        )

        current_ctx.set(_ctx)
        del _ctx.node.properties['resource_config']['RoleName']

        self.fake_client.delete_instance_profile = \
            MagicMock()

        instance_profile.delete(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_called_with('iam', **CLIENT_CONFIG)

        self.assertEqual(_ctx.instance.runtime_properties, {})


if __name__ == '__main__':
    unittest.main()

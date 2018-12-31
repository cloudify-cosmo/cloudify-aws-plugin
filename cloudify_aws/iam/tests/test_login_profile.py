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

from cloudify_aws.iam.resources import login_profile


# Constants
LOGIN_PROFILE_TH = ['cloudify.nodes.Root',
                    'cloudify.nodes.aws.iam.LoginProfile']

NODE_PROPERTIES = {
    'use_external_resource': False,
    'resource_config': {},
    'client_config': CLIENT_CONFIG
}


class TestIAMLoginProfile(TestBase):

    def setUp(self):
        super(TestIAMLoginProfile, self).setUp()

        self.fake_boto, self.fake_client = self.fake_boto_client('iam')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None

        super(TestIAMLoginProfile, self).tearDown()

    def test_configure(self):
        self._prepare_configure(
            type_hierarchy=LOGIN_PROFILE_TH,
            type_name='iam',
            type_class=login_profile)

    def test_attach_to_User(self):
        _source_ctx, _target_ctx, _ctx = self._create_common_relationships(
            'test_attach_to',
            LOGIN_PROFILE_TH,
            ['cloudify.nodes.Root', 'cloudify.nodes.aws.iam.User']
        )
        current_ctx.set(_ctx)

        self.fake_client.create_login_profile = MagicMock(return_value={})

        login_profile.attach_to(
            ctx=_ctx, resource_config=None, iface=None
        )

        self.fake_client.create_login_profile.assert_called_with(
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

    def test_detach_from_User(self):
        _source_ctx, _target_ctx, _ctx = self._create_common_relationships(
            'test_detach_from',
            LOGIN_PROFILE_TH,
            ['cloudify.nodes.Root', 'cloudify.nodes.aws.iam.User']
        )
        current_ctx.set(_ctx)

        self.fake_client.delete_login_profile = MagicMock(return_value={})

        login_profile.detach_from(
            ctx=_ctx, resource_config=None, iface=None
        )

        self.fake_client.delete_login_profile.assert_called_with(
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


if __name__ == '__main__':
    unittest.main()
